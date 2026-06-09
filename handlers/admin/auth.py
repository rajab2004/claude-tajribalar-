from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_admin_by_telegram_id,
    increment_admin_wrong_attempts,
    reset_admin_wrong_attempts,
)
from utils.password_generator import verify_password, generate_password, hash_password
from utils.keyboards import get_admin_main_menu, get_start_keyboard
from utils.helpers import clear_state
from services.email_service import send_admin_password_recovery
from handlers.admin.states import AdminAuthStates

router = Router()

MAX_ATTEMPTS = 10


@router.message(F.text == "🔐 Admin sifatida kirish")
async def admin_login_start(message: Message, state: FSMContext, session: AsyncSession):
    """Admin kirish tugmasi"""
    admin = await get_admin_by_telegram_id(session, message.from_user.id)
    if not admin:
        await message.answer(
            "⛔ <b>Siz admin emassiz!</b>",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
        return

    # Allaqachon session da admin bo'lsa
    state_data = await state.get_data()
    if state_data.get("admin_id") and state_data.get("is_admin_logged_in"):
        await message.answer(
            "✅ Siz allaqachon admin sifatida kirgansiz!",
            reply_markup=get_admin_main_menu()
        )
        return

    await state.set_state(AdminAuthStates.waiting_password)
    await message.answer(
        "🔐 <b>Admin parolini kiriting:</b>",
        parse_mode="HTML",
        reply_markup=__import__("aiogram").types.ReplyKeyboardRemove()
    )


@router.message(AdminAuthStates.waiting_password)
async def admin_login_password(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    telegram_id = message.from_user.id
    password = message.text.strip() if message.text else ""

    admin = await get_admin_by_telegram_id(session, telegram_id)
    if not admin:
        await clear_state(state)
        await message.answer("⛔ Admin topilmadi.", reply_markup=get_start_keyboard())
        return

    # Bloklangan holat
    if admin.wrong_attempts >= MAX_ATTEMPTS:
        await _handle_max_attempts(message, admin, session, bot)
        await clear_state(state)
        return

    # Parol tekshiruvi
    if not verify_password(password, admin.password_hash):
        attempts = await increment_admin_wrong_attempts(session, telegram_id)

        if attempts >= MAX_ATTEMPTS:
            await _handle_max_attempts(message, admin, session, bot)
            await clear_state(state)
        else:
            remaining = MAX_ATTEMPTS - attempts
            await message.answer(
                f"❌ <b>Parol noto'g'ri!</b>\n"
                f"Qolgan urinishlar: <b>{remaining}</b> ta",
                parse_mode="HTML"
            )
        return

    # Muvaffaqiyatli kirish
    await reset_admin_wrong_attempts(session, telegram_id)
    await state.update_data(
        admin_id=admin.id,
        admin_telegram_id=admin.telegram_id,
        is_admin_logged_in=True
    )
    await state.set_state(None)

    await message.answer(
        "✅ <b>Admin paneliga xush kelibsiz!</b>",
        parse_mode="HTML",
        reply_markup=get_admin_main_menu()
    )
    logger.info(f"Admin kirdi: telegram_id={telegram_id}")


async def _handle_max_attempts(message: Message, admin, session: AsyncSession, bot: Bot):
    """10 ta noto'g'ri urinishdan keyin - yangi parol Gmail ga yuborish"""
    new_password = generate_password(10)
    new_hash = hash_password(new_password)

    # Yangi parolni bazaga saqlash
    from database.crud import update_admin_password
    await update_admin_password(session, admin.id, new_hash)

    # Gmail ga yuborish
    if admin.gmail:
        sent = await send_admin_password_recovery(
            admin.gmail,
            admin.username or "admin",
            new_password
        )
        if sent:
            await message.answer(
                "✅ <b>Parol Gmail manzilingizga yuborildi.</b>\n"
                "Email'ingizni tekshiring.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            logger.warning(f"Admin max attempts, parol Gmail ga yuborildi: {admin.gmail}")
        else:
            await message.answer(
                "❌ Gmail yuborishda xato. Admin bilan bog'laning.",
                reply_markup=get_start_keyboard()
            )
    else:
        await message.answer(
            "🚫 <b>Urinishlar tugadi.</b> Gmail manzil yo'q.\n"
            "Server administratori bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )
