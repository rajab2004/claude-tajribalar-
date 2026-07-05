"""
Foydalanuvchi kirish va parol o'zgartirish
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from utils.keyboards import user_main_menu, start_keyboard
import config

router = Router()


class UserAuthStates(StatesGroup):
    waiting_password = State()
    waiting_old_password = State()
    waiting_new_password = State()
    waiting_confirm_password = State()


# ─── Kirish ────────────────────────────────────────────────────────────
@router.message(F.text == "👤 Foydalanuvchi sifatida kirish")
async def user_login_start(message: Message, state: FSMContext):
    await state.set_state(UserAuthStates.waiting_password)
    await message.answer(
        "🔑 Parolingizni kiriting:\n\n"
        "❓ Agar parolingiz bo'lmasa, admin bilan bog'laning:\n"
        f"📞 {config.ADMIN_PHONE}\n"
        f"💬 @{config.ADMIN_USERNAME}"
    )


@router.message(UserAuthStates.waiting_password)
async def user_login_check(message: Message, state: FSMContext,
                             db: AsyncSession):
    password = message.text.strip()
    tg_id = message.from_user.id

    success, user = await crud.verify_user_password(db, tg_id, password)
    await db.commit()

    if success:
        await state.clear()
        await state.update_data(user_logged_in=True)
        await message.answer(
            f"✅ Xush kelibsiz!\n\n"
            f"📅 Muddatingiz: {user.expires_at.strftime('%d.%m.%Y')} gacha",
            reply_markup=user_main_menu()
        )
        return

    if user is None:
        await message.answer(
            "❌ Siz tizimda ro'yxatdan o'tmagansiz.\n"
            f"Admin bilan bog'laning: 📞 {config.ADMIN_PHONE}"
        )
        await state.clear()
        return

    # Foydalanuvchi topildi lekin kirish muvaffaqiyatsiz
    from datetime import datetime
    if user.expires_at < datetime.utcnow():
        await message.answer(
            "⏰ Sizning muddatingiz tugagan!\n\n"
            f"Davom etish uchun admin bilan bog'laning:\n"
            f"📞 {config.ADMIN_PHONE}\n"
            f"💬 @{config.ADMIN_USERNAME}"
        )
        await state.clear()
        return

    # Noto'g'ri parol
    attempts = user.wrong_attempts
    remaining = config.MAX_WRONG_ATTEMPTS - attempts

    if attempts >= config.MAX_WRONG_ATTEMPTS:
        await message.answer(
            f"🚫 Parol {config.MAX_WRONG_ATTEMPTS} marta noto'g'ri kiritildi!\n\n"
            f"Admin bilan bog'laning:\n"
            f"📞 {config.ADMIN_PHONE}\n"
            f"💬 @{config.ADMIN_USERNAME}",
            reply_markup=start_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ Parol noto'g'ri!\n"
            f"⚠️ {remaining} ta urinish qoldi."
        )


# ─── Parol o'zgartirish ────────────────────────────────────────────────
@router.message(F.text == "🔑 Parolni o'zgartirish")
async def change_password_start(message: Message, state: FSMContext):
    await state.set_state(UserAuthStates.waiting_old_password)
    await message.answer("🔑 Eski parolingizni kiriting:")


@router.message(UserAuthStates.waiting_old_password)
async def change_password_old(message: Message, state: FSMContext,
                               db: AsyncSession):
    old_password = message.text.strip()
    tg_id = message.from_user.id
    success, user = await crud.verify_user_password(db, tg_id, old_password)

    if not success or user is None:
        await message.answer("❌ Eski parol noto'g'ri! Qayta urinib ko'ring.")
        return

    await state.update_data(user_id=user.id)
    await state.set_state(UserAuthStates.waiting_new_password)
    await message.answer("🆕 Yangi parolingizni kiriting (kamida 6 belgi):")


@router.message(UserAuthStates.waiting_new_password)
async def change_password_new(message: Message, state: FSMContext):
    new_pw = message.text.strip()
    if len(new_pw) < 6:
        await message.answer("❌ Parol kamida 6 belgi bo'lishi kerak!")
        return
    await state.update_data(new_password=new_pw)
    await state.set_state(UserAuthStates.waiting_confirm_password)
    await message.answer("🔄 Yangi parolni tasdiqlang (qayta kiriting):")


@router.message(UserAuthStates.waiting_confirm_password)
async def change_password_confirm(message: Message, state: FSMContext,
                                   db: AsyncSession):
    data = await state.get_data()
    confirm = message.text.strip()

    if confirm != data.get("new_password"):
        await message.answer("❌ Parollar mos kelmadi! Qayta kiriting:")
        await state.set_state(UserAuthStates.waiting_new_password)
        return

    await crud.update_user_password(db, data["user_id"], confirm)
    await db.commit()
    await state.clear()
    await message.answer(
        "✅ Parol muvaffaqiyatli o'zgartirildi!",
        reply_markup=user_main_menu()
    )
