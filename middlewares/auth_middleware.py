from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger

from database.connection import AsyncSessionFactory
from database.crud import get_user_by_telegram_id, get_admin_by_telegram_id


# ============================================================
# DATABASE SESSION MIDDLEWARE
# ============================================================

class DatabaseMiddleware(BaseMiddleware):
    """
    Har bir so'rov uchun database sessiyasini avtomatik ochib,
    handler ga uzatadi va keyin yopadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with AsyncSessionFactory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Handler xatosi (DB rollback): {e}")
                raise
            finally:
                await session.close()


# ============================================================
# AUTH MIDDLEWARE — foydalanuvchi holati tekshiruvi
# ============================================================

class UserAuthMiddleware(BaseMiddleware):
    """
    Foydalanuvchi login holatini tekshiradi.
    FSM data ga 'db_user' va 'is_logged_in' ni qo'shadi.
    Login kerak bo'lmagan handlerlar o'zida tekshiradi.
    """

    # Login talab qilinmaydigan komandalar
    SKIP_COMMANDS = {"/start"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if not session:
            return await handler(event, data)

        # Telegram ID olish
        telegram_id = None
        if isinstance(event, Message):
            telegram_id = event.from_user.id if event.from_user else None
            # /start komandasi uchun o'tkazib yuborish
            if event.text and event.text.strip() in self.SKIP_COMMANDS:
                data["db_user"] = None
                data["is_user_logged_in"] = False
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id if event.from_user else None

        if telegram_id:
            try:
                db_user = await get_user_by_telegram_id(session, telegram_id)
                data["db_user"] = db_user
                data["is_user_logged_in"] = (
                    db_user is not None and db_user.is_active
                )
            except Exception as e:
                logger.error(f"UserAuthMiddleware xatosi: {e}")
                data["db_user"] = None
                data["is_user_logged_in"] = False
        else:
            data["db_user"] = None
            data["is_user_logged_in"] = False

        return await handler(event, data)


class AdminAuthMiddleware(BaseMiddleware):
    """
    Admin login holatini tekshiradi.
    FSM data ga 'db_admin' va 'is_admin_logged_in' ni qo'shadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if not session:
            return await handler(event, data)

        telegram_id = None
        if isinstance(event, (Message, CallbackQuery)):
            telegram_id = event.from_user.id if event.from_user else None

        if telegram_id:
            try:
                db_admin = await get_admin_by_telegram_id(session, telegram_id)
                data["db_admin"] = db_admin
                data["is_admin"] = db_admin is not None
            except Exception as e:
                logger.error(f"AdminAuthMiddleware xatosi: {e}")
                data["db_admin"] = None
                data["is_admin"] = False
        else:
            data["db_admin"] = None
            data["is_admin"] = False

        return await handler(event, data)
