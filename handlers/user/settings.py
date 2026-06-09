from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_user_by_telegram_id,
    update_user_password,
    get_active_session_by_user_id,
    disconnect_session,
    close_user_announcements,
    update_announcement_interval,
)
from services.pyrogram_client import (
    start_phone_auth,
    verify_phone_code,
    verify_2fa_password,
    cancel_auth,
    disconnect_client,
    create_client_from_session,
)
from database.crud import create_session
from utils.password_generator import verify_password, hash_password, is_valid_password
from utils.keyboards import (
    get_settings_keyboard,
    get_user_main_menu,
    get_phone_keyboard,
    get_interval_keyboard,
    get_yes_no_keyboard,
    get_cancel_keyboard,
)
from utils.helpers import (
    normalize_phone,
    is_expired,
    format_date,
    mask_password,
    clear_state,
)
from handlers.user.states import PhoneAuthStates, SettingsStates

router = Router()


def _auth_check(user) -> bool:
    return user and user.is_active and not is_expired(user.expires_at)


# ============================================================
# SOZLAMALAR MENYUSI
# ============================================================

@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        await message.answer("⚠️ Avval kiring.")
        return

    db_session = await get_active_session_by_user_id(session, user.id)
    session_status = "✅ Ulangan" if db_session else "❌ Ulanmagan"
    expires = format_date(user.expires_at)

    await message.answer(
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"📅 <b>Muddatingiz:</b> {expires} gacha\n"
        f"🔑 <b>Parol:</b> {mask_password()}\n"
        f"📱 <b>Akkaunt:</b> {session_status}",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# PAROL O'ZGARTIRISH
# ============================================================

@router.message(F.text == "🔄 Parolni o'zgartirish")
async def change_password_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return
    await state.set_state(SettingsStates.waiting_old_password)
    await state.update_data(user_id=user.id)
    await message.answer(
        "🔑 <b>Eski parolni kiriting:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(SettingsStates.waiting_old_password)
async def change_password_old(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_settings_keyboard())
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not verify_password(message.text.strip(), user.password_hash):
        await message.answer("❌ <b>Eski parol noto'g'ri!</b>", parse_mode="HTML")
        return

    await state.set_state(SettingsStates.waiting_new_password)
    await message.answer(
        "🔑 <b>Yangi parolni kiriting</b> (kamida 6 belgi):",
        parse_mode="HTML"
    )


@router.message(SettingsStates.waiting_new_password)
async def change_password_new(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_settings_keyboard())
        return

    new_pass = message.text.strip() if message.text else ""
    if not is_valid_password(new_pass, min_length=6):
        await message.answer("❌ <b>Parol kamida 6 belgi bo'lishi kerak!</b>", parse_mode="HTML")
        return

    await state.update_data(new_password=new_pass)
    await state.set_state(SettingsStates.waiting_confirm_password)
    await message.answer("🔑 <b>Yangi parolni qayta kiriting (tasdiqlash):</b>", parse_mode="HTML")


@router.message(SettingsStates.waiting_confirm_password)
async def change_password_confirm(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_settings_keyboard())
        return

    data = await state.get_data()
    new_pass = data.get("new_password", "")
    user_id = data.get("user_id")

    if message.text.strip() != new_pass:
        await message.answer("❌ <b>Parollar mos kelmadi!</b> Qayta kiriting.", parse_mode="HTML")
        await state.set_state(SettingsStates.waiting_new_password)
        await message.answer("🔑 <b>Yangi parolni kiriting:</b>", parse_mode="HTML")
        return

    new_hash = hash_password(new_pass)
    await update_user_password(session, user_id, new_hash)
    await clear_state(state)
    await message.answer(
        "✅ <b>Parol muvaffaqiyatli o'zgartirildi!</b>",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    logger.info(f"Foydalanuvchi paroli o'zgartirildi: user_id={user_id}")


# ============================================================
# TELEGRAM AKKAUNTNI ULASH
# ============================================================

@router.message(F.text == "📱 Telegram akkauntni ulash")
async def link_account_start(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    # Allaqachon ulangan sessiya bormi?
    existing = await get_active_session_by_user_id(session, user.id)
    if existing:
        await message.answer(
            "✅ <b>Telegram akkauntingiz allaqachon ulangan!</b>\n"
            "Uzish uchun: <b>⚙️ Sozlamalar → 🔌 Telegram akkauntni uzish</b>",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )
        return

    await state.set_state(PhoneAuthStates.waiting_phone)
    await state.update_data(user_id=user.id, db_user_id=user.id)
    await message.answer(
        "📱 <b>Telegram raqamingizni kiriting yoki kontakt ulashing:</b>\n\n"
        "Formatlar:\n"
        "• <code>+998991234567</code>\n"
        "• <code>998991234567</code>\n"
        "• <code>991234567</code>",
        parse_mode="HTML",
        reply_markup=get_phone_keyboard()
    )


@router.message(PhoneAuthStates.waiting_phone, F.contact)
async def link_account_contact(message: Message, state: FSMContext, session: AsyncSession):
    """Kontakt ulashish orqali"""
    contact: Contact = message.contact
    phone = contact.phone_number
    await _process_phone(message, state, phone)


@router.message(PhoneAuthStates.waiting_phone, F.text)
async def link_account_phone_text(message: Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await clear_state(state)
        await message.answer("⬅️ Orqaga", reply_markup=get_user_main_menu())
        return
    await _process_phone(message, state, message.text.strip())


async def _process_phone(message: Message, state: FSMContext, phone_raw: str):
    phone = normalize_phone(phone_raw)
    if not phone:
        await message.answer(
            "❌ <b>Noto'g'ri format!</b> Qayta kiriting.\n"
            "Misol: <code>+998991234567</code>",
            parse_mode="HTML"
        )
        return

    await message.answer("⏳ Kod yuborilmoqda...", reply_markup=__import__("aiogram").types.ReplyKeyboardRemove())

    ok, result = await start_phone_auth(message.from_user.id, phone)

    if not ok:
        if result.startswith("flood:"):
            wait = result.split(":")[1]
            await message.answer(
                f"⏳ <b>Juda ko'p urinish!</b> {wait} soniya kuting.",
                parse_mode="HTML"
            )
        elif result == "invalid_phone":
            await message.answer("❌ <b>Noto'g'ri telefon raqam!</b>", parse_mode="HTML")
        else:
            await message.answer("❌ Xato yuz berdi. Qayta urinib ko'ring.")
        await clear_state(state)
        await message.answer("🏠", reply_markup=get_user_main_menu())
        return

    await state.update_data(phone=phone, code_attempts=0)
    await state.set_state(PhoneAuthStates.waiting_code)
    await message.answer(
        "📨 <b>Telegram kodni kiriting</b>\n"
        "(Sizga SMS yoki Telegram orqali yuborildi)\n\n"
        "⏱ Kod 5 daqiqa amal qiladi.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(PhoneAuthStates.waiting_code)
async def link_account_code(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await cancel_auth(message.from_user.id)
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_main_menu())
        return

    code = message.text.strip().replace(" ", "") if message.text else ""
    result, session_string = await verify_phone_code(message.from_user.id, code)

    if result == "success":
        data = await state.get_data()
        db_user_id = data.get("db_user_id")
        phone = data.get("phone", "")
        await create_session(session, db_user_id, session_string, phone)
        await clear_state(state)
        await message.answer(
            "✅ <b>Akkaunt muvaffaqiyatli ulandi!</b>",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )
        logger.info(f"Akkaunt ulandi: user_id={db_user_id}, phone={phone}")

    elif result == "2fa":
        await state.set_state(PhoneAuthStates.waiting_2fa)
        await message.answer(
            "🔐 <b>Ikki bosqichli himoya (2FA) paroli kiriting:</b>",
            parse_mode="HTML"
        )

    elif result == "invalid":
        data = await state.get_data()
        attempts = data.get("code_attempts", 0) + 1
        await state.update_data(code_attempts=attempts)
        if attempts >= 3:
            await cancel_auth(message.from_user.id)
            await clear_state(state)
            await message.answer(
                "🚫 <b>3 marta noto'g'ri kod kiritildi.</b>\n"
                "Jarayon bekor qilindi.",
                parse_mode="HTML",
                reply_markup=get_user_main_menu()
            )
        else:
            await message.answer(
                f"❌ <b>Kod noto'g'ri!</b> Qoldi: {3 - attempts} ta urinish.",
                parse_mode="HTML"
            )

    elif result == "expired":
        await clear_state(state)
        await message.answer(
            "⏰ <b>Kod eskirgan!</b> Qayta urinib ko'ring.",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )

    elif result == "max_attempts":
        await clear_state(state)
        await message.answer(
            "🚫 <b>Urinishlar tugadi.</b> Qayta /start bosing.",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )
    else:
        await clear_state(state)
        await message.answer("❌ Xato yuz berdi.", reply_markup=get_user_main_menu())


@router.message(PhoneAuthStates.waiting_2fa)
async def link_account_2fa(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await cancel_auth(message.from_user.id)
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_main_menu())
        return

    password = message.text.strip() if message.text else ""
    result, session_string = await verify_2fa_password(message.from_user.id, password)

    if result == "success":
        data = await state.get_data()
        db_user_id = data.get("db_user_id")
        phone = data.get("phone", "")
        await create_session(session, db_user_id, session_string, phone)
        await clear_state(state)
        await message.answer(
            "✅ <b>Akkaunt muvaffaqiyatli ulandi!</b>",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )
        logger.info(f"2FA orqali ulandi: user_id={db_user_id}")

    elif result == "invalid":
        await message.answer(
            "❌ <b>2FA parol noto'g'ri!</b> Qayta urinib ko'ring.",
            parse_mode="HTML"
        )
    else:
        await cancel_auth(message.from_user.id)
        await clear_state(state)
        await message.answer("❌ Xato yuz berdi.", reply_markup=get_user_main_menu())


# ============================================================
# AKKAUNTNI UZISH
# ============================================================

@router.message(F.text == "🔌 Telegram akkauntni uzish")
async def disconnect_account_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    existing = await get_active_session_by_user_id(session, user.id)
    if not existing:
        await message.answer(
            "ℹ️ Ulangan akkaunt yo'q.",
            reply_markup=get_settings_keyboard()
        )
        return

    await state.update_data(user_id=user.id)
    await message.answer(
        "⚠️ <b>Rostdan akkauntni uzmoqchimisiz?</b>\n\n"
        "• Barcha ochiq e'lonlar avtomatik yopiladi\n"
        "• Xabar yuborish to'xtatiladi",
        reply_markup=get_yes_no_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "yes")
async def disconnect_account_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_id = data.get("user_id")
    if not user_id:
        await callback.answer("❌ Xato!")
        return

    # Sessiyani o'chirish
    await disconnect_session(session, user_id)
    await disconnect_client(user_id)

    # Ochiq e'lonlarni yopish
    closed = await close_user_announcements(session, user_id)

    await clear_state(state)
    await callback.message.edit_text(
        f"✅ <b>Akkaunt uzildi.</b>\n"
        f"{'📋 ' + str(closed) + ' ta e'lon yopildi.' if closed else ''}",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Qayta ulashingiz mumkin.",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()
    logger.info(f"Akkaunt uzildi: user_id={user_id}")


@router.callback_query(F.data == "no")
async def disconnect_account_cancel(callback: CallbackQuery, state: FSMContext):
    await clear_state(state)
    await callback.message.edit_text("✅ Bekor qilindi.")
    await callback.message.answer("⚙️ Sozlamalar:", reply_markup=get_settings_keyboard())
    await callback.answer()


# ============================================================
# INTERVAL O'ZGARTIRISH
# ============================================================

@router.message(F.text == "⏱ Yuborish intervalini o'zgartirish")
async def change_interval_start(message: Message, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    await message.answer(
        "⏱ <b>Yangi yuborish intervalini tanlang:</b>",
        reply_markup=get_interval_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("interval_"))
async def change_interval_set(callback: CallbackQuery, session: AsyncSession):
    minutes = int(callback.data.split("_")[-1])
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Xato!")
        return

    await update_announcement_interval(session, user.id, minutes)
    await callback.message.edit_text(
        f"✅ <b>Interval {minutes} daqiqaga o'zgartirildi!</b>",
        parse_mode="HTML"
    )
    await callback.answer(f"✅ {minutes} daqiqa!")
    logger.info(f"Interval o'zgartirildi: user_id={user.id}, interval={minutes}")
