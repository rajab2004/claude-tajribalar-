from datetime import datetime
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database.connection import AsyncSessionLocal
from database import crud
import config

# Muddati tugagan foydalanuvchiga ham ruxsat etiladigan amallar
_ALLOWED_TEXTS_WHEN_BLOCKED = {
    "📞 Admin bilan bog'lanish",
    "🔐 Admin sifatida kirish",
    "🚪 Chiqish",
}


def _expiry_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📞 Admin bilan bog'lanish")
    return kb.as_markup(resize_keyboard=True)


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

            user = None
            if telegram_id:
                user = await crud.get_user_by_telegram_id(db, telegram_id)
            data["current_user"] = user

            is_blocked = (
                user is not None
                and telegram_id != config.ADMIN_TELEGRAM_ID
                and (not user.is_active or user.expires_at < datetime.utcnow())
            )

            if is_blocked:
                if isinstance(event, Message):
                    text = event.text or ""
                    if text.startswith("/start") or text in _ALLOWED_TEXTS_WHEN_BLOCKED:
                        return await handler(event, data)
                    await event.answer(
                        "⏰ Sizning obuna muddatingiz tugagan!\n\n"
                        "Iltimos, davom etish uchun adminga yozib "
                        "to'lovni amalga oshiring.\n"
                        f"📞 {config.ADMIN_PHONE}\n"
                        f"💬 @{config.ADMIN_USERNAME}\n\n"
                        "Ruxsat berilgach, bot avvalgidek ishlashda "
                        "davom etadi — hech narsangiz o'chib ketmaydi.",
                        reply_markup=_expiry_keyboard()
                    )
                    return
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "⏰ Obuna muddatingiz tugagan. Admin bilan bog'laning.",
                        show_alert=True
                    )
                    return

            return await handler(event, data)
