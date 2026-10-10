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
from utils.helpers import is_valid_channel_link, parse_bulk_links
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
        "🔗 Guruh yoki kanal linkini kiriting.\n\n"
        "📌 1 ta link ham, 150 tagacha link ham yuborishingiz mumkin — "
        "har birini alohida qatorga yozing:\n"
        "https://t.me/guruh1\n"
        "https://t.me/guruh2\n"
        "@guruh3 ...\n\n"
        "⚠️ <b>Muhim eslatma:</b>\n"
        "Xabarlar <b>sizning Telegram akkauntingizdan</b> yuboriladi.\n"
        "Shuning uchun:\n"
        "  • Siz o'sha guruh/kanalga a'zo bo'lishingiz kerak\n"
        "  • Guruhda yozish imkoniyati cheklanmagan bo'lishi kerak\n"
        "  • Guruhda siz muzlatilmagan bo'lishingiz kerak\n\n"
        "🤖 Bot guruhga o'zi qo'shilmaydi — faqat siz allaqachon "
        "a'zo bo'lgan guruhga yozadi!",
        parse_mode="HTML"
    )


@router.message(ChannelStates.waiting_link)
async def add_channel_link(message: Message, state: FSMContext,
                            db: AsyncSession):
    tg_id = message.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)
    if not user:
        await state.clear()
        return

    links, invalid_count = parse_bulk_links(message.text or "")
    if not links:
        await message.answer(
            "❌ To'g'ri formatdagi link topilmadi!\n"
            "Format: https://t.me/guruhadi yoki @guruhadi\n"
            "Bir nechta bo'lsa — har birini alohida qatorga yozing."
        )
        return

    existing = await crud.get_user_channel_links(db, user.id)
    new_links = [l for l in links if l not in existing]
    already_added = len(links) - len(new_links)

    room = max(0, config.MAX_CHANNELS - len(existing))
    to_save = new_links[:room]
    overflow = len(new_links) - len(to_save)

    if not to_save:
        await message.answer(
            "❌ Saqlash uchun bo'sh joy yo'q yoki barcha linklar "
            "allaqachon qo'shilgan."
        )
        return

    await state.update_data(links=to_save)

    if len(links) == 1 and len(to_save) == 1:
        text = f"🔗 Link: <code>{to_save[0]}</code>\n\nSaqlaysizmi?"
    else:
        text = (
            f"📊 {len(links)} ta link aniqlandi.\n"
            f"✅ Saqlanadigan: {len(to_save)} ta\n"
        )
        if already_added:
            text += f"♻️ {already_added} ta allaqachon qo'shilgan (o'tkazib yuborildi)\n"
        if invalid_count:
            text += f"⚠️ {invalid_count} ta noto'g'ri formatda edi\n"
        if overflow:
            text += (
                f"🚫 {overflow} ta link {config.MAX_CHANNELS} ta limit "
                f"tufayli sig'madi\n"
            )
        text += f"\n<b>{len(to_save)} ta linkni saqlamoqchimisiz?</b>"

    await message.answer(
        text,
        reply_markup=save_cancel_keyboard("ch:save", "ch:cancel"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "ch:save")
async def save_channel(callback: CallbackQuery, state: FSMContext,
                        db: AsyncSession):
    data = await state.get_data()
    links = data.get("links", [])
    tg_id = callback.from_user.id
    user = await crud.get_user_by_telegram_id(db, tg_id)

    if not user or not links:
        await callback.message.edit_text("❌ Xatolik yuz berdi.")
        await state.clear()
        await callback.answer()
        return

    result = await crud.add_channels_bulk(db, user.id, links)
    await db.commit()
    await state.clear()

    parts = [f"✅ {result['added']} ta link muvaffaqiyatli saqlandi!"]
    if result["duplicates"]:
        parts.append(f"♻️ {result['duplicates']} ta takroriy edi")
    if result["overflow"]:
        parts.append(
            f"🚫 {result['overflow']} ta link {config.MAX_CHANNELS} ta "
            f"limit tufayli saqlanmadi"
        )
    await callback.message.edit_text("\n".join(parts))
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
