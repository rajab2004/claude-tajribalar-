"""
Admin statistika va sozlamalar
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from services.password_gen import generate_password
from utils.keyboards import admin_main_menu, save_cancel_keyboard
import config

router = Router()


class AdminSettingsStates(StatesGroup):
    waiting_new_password = State()
    waiting_gmail = State()
    waiting_phone = State()
    waiting_change_user_id = State()


# ─── Statistika ────────────────────────────────────────────────────────
@router.message(F.text == "📊 Bot statistikasi")
async def bot_stats(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return

    stats = await crud.get_statistics(db)
    await message.answer(
        f"📊 <b>BOT STATISTIKASI</b>\n"
        f"{'━' * 25}\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"🟢 Faol: {stats['active_users']}\n"
        f"🔴 Nofaol: {stats['inactive_users']}\n"
        f"⏰ Muddati tugagan: {stats['expired_users']}\n"
        f"{'━' * 25}\n"
        f"📱 Ulangan akkauntlar: {stats['connected_sessions']}\n"
        f"{'━' * 25}\n"
        f"📝 Jami e'lonlar: {stats['total_announcements']}\n"
        f"📢 Ochiq e'lonlar: {stats['open_announcements']}\n"
        f"🔒 Yopilgan e'lonlar: {stats['closed_announcements']}\n"
        f"{'━' * 25}",
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )


# ─── Admin sozlamalari ─────────────────────────────────────────────────
@router.message(F.text == "⚙️ Admin sozlamalari")
async def admin_settings(message: Message):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Parolni o'zgartirish",
                   callback_data="adm_cfg:password")
    builder.button(text="📧 Gmail o'zgartirish",
                   callback_data="adm_cfg:gmail")
    builder.button(text="📞 Bog'lanish ma'lumotlari",
                   callback_data="adm_cfg:contact")
    builder.button(text="🔑 User parolini o'zgartirish",
                   callback_data="adm_cfg:user_pass")
    builder.adjust(1)
    await message.answer(
        "⚙️ Admin sozlamalari:",
        reply_markup=builder.as_markup()
    )


# ─── Admin parolini o'zgartirish ───────────────────────────────────────
@router.callback_query(F.data == "adm_cfg:password")
async def change_admin_password(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettingsStates.waiting_new_password)
    await callback.message.edit_text("🔑 Yangi parolni kiriting:")
    await callback.answer()


@router.message(AdminSettingsStates.waiting_new_password)
async def save_admin_password(message: Message, state: FSMContext,
                               db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    new_pw = message.text.strip()
    if len(new_pw) < 6:
        await message.answer("❌ Parol kamida 6 belgi bo'lishi kerak!")
        return
    admin = await crud.get_admin_by_telegram_id(db, config.ADMIN_TELEGRAM_ID)
    if admin:
        await crud.update_admin_password(db, admin.id, new_pw)
        await db.commit()
    await state.clear()
    await message.answer(
        "✅ Admin paroli o'zgartirildi!\n"
        "⚠️ .env fayldagi ADMIN_PASSWORD ni ham yangilang!",
        reply_markup=admin_main_menu()
    )


# ─── Gmail o'zgartirish ─────────────────────────────────────────────────
@router.callback_query(F.data == "adm_cfg:gmail")
async def change_gmail(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettingsStates.waiting_gmail)
    await callback.message.edit_text("📧 Yangi Gmail manzilini kiriting:")
    await callback.answer()


@router.message(AdminSettingsStates.waiting_gmail)
async def save_gmail(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    gmail = message.text.strip()
    if "@" not in gmail:
        await message.answer("❌ Noto'g'ri email format!")
        return
    admin = await crud.get_admin_by_telegram_id(db, config.ADMIN_TELEGRAM_ID)
    if admin:
        await crud.update_admin_info(db, admin.id, gmail=gmail)
        await db.commit()
    await state.clear()
    await message.answer(
        f"✅ Gmail manzil o'zgartirildi: {gmail}",
        reply_markup=admin_main_menu()
    )


# ─── Bog'lanish ma'lumotlari ───────────────────────────────────────────
@router.callback_query(F.data == "adm_cfg:contact")
async def change_contact(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSettingsStates.waiting_phone)
    await callback.message.edit_text(
        "📞 Yangi telefon raqamini kiriting (+998XXXXXXXXX):"
    )
    await callback.answer()


@router.message(AdminSettingsStates.waiting_phone)
async def save_contact(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    from utils.helpers import normalize_phone
    phone = normalize_phone(message.text.strip())
    if not phone:
        await message.answer("❌ Noto'g'ri format!")
        return
    admin = await crud.get_admin_by_telegram_id(db, config.ADMIN_TELEGRAM_ID)
    if admin:
        await crud.update_admin_info(db, admin.id, phone=phone)
        await db.commit()
    await state.clear()
    await message.answer(
        f"✅ Telefon raqam o'zgartirildi: {phone}",
        reply_markup=admin_main_menu()
    )


# ─── User parolini o'zgartirish ────────────────────────────────────────
@router.callback_query(F.data == "adm_cfg:user_pass")
async def change_user_password_start(callback: CallbackQuery,
                                      state: FSMContext):
    await state.set_state(AdminSettingsStates.waiting_change_user_id)
    await callback.message.edit_text(
        "👤 Foydalanuvchi Telegram ID sini kiriting:"
    )
    await callback.answer()


@router.message(AdminSettingsStates.waiting_change_user_id)
async def change_user_password(message: Message, state: FSMContext,
                                db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Telegram ID faqat raqam bo'lishi kerak!")
        return

    tg_id = int(message.text.strip())
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!")
        await state.clear()
        return

    new_password = generate_password(10)
    await crud.update_user_password(db, user.id, new_password)
    await crud.reset_wrong_attempts(db, user.id)
    await db.commit()
    await state.clear()

    # Foydalanuvchiga yangi parolni yuborish
    try:
        await message.bot.send_message(
            tg_id,
            f"🔑 Parolingiz o'zgartirildi!\n\n"
            f"Yangi parolingiz: <code>{new_password}</code>",
            parse_mode="HTML"
        )
        notify = "✅ Yangi parol foydalanuvchiga yuborildi."
    except Exception:
        notify = (f"⚠️ Foydalanuvchiga yuborib bo'lmadi.\n"
                  f"Parol: <code>{new_password}</code>")

    await message.answer(
        f"✅ Parol yangilandi!\n{notify}",
        reply_markup=admin_main_menu(),
        parse_mode="HTML"
    )
