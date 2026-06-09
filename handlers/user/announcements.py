from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.crud import (
    get_user_by_telegram_id,
    get_channels_by_user_id,
    create_announcement,
    get_announcement_by_id,
    get_open_announcements_by_user,
    get_closed_announcements_by_user,
    close_announcement,
    deactivate_channel,
)
from services.pyrogram_client import send_to_all_channels
from utils.keyboards import (
    get_announcement_confirm_keyboard,
    get_close_announcement_keyboard,
    get_my_announcements_menu,
    get_open_announcements_keyboard,
    get_closed_announcements_keyboard,
    get_user_main_menu,
    get_cancel_keyboard,
)
from utils.helpers import (
    is_expired,
    clear_state,
    truncate_text,
    format_datetime,
)
from handlers.user.states import AnnouncementStates

router = Router()


def _auth_check(user) -> bool:
    return user and user.is_active and not is_expired(user.expires_at)


# ============================================================
# YANGI E'LON YARATISH
# ============================================================

@router.message(F.text == "📝 Yangi e'lon yaratish")
async def new_announcement_start(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        await message.answer("⚠️ Avval kiring.")
        return

    channels = await get_channels_by_user_id(session, user.id)
    if not channels:
        await message.answer(
            "📭 <b>Hali hech qanday kanal/guruh qo'shilmagan!</b>\n\n"
            "Avval <b>📢 Guruh va kanallar</b> bo'limidan link qo'shing.",
            parse_mode="HTML",
            reply_markup=get_user_main_menu()
        )
        return

    await state.set_state(AnnouncementStates.waiting_text)
    await state.update_data(user_id=user.id)
    await message.answer(
        "📝 <b>Guruh va kanallarga yubormoqchi bo'lgan xabaringizni yozing:</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AnnouncementStates.waiting_text)
async def new_announcement_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_main_menu())
        return

    if not message.text or not message.text.strip():
        await message.answer("❌ Xabar bo'sh bo'lmasligi kerak!")
        return

    text = message.text.strip()
    await state.update_data(announcement_text=text)
    await state.set_state(AnnouncementStates.confirm)

    await message.answer(
        f"📋 <b>Quyidagi e'lonni yuborasizmi?</b>\n"
        f"──────────────────\n"
        f"{text}\n"
        f"──────────────────",
        reply_markup=get_announcement_confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_announcement")
async def cancel_announcement(callback: CallbackQuery, state: FSMContext):
    await clear_state(state)
    await callback.message.edit_text("❌ E'lon bekor qilindi.")
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=get_user_main_menu())
    await callback.answer()


@router.callback_query(F.data == "send_announcement", AnnouncementStates.confirm)
async def send_announcement_execute(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot
):
    data = await state.get_data()
    user_id = data.get("user_id")
    text = data.get("announcement_text", "")
    await clear_state(state)

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not _auth_check(user):
        await callback.answer("⚠️ Avval kiring!")
        return

    channels = await get_channels_by_user_id(session, user.id)
    if not channels:
        await callback.message.edit_text("📭 Kanallar topilmadi.")
        return

    await callback.message.edit_text("⏳ <b>Yuborilmoqda...</b>", parse_mode="HTML")

    # Xabarlarni yuborish
    success_count, fail_count, failed_channel_ids = await send_to_all_channels(
        user_id=user.id,
        channels=channels,
        text=text,
    )

    # Muvaffaqiyatsiz kanallarni deaktiv qilish
    if failed_channel_ids:
        for ch_id in failed_channel_ids:
            await deactivate_channel(session, ch_id)

    # E'lonni bazaga saqlash
    announcement = await create_announcement(
        session,
        user_id=user.id,
        message_text=text,
        interval_minutes=5,  # default
    )

    # Natija xabari
    result_text = f"✅ <b>Yuborildi!</b>\n"
    if fail_count > 0:
        result_text += (
            f"📤 {success_count} ta guruhga yetkazildi\n"
            f"❌ {fail_count} ta guruhga yuborilmadi va o'chirildi"
        )
    else:
        result_text += f"📤 {success_count} ta guruhga yetkazildi"

    await callback.message.edit_text(result_text, parse_mode="HTML")

    # Bot chatida e'lon + "Yuk ochiq" + Yopish tugmasi
    preview = truncate_text(text, 200)
    await bot.send_message(
        callback.from_user.id,
        f"📦 <b>Yuk ochiq</b>\n\n{preview}",
        reply_markup=get_close_announcement_keyboard(announcement.id),
        parse_mode="HTML"
    )

    # Bosh menyuga qaytish
    await bot.send_message(
        callback.from_user.id,
        "🏠 <b>Bosh menyu</b>",
        reply_markup=get_user_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()
    logger.info(
        f"E'lon yuborildi: user={user.id}, "
        f"success={success_count}, fail={fail_count}"
    )


# ============================================================
# E'LONNI YOPISH (inline tugma)
# ============================================================

@router.callback_query(F.data.startswith("close_ann_"))
async def close_announcement_callback(
    callback: CallbackQuery,
    session: AsyncSession
):
    ann_id = int(callback.data.split("_")[-1])
    announcement = await get_announcement_by_id(session, ann_id)

    if not announcement:
        await callback.answer("❌ E'lon topilmadi!")
        return

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user or announcement.user_id != user.id:
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    if announcement.status == "closed":
        await callback.answer("ℹ️ E'lon allaqachon yopilgan!")
        return

    await close_announcement(session, ann_id)

    # Xabardagi matnni tahrirlash
    original_text = callback.message.text or ""
    # "📦 Yuk ochiq" ni "🔒 Yuk yopildi" ga almashtirish
    new_text = original_text.replace("📦 Yuk ochiq", "🔒 Yuk yopildi")

    await callback.message.edit_text(new_text, parse_mode="HTML")
    await callback.answer("✅ E'lon yopildi!")
    logger.info(f"E'lon yopildi: id={ann_id}, user={user.id}")


# ============================================================
# MENING E'LONLARIM
# ============================================================

@router.message(F.text == "📋 Mening e'lonlarim")
async def my_announcements_menu(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        await message.answer("⚠️ Avval kiring.")
        return

    await message.answer(
        "📋 <b>Mening e'lonlarim</b>",
        reply_markup=get_my_announcements_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "📢 Ochiq e'lonlarim")
async def open_announcements_list(message: Message, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    announcements = await get_open_announcements_by_user(session, user.id)
    if not announcements:
        await message.answer(
            "📭 <b>Ochiq e'lonlar yo'q.</b>",
            parse_mode="HTML",
            reply_markup=get_my_announcements_menu()
        )
        return

    await message.answer(
        f"📢 <b>Ochiq e'lonlaringiz ({len(announcements)} ta):</b>",
        reply_markup=get_open_announcements_keyboard(announcements),
        parse_mode="HTML"
    )


@router.message(F.text == "🔒 Yopilgan e'lonlarim")
async def closed_announcements_list(message: Message, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    announcements = await get_closed_announcements_by_user(session, user.id)
    if not announcements:
        await message.answer(
            "📭 <b>Yopilgan e'lonlar yo'q.</b>",
            parse_mode="HTML",
            reply_markup=get_my_announcements_menu()
        )
        return

    await message.answer(
        f"🔒 <b>Yopilgan e'lonlaringiz ({len(announcements)} ta):</b>",
        reply_markup=get_closed_announcements_keyboard(announcements),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "my_ann_back")
async def my_ann_back_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("ann_preview_"))
async def open_ann_preview(callback: CallbackQuery, session: AsyncSession):
    ann_id = int(callback.data.split("_")[-1])
    ann = await get_announcement_by_id(session, ann_id)
    if not ann:
        await callback.answer("❌ Topilmadi!")
        return
    await callback.answer(
        f"📝 {truncate_text(ann.message_text, 200)}",
        show_alert=True
    )


@router.callback_query(F.data.startswith("closed_ann_preview_"))
async def closed_ann_preview(callback: CallbackQuery, session: AsyncSession):
    ann_id = int(callback.data.split("_")[-1])
    ann = await get_announcement_by_id(session, ann_id)
    if not ann:
        await callback.answer("❌ Topilmadi!")
        return
    closed_at = format_datetime(ann.closed_at) if ann.closed_at else "Noma'lum"
    await callback.answer(
        f"🔒 Yopildi: {closed_at}\n\n{truncate_text(ann.message_text, 150)}",
        show_alert=True
    )


# ============================================================
# ADMIN BILAN BOG'LANISH
# ============================================================

@router.message(F.text == "📞 Admin bilan bog'lanish")
async def admin_contact(message: Message, session: AsyncSession):
    from database.crud import get_first_admin
    admin = await get_first_admin(session)
    if not admin:
        await message.answer("❌ Admin ma'lumotlari topilmadi.")
        return

    await message.answer(
        "📞 <b>Admin bilan bog'lanish:</b>\n\n"
        f"📱 <b>Telefon:</b> {admin.phone or 'Mavjud emas'}\n"
        f"💬 <b>Telegram:</b> @{admin.username or 'Mavjud emas'}",
        parse_mode="HTML",
        reply_markup=get_user_main_menu()
    )
