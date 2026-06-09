from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from config import config


# Async engine yaratish
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,           # SQL so'rovlarini logga yozmaslik (production)
    pool_size=10,         # Bir vaqtda max ulanishlar
    max_overflow=20,      # Qo'shimcha ulanishlar
    pool_pre_ping=True,   # Uzilgan ulanishlarni avtomatik tiklaish
    pool_recycle=3600,    # 1 soatda ulanishni yangilash
)

# Session factory
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass"""
    pass


async def get_session() -> AsyncSession:
    """Dependency injection uchun session qaytaradi"""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session xatosi: {e}")
            raise
        finally:
            await session.close()


async def create_tables():
    """Barcha jadvallarni yaratadi (agar mavjud bo'lmasa)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database jadvallari tayyor!")


async def drop_tables():
    """Barcha jadvallarni o'chiradi (faqat dev uchun!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ Barcha jadvallar o'chirildi!")
