"""
/start handler — kirish menyusi
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from utils.keyboards import start_keyboard
import config

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    tg_id = message.from_user.id

    # Admin uchun start eventi qayd qilinmaydi
    if tg_id != config.ADMIN_TELEGRAM_ID:
        existing_user = await crud.get_user_by_telegram_id(db, tg_id)
        if not existing_user:
            # Bo'tga birinchi marta /start bosgan (yoki hali ruxsat
            # berilmagan) odam — admin panelda "Yangi foydalanuvchilar"
            # bo'limida ko'rinishi uchun qayd qilinadi
            await crud.log_start_event(
                db, tg_id, message.from_user.username,
                message.from_user.full_name
            )
            await db.commit()

    await message.answer(
        "🤖 Xush kelibsiz!\n\n"
        "Iltimos, kirish turini tanlang:",
        reply_markup=start_keyboard()
    )
