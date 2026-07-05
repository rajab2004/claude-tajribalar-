"""
Fonga ishlaydigan vazifalar:
1. E'lonlarni foydalanuvchi akkauntidan yuborish (bot emas)
2. Muddati tugagan foydalanuvchilarni tekshirish
3. Yopilgan e'lonlarni o'chirish
"""
import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.connection import AsyncSessionLocal
from database import crud
import config
from services.pyrogram_client import get_client, send_to_channel

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)


async def send_announcements(bot: Bot):
    """
    Har daqiqada ishga tushadi.
    Vaqti kelgan e'lonlarni foydalanuvchi akkauntidan yuboradi.
    (Bot nomidan EMAS — foydalanuvchi o'z akkauntidan yozadi)
    """
    async with AsyncSessionLocal() as db:
        try:
            announcements = await crud.get_open_announcements(db)
            now = datetime.utcnow()

            for ann in announcements:
                # Interval tekshiruvi
                if ann.last_sent_at:
                    elapsed = (now - ann.last_sent_at).total_seconds() / 60
                    if elapsed < ann.interval_minutes:
                        continue

                user = ann.user
                if not user or not user.is_active:
                    continue
                if user.expires_at < now:
                    continue

                # Foydalanuvchi Telegram session (akkaunt)
                sess_str = await crud.get_session(db, user.id)
                if not sess_str:
                    logger.warning(
                        f"User {user.id} sessionsiz — e'lon yuborilmadi"
                    )
                    continue

                # Foydalanuvchi akkauntining Pyrogram clienti
                client = await get_client(user.id, sess_str)
                if not client:
                    logger.error(
                        f"User {user.id} client xatosi — e'lon yuborilmadi"
                    )
                    continue

                channels = await crud.get_user_channels(db, user.id)
                if not channels:
                    continue

                sent_count = 0
                failed_count = 0
                failed_ch_ids = []

                # Foydalanuvchi akkauntidan har bir guruh/kanalga yuborish
                for ch in channels:
                    success, reason = await send_to_channel(
                        client, ch.link, ann.message_text
                    )
                    if success:
                        sent_count += 1
                        await crud.add_send_log(db, ann.id, ch.id, True)
                        logger.info(
                            f"✅ User {user.id} akkauntidan {ch.link} ga yuborildi"
                        )
                    else:
                        failed_count += 1
                        failed_ch_ids.append(ch.id)
                        await crud.add_send_log(db, ann.id, ch.id, False, reason)
                        logger.warning(
                            f"❌ {ch.link}: {reason}"
                        )

                    await asyncio.sleep(config.SESSION_SEND_DELAY)

                # Kirish imkoni yo'q kanallarni o'chirish
                for ch_id in failed_ch_ids:
                    await crud.deactivate_channel(db, ch_id)

                await crud.update_last_sent(db, ann.id)
                await db.commit()

                # Foydalanuvchiga natija
                if failed_count > 0:
                    await bot.send_message(
                        user.telegram_id,
                        f"📊 E'lon natijasi:\n"
                        f"✅ {sent_count} ta guruhga yetkazildi\n"
                        f"❌ {failed_count} ta guruh o'chirildi "
                        f"(akkauntingiz a'zo emas yoki yozish huquqi yo'q)"
                    )

        except Exception as e:
            logger.error(f"send_announcements xatosi: {e}")
            try:
                await db.rollback()
            except Exception:
                pass


async def check_expired_users(bot: Bot):
    """Har kecha 23:59 da ishga tushadi"""
    async with AsyncSessionLocal() as db:
        try:
            expired = await crud.get_expired_users(db)
            for user in expired:
                await crud.close_all_user_announcements(db, user.id)
                await crud.deactivate_user(db, user.id)
                await db.commit()

                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"⏰ Sizning bot ishlatish muddatingiz tugadi!\n\n"
                        f"Davom etish uchun admin bilan bog'laning:\n"
                        f"📞 {config.ADMIN_PHONE}\n"
                        f"💬 @{config.ADMIN_USERNAME}"
                    )
                except Exception:
                    pass

            logger.info(f"Muddati tugagan: {len(expired)} ta foydalanuvchi")
        except Exception as e:
            logger.error(f"check_expired_users xatosi: {e}")


async def delete_old_announcements():
    """Har kecha 00:00 da ishga tushadi"""
    async with AsyncSessionLocal() as db:
        try:
            await crud.delete_old_closed_announcements(db)
            await db.commit()
            logger.info("Eski yopilgan e'lonlar o'chirildi")
        except Exception as e:
            logger.error(f"delete_old_announcements xatosi: {e}")


def setup_scheduler(bot: Bot):
    scheduler.add_job(
        send_announcements,
        trigger="interval",
        minutes=1,
        args=[bot],
        id="send_announcements",
        replace_existing=True,
    )
    scheduler.add_job(
        check_expired_users,
        trigger=CronTrigger(hour=23, minute=59),
        args=[bot],
        id="check_expired",
        replace_existing=True,
    )
    scheduler.add_job(
        delete_old_announcements,
        trigger=CronTrigger(hour=0, minute=0),
        id="delete_old",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("✅ Scheduler ishga tushdi")
