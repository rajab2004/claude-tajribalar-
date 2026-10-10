"""
Admin — umumiy guruh linklari (150 tagacha) boshqaruvi.
Admin ruxsat bergan foydalanuvchilar o'zi guruh qo'shmasdan
shu umumiy linklardan foydalanib e'lon yubora oladi.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import crud
from utils.keyboards import shared_channels_menu, save_cancel_keyboard
from utils.helpers import parse_bulk_links
import config

router = Router()


class SharedChannelStates(StatesGroup):
    waiting_links = State()


@router.message(F.text == "🔗 Guruhlar linki")
async def shared_channels_menu_handler(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    count = await crud.count_shared_channels(db)
    await message.answer(
        f"🔗 Umumiy guruh linklari\n"
        f"📊 {count}/{config.MAX_SHARED_CHANNELS} ta\n\n"
        f"Bu yerga qo'shgan linklaringizdan, siz ruxsat bergan "
        f"foydalanuvchilar o'zi guruh qo'shmasdan foydalanishi mumkin.",
        reply_markup=shared_channels_menu()
    )


@router.message(F.text == "➕ Link qo'shish (umumiy)")
async def add_shared_start(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    await state.set_state(SharedChannelStates.waiting_links)
    await message.answer(
        "🔗 Bitta yoki bir nechta (150 tagacha) link yuboring.\n"
        "Har bir linkni alohida qatorga yozing.\n\n"
        "Format: https://t.me/guruhadi yoki @guruhadi"
    )


@router.message(SharedChannelStates.waiting_links)
async def add_shared_links(message: Message, state: FSMContext,
                            db: AsyncSession):
    links, invalid_count = parse_bulk_links(message.text or "")
    if not links:
        await message.answer(
            "❌ To'g'ri formatdagi link topilmadi. Qayta yuboring."
        )
        return

    existing = await crud.get_shared_channel_links(db)
    new_links = [l for l in links if l not in existing]
    dup_count = len(links) - len(new_links)

    room = max(0, config.MAX_SHARED_CHANNELS - len(existing))
    to_save = new_links[:room]
    overflow = len(new_links) - len(to_save)

    if not to_save:
        await message.answer(
            "❌ Saqlash uchun bo'sh joy yo'q yoki barcha linklar "
            "allaqachon qo'shilgan."
        )
        return

    await state.update_data(links=to_save)

    text = f"📊 {len(links)} ta link aniqlandi.\n"
    if dup_count:
        text += f"♻️ {dup_count} ta takroriy (o'tkazib yuboriladi)\n"
    if invalid_count:
        text += f"⚠️ {invalid_count} ta noto'g'ri formatda edi\n"
    if overflow:
        text += (
            f"🚫 {overflow} ta link {config.MAX_SHARED_CHANNELS} ta "
            f"limit tufayli sig'madi\n"
        )
    text += f"\n<b>{len(to_save)} ta linkni saqlamoqchimisiz?</b>"

    await message.answer(
        text,
        reply_markup=save_cancel_keyboard("shch:save", "shch:cancel"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "shch:save")
async def save_shared_links(callback: CallbackQuery, state: FSMContext,
                             db: AsyncSession):
    data = await state.get_data()
    links = data.get("links", [])

    result = await crud.add_shared_channels_bulk(db, links)
    await db.commit()
    await state.clear()

    await callback.message.edit_text(
        f"✅ {result['added']} ta link saqlandi!"
    )
    await callback.answer()


@router.callback_query(F.data == "shch:cancel")
async def cancel_shared(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


@router.message(F.text == "📋 Umumiy linklarni ko'rish")
async def list_shared(message: Message, db: AsyncSession):
    if message.from_user.id != config.ADMIN_TELEGRAM_ID:
        return
    channels = await crud.get_shared_channels(db)
    if not channels:
        await message.answer(
            "📭 Umumiy link qo'shilmagan.",
            reply_markup=shared_channels_menu()
        )
        return

    for ch in channels:
        builder = InlineKeyboardBuilder()
        builder.button(text="🗑 O'chirish", callback_data=f"shch:del:{ch.id}")
        await message.answer(
            f"🔗 {ch.link}",
            reply_markup=builder.as_markup()
        )

    await message.answer(
        f"📊 Jami: {len(channels)} ta",
        reply_markup=shared_channels_menu()
    )


@router.callback_query(F.data.startswith("shch:del:"))
async def delete_shared_cb(callback: CallbackQuery, db: AsyncSession):
    if callback.from_user.id != config.ADMIN_TELEGRAM_ID:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    ch_id = int(callback.data.split(":")[2])
    await crud.delete_shared_channel(db, ch_id)
    await db.commit()
    await callback.message.edit_text("🗑 Link o'chirildi.")
    await callback.answer("✅ O'chirildi")
