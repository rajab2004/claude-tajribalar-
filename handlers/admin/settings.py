from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_admin_by_telegram_id,
    get_admin_by_id,
    update_admin_password,
    update_admin_gmail,
    update_admin_contact,
    get_user_by_telegram_id,
    update_user_password,
)
from utils.password_generator import (
    hash_password,
    generate_password,
    is_valid_password,
    verify_password,
)
from utils.keyboards import (
    get_admin_settings_keyboard,
    get_admin_main_menu,
    get_cancel_keyboard,
)
from utils.helpers import clear_state, format_date
from handlers.admin.states import AdminSettingsStates

router = Router()


def _is_admin(data: dict) -> bool:
    return bool(data.get("is_admin_logged_in"))


# ============================================================
# SOZLAMALAR MENYUSI
# ============================================================

@router.message(F.text == "⚙️ Admin sozlamalari")
async def admin_settings_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    if not _is_admin(data):
        await message.answer("⛔ Admin sifatida kirmadingiz!")
        return
    await message.answer(
        "⚙️ <b>Admin sozlamalari</b>",
        reply_markup=get_admin_settings_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🏠 Bosh menyuga qaytish")
async def admin_go_home(message: Message, state: FSMContext):
    data = await state.get_data()
    if _is_admin(data):
        await message.answer("🏠 <b>Admin bosh menyu</b>", reply_markup=get_admin_main_menu(), parse_mode="HTML")


# ============================================================
# ADMIN PAROLINI O'ZGARTIRISH
# ============================================================

@router.message(F.text == "🔑 Parolni o'zgartirish")
async def admin_change_password_start(message: Message, state: FSMContext):
    data = await state.get_data()
    if not _is_admin(data):
        return

    await state.set_state(AdminSettingsStates.waiting_new_password)
    await message.answer(
        "🔑 <b>Yangi parolni kiriting</b> (kamida 8 belgi):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminSettingsStates.waiting_new_password)
async def admin_change_password_new(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    new_pass = message.text.strip() if message.text else ""
    if not is_valid_password(new_pass, min_length=8):
        await message.answer("❌ <b>Parol kamida 8 belgi bo'lishi kerak!</b>", parse_mode="HTML")
        return

    await state.update_data(new_admin_password=new_pass)
    await state.set_state(AdminSettingsStates.waiting_confirm_password)
    await message.answer("🔑 <b>Yangi parolni qayta kiriting:</b>", parse_mode="HTML")


@router.message(AdminSettingsStates.waiting_confirm_password)
async def admin_change_password_confirm(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    data = await state.get_data()
    new_pass = data.get("new_admin_password", "")
    admin_id = data.get("admin_id")

    if message.text.strip() != new_pass:
        await message.answer("❌ <b>Parollar mos kelmadi!</b>", parse_mode="HTML")
        await state.set_state(AdminSettingsStates.waiting_new_password)
        await message.answer("🔑 Yangi parolni qaytadan kiriting:")
        return

    new_hash = hash_password(new_pass)
    await update_admin_password(session, admin_id, new_hash)
    await clear_state(state)
    await state.update_data(admin_id=admin_id, is_admin_logged_in=True)

    await message.answer(
        "✅ <b>Admin paroli muvaffaqiyatli o'zgartirildi!</b>",
        parse_mode="HTML",
        reply_markup=get_admin_settings_keyboard()
    )
    logger.info(f"Admin paroli o'zgartirildi: id={admin_id}")


# ============================================================
# GMAIL O'ZGARTIRISH
# ============================================================

@router.message(F.text == "📧 Gmail manzilini o'zgartirish")
async def admin_change_gmail_start(message: Message, state: FSMContext):
    data = await state.get_data()
    if not _is_admin(data):
        return
    await state.set_state(AdminSettingsStates.waiting_new_gmail)
    await message.answer(
        "📧 <b>Yangi Gmail manzilini kiriting:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminSettingsStates.waiting_new_gmail)
async def admin_change_gmail(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await state.update_data(**(await state.get_data()))
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    gmail = message.text.strip() if message.text else ""
    if "@" not in gmail or "." not in gmail:
        await message.answer("❌ <b>Noto'g'ri Gmail format!</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    admin_id = data.get("admin_id")
    await update_admin_gmail(session, admin_id, gmail)
    await clear_state(state)
    await state.update_data(admin_id=admin_id, is_admin_logged_in=True)

    await message.answer(
        f"✅ <b>Gmail manzil yangilandi:</b> {gmail}",
        parse_mode="HTML",
        reply_markup=get_admin_settings_keyboard()
    )
    logger.info(f"Admin Gmail yangilandi: {gmail}")


# ============================================================
# BOG'LANISH MA'LUMOTLARI
# ============================================================

@router.message(F.text == "📞 Bog'lanish ma'lumotlarini o'zgartirish")
async def admin_change_contact_start(message: Message, state: FSMContext):
    data = await state.get_data()
    if not _is_admin(data):
        return
    await state.set_state(AdminSettingsStates.waiting_new_phone)
    await message.answer(
        "📞 <b>Yangi telefon raqamini kiriting:</b>\n"
        "Misol: <code>+998901234567</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminSettingsStates.waiting_new_phone)
async def admin_change_phone(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await state.update_data(**(await state.get_data()))
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    phone = message.text.strip() if message.text else ""
    await state.update_data(new_admin_phone=phone)
    await state.set_state(AdminSettingsStates.waiting_new_username)
    await message.answer(
        "💬 <b>Yangi Telegram username kiriting</b> (@ belgisiz):",
        parse_mode="HTML"
    )


@router.message(AdminSettingsStates.waiting_new_username)
async def admin_change_username(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    username = message.text.strip().lstrip("@") if message.text else ""
    data = await state.get_data()
    phone = data.get("new_admin_phone", "")
    admin_id = data.get("admin_id")

    await update_admin_contact(session, admin_id, phone=phone, username=username)
    await clear_state(state)
    await state.update_data(admin_id=admin_id, is_admin_logged_in=True)

    await message.answer(
        f"✅ <b>Bog'lanish ma'lumotlari yangilandi!</b>\n\n"
        f"📞 Tel: {phone}\n"
        f"💬 @{username}",
        parse_mode="HTML",
        reply_markup=get_admin_settings_keyboard()
    )
    logger.info(f"Admin kontakt yangilandi: phone={phone}, username={username}")


# ============================================================
# FOYDALANUVCHI PAROLINI O'ZGARTIRISH
# ============================================================

@router.message(F.text == "👤 Foydalanuvchi parolini o'zgartirish")
async def reset_user_password_start(message: Message, state: FSMContext):
    data = await state.get_data()
    if not _is_admin(data):
        return
    await state.set_state(AdminSettingsStates.waiting_user_id_for_reset)
    await message.answer(
        "👤 <b>Foydalanuvchi Telegram ID sini kiriting:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminSettingsStates.waiting_user_id_for_reset)
async def reset_user_password_execute(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot
):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await state.update_data(**(await state.get_data()))
        await message.answer("❌ Bekor.", reply_markup=get_admin_settings_keyboard())
        return

    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ <b>Noto'g'ri format!</b> Faqat raqam kiriting.", parse_mode="HTML")
        return

    user = await get_user_by_telegram_id(session, tg_id)
    if not user:
        await message.answer(
            f"❌ <b>ID {tg_id} bazada topilmadi!</b>",
            parse_mode="HTML"
        )
        return

    # Yangi parol generatsiya
    new_password = generate_password(10)
    new_hash = hash_password(new_password)
    await update_user_password(session, user.id, new_hash)

    data = await state.get_data()
    admin_id = data.get("admin_id")
    await clear_state(state)
    await state.update_data(admin_id=admin_id, is_admin_logged_in=True)

    await message.answer(
        f"✅ <b>Parol yangilandi!</b>\n\n"
        f"👤 ID: <code>{tg_id}</code>\n"
        f"🔑 Yangi parol: <code>{new_password}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_settings_keyboard()
    )

    # Foydalanuvchiga xabar
    try:
        from config import config
        await bot.send_message(
            tg_id,
            f"🔑 <b>Parolingiz yangilandi!</b>\n\n"
            f"🔑 Yangi parol: <code>{new_password}</code>\n"
            f"🤖 Bot: @{config.BOT_USERNAME}",
            parse_mode="HTML"
        )
        logger.info(f"Foydalanuvchi paroli yangilandi: tg_id={tg_id}")
    except Exception as e:
        await message.answer(
            f"⚠️ Foydalanuvchiga xabar yuborilmadi.\n"
            f"🔑 Parol: <code>{new_password}</code>",
            parse_mode="HTML"
        )
        logger.warning(f"Foydalanuvchiga xabar yuborilmadi: {tg_id} | {e}")
