"""
Admin — barcha bot foydalanuvchilariga (o'z mijozlariga) 1 martada
xabar yuborish (matn, rasm, video, fayl — istalgani)
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from utils.keyboards import admin_main_menu, save_cancel_keyboard
import config

router = Router()
logger = logging.getLogger(__name__)


class BroadcastStates(StatesGroup):
    waiting_content = State()


@router.message(F.text == "📢 Hammaga xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    await state.set_state(BroadcastStates.waiting_content)
    await message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni jo'nating.\n\n"
        "✏️ Matn, 🖼 rasm, 🎬 video, 📎 fayl — istalgan turdagi "
        "xabarni yuborishingiz mumkin."
    )


@router.message(BroadcastStates.waiting_content)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(
        chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await message.answer(
        "⬆️ Yuqoridagi xabar shu ko'rinishda barcha foydalanuvchilarga "
        "yuboriladi. Tasdiqlaysizmi?",
        reply_markup=save_cancel_keyboard("bcast:send", "bcast:cancel")
    )


@router.callback_query(F.data == "bcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "bcast:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext,
                          db: AsyncSession, bot: Bot):
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_text("⏳ Yuborilmoqda...")

    users = await crud.get_all_users(db)
    sent, failed = 0, 0

    for user in users:
        try:
            await bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=data["chat_id"],
                message_id=data["message_id"],
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast xato user {user.telegram_id}: {e}")
        await asyncio.sleep(0.05)

    await callback.message.answer(
        f"✅ Yuborildi: {sent} ta\n"
        f"❌ Yetkazilmadi: {failed} ta (bot bilan suhbatni bloklagan)",
        reply_markup=admin_main_menu()
    )
    await callback.answer()
