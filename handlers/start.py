from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from utils.keyboards import get_start_keyboard
from utils.helpers import clear_state

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Bot ishga tushganda - asosiy menyu"""
    await clear_state(state)
    await message.answer(
        "👋 <b>Xush kelibsiz!</b>\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )
