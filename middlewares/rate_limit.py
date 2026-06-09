import time
from typing import Any, Awaitable, Callable, Dict
from collections import defaultdict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger


# ============================================================
# RATE LIMITING MIDDLEWARE
# ============================================================

class RateLimitMiddleware(BaseMiddleware):
    """
    Spam bosishlardan himoya qiluvchi middleware.
    Har bir foydalanuvchi uchun so'rovlar sonini cheklaydi.

    Sozlamalar:
    - rate_limit: sekundiga ruxsat etilgan so'rovlar soni (default: 1)
    - window: vaqt oynasi sekundlarda (default: 1 sekund)
    - max_requests: window ichida max so'rovlar (default: 3)
    """

    def __init__(
        self,
        rate_limit: float = 1.0,     # Har 1 sekundda
        max_requests: int = 3,        # Max 3 ta so'rov
        window: float = 1.0,          # 1 soniyalik oyna
        cooldown: float = 5.0,        # Blok vaqti (sekund)
    ):
        self.rate_limit = rate_limit
        self.max_requests = max_requests
        self.window = window
        self.cooldown = cooldown

        # {user_id: [timestamp1, timestamp2, ...]}
        self._requests: Dict[int, list] = defaultdict(list)
        # {user_id: blocked_until_timestamp}
        self._blocked: Dict[int, float] = {}

        super().__init__()

    def _is_blocked(self, user_id: int) -> bool:
        """Foydalanuvchi bloklangan yoki yo'qligini tekshirish"""
        if user_id in self._blocked:
            if time.time() < self._blocked[user_id]:
                return True
            else:
                # Blok vaqti tugagan
                del self._blocked[user_id]
        return False

    def _check_rate(self, user_id: int) -> bool:
        """
        So'rov limitini tekshirish.
        True - o'tkazib yuborish, False - bloklansin.
        """
        now = time.time()

        # Eski so'rovlarni olib tashlash
        self._requests[user_id] = [
            ts for ts in self._requests[user_id]
            if now - ts < self.window
        ]

        # Yangi so'rov qo'shish
        self._requests[user_id].append(now)

        # Limit tekshiruvi
        if len(self._requests[user_id]) > self.max_requests:
            self._blocked[user_id] = now + self.cooldown
            logger.warning(f"Rate limit: user {user_id} {self.cooldown}s blok")
            return False

        return True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        # Bloklangan foydalanuvchi
        if self._is_blocked(user_id):
            if isinstance(event, Message):
                remaining = int(self._blocked[user_id] - time.time())
                await event.answer(
                    f"⚠️ Juda tez bosyapsiz! {remaining} soniya kuting.",
                    show_alert=False
                )
            elif isinstance(event, CallbackQuery):
                remaining = int(self._blocked[user_id] - time.time())
                await event.answer(
                    f"⚠️ Juda tez bosyapsiz! {remaining} soniya kuting.",
                    show_alert=True
                )
            return

        # Rate limit tekshiruvi
        if not self._check_rate(user_id):
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Juda ko'p so'rov yubordingiz. Biroz kuting."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Juda ko'p bosyapsiz! Biroz kuting.",
                    show_alert=True
                )
            return

        return await handler(event, data)


# ============================================================
# LOGGER MIDDLEWARE — barcha amallarni loglash
# ============================================================

class LoggingMiddleware(BaseMiddleware):
    """
    Barcha kiruvchi xabarlar va callback larni loglaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            user_info = f"[{user.id}] @{user.username or 'N/A'}" if user else "Unknown"
            text = event.text or event.caption or f"[{event.content_type}]"
            logger.info(f"📨 Message | {user_info} | {text[:80]}")

        elif isinstance(event, CallbackQuery):
            user = event.from_user
            user_info = f"[{user.id}] @{user.username or 'N/A'}" if user else "Unknown"
            logger.info(f"🔘 Callback | {user_info} | {event.data}")

        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(f"❌ Handler xatosi: {type(e).__name__}: {e}")
            raise
