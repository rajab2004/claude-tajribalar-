from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database.connection import AsyncSessionLocal
from database import crud


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as db:
            data["db"] = db
            telegram_id = None
            if isinstance(event, (Message, CallbackQuery)):
                telegram_id = event.from_user.id if event.from_user else None
            if telegram_id:
                user = await crud.get_user_by_telegram_id(db, telegram_id)
                data["current_user"] = user
            else:
                data["current_user"] = None
            return await handler(event, data)
