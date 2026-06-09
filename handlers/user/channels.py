from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    get_user_by_telegram_id,
    get_channels_by_user_id,
    count_user_channels,
    add_channel,
    delete_channel,
    get_channel_by_id,
)
from utils.keyboards import (
    get_channels_menu,
    get_channels_list_keyboard,
    get_channel_delete_confirm,
    get_user_main_menu,
    get_cancel_keyboard,
)
from utils.helpers import (
    is_valid_telegram_link,
    normalize_link,
    is_expired,
    clear_state,
)
from handlers.user.states import ChannelStates

router = Router()

MAX_CHANNELS = 150


def _auth_check(user) -> bool:
    return user and user.is_active and not is_expired(user.expires_at)


# ============================================================
# KANALLAR MENYUSI
# ============================================================

@router.message(F.text == "📢 Guruh va kanallar")
async def channels_menu(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        await message.answer("⚠️ Avval kiring.", reply_markup=__import__("utils.keyboards", fromlist=["get_start_keyboard"]).get_start_keyboard())
        return

    count = await count_user_channels(session, user.id)
    await message.answer(
        f"📢 <b>Guruh va kanallar</b>\n"
        f"Qo'shilgan linklar: <b>{count}</b> / {MAX_CHANNELS}",
        reply_markup=get_channels_menu(),
        parse_mode="HTML"
    )


# ============================================================
# YANGI LINK QO'SHISH
# ============================================================

@router.message(F.text == "➕ Yangi link qo'shish")
async def add_channel_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    count = await count_user_channels(session, user.id)
    if count >= MAX_CHANNELS:
        await message.answer(
            f"🚫 <b>Maksimal {MAX_CHANNELS} ta link qo'shish mumkin.</b>\n"
            "Avval eskisini o'chiring.",
            parse_mode="HTML"
        )
        return

    await state.set_state(ChannelStates.waiting_link)
    await state.update_data(user_id=user.id)
    await message.answer(
        "🔗 <b>E'lon tashlash uchun guruh/kanal linkini kiriting:</b>\n\n"
        "Qabul qilinadigan formatlar:\n"
        "• <code>https://t.me/username</code>\n"
        "• <code>https://t.me/+hashcode</code>\n"
        "• <code>@username</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(ChannelStates.waiting_link)
async def add_channel_link(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await clear_state(state)
        await message.answer("❌ Bekor qilindi.", reply_markup=get_channels_menu())
        return

    link = message.text.strip() if message.text else ""

    if not is_valid_telegram_link(link):
        await message.answer(
            "❌ <b>Noto'g'ri format!</b> Qayta kiriting.\n\n"
            "Misol: <code>https://t.me/username</code> yoki <code>@username</code>",
            parse_mode="HTML"
        )
        return

    link = normalize_link(link)
    data = await state.get_data()
    user_id = data.get("user_id")

    count = await count_user_channels(session, user_id)
    if count >= MAX_CHANNELS:
        await clear_state(state)
        await message.answer(
            f"🚫 Maksimal {MAX_CHANNELS} ta limit to'ldi.",
            reply_markup=get_channels_menu()
        )
        return

    channel = await add_channel(session, user_id, link)
    await clear_state(state)

    if channel:
        await message.answer(
            f"✅ <b>Link muvaffaqiyatli qo'shildi!</b>\n\n"
            f"⚠️ <i>Diqqat: Bot guruhda/kanalda xabar yuborish huquqiga ega bo'lishi "
            f"va cheklanmagan/muzlatilmagan bo'lishi kerak!</i>",
            parse_mode="HTML",
            reply_markup=get_channels_menu()
        )
    else:
        await message.answer(
            "❌ Link qo'shishda xato yuz berdi.",
            reply_markup=get_channels_menu()
        )


# ============================================================
# BARCHA LINKLARNI KO'RISH
# ============================================================

@router.message(F.text == "📋 Barcha linklarni ko'rish")
async def list_channels(message: Message, state: FSMContext, session: AsyncSession):
    await clear_state(state)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not _auth_check(user):
        return

    channels = await get_channels_by_user_id(session, user.id)
    if not channels:
        await message.answer(
            "📭 <b>Hali hech qanday link qo'shilmagan.</b>",
            parse_mode="HTML",
            reply_markup=get_channels_menu()
        )
        return

    await message.answer(
        f"📋 <b>Sizning linklaringiz ({len(channels)} ta):</b>",
        reply_markup=get_channels_list_keyboard(channels),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "channels_list")
async def channels_list_callback(callback: CallbackQuery, session: AsyncSession):
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not _auth_check(user):
        await callback.answer("⚠️ Avval kiring!")
        return

    channels = await get_channels_by_user_id(session, user.id)
    if not channels:
        await callback.message.edit_text("📭 Hali hech qanday link yo'q.")
        return

    await callback.message.edit_text(
        f"📋 <b>Sizning linklaringiz ({len(channels)} ta):</b>",
        reply_markup=get_channels_list_keyboard(channels),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "channels_back")
async def channels_back_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ============================================================
# KANALNI O'CHIRISH
# ============================================================

@router.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel_confirm(callback: CallbackQuery, session: AsyncSession):
    channel_id = int(callback.data.split("_")[-1])
    channel = await get_channel_by_id(session, channel_id)

    if not channel:
        await callback.answer("❌ Kanal topilmadi!")
        return

    # Ownership tekshiruvi
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user or channel.user_id != user.id:
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    link_text = channel.link if len(channel.link) <= 40 else channel.link[:37] + "..."
    await callback.message.edit_text(
        f"🗑 <b>Rostdan o'chirmoqchimisiz?</b>\n\n"
        f"🔗 {link_text}",
        reply_markup=get_channel_delete_confirm(channel_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_channel_"))
async def delete_channel_execute(callback: CallbackQuery, session: AsyncSession):
    channel_id = int(callback.data.split("_")[-1])
    channel = await get_channel_by_id(session, channel_id)

    if not channel:
        await callback.answer("❌ Kanal topilmadi!")
        return

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user or channel.user_id != user.id:
        await callback.answer("⛔ Ruxsat yo'q!")
        return

    await delete_channel(session, channel_id)

    channels = await get_channels_by_user_id(session, user.id)
    if channels:
        await callback.message.edit_text(
            f"✅ Link o'chirildi!\n\n"
            f"📋 <b>Qolgan linklaringiz ({len(channels)} ta):</b>",
            reply_markup=get_channels_list_keyboard(channels),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "✅ Link o'chirildi!\n\n📭 Linklaringiz yo'q."
        )
    await callback.answer("✅ O'chirildi!")
