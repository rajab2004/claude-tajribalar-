"""
Bot asosiy fayl
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from config import validate_config
from database.connection import init_db, AsyncSessionLocal
from database import crud

from handlers.start import router as start_router
from handlers.user.auth import router as user_auth_router
from handlers.user.telegram_connect import router as connect_router
from handlers.user.channels import router as channels_router
from handlers.user.announcements import router as announcements_router
from handlers.user.settings import router as settings_router
from handlers.admin.auth import router as admin_auth_router
from handlers.admin.users import router as admin_users_router
from handlers.admin.stats import router as admin_stats_router
from handlers.admin.broadcast import router as admin_broadcast_router
from handlers.admin.shared_channels import router as admin_shared_channels_router

from middlewares.auth_middleware import AuthMiddleware
from services.scheduler import setup_scheduler
from services.pyrogram_client import get_client, load_all_sessions

# Barcha kutubxona loglarini o'chirish (aiogram, pyrogram, sqlalchemy...)
for _noisy in ["aiogram", "pyrogram", "sqlalchemy", "apscheduler",
               "asyncio", "aiohttp", "urllib3"]:
    logging.getLogger(_noisy).setLevel(logging.CRITICAL)

# Xatolarni faylga yozish (terminalda ko'rinmaydi)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8")],
)

# Terminal uchun faqat bot logger
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
logger.propagate = False
_console = logging.StreamHandler(sys.stdout)
_console.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_console)


async def on_startup(bot: Bot):
    validate_config()
    await init_db()

    async with AsyncSessionLocal() as db:
        await crud.create_admin(db)
        await db.commit()

        users = await crud.get_active_users(db)
        sessions_to_load = []
        for user in users:
            sess_str = await crud.get_session(db, user.id)
            if sess_str:
                sessions_to_load.append((user.id, sess_str))

    if sessions_to_load:
        await load_all_sessions(sessions_to_load)

    setup_scheduler(bot)

    me = await bot.get_me()
    logger.info(f"✅ Bot ishga tushdi: @{me.username}")


async def on_shutdown(bot: Bot):
    from services.scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def main():
    try:
        validate_config()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(start_router)
    dp.include_router(admin_auth_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_stats_router)
    dp.include_router(admin_broadcast_router)
    dp.include_router(admin_shared_channels_router)
    dp.include_router(user_auth_router)
    dp.include_router(connect_router)
    dp.include_router(channels_router)
    dp.include_router(announcements_router)
    dp.include_router(settings_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
