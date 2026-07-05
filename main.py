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

from middlewares.auth_middleware import AuthMiddleware
from services.scheduler import setup_scheduler
from services.pyrogram_client import get_client, load_all_sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    logger.info("🚀 Bot ishga tushmoqda...")

    validate_config()

    await init_db()
    logger.info("✅ Database tayyor")

    async with AsyncSessionLocal() as db:
        # Admin yaratish
        await crud.create_admin(db)
        await db.commit()

        # Bot qayta ishga tushganda barcha foydalanuvchi sessionlarini yuklash
        logger.info("📱 Foydalanuvchi akkauntlari yuklanmoqda...")
        users = await crud.get_active_users(db)
        sessions_to_load = []
        for user in users:
            sess_str = await crud.get_session(db, user.id)
            if sess_str:
                sessions_to_load.append((user.id, sess_str))

    if sessions_to_load:
        await load_all_sessions(sessions_to_load)
        logger.info(f"✅ {len(sessions_to_load)} ta akkaunt sessioni yuklandi")
    else:
        logger.info("ℹ️ Aktiv session topilmadi")

    setup_scheduler(bot)
    logger.info("✅ Scheduler tayyor")

    me = await bot.get_me()
    logger.info(f"✅ Bot ishga tushdi: @{me.username}")


async def on_shutdown(bot: Bot):
    logger.info("⛔ Bot to'xtatilmoqda...")
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
    dp.include_router(user_auth_router)
    dp.include_router(connect_router)
    dp.include_router(channels_router)
    dp.include_router(announcements_router)
    dp.include_router(settings_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🤖 Polling boshlandi...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
