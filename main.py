import asyncio
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.connection import create_tables
from database.crud import (
    get_admin_by_telegram_id,
    create_admin,
    get_all_connected_sessions,
)
from database.connection import AsyncSessionFactory
from utils.password_generator import hash_password
from middlewares import (
    DatabaseMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
)
from handlers.start import router as start_router
from handlers.user import user_router
from handlers.admin import admin_router
from services.scheduler import start_scheduler, stop_scheduler, set_bot
from services.pyrogram_client import create_client_from_session, stop_all_clients


# ============================================================
# LOGGING SOZLASH
# ============================================================

def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    logger.add(
        "logs/bot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )


# ============================================================
# ADMIN YARATISH (birinchi ishga tushishda)
# ============================================================

async def ensure_first_admin():
    """
    Agar bazada admin bo'lmasa, .env dagi ADMIN_TELEGRAM_ID
    bilan boshlang'ich admin yaratadi.
    """
    if not config.ADMIN_TELEGRAM_ID:
        logger.warning("ADMIN_TELEGRAM_ID .env da ko'rsatilmagan!")
        return

    async with AsyncSessionFactory() as session:
        try:
            existing = await get_admin_by_telegram_id(session, config.ADMIN_TELEGRAM_ID)
            if existing:
                logger.info(f"Admin allaqachon mavjud: {config.ADMIN_TELEGRAM_ID}")
                return

            # Default parol: "Admin@2024!" — birinchi kirishda o'zgartirilsin
            default_password = "Admin@2024!"
            password_hash = hash_password(default_password)

            await create_admin(
                session,
                telegram_id=config.ADMIN_TELEGRAM_ID,
                password_hash=password_hash,
                gmail=config.GMAIL_USER or None,
                phone=config.ADMIN_PHONE or None,
                username=config.ADMIN_USERNAME or None,
            )
            await session.commit()

            logger.success(
                f"✅ Boshlang'ich admin yaratildi!\n"
                f"   Telegram ID: {config.ADMIN_TELEGRAM_ID}\n"
                f"   Default parol: {default_password}\n"
                f"   ⚠️  Darhol parolni o'zgartiring!"
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Admin yaratishda xato: {e}")


# ============================================================
# SAQLANGAN SESSIYALARNI TIKLASH
# ============================================================

async def restore_sessions():
    """
    Bot qayta ishga tushganda bazadagi barcha ulangan
    sessiyalarni (Pyrogram clientlarni) tiklaydi.
    """
    async with AsyncSessionFactory() as session:
        try:
            sessions = await get_all_connected_sessions(session)
            if not sessions:
                logger.info("Tiklanadigan sessiya yo'q.")
                return

            restored = 0
            failed = 0

            for db_session in sessions:
                client = await create_client_from_session(
                    db_session.user_id,
                    db_session.session_string
                )
                if client:
                    restored += 1
                else:
                    # Sessiya ishlamay qolgan → bazada ham o'chirish
                    from database.crud import mark_session_disconnected
                    await mark_session_disconnected(session, db_session.id)
                    failed += 1

            await session.commit()
            logger.info(f"Sessiyalar tiklandi: {restored} ta muvaffaqiyatli, {failed} ta muvaffaqiyatsiz")

        except Exception as e:
            await session.rollback()
            logger.error(f"Sessiya tiklashda xato: {e}")


# ============================================================
# BOT ISHGA TUSHIRISH
# ============================================================

async def on_startup(bot: Bot):
    """Bot ishga tushganda bajariladigan amallar"""
    logger.info("🚀 Bot ishga tushmoqda...")

    # 1. Database jadvallari
    await create_tables()

    # 2. Boshlang'ich admin
    await ensure_first_admin()

    # 3. Pyrogram sessiyalarini tiklash
    await restore_sessions()

    # 4. Scheduler ishga tushirish
    admin_info = None
    async with AsyncSessionFactory() as session:
        from database.crud import get_first_admin
        admin_info = await get_first_admin(session)

    set_bot(
        bot=bot,
        admin_phone=admin_info.phone if admin_info else "",
        admin_username=admin_info.username if admin_info else "",
    )
    start_scheduler()

    # 5. Bot ma'lumotlari
    bot_info = await bot.get_me()
    logger.success(
        f"✅ Bot muvaffaqiyatli ishga tushdi!\n"
        f"   Ism: {bot_info.full_name}\n"
        f"   Username: @{bot_info.username}\n"
        f"   ID: {bot_info.id}"
    )


async def on_shutdown(bot: Bot):
    """Bot to'xtatilganda bajariladigan amallar"""
    logger.info("⛔ Bot to'xtatilmoqda...")

    # Scheduler to'xtatish
    stop_scheduler()

    # Barcha Pyrogram clientlarni to'xtatish
    await stop_all_clients()

    # Bot sessiyasini yopish
    await bot.session.close()

    logger.info("✅ Bot to'xtatildi.")


# ============================================================
# DISPATCHER SOZLASH
# ============================================================

def create_dispatcher() -> Dispatcher:
    """Dispatcher va middlewarelarni sozlash"""
    dp = Dispatcher(storage=MemoryStorage())

    # ── Middlewarelar (tartib muhim!) ──────────────────────
    # 1. Logging — eng birinchi
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # 2. Rate limiting
    dp.message.middleware(RateLimitMiddleware(max_requests=5, window=2.0, cooldown=10.0))
    dp.callback_query.middleware(RateLimitMiddleware(max_requests=10, window=2.0, cooldown=5.0))

    # 3. Database session
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # ── Handlerlar ro'yxatga olish ─────────────────────────
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    return dp


# ============================================================
# ASOSIY FUNKSIYA
# ============================================================

async def main():
    setup_logging()

    # Log papkasini yaratish
    import os
    os.makedirs("logs", exist_ok=True)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = create_dispatcher()

    # Startup / Shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("📡 Polling boshlandi...")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — bot to'xtatildi.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
