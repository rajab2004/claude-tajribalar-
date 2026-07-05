"""
/start handler — kirish menyusi
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from utils.keyboards import start_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🤖 Xush kelibsiz!\n\n"
        "Iltimos, kirish turini tanlang:",
        reply_markup=start_keyboard()
    )
