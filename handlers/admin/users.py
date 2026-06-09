from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_admin_by_telegram_id,
    get_all_users,
    get_active_users,
    get_expired_users,
    get_user_by_id,
    create_user,
    delete_user,
    extend_user_expiry,
)
from utils.password_generator import generate_password, hash_password
from utils.keyboards import (
    get_admin_main_menu,
    get_users_list_menu,
    get_months_keyboard,
    get_user_actions_keyboard,
    get_extend_months_keyboard,
    get_save_cancel_keyboard,
    get_cancel_keyboard,
)
from utils.helpers import (
    format_date,
    format_user_info,
    is_expired,
    clear_state,
)
from services.email_service import send_user_credentials
from handlers.admin.states import AddUserStates

router = Router()


def _is_admin_logged_in(state_data: dict) -> bool:
    return bool(state_data.get("is_admin_logged_in"))


async def _check_admin(message_or_callback, state: FSMContext) -> bool:
    data = await state.get_data()
    if not _is_admin_logged_in(data):
        if hasattr(message_or_callback, "answer"):
            await message_or_callback.answer("⛔ Admin sifatida kirmadingiz!")
        return False
    return True


# ============================================================
# FOYDALANUVCHILAR RO'YXATI MENYUSI
# ============================================================

@router.message(F.text == "👥 Foydalanuvchilar ro'yhati")
async def users_list_menu(message: Message, state: FSMContext):
    if not await _check_admin(message, state):
        return
    await message.answer(
        "👥 <b>Foydalanuvchilar ro'yhati</b>",
        reply_markup=get_users_list_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "👥 Barcha foydalanuvchilar")
async def all_users_list(message: Message, state: FSMContext, session: AsyncSession):
    if not await _check_admin(message, state):
        return

    users = await get_all_users(session)
    if not users:
        await message.answer("📭 Hali foydalanuvchi yo'q.", reply_markup=get_users_list_menu())
        return

    await message.answer(
        f"👥 <b>Barcha foydalanuvchilar ({len(users)} ta):</b>",
        parse_mode="HTML",
        reply_markup=get_users_list_menu()
    )

    for user in users:
        status = "🟢 Faol" if user.is_active and not is_expired(user.expires_at) else "🔴 Nofaol"
        text = (
            f"👤 ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or 'Mavjud emas'}\n"
            f"📅 Muddat: {format_date(user.expires_at)}\n"
            f"📊 Holat: {status}"
        )
        expired = is_expired(user.expires_at)
        await message.answer(
            text,
            reply_markup=get_user_actions_keyboard(user.id, is_expired=expired),
            parse_mode="HTML"
        )


@router.message(F.text == "🟢 Faol foydalanuvchilar")
async def active_users_list(message: Message, state: FSMContext, session: AsyncSession):
    if not await _check_admin(message, state):
        return

    users = await get_active_users(session)
    if not users:
        await message.answer("📭 Faol foydalanuvchi yo'q.", reply_markup=get_users_list_menu())
        return

    await message.answer(
        f"🟢 <b>Faol foydalanuvchilar ({len(users)} ta):</b>",
        parse_mode="HTML",
        reply_markup=get_users_list_menu()
    )

    for user in users:
        text = (
            f"👤 ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or 'Mavjud emas'}\n"
            f"📅 Muddat: {format_date(user.expires_at)}\n"
            f"🟢 Holat: Faol"
        )
        await message.answer(
            text,
            reply_markup=get_user_actions_keyboard(user.id, is_expired=False),
            parse_mode="HTML"
        )


@router.message(F.text == "⏰ Muddati tugagan foydalanuvchilar")
async def expired_users_list(message: Message, state: FSMContext, session: AsyncSession):
    if not await _check_admin(message, state):
        return

    users = await get_expired_users(session)
    if not users:
        await message.answer("✅ Muddati tugagan foydalanuvchi yo'q.", reply_markup=get_users_list_menu())
        return

    await message.answer(
        f"⏰ <b>Muddati tugagan foydalanuvchilar ({len(users)} ta):</b>",
        parse_mode="HTML",
        reply_markup=get_users_list_menu()
    )

    for user in users:
        text = (
            f"👤 ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or 'Mavjud emas'}\n"
            f"📅 Tugagan: {format_date(user.expires_at)}\n"
            f"🔴 Holat: Muddat tugagan"
        )
        await message.answer(
            text,
            reply_markup=get_user_actions_keyboard(user.id, is_expired=True),
            parse_mode="HTML"
        )


# ============================================================
# FOYDALANUVCHI O'CHIRISH
# ============================================================

@router.callback_query(F.data.startswith("delete_user_"))
async def delete_user_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not _is_admin_logged_in(await state.get_data()):
        await callback.answer("⛔ Admin sifatida kirmadingiz!")
        return

    user_id = int(callback.data.split("_")[-1])
    user = await get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!")
        return

    await callback.message.edit_text(
        f"🗑 <b>Rostdan o'chirmoqchimisiz?</b>\n\n"
        f"👤 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"📞 Tel: {user.phone or 'N/A'}",
        reply_markup=__import__("aiogram.utils.keyboard", fromlist=["InlineKeyboardBuilder"]).InlineKeyboardBuilder().row(
            __import__("aiogram.types", fromlist=["InlineKeyboardButton"]).InlineKeyboardButton(
                text="🗑 O'chirish", callback_data=f"confirm_delete_user_{user_id}"
            ),
            __import__("aiogram.types", fromlist=["InlineKeyboardButton"]).InlineKeyboardButton(
                text="❌ Bekor", callback_data="cancel_delete_user"
            )
        ).as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_user_"))
async def delete_user_execute(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not _is_admin_logged_in(await state.get_data()):
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    user_id = int(callback.data.split("_")[-1])
    user = await get_user_by_id(session, user_id)
    tg_id = user.telegram_id if user else "?"

    await delete_user(session, user_id)
    await callback.message.edit_text(
        f"✅ <b>Foydalanuvchi o'chirildi!</b>\n"
        f"👤 Telegram ID: <code>{tg_id}</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ O'chirildi!")
    logger.info(f"Foydalanuvchi o'chirildi: id={user_id}, tg_id={tg_id}")


@router.callback_query(F.data == "cancel_delete_user")
async def cancel_delete_user(callback: CallbackQuery):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# ============================================================
# MUDDATNI UZAYTIRISH
# ============================================================

@router.callback_query(F.data.startswith("extend_user_"))
async def extend_user_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin_logged_in(await state.get_data()):
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    user_id = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        "📅 <b>Necha oyga uzaytirmoqchisiz?</b>",
        reply_markup=get_extend_months_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_months_"))
async def extend_user_execute(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    if not _is_admin_logged_in(await state.get_data()):
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    parts = callback.data.split("_")
    user_id = int(parts[2])
    months = int(parts[3])

    user = await get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!")
        return

    new_expires = await extend_user_expiry(session, user_id, months)
    expires_str = format_date(new_expires)

    await callback.message.edit_text(
        f"✅ <b>Muddat uzaytirildi!</b>\n\n"
        f"👤 ID: <code>{user.telegram_id}</code>\n"
        f"📅 Yangi muddat: <b>{expires_str}</b>",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            user.telegram_id,
            f"✅ <b>Limitingiz uzaytirildi!</b>\n\n"
            f"📅 Yangi muddat: <b>{expires_str}</b> gacha",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborilmadi: {user.telegram_id} | {e}")

    await callback.answer(f"✅ {months} oyga uzaytirildi!")
    logger.info(f"Muddat uzaytirildi: user_id={user_id}, months={months}")


# ============================================================
# YANGI FOYDALANUVCHI QO'SHISH
# ============================================================

@router.message(F.text == "➕ Foydalanuvchi qo'shish")
async def add_user_start(message: Message, state: FSMContext):
    if not await _check_admin(message, state):
        return

    await state.set_state(AddUserStates.waiting_telegram_id)
    await message.answer(
        "👤 <b>Foydalanuvchi Telegram ID sini kiriting:</b>\n\n"
        "ℹ️ ID ni bilish uchun foydalanuvchi @userinfobot ga xabar yuborsin.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddUserStates.waiting_telegram_id)
async def add_user_telegram_id(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_menu())
        return

    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ <b>Noto'g'ri format!</b> Faqat raqam kiriting.", parse_mode="HTML")
        return

    # Allaqachon bormi?
    from database.crud import get_user_by_telegram_id
    existing = await get_user_by_telegram_id(session, tg_id)
    if existing:
        await message.answer(
            f"⚠️ <b>Bu Telegram ID allaqachon bazada mavjud!</b>\n"
            f"Muddat: {format_date(existing.expires_at)}",
            parse_mode="HTML"
        )
        return

    await state.update_data(new_user_tg_id=tg_id)
    await state.set_state(AddUserStates.waiting_phone)
    await message.answer(
        "📞 <b>Telefon raqamini kiriting:</b>\n"
        "Misol: <code>+998901234567</code>",
        parse_mode="HTML"
    )


@router.message(AddUserStates.waiting_phone)
async def add_user_phone(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_menu())
        return

    phone = message.text.strip() if message.text else ""
    await state.update_data(new_user_phone=phone)
    await state.set_state(AddUserStates.waiting_months)

    await message.answer(
        "📅 <b>Foydalanuvchi necha oy ishlata olsin?</b>",
        reply_markup=get_months_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("months_"), AddUserStates.waiting_months)
async def add_user_months(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    months = int(callback.data.split("_")[-1])
    data = await state.get_data()
    tg_id = data.get("new_user_tg_id")
    phone = data.get("new_user_phone", "")

    # Parol generatsiya
    password = generate_password(10)

    await state.update_data(new_user_months=months, generated_password=password)
    await state.set_state(AddUserStates.confirm)

    from datetime import datetime, timezone, timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(days=30 * months)

    await callback.message.edit_text(
        f"📋 <b>Yangi foydalanuvchi ma'lumotlari:</b>\n\n"
        f"👤 <b>Telegram ID:</b> <code>{tg_id}</code>\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"🔑 <b>Parol:</b> <code>{password}</code>\n"
        f"📅 <b>Muddat:</b> {months} oy ({format_date(expires_at)} gacha)",
        reply_markup=get_save_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "save", AddUserStates.confirm)
async def add_user_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    tg_id = data.get("new_user_tg_id")
    phone = data.get("new_user_phone", "")
    months = data.get("new_user_months", 1)
    password = data.get("generated_password", "")
    admin_id = data.get("admin_id")

    password_hash = hash_password(password)

    user = await create_user(
        session,
        telegram_id=tg_id,
        password_hash=password_hash,
        months=months,
        phone=phone,
        admin_id=admin_id
    )

    expires_str = format_date(user.expires_at)
    await clear_state(state)

    await callback.message.edit_text(
        f"✅ <b>Foydalanuvchi muvaffaqiyatli qo'shildi!</b>\n\n"
        f"👤 ID: <code>{tg_id}</code>\n"
        f"📅 Muddat: {expires_str}",
        parse_mode="HTML"
    )

    # Foydalanuvchiga ma'lumot yuborish
    from config import config
    sent = await send_user_credentials(
        bot=bot,
        user_telegram_id=tg_id,
        password=password,
        expires_at=expires_str,
        bot_username=config.BOT_USERNAME
    )
    if not sent:
        await callback.message.answer(
            f"⚠️ Foydalanuvchiga xabar yuborilmadi (bot bloklangan bo'lishi mumkin).\n"
            f"🔑 Parol: <code>{password}</code>",
            parse_mode="HTML"
        )

    await callback.message.answer("🏠 Admin menyu:", reply_markup=get_admin_main_menu())
    await callback.answer("✅ Saqlandi!")
    logger.info(f"Yangi foydalanuvchi qo'shildi: tg_id={tg_id}, months={months}")


@router.callback_query(F.data == "cancel", AddUserStates.confirm)
async def add_user_cancel(callback: CallbackQuery, state: FSMContext):
    await clear_state(state)
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer("🏠 Admin menyu:", reply_markup=get_admin_main_menu())
    await callback.answer()
