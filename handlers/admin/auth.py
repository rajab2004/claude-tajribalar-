"""
Admin kirish
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from services.email_service import send_password_email
from utils.keyboards import admin_main_menu, start_keyboard
import config

router = Router()


class AdminAuthStates(StatesGroup):
    waiting_password = State()


@router.message(F.text == "🔐 Admin sifatida kirish")
async def admin_login_start(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        await message.answer(
            "❌ Siz admin emassiz!",
            reply_markup=start_keyboard()
        )
        return
    await state.set_state(AdminAuthStates.waiting_password)
    await message.answer("🔑 Admin parolini kiriting:")


@router.message(AdminAuthStates.waiting_password)
async def admin_login_check(message: Message, state: FSMContext,
                             db: AsyncSession):
    password = message.text.strip()
    tg_id = message.from_user.id

    if tg_id != config.ADMIN_TELEGRAM_ID:
        await state.clear()
        await message.answer("❌ Ruxsat yo'q!", reply_markup=start_keyboard())
        return

    success, admin = await crud.verify_admin_password(db, tg_id, password)
    await db.commit()

    if success:
        await state.clear()
        await message.answer(
            "✅ Admin paneliga xush kelibsiz!",
            reply_markup=admin_main_menu()
        )
        return

    if admin is None:
        # Admin bazada yo'q — yaratish
        await crud.create_admin(db)
        await db.commit()
        await message.answer("❌ Noto'g'ri parol!")
        return

    attempts = admin.wrong_attempts
    remaining = config.MAX_WRONG_ATTEMPTS - attempts

    if attempts >= config.MAX_WRONG_ATTEMPTS:
        # Gmail ga yuborish
        if admin.gmail:
            sent = await send_password_email(admin.gmail, config.ADMIN_PASSWORD)
            if sent:
                await message.answer(
                    f"🚫 Parol {config.MAX_WRONG_ATTEMPTS} marta noto'g'ri!\n\n"
                    f"📧 Parol Gmail manzilingizga yuborildi:\n{admin.gmail}",
                    reply_markup=start_keyboard()
                )
            else:
                await message.answer(
                    f"🚫 Parol {config.MAX_WRONG_ATTEMPTS} marta noto'g'ri!\n"
                    f"❌ Email yuborishda xatolik. .env faylni tekshiring.",
                    reply_markup=start_keyboard()
                )
        else:
            await message.answer(
                f"🚫 Parol {config.MAX_WRONG_ATTEMPTS} marta noto'g'ri!\n"
                f"Gmail manzil sozlanmagan.",
                reply_markup=start_keyboard()
            )
        await state.clear()
    else:
        await message.answer(
            f"❌ Parol noto'g'ri!\n"
            f"⚠️ {remaining} ta urinish qoldi."
        )


@router.message(F.text == "🚪 Chiqish")
async def admin_logout(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Admin paneldan chiqdingiz.",
        reply_markup=start_keyboard()
    )
