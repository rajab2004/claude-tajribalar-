"""
Guruh va kanallar boshqaruvi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from utils.keyboards import (
    channels_menu, user_main_menu,
    save_cancel_keyboard, InlineKeyboardBuilder
)
from utils.helpers import is_valid_channel_link
import config

router = Router()


class ChannelStates(StatesGroup):
    waiting_link = State()


@router.message(F.text == "📢 Guruh va kanallar")
async def channels_menu_handler(message: Message, state: FSMContext,
                                 db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await message.answer("❌ Avval tizimga kiring.")
        return

    channels = await crud.get_user_channels(db, user.id)
    await message.answer(
        f"📢 Guruh va Kanallar\n"
        f"📊 Qo'shilgan: {len(channels)}/{config.MAX_CHANNELS}",
        reply_markup=channels_menu()
    )


@router.message(F.text == "➕ Yangi link qo'shish")
async def add_channel_start(message: Message, state: FSMContext,
                             db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        return

    channels = await crud.get_user_channels(db, user.id)
    if len(channels) >= config.MAX_CHANNELS:
        await message.answer(
            f"❌ Maksimal {config.MAX_CHANNELS} ta link qo'shish mumkin!\n"
            "Avval eskisini o'chiring."
        )
        return

    await state.set_state(ChannelStates.waiting_link)
    await message.answer(
        "🔗 Guruh yoki kanal linkini kiriting:\n\n"
        "📌 Format: https://t.me/guruhadi yoki @guruhadi\n\n"
        "⚠️ <b>Muhim eslatma:</b>\n"
        "Xabarlar <b>sizning Telegram akkauntingizdan</b> yuboriladi.\n"
        "Shuning uchun:\n"
        "  • Siz o'sha guruh/kanalga a'zo bo'lishingiz kerak\n"
        "  • Guruhda yozish imkoniyati cheklanmagan bo'lishi kerak\n"
        "  • Guruhda siz muzlatilmagan bo'lishingiz kerak\n\n"
        "🤖 Bot guruhda admin bo'lishi shart emas!",
        parse_mode="HTML"
    )


@router.message(ChannelStates.waiting_link)
async def add_channel_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not is_valid_channel_link(link):
        await message.answer(
            "❌ Noto'g'ri link formati!\n"
            "Format: https://t.me/guruhadi yoki @guruhadi"
        )
        return

    await state.update_data(link=link)
    kb = save_cancel_keyboard("ch:save", "ch:cancel")
    await message.answer(
        f"🔗 Link: <code>{link}</code>\n\n"
        f"Saqlaysizmi?",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "ch:save")
async def save_channel(callback: CallbackQuery, state: FSMContext,
                        db: AsyncSession):
    data = await state.get_data()
    tg_id = callback.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)

    ch = await crud.add_channel(db, user.id, data["link"])
    await db.commit()
    await state.clear()

    if ch is None:
        await callback.message.edit_text(
            f"❌ Maksimal {config.MAX_CHANNELS} ta limit!"
        )
    else:
        await callback.message.edit_text(
            f"✅ Link muvaffaqiyatli qo'shildi!\n🔗 {data['link']}"
        )
    await callback.answer()


@router.callback_query(F.data == "ch:cancel")
async def cancel_channel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


@router.message(F.text == "📋 Barcha linklarni ko'rish")
async def list_channels(message: Message, db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        return

    channels = await crud.get_user_channels(db, user.id)
    if not channels:
        await message.answer(
            "📭 Hech qanday link qo'shilmagan.\n"
            "➕ Yangi link qo'shing.",
            reply_markup=channels_menu()
        )
        return

    for ch in channels:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🗑 O'chirish",
            callback_data=f"ch:del:{ch.id}"
        )
        await message.answer(
            f"🔗 {ch.link}\n"
            f"📅 {ch.added_at.strftime('%d.%m.%Y')}",
            reply_markup=builder.as_markup()
        )

    await message.answer(
        f"📊 Jami: {len(channels)}/{config.MAX_CHANNELS} ta",
        reply_markup=channels_menu()
    )


@router.callback_query(F.data.startswith("ch:del:"))
async def delete_channel_cb(callback: CallbackQuery, db: AsyncSession):
    ch_id = int(callback.data.split(":")[2])
    tg_id = callback.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    await crud.delete_channel(db, ch_id, user.id)
    await db.commit()
    await callback.message.edit_text("🗑 Link o'chirildi.")
    await callback.answer("✅ O'chirildi")


@router.message(F.text == "🏠 Bosh menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh menyu:", reply_markup=user_main_menu())
