"""
Foydalanuvchi sozlamalari
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from utils.keyboards import (
    user_main_menu, settings_keyboard,
    interval_keyboard, confirm_keyboard
)
from utils.helpers import format_expiry
import config

router = Router()


@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await message.answer("❌ Avval tizimga kiring.")
        return

    sess = await crud.get_session(db, user.id)
    conn_status = "✅ Ulangan" if sess else "❌ Ulanmagan"

    await message.answer(
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"📱 Akkaunt: {conn_status}\n"
        f"📅 Muddat: {format_expiry(user.expires_at)}\n"
        f"⏱ Yuborish intervali: {user.interval_minutes} daqiqa",
        reply_markup=settings_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "settings:interval")
async def change_interval(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏱ Yuborish intervalini tanlang:",
        reply_markup=interval_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("interval:"))
async def set_interval(callback: CallbackQuery, db: AsyncSession):
    minutes = int(callback.data.split(":")[1])
    tg_id = callback.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    await crud.update_user_interval(db, user.id, minutes)
    await db.commit()

    await callback.message.edit_text(
        f"✅ Yuborish intervali {minutes} daqiqaga o'rnatildi!"
    )
    await callback.answer()


@router.callback_query(F.data == "settings:disconnect")
async def disconnect_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Telegram akkauntingizni uzmoqchimisiz?\n\n"
        "Barcha ochiq e'lonlar avtomatik yopiladi!",
        reply_markup=confirm_keyboard("disconnect:yes", "disconnect:no")
    )
    await callback.answer()


@router.callback_query(F.data == "disconnect:yes")
async def disconnect_account(callback: CallbackQuery, db: AsyncSession):
    tg_id = callback.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    from services.pyrogram_client import disconnect_client
    await disconnect_client(user.id)
    await crud.disconnect_session(db, user.id)
    await crud.close_all_user_announcements(db, user.id)
    await db.commit()

    await callback.message.edit_text(
        "✅ Telegram akkauntingiz uzildi.\n"
        "Barcha ochiq e'lonlar yopildi."
    )
    await callback.answer()


@router.callback_query(F.data == "disconnect:no")
async def disconnect_cancel(callback: CallbackQuery):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=user_main_menu())
    await callback.answer()


@router.message(F.text == "📞 Admin bilan bog'lanish")
async def admin_contact(message: Message):
    await message.answer(
        f"📞 Admin bilan bog'lanish:\n\n"
        f"☎️ Telefon: {config.ADMIN_PHONE}\n"
        f"💬 Telegram: @{config.ADMIN_USERNAME}"
    )
