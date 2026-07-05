"""
Telegram akkaunt ulash handler
"""
from aiogram import Router, F
from aiogram.types import Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from services.pyrogram_client import (
    start_phone_auth, verify_otp, verify_2fa
)
from utils.keyboards import (
    user_main_menu, share_contact_keyboard, remove_keyboard
)
from utils.helpers import normalize_phone
import config

router = Router()


class TelegramConnectStates(StatesGroup):
    waiting_phone = State()
    waiting_otp = State()
    waiting_2fa = State()


@router.message(F.text == "📱 Telegram akkauntni ulash")
async def connect_start(message: Message, state: FSMContext, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await message.answer("❌ Avval tizimga kiring.")
        return

    existing = await crud.get_session(db, user.id)
    if existing:
        await message.answer(
            "✅ Telegram akkauntingiz allaqachon ulangan!\n"
            "Uzish uchun ⚙️ Sozlamalar bo'limiga o'ting."
        )
        return

    await state.set_state(TelegramConnectStates.waiting_phone)
    await message.answer(
        "📱 Telegram raqamingizni kiriting yoki kontakt ulashing:\n\n"
        "Format: +998 99 123 45 67 yoki 99 123 45 67",
        reply_markup=share_contact_keyboard()
    )


@router.message(TelegramConnectStates.waiting_phone, F.contact)
async def connect_contact(message: Message, state: FSMContext):
    contact: Contact = message.contact
    phone = normalize_phone(contact.phone_number)
    if not phone:
        await message.answer("❌ Noto'g'ri raqam formati.")
        return
    await _send_otp(message, state, phone)


@router.message(TelegramConnectStates.waiting_phone)
async def connect_phone(message: Message, state: FSMContext):
    phone = normalize_phone(message.text.strip())
    if not phone:
        await message.answer(
            "❌ Noto'g'ri format!\n"
            "To'g'ri: +998 99 123 45 67 yoki 99 123 45 67"
        )
        return
    await _send_otp(message, state, phone)


async def _send_otp(message: Message, state: FSMContext, phone: str):
    await message.answer("⏳ Kod yuborilmoqda...", reply_markup=remove_keyboard())
    success, code_hash, error = await start_phone_auth(phone)

    if not success:
        await message.answer(
            f"❌ Xatolik: {error}",
            reply_markup=user_main_menu()
        )
        await state.clear()
        return

    await state.update_data(phone=phone, code_hash=code_hash, otp_attempts=0)
    await state.set_state(TelegramConnectStates.waiting_otp)
    await message.answer(
        f"✅ Kod {phone} ga yuborildi!\n"
        f"📲 Telegram ilovangizdan kelgan kodni kiriting:\n"
        f"⏰ Kod 5 daqiqa amal qiladi"
    )


@router.message(TelegramConnectStates.waiting_otp)
async def connect_otp(message: Message, state: FSMContext, db: AsyncSession):
    code = message.text.strip().replace(" ", "").replace("-", "")
    data = await state.get_data()

    success, result, extra = await verify_otp(
        data["phone"], code, data["code_hash"]
    )

    if extra == "2fa_needed":
        await state.set_state(TelegramConnectStates.waiting_2fa)
        await message.answer(
            "🔐 Ikki bosqichli himoya (2FA) yoqilgan.\n"
            "Telegram parolingizni kiriting:"
        )
        return

    if not success:
        attempts = data.get("otp_attempts", 0) + 1
        await state.update_data(otp_attempts=attempts)
        if attempts >= config.OTP_MAX_ATTEMPTS:
            await message.answer(
                "🚫 3 marta noto'g'ri kod. Qayta boshlang.",
                reply_markup=user_main_menu()
            )
            await state.clear()
        else:
            remaining = config.OTP_MAX_ATTEMPTS - attempts
            await message.answer(
                f"❌ {result}\n⚠️ {remaining} ta urinish qoldi."
            )
        return

    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    await crud.save_session(db, user.id, result, data["phone"])
    await db.commit()
    await state.clear()
    await message.answer(
        "✅ Telegram akkauntingiz muvaffaqiyatli ulandi! 🎉",
        reply_markup=user_main_menu()
    )


@router.message(TelegramConnectStates.waiting_2fa)
async def connect_2fa(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    success, session_string, error = await verify_2fa(
        data["phone"], message.text.strip()
    )

    if not success:
        await message.answer(f"❌ {error}\nQayta kiriting:")
        return

    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    await crud.save_session(db, user.id, session_string, data["phone"])
    await db.commit()
    await state.clear()
    await message.answer(
        "✅ Telegram akkauntingiz muvaffaqiyatli ulandi! 🎉",
        reply_markup=user_main_menu()
    )
