"""
Admin — foydalanuvchilar boshqaruvi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from services.password_gen import generate_password
from utils.keyboards import (
    admin_main_menu, users_list_menu,
    months_keyboard, user_action_keyboard,
    save_cancel_keyboard
)
from utils.helpers import format_expiry, normalize_phone
import config

router = Router()


class AddUserStates(StatesGroup):
    waiting_tg_id = State()
    waiting_phone = State()
    waiting_months = State()
    waiting_confirm = State()


class ExtendUserStates(StatesGroup):
    waiting_months = State()


# ═══════════════════════════════════════════════════════
#  FOYDALANUVCHI QO'SHISH
# ═══════════════════════════════════════════════════════

@router.message(F.text == "➕ Foydalanuvchi qo'shish")
async def add_user_start(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    await state.set_state(AddUserStates.waiting_tg_id)
    await message.answer("👤 Foydalanuvchi Telegram ID sini kiriting:")


@router.message(AddUserStates.waiting_tg_id)
async def add_user_tg_id(message: Message, state: FSMContext, db: AsyncSession):
    tg_id_text = message.text.strip()
    if not tg_id_text.isdigit():
        await message.answer("❌ Telegram ID faqat raqamlardan iborat bo'lishi kerak!")
        return

    tg_id = int(tg_id_text)
    existing = await crud.get_user_by_telegram_id(db, tg_id)
    if existing:
        await message.answer(
            f"⚠️ Bu Telegram ID allaqachon ro'yxatdan o'tgan!\n"
            f"ID: {tg_id}"
        )
        return

    await state.update_data(tg_id=tg_id)
    await state.set_state(AddUserStates.waiting_phone)
    await message.answer("📞 Telefon raqamini kiriting (+998XXXXXXXXX):")


@router.message(AddUserStates.waiting_phone)
async def add_user_phone(message: Message, state: FSMContext):
    phone = normalize_phone(message.text.strip())
    if not phone:
        await message.answer("❌ Noto'g'ri format! +998XXXXXXXXX formatida kiriting.")
        return

    # Parolni avtomatik generatsiya
    password = generate_password(10)
    await state.update_data(phone=phone, password=password)
    await state.set_state(AddUserStates.waiting_months)
    await message.answer(
        f"🔑 Avtomatik parol: <code>{password}</code>\n\n"
        f"📅 Necha oy ishlata olsin?",
        reply_markup=months_keyboard("add_months"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("add_months:"))
async def add_user_months(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.update_data(months=months)

    await callback.message.edit_text(
        f"📋 Yangi foydalanuvchi:\n"
        f"{'━' * 25}\n"
        f"👤 Telegram ID: <code>{data['tg_id']}</code>\n"
        f"📞 Telefon: {data['phone']}\n"
        f"🔑 Parol: <code>{data['password']}</code>\n"
        f"📅 Muddat: {months} oy\n"
        f"{'━' * 25}\n\n"
        f"Saqlaysizmi?",
        reply_markup=save_cancel_keyboard("admin_user:save", "admin_user:cancel"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_user:save")
async def add_user_save(callback: CallbackQuery, state: FSMContext,
                         db: AsyncSession):
    data = await state.get_data()
    admin = await crud.get_admin_by_telegram_id(db, config.ADMIN_TELEGRAM_ID)

    user = await crud.create_user(
        db,
        telegram_id=data["tg_id"],
        phone=data["phone"],
        password=data["password"],
        months=data["months"],
        admin_id=admin.id if admin else 1,
    )
    await db.commit()
    await state.clear()

    # Foydalanuvchiga xabar yuborish
    try:
        bot = callback.bot
        await bot.send_message(
            data["tg_id"],
            f"🎉 Xush kelibsiz!\n\n"
            f"Sizga bot kirish ma'lumotlari:\n"
            f"🔑 Parol: <code>{data['password']}</code>\n"
            f"📅 Muddat: {data['months']} oy\n\n"
            f"Botga o'tish va boshlash uchun /start bosing.",
            parse_mode="HTML"
        )
        notify = "✅ Foydalanuvchiga xabar yuborildi."
    except Exception:
        notify = "⚠️ Foydalanuvchiga xabar yuborishda xatolik (bot bilan suhbat yo'q)."

    await callback.message.edit_text(
        f"✅ Foydalanuvchi muvaffaqiyatli qo'shildi!\n\n{notify}"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_user:cancel")
async def add_user_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# ═══════════════════════════════════════════════════════
#  FOYDALANUVCHILAR RO'YHATI
# ═══════════════════════════════════════════════════════

@router.message(F.text == "👥 Foydalanuvchilar ro'yhati")
async def users_list(message: Message):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    await message.answer(
        "👥 Foydalanuvchilar bo'limi:",
        reply_markup=users_list_menu()
    )


@router.message(F.text == "👥 Barcha foydalanuvchilar")
async def all_users(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    users = await crud.get_all_users(db)

    if not users:
        await message.answer("📭 Hech qanday foydalanuvchi yo'q.")
        return

    for user in users:
        from datetime import datetime
        is_exp = user.expires_at < datetime.utcnow()
        status = "🔴 Muddati tugagan" if is_exp else ("🟢 Faol" if user.is_active else "⚫ Nofaol")
        await message.answer(
            f"👤 ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or '—'}\n"
            f"📅 {format_expiry(user.expires_at)}\n"
            f"⚡ {status}",
            reply_markup=user_action_keyboard(user.id),
            parse_mode="HTML"
        )

    await message.answer(f"📊 Jami: {len(users)} ta", reply_markup=users_list_menu())


@router.message(F.text == "🟢 Faol foydalanuvchilar")
async def active_users(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    users = await crud.get_active_users(db)

    if not users:
        await message.answer("📭 Faol foydalanuvchi yo'q.")
        return

    for user in users:
        await message.answer(
            f"🟢 ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or '—'}\n"
            f"📅 {format_expiry(user.expires_at)}",
            reply_markup=user_action_keyboard(user.id),
            parse_mode="HTML"
        )

    await message.answer(f"📊 Faol: {len(users)} ta", reply_markup=users_list_menu())


@router.message(F.text == "⏰ Muddati tugaganlar")
async def expired_users_list(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    users = await crud.get_expired_users(db)

    if not users:
        await message.answer("📭 Muddati tugagan foydalanuvchi yo'q.")
        return

    for user in users:
        await message.answer(
            f"⏰ ID: <code>{user.telegram_id}</code>\n"
            f"📞 Tel: {user.phone or '—'}\n"
            f"📅 Tugagan: {user.expires_at.strftime('%d.%m.%Y')}",
            reply_markup=user_action_keyboard(user.id, show_extend=True),
            parse_mode="HTML"
        )

    await message.answer(f"📊 Muddati tugagan: {len(users)} ta",
                         reply_markup=users_list_menu())


# ─── O'chirish ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin_user:delete:"))
async def delete_user_cb(callback: CallbackQuery, db: AsyncSession):
    if callback.from_user.id != config.ADMIN_TELEGRAM_ID:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    user = await crud.get_user_by_id(db, user_id)
    if user:
        try:
            await callback.bot.send_message(
                user.telegram_id,
                "❌ Sizning hisobingiz o'chirildi."
            )
        except Exception:
            pass
    await crud.delete_user(db, user_id)
    await db.commit()
    await callback.message.edit_text("🗑 Foydalanuvchi o'chirildi.")
    await callback.answer("✅ O'chirildi")


# ─── Muddatni uzaytirish ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin_user:extend:"))
async def extend_user_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_TELEGRAM_ID:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    await state.update_data(extend_user_id=user_id)
    await callback.message.edit_text(
        "📅 Qancha muddatga uzaytirmoqchisiz?",
        reply_markup=months_keyboard("extend_months")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_months:"))
async def extend_months_cb(callback: CallbackQuery, state: FSMContext,
                            db: AsyncSession):
    months = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_id = data.get("extend_user_id")

    if not user_id:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    await crud.extend_user_expiry(db, user_id, months)
    user = await crud.get_user_by_id(db, user_id)
    await db.commit()
    await state.clear()

    if user:
        try:
            await callback.bot.send_message(
                user.telegram_id,
                f"🎉 Hisobingiz faollashtirildi!\n"
                f"📅 Yangi muddat: {user.expires_at.strftime('%d.%m.%Y')} gacha"
            )
        except Exception:
            pass

    await callback.message.edit_text(
        f"✅ Muddat {months} oyga uzaytirildi!"
    )
    await callback.answer()


@router.message(F.text == "🔙 Admin menyu")
async def back_to_admin(message: Message):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    await message.answer("⚙️ Admin panel:", reply_markup=admin_main_menu())
