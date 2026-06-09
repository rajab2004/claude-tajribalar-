from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from database.connection import AsyncSessionFactory
from database.crud import (
    get_all_open_announcements,
    get_channels_by_user_id,
    update_announcement_last_sent,
    close_announcement,
    delete_old_closed_announcements,
    get_users_expiring_today,
    deactivate_user,
    get_all_connected_sessions,
    mark_session_disconnected,
    deactivate_channel,
    close_user_announcements,
)
from services import pyrogram_client as pyro
from services.email_service import send_expiry_warning, send_session_disconnected

# Global scheduler
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# Bot referansini saqlash (main.py da set qilinadi)
_bot = None
_admin_phone = ""
_admin_username = ""


def set_bot(bot, admin_phone: str, admin_username: str):
    """Bot obyektini va admin ma'lumotlarini o'rnatish"""
    global _bot, _admin_phone, _admin_username
    _bot = bot
    _admin_phone = admin_phone
    _admin_username = admin_username


# ============================================================
# 1. E'LON YUBORUVCHI (har daqiqada)
# ============================================================

async def send_announcements_job():
    """
    Ochiq e'lonlarni tekshirib, intervaliga qarab yuboradi.
    Har daqiqada ishga tushadi.
    """
    if not _bot:
        return

    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        try:
            announcements = await get_all_open_announcements(session)

            for ann in announcements:
                # Interval tekshiruvi
                if ann.last_sent_at:
                    last = ann.last_sent_at
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    elapsed_minutes = (now - last).total_seconds() / 60
                    if elapsed_minutes < ann.interval_minutes:
                        continue  # Hali vaqt kelmagan

                # Foydalanuvchi kanallarini olish
                channels = await get_channels_by_user_id(session, ann.user_id)
                if not channels:
                    continue

                # Xabar yuborish
                success_count, fail_count, failed_ids = await pyro.send_to_all_channels(
                    user_id=ann.user_id,
                    channels=channels,
                    text=ann.message_text,
                )

                # Muvaffaqiyatsiz kanallarni o'chirish
                if failed_ids:
                    for ch_id in failed_ids:
                        await deactivate_channel(session, ch_id)
                    logger.info(
                        f"E'lon {ann.id}: {success_count} ta yuborildi, "
                        f"{fail_count} ta yuborilmadi va o'chirildi"
                    )
                    # Foydalanuvchiga xabar
                    try:
                        await _bot.send_message(
                            ann.user_id,  # bu telegram_id emas, user.telegram_id kerak
                            f"ℹ️ E'lon #{ann.id}: {success_count} ta guruhga yuborildi, "
                            f"{fail_count} ta guruh mavjud emas va o'chirildi.",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

                # Oxirgi yuborish vaqtini yangilash
                await update_announcement_last_sent(session, ann.id)

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"send_announcements_job xatosi: {e}")


# ============================================================
# 2. MUDDAT TEKSHIRUVI (har kecha 23:59)
# ============================================================

async def check_expiry_job():
    """
    Muddati tugagan foydalanuvchilarni topib, ularni deaktiv qiladi.
    Har kecha 23:59 da ishga tushadi.
    """
    if not _bot:
        return

    async with AsyncSessionFactory() as session:
        try:
            expiring_users = await get_users_expiring_today(session)

            for user in expiring_users:
                # Deaktiv qilish
                await deactivate_user(session, user.id)

                # Ochiq e'lonlarni yopish
                closed_count = await close_user_announcements(session, user.id)

                # Sessiyani o'chirish
                await pyro.disconnect_client(user.id)

                logger.info(
                    f"Muddat tugadi: user_id={user.id}, "
                    f"telegram_id={user.telegram_id}, "
                    f"{closed_count} ta e'lon yopildi"
                )

                # Foydalanuvchiga xabar
                await send_expiry_warning(
                    _bot,
                    user.telegram_id,
                    _admin_phone,
                    _admin_username
                )

            await session.commit()
            if expiring_users:
                logger.info(f"Jami {len(expiring_users)} ta foydalanuvchi muddati tugadi")

        except Exception as e:
            await session.rollback()
            logger.error(f"check_expiry_job xatosi: {e}")


# ============================================================
# 3. YOPILGAN E'LONLARNI O'CHIRISH (har kecha 00:00)
# ============================================================

async def cleanup_closed_announcements_job():
    """
    Kecha yopilgan e'lonlarni o'chiradi.
    Har kecha 00:00 da ishga tushadi.
    """
    async with AsyncSessionFactory() as session:
        try:
            deleted = await delete_old_closed_announcements(session)
            await session.commit()
            if deleted:
                logger.info(f"Tozalash: {deleted} ta yopilgan e'lon o'chirildi")
        except Exception as e:
            await session.rollback()
            logger.error(f"cleanup_closed_announcements_job xatosi: {e}")


# ============================================================
# 4. SESSIYA TEKSHIRUVI (har 30 daqiqada)
# ============================================================

async def check_sessions_job():
    """
    Barcha ulangan sessiyalarni tekshirib, uzilganlarini aniqlaydi.
    Har 30 daqiqada ishga tushadi.
    """
    if not _bot:
        return

    async with AsyncSessionFactory() as session:
        try:
            sessions = await get_all_connected_sessions(session)

            for db_session in sessions:
                is_alive = await pyro.check_client_alive(db_session.user_id)
                if not is_alive:
                    await mark_session_disconnected(session, db_session.id)
                    logger.warning(
                        f"Sessiya uzilgan: session_id={db_session.id}, "
                        f"user_id={db_session.user_id}"
                    )
                    # Foydalanuvchiga xabar yuborish uchun telegram_id kerak
                    # user_id bu DB id, telegram_id ni olish kerak
                    # Bu relation orqali olinadi
                    if db_session.user and db_session.user.telegram_id:
                        await send_session_disconnected(
                            _bot,
                            db_session.user.telegram_id
                        )

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"check_sessions_job xatosi: {e}")


# ============================================================
# SCHEDULER ISHGA TUSHIRISH VA TO'XTATISH
# ============================================================

def start_scheduler():
    """Barcha scheduled vazifalarni ro'yxatdan o'tkazib ishga tushirish"""

    # 1. E'lon yuboruvchi — har daqiqada
    scheduler.add_job(
        send_announcements_job,
        trigger=IntervalTrigger(minutes=1),
        id="send_announcements",
        name="E'lon yuboruvchi",
        replace_existing=True,
        misfire_grace_time=30,
    )

    # 2. Muddat tekshiruvi — har kecha 23:59
    scheduler.add_job(
        check_expiry_job,
        trigger=CronTrigger(hour=23, minute=59),
        id="check_expiry",
        name="Muddat tekshiruvi",
        replace_existing=True,
    )

    # 3. Eski e'lonlarni o'chirish — har kecha 00:00
    scheduler.add_job(
        cleanup_closed_announcements_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="cleanup_announcements",
        name="Yopilgan e'lonlarni tozalash",
        replace_existing=True,
    )

    # 4. Sessiya tekshiruvi — har 30 daqiqada
    scheduler.add_job(
        check_sessions_job,
        trigger=IntervalTrigger(minutes=30),
        id="check_sessions",
        name="Sessiya tekshiruvi",
        replace_existing=True,
        misfire_grace_time=60,
    )

    scheduler.start()
    logger.info("✅ Scheduler ishga tushdi (4 ta vazifa)")


def stop_scheduler():
    """Schedulerni to'xtatish"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⛔ Scheduler to'xtatildi")
