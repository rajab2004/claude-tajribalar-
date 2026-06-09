from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_user_by_telegram_id,
    increment_user_wrong_attempts,
    reset_user_wrong_attempts,
    get_first_admin,
)
from utils.password_generator import verify_password
from utils.keyboards import get_user_main_menu, get_start_keyboard
from utils.helpers import clear_state, is_expired, format_date
from handlers.user.states import UserAuthStates

router = Router()

MAX_ATTEMPTS = 10


# ============================================================
# KIRISH JARAYONI
# ============================================================

@router.message(F.text == "👤 Foydalanuvchi sifatida kirish")
async def user_login_start(message: Message, state: FSMContext, session: AsyncSession):
    """Foydalanuvchi kirish tugmasi bosildi"""
    # Allaqachon login bo'lganmi?
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user and user.is_active and not is_expired(user.expires_at):
        await state.update_data(user_id=user.id, telegram_id=user.telegram_id)
        await message.answer(
            "✅ Siz allaqachon kirgansiz!",
            reply_markup=get_user_main_menu()
        )
        return

    await state.set_state(UserAuthStates.waiting_password)
    await message.answer(
        "🔑 <b>Parolingizni kiriting:</b>",
        reply_markup=__import__("aiogram").types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


@router.message(UserAuthStates.waiting_password)
async def user_login_password(message: Message, state: FSMContext, session: AsyncSession):
    """Foydalanuvchi parolni kiritdi"""
    telegram_id = message.from_user.id
    password = message.text.strip() if message.text else ""

    # Foydalanuvchini topish
    user = await get_user_by_telegram_id(session, telegram_id)

    if not user:
        await message.answer(
            "❌ <b>Sizning Telegram ID bazada topilmadi.</b>\n"
            "Admin bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
        await clear_state(state)
        return

    # Bloklangan (10 ta urinish)
    if user.wrong_attempts >= MAX_ATTEMPTS:
        admin = await get_first_admin(session)
        admin_info = ""
        if admin:
            admin_info = f"\n📞 {admin.phone or 'N/A'}\n💬 @{admin.username or 'N/A'}"
        await message.answer(
            f"🚫 <b>Parol {MAX_ATTEMPTS} marta noto'g'ri kiritildi.</b>\n"
            f"Admin bilan bog'laning:{admin_info}",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
        await clear_state(state)
        return

    # Parol tekshiruvi
    if not verify_password(password, user.password_hash):
        attempts = await increment_user_wrong_attempts(session, telegram_id)
        remaining = MAX_ATTEMPTS - attempts

        if remaining <= 0:
            admin = await get_first_admin(session)
            admin_info = ""
            if admin:
                admin_info = f"\n📞 {admin.phone or 'N/A'}\n💬 @{admin.username or 'N/A'}"
            await message.answer(
                f"🚫 <b>Parol {MAX_ATTEMPTS} marta noto'g'ri kiritildi.</b>\n"
                f"Admin bilan bog'laning:{admin_info}",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            await clear_state(state)
        else:
            await message.answer(
                f"❌ <b>Parol noto'g'ri!</b>\n"
                f"Qolgan urinishlar: <b>{remaining}</b> ta",
                parse_mode="HTML"
            )
        return

    # Muddat tekshiruvi
    if is_expired(user.expires_at):
        admin = await get_first_admin(session)
        admin_info = ""
        if admin:
            admin_info = f"\n📞 {admin.phone or 'N/A'}\n💬 @{admin.username or 'N/A'}"
        await message.answer(
            f"⏰ <b>Botdan foydalanish muddatingiz tugagan.</b>\n"
            f"Davom etish uchun admin bilan bog'laning:{admin_info}",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
        await clear_state(state)
        return

    # Aktiv emas
    if not user.is_active:
        await message.answer(
            "🚫 <b>Akkauntingiz bloklangan.</b>\n"
            "Admin bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
        await clear_state(state)
        return

    # Muvaffaqiyatli kirish
    await reset_user_wrong_attempts(session, telegram_id)
    await state.update_data(user_id=user.id, telegram_id=user.telegram_id)
    await state.set_state(None)

    expires_str = format_date(user.expires_at)
    await message.answer(
        f"✅ <b>Muvaffaqiyatli kirdingiz!</b>\n"
        f"📅 Muddat: <b>{expires_str}</b> gacha",
        parse_mode="HTML",
        reply_markup=get_user_main_menu()
    )
    logger.info(f"Foydalanuvchi kirdi: telegram_id={telegram_id}")


# ============================================================
# BOSH MENYU
# ============================================================

@router.message(F.text == "🏠 Bosh menyuga qaytish")
async def go_home(message: Message, state: FSMContext, session: AsyncSession):
    """Bosh menyuga qaytish"""
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user or is_expired(user.expires_at) or not user.is_active:
        await clear_state(state)
        await message.answer(
            "⚠️ Davom etish uchun avval kiring.",
            reply_markup=get_start_keyboard()
        )
        return
    await message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=get_user_main_menu(),
        parse_mode="HTML"
    )
