from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_bot_statistics
from utils.keyboards import get_admin_main_menu
from utils.helpers import format_stats

router = Router()


@router.message(F.text == "📊 Bot statistikasi")
async def bot_statistics(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    if not data.get("is_admin_logged_in"):
        await message.answer("⛔ Admin sifatida kirmadingiz!")
        return

    stats = await get_bot_statistics(session)
    await message.answer(
        format_stats(stats),
        parse_mode="HTML",
        reply_markup=get_admin_main_menu()
    )
