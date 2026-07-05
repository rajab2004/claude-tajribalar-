"""
E'lon yaratish va boshqarish
— xabarlar foydalanuvchi ulagan Telegram akkauntidan yuboriladi
— bot nomidan EMAS
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.connection import AsyncSessionLocal
from services.pyrogram_client import get_client, send_to_channel
from utils.keyboards import (
    user_main_menu, announcements_menu,
    close_announcement_keyboard,
    save_cancel_keyboard
)
from utils.helpers import truncate
import config

router = Router()
logger = logging.getLogger(__name__)


class AnnouncementStates(StatesGroup):
    waiting_text = State()


# ─── Yangi e'lon yaratish ──────────────────────────────────────────────
@router.message(F.text == "📝 Yangi e'lon yaratish")
async def new_announcement_start(message: Message, state: FSMContext,
                                  db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await message.answer("❌ Avval tizimga kiring.")
        return

    # Foydalanuvchi Telegram akkauntini ulagan?
    sess = await crud.get_session(db, user.id)
    if not sess:
        await message.answer(
            "❌ Telegram akkauntingiz ulanmagan!\n\n"
            "📱 Avval '📱 Telegram akkauntni ulash' bo'limiga o'ting.\n"
            "Akkaunt ulanganidan keyin xabarlar sizning akkauntingizdan yuboriladi."
        )
        return

    channels = await crud.get_user_channels(db, user.id)
    if not channels:
        await message.answer(
            "❌ Hech qanday guruh/kanal qo'shilmagan!\n"
            "📢 Avval '📢 Guruh va kanallar' bo'limidan qo'shing."
        )
        return

    await state.set_state(AnnouncementStates.waiting_text)
    await message.answer(
        f"📝 E'lon matnini yozing:\n\n"
        f"📊 {len(channels)} ta guruh/kanalga sizning akkauntingizdan yuboriladi\n"
        f"⏱ Interval: {user.interval_minutes} daqiqa"
    )


@router.message(AnnouncementStates.waiting_text)
async def announcement_text(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("❌ E'lon matni bo'sh bo'lishi mumkin emas!")
        return

    await state.update_data(text=text)
    kb = save_cancel_keyboard("ann:send", "ann:cancel")
    await message.answer(
        f"📋 E'lon ko'rinishi:\n"
        f"{'─' * 30}\n"
        f"{text}\n"
        f"{'─' * 30}\n\n"
        f"✅ Yuborasizmi?",
        reply_markup=kb
    )


@router.callback_query(F.data == "ann:cancel")
async def cancel_announcement(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ E'lon bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "ann:send")
async def send_announcement(callback: CallbackQuery, state: FSMContext,
                             db: AsyncSession, bot: Bot):
    data = await state.get_data()
    text = data.get("text", "")
    tg_id = callback.from_user.id

    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    await callback.message.edit_text("⏳ Yuborilmoqda...")
    await state.clear()

    # E'lon bazaga saqlanadi
    ann = await crud.create_announcement(db, user.id, text, user.interval_minutes)
    await db.commit()

    # Bot chatida e'lon kartasi — "Yuk ochiq" + Yopish tugmasi
    sent_msg = await bot.send_message(
        tg_id,
        f"📦 <b>Yuk ochiq</b>\n\n{text}",
        reply_markup=close_announcement_keyboard(ann.id),
        parse_mode="HTML"
    )
    await crud.save_announcement_message_id(db, ann.id, sent_msg.message_id)
    await db.commit()

    # Fon vazifasi — guruh/kanallarga foydalanuvchi akkauntidan yuborish
    user_data = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "interval_minutes": user.interval_minutes,
    }
    asyncio.create_task(
        _send_from_user_account(bot, user_data, ann.id, text)
    )

    await callback.message.edit_text("✅ E'lon yaratildi!")
    await bot.send_message(
        tg_id,
        "🏠 Bosh menyu:",
        reply_markup=user_main_menu()
    )


async def _send_from_user_account(bot: Bot, user_data: dict,
                                   ann_id: int, text: str):
    """
    Foydalanuvchi ulagan Telegram akkauntidan guruh/kanallarga yuboradi.
    Bot nomidan EMAS — foydalanuvchi o'z akkauntidan yozadi.
    """
    async with AsyncSessionLocal() as db:
        try:
            user_id = user_data["id"]
            tg_id = user_data["telegram_id"]

            # Foydalanuvchi session (Telegram akkaunt)
            sess_str = await crud.get_session(db, user_id)
            if not sess_str:
                logger.warning(f"User {user_id}: session topilmadi")
                await bot.send_message(
                    tg_id,
                    "❌ Telegram akkauntingiz ulanmagan! E'lon yuborilmadi."
                )
                return

            # Foydalanuvchi akkauntining Pyrogram clienti
            client = await get_client(user_id, sess_str)
            if not client:
                logger.error(f"User {user_id}: Pyrogram client yaratilmadi")
                await bot.send_message(
                    tg_id,
                    "❌ Telegram akkauntga ulanib bo'lmadi. "
                    "Sozlamalardan qayta ulang."
                )
                return

            # Guruh/kanallar ro'yhati
            channels = await crud.get_user_channels(db, user_id)
            if not channels:
                return

            sent_count = 0
            failed_count = 0
            failed_ch_ids = []

            # Har bir guruh/kanalga foydalanuvchi akkauntidan yuborish
            for ch in channels:
                success, reason = await send_to_channel(client, ch.link, text)

                if success:
                    sent_count += 1
                    await crud.add_send_log(db, ann_id, ch.id, True)
                    logger.info(
                        f"✅ User {user_id} akkauntidan {ch.link} ga yuborildi"
                    )
                else:
                    failed_count += 1
                    failed_ch_ids.append(ch.id)
                    await crud.add_send_log(db, ann_id, ch.id, False, reason)
                    logger.warning(
                        f"❌ User {user_id} — {ch.link}: {reason}"
                    )

                # Flood limit oldini olish
                await asyncio.sleep(config.SESSION_SEND_DELAY)

            # Kirish imkoni yo'q kanallarni o'chirish
            for ch_id in failed_ch_ids:
                await crud.deactivate_channel(db, ch_id)

            await crud.update_last_sent(db, ann_id)
            await db.commit()

            # Natija xabari
            msg_parts = [f"📊 <b>Yuborish natijasi:</b>"]
            msg_parts.append(f"✅ {sent_count} ta guruhga yetkazildi")
            if failed_count > 0:
                msg_parts.append(
                    f"❌ {failed_count} ta guruh o'chirildi "
                    f"(akkauntingiz a'zo emas yoki yozish huquqi yo'q)"
                )
            await bot.send_message(tg_id, "\n".join(msg_parts),
                                   parse_mode="HTML")

        except Exception as e:
            logger.error(f"_send_from_user_account xatosi: {e}")
            try:
                await db.rollback()
            except Exception:
                pass


# ─── E'lon yopish ──────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("ann:close:"))
async def close_announcement_cb(callback: CallbackQuery, db: AsyncSession):
    ann_id = int(callback.data.split(":")[2])
    tg_id = callback.from_user.id

    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    ann = await crud.get_announcement_by_id(db, ann_id)
    if not ann or ann.user_id != user.id:
        await callback.answer("❌ E'lon topilmadi!", show_alert=True)
        return

    await crud.close_announcement(db, ann_id)
    await db.commit()

    # Bot chatidagi xabarni tahrirlash
    try:
        original = callback.message.text or ""
        new_text = original.replace("📦 Yuk ochiq", "🔒 Yuk yopildi")
        if new_text == original:
            new_text = "🔒 Yuk yopildi\n\n" + original
        await callback.message.edit_text(new_text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Xabarni tahrirlashda xato: {e}")

    await callback.answer("✅ E'lon yopildi! Yuborish to'xtatildi.")


# ─── Mening e'lonlarim ─────────────────────────────────────────────────
@router.message(F.text == "📋 Mening e'lonlarim")
async def my_announcements(message: Message, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        return
    await message.answer("📋 E'lonlarim:", reply_markup=announcements_menu())


@router.message(F.text == "📢 Ochiq e'lonlarim")
async def open_announcements(message: Message, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        return

    anns = await crud.get_user_open_announcements(db, user.id)
    if not anns:
        await message.answer(
            "📭 Hozirda ochiq e'lonlar yo'q.",
            reply_markup=announcements_menu()
        )
        return

    for ann in anns:
        await message.answer(
            f"📢 E'lon #{ann.id}\n"
            f"📝 {truncate(ann.message_text, 100)}\n"
            f"⏱ Har {ann.interval_minutes} daqiqada yuboriladi\n"
            f"📅 {ann.created_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=close_announcement_keyboard(ann.id)
        )

    await message.answer(
        f"📊 Jami {len(anns)} ta ochiq e'lon",
        reply_markup=announcements_menu()
    )


@router.message(F.text == "🔒 Yopilgan e'lonlarim")
async def closed_announcements(message: Message, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        return

    anns = await crud.get_user_closed_announcements(db, user.id)
    if not anns:
        await message.answer(
            "📭 Yopilgan e'lonlar yo'q.",
            reply_markup=announcements_menu()
        )
        return

    for ann in anns:
        closed_time = (ann.closed_at.strftime('%d.%m.%Y %H:%M')
                       if ann.closed_at else "—")
        await message.answer(
            f"🔒 E'lon #{ann.id}\n"
            f"📝 {truncate(ann.message_text, 100)}\n"
            f"🕐 Yopilgan: {closed_time}"
        )

    await message.answer(
        f"📊 Jami {len(anns)} ta yopilgan e'lon\n"
        f"⚠️ Bugun yarim tunda avtomatik o'chiriladi",
        reply_markup=announcements_menu()
    )
