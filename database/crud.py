from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import Admin, User, Session, Channel, Announcement, SendLog


# ============================================================
# ADMIN CRUD
# ============================================================

async def get_admin_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[Admin]:
    """Telegram ID bo'yicha admin topish"""
    result = await session.execute(
        select(Admin).where(Admin.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_admin_by_id(session: AsyncSession, admin_id: int) -> Optional[Admin]:
    """ID bo'yicha admin topish"""
    result = await session.execute(
        select(Admin).where(Admin.id == admin_id)
    )
    return result.scalar_one_or_none()


async def create_admin(
    session: AsyncSession,
    telegram_id: int,
    password_hash: str,
    gmail: str = None,
    phone: str = None,
    username: str = None
) -> Admin:
    """Yangi admin yaratish"""
    admin = Admin(
        telegram_id=telegram_id,
        password_hash=password_hash,
        gmail=gmail,
        phone=phone,
        username=username,
    )
    session.add(admin)
    await session.flush()
    await session.refresh(admin)
    logger.info(f"Yangi admin yaratildi: {telegram_id}")
    return admin


async def update_admin_password(
    session: AsyncSession,
    admin_id: int,
    new_password_hash: str
) -> bool:
    """Admin parolini yangilash"""
    result = await session.execute(
        update(Admin)
        .where(Admin.id == admin_id)
        .values(password_hash=new_password_hash, wrong_attempts=0)
    )
    return result.rowcount > 0


async def update_admin_gmail(
    session: AsyncSession,
    admin_id: int,
    new_gmail: str
) -> bool:
    """Admin Gmail manzilini yangilash"""
    result = await session.execute(
        update(Admin)
        .where(Admin.id == admin_id)
        .values(gmail=new_gmail)
    )
    return result.rowcount > 0


async def update_admin_contact(
    session: AsyncSession,
    admin_id: int,
    phone: str = None,
    username: str = None
) -> bool:
    """Admin bog'lanish ma'lumotlarini yangilash"""
    values = {}
    if phone is not None:
        values["phone"] = phone
    if username is not None:
        values["username"] = username
    if not values:
        return False
    result = await session.execute(
        update(Admin).where(Admin.id == admin_id).values(**values)
    )
    return result.rowcount > 0


async def increment_admin_wrong_attempts(
    session: AsyncSession,
    telegram_id: int
) -> int:
    """Admin noto'g'ri urinishlar sonini oshirish, yangi qiymatni qaytarish"""
    result = await session.execute(
        select(Admin).where(Admin.telegram_id == telegram_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        return 0
    admin.wrong_attempts += 1
    await session.flush()
    return admin.wrong_attempts


async def reset_admin_wrong_attempts(
    session: AsyncSession,
    telegram_id: int
) -> None:
    """Admin noto'g'ri urinishlarini nolga qaytarish"""
    await session.execute(
        update(Admin)
        .where(Admin.telegram_id == telegram_id)
        .values(wrong_attempts=0)
    )


async def get_first_admin(session: AsyncSession) -> Optional[Admin]:
    """Birinchi (asosiy) adminni olish"""
    result = await session.execute(
        select(Admin).order_by(Admin.id.asc()).limit(1)
    )
    return result.scalar_one_or_none()


# ============================================================
# USER CRUD
# ============================================================

async def get_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int
) -> Optional[User]:
    """Telegram ID bo'yicha foydalanuvchi topish"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """ID bo'yicha foydalanuvchi topish"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    password_hash: str,
    months: int,
    phone: str = None,
    admin_id: int = None
) -> User:
    """Yangi foydalanuvchi yaratish"""
    expires_at = datetime.now(timezone.utc) + timedelta(days=30 * months)
    user = User(
        telegram_id=telegram_id,
        password_hash=password_hash,
        phone=phone,
        is_active=True,
        expires_at=expires_at,
        created_by=admin_id,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    logger.info(f"Yangi foydalanuvchi yaratildi: {telegram_id}, muddat: {months} oy")
    return user


async def update_user_password(
    session: AsyncSession,
    user_id: int,
    new_password_hash: str
) -> bool:
    """Foydalanuvchi parolini yangilash"""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=new_password_hash, wrong_attempts=0)
    )
    return result.rowcount > 0


async def increment_user_wrong_attempts(
    session: AsyncSession,
    telegram_id: int
) -> int:
    """Foydalanuvchi noto'g'ri urinishlar sonini oshirish"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return 0
    user.wrong_attempts += 1
    await session.flush()
    return user.wrong_attempts


async def reset_user_wrong_attempts(
    session: AsyncSession,
    telegram_id: int
) -> None:
    """Foydalanuvchi noto'g'ri urinishlarini nolga qaytarish"""
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(wrong_attempts=0)
    )


async def deactivate_user(session: AsyncSession, user_id: int) -> bool:
    """Foydalanuvchini deaktiv qilish"""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    return result.rowcount > 0


async def extend_user_expiry(
    session: AsyncSession,
    user_id: int,
    months: int
) -> Optional[datetime]:
    """Foydalanuvchi muddatini uzaytirish"""
    user = await get_user_by_id(session, user_id)
    if not user:
        return None

    now = datetime.now(timezone.utc)
    # Agar muddat o'tgan bo'lsa, hozirdan boshlab hisoblash
    base = user.expires_at if user.expires_at and user.expires_at > now else now
    new_expires = base + timedelta(days=30 * months)

    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(expires_at=new_expires, is_active=True)
    )
    logger.info(f"User {user_id} muddati {months} oyga uzaytirildi: {new_expires}")
    return new_expires


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """Foydalanuvchini o'chirish (cascade: session, channel, announcement ham o'chadi)"""
    result = await session.execute(
        delete(User).where(User.id == user_id)
    )
    logger.info(f"Foydalanuvchi o'chirildi: {user_id}")
    return result.rowcount > 0


async def get_all_users(session: AsyncSession) -> list[User]:
    """Barcha foydalanuvchilarni olish"""
    result = await session.execute(
        select(User).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active_users(session: AsyncSession) -> list[User]:
    """Faol foydalanuvchilarni olish"""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(User).where(
            and_(User.is_active == True, User.expires_at > now)
        ).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def get_expired_users(session: AsyncSession) -> list[User]:
    """Muddati tugagan foydalanuvchilarni olish"""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(User).where(
            User.expires_at <= now
        ).order_by(User.expires_at.asc())
    )
    return list(result.scalars().all())


async def get_users_expiring_today(session: AsyncSession) -> list[User]:
    """Bugun muddati tugaydigan foydalanuvchilar (scheduler uchun)"""
    now = datetime.now(timezone.utc)
    end_of_day = now.replace(hour=23, minute=59, second=59)
    result = await session.execute(
        select(User).where(
            and_(
                User.is_active == True,
                User.expires_at <= end_of_day,
                User.expires_at >= now
            )
        )
    )
    return list(result.scalars().all())


# ============================================================
# SESSION CRUD
# ============================================================

async def get_active_session_by_user_id(
    session: AsyncSession,
    user_id: int
) -> Optional[Session]:
    """Foydalanuvchining faol sessiyasini olish"""
    result = await session.execute(
        select(Session).where(
            and_(Session.user_id == user_id, Session.is_connected == True)
        )
    )
    return result.scalar_one_or_none()


async def create_session(
    session: AsyncSession,
    user_id: int,
    session_string_encrypted: str,
    phone: str = None
) -> Session:
    """Yangi sessiya yaratish"""
    # Eski sessiyalarni o'chirish (1 ta foydalanuvchi - 1 ta sessiya)
    await session.execute(
        delete(Session).where(Session.user_id == user_id)
    )

    new_session = Session(
        user_id=user_id,
        session_string=session_string_encrypted,
        phone=phone,
        is_connected=True,
    )
    session.add(new_session)
    await session.flush()
    await session.refresh(new_session)
    logger.info(f"Yangi sessiya yaratildi: user_id={user_id}")
    return new_session


async def disconnect_session(session: AsyncSession, user_id: int) -> bool:
    """Sessiyani o'chirish (foydalanuvchi uzganda)"""
    result = await session.execute(
        delete(Session).where(Session.user_id == user_id)
    )
    logger.info(f"Sessiya o'chirildi: user_id={user_id}")
    return result.rowcount > 0


async def mark_session_disconnected(
    session: AsyncSession,
    session_id: int
) -> bool:
    """Sessiyani uzilgan deb belgilash"""
    result = await session.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(
            is_connected=False,
            disconnected_at=datetime.now(timezone.utc)
        )
    )
    return result.rowcount > 0


async def get_all_connected_sessions(session: AsyncSession) -> list[Session]:
    """Barcha ulangan sessiyalarni olish (scheduler uchun)"""
    result = await session.execute(
        select(Session).where(Session.is_connected == True)
    )
    return list(result.scalars().all())


# ============================================================
# CHANNEL CRUD
# ============================================================

async def get_channels_by_user_id(
    session: AsyncSession,
    user_id: int,
    only_active: bool = True
) -> list[Channel]:
    """Foydalanuvchi kanallarini olish"""
    query = select(Channel).where(Channel.user_id == user_id)
    if only_active:
        query = query.where(Channel.is_active == True)
    query = query.order_by(Channel.added_at.asc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_channel_by_id(
    session: AsyncSession,
    channel_id: int
) -> Optional[Channel]:
    """ID bo'yicha kanal topish"""
    result = await session.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    return result.scalar_one_or_none()


async def count_user_channels(session: AsyncSession, user_id: int) -> int:
    """Foydalanuvchi kanallar sonini hisoblash"""
    result = await session.execute(
        select(func.count(Channel.id)).where(
            and_(Channel.user_id == user_id, Channel.is_active == True)
        )
    )
    return result.scalar_one() or 0


async def add_channel(
    session: AsyncSession,
    user_id: int,
    link: str
) -> Optional[Channel]:
    """Yangi kanal qo'shish (max 150 ta limit)"""
    count = await count_user_channels(session, user_id)
    if count >= 150:
        return None

    channel = Channel(user_id=user_id, link=link, is_active=True)
    session.add(channel)
    await session.flush()
    await session.refresh(channel)
    logger.info(f"Yangi kanal qo'shildi: user_id={user_id}, link={link}")
    return channel


async def delete_channel(session: AsyncSession, channel_id: int) -> bool:
    """Kanalni o'chirish"""
    result = await session.execute(
        delete(Channel).where(Channel.id == channel_id)
    )
    return result.rowcount > 0


async def deactivate_channel(session: AsyncSession, channel_id: int) -> bool:
    """Kanalni deaktiv qilish (xato bo'lganda)"""
    result = await session.execute(
        update(Channel)
        .where(Channel.id == channel_id)
        .values(is_active=False)
    )
    return result.rowcount > 0


# ============================================================
# ANNOUNCEMENT CRUD
# ============================================================

async def create_announcement(
    session: AsyncSession,
    user_id: int,
    message_text: str,
    interval_minutes: int = 5
) -> Announcement:
    """Yangi e'lon yaratish"""
    announcement = Announcement(
        user_id=user_id,
        message_text=message_text,
        status="open",
        interval_minutes=interval_minutes,
    )
    session.add(announcement)
    await session.flush()
    await session.refresh(announcement)
    logger.info(f"Yangi e'lon yaratildi: user_id={user_id}, id={announcement.id}")
    return announcement


async def get_announcement_by_id(
    session: AsyncSession,
    announcement_id: int
) -> Optional[Announcement]:
    """ID bo'yicha e'lon topish"""
    result = await session.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    return result.scalar_one_or_none()


async def get_open_announcements_by_user(
    session: AsyncSession,
    user_id: int
) -> list[Announcement]:
    """Foydalanuvchining ochiq e'lonlarini olish"""
    result = await session.execute(
        select(Announcement).where(
            and_(
                Announcement.user_id == user_id,
                Announcement.status == "open"
            )
        ).order_by(Announcement.created_at.desc())
    )
    return list(result.scalars().all())


async def get_closed_announcements_by_user(
    session: AsyncSession,
    user_id: int
) -> list[Announcement]:
    """Foydalanuvchining yopilgan e'lonlarini olish"""
    result = await session.execute(
        select(Announcement).where(
            and_(
                Announcement.user_id == user_id,
                Announcement.status == "closed"
            )
        ).order_by(Announcement.closed_at.desc())
    )
    return list(result.scalars().all())


async def close_announcement(
    session: AsyncSession,
    announcement_id: int
) -> bool:
    """E'lonni yopish"""
    result = await session.execute(
        update(Announcement)
        .where(Announcement.id == announcement_id)
        .values(status="closed", closed_at=datetime.now(timezone.utc))
    )
    logger.info(f"E'lon yopildi: {announcement_id}")
    return result.rowcount > 0


async def update_announcement_last_sent(
    session: AsyncSession,
    announcement_id: int
) -> None:
    """E'lon oxirgi yuborilish vaqtini yangilash"""
    await session.execute(
        update(Announcement)
        .where(Announcement.id == announcement_id)
        .values(last_sent_at=datetime.now(timezone.utc))
    )


async def update_announcement_interval(
    session: AsyncSession,
    user_id: int,
    interval_minutes: int
) -> bool:
    """Foydalanuvchining barcha ochiq e'lonlari intervalini yangilash"""
    result = await session.execute(
        update(Announcement)
        .where(
            and_(
                Announcement.user_id == user_id,
                Announcement.status == "open"
            )
        )
        .values(interval_minutes=interval_minutes)
    )
    return result.rowcount > 0


async def get_all_open_announcements(session: AsyncSession) -> list[Announcement]:
    """Barcha ochiq e'lonlarni olish (scheduler uchun)"""
    result = await session.execute(
        select(Announcement).where(Announcement.status == "open")
    )
    return list(result.scalars().all())


async def close_user_announcements(
    session: AsyncSession,
    user_id: int
) -> int:
    """Foydalanuvchining barcha ochiq e'lonlarini yopish"""
    result = await session.execute(
        update(Announcement)
        .where(
            and_(
                Announcement.user_id == user_id,
                Announcement.status == "open"
            )
        )
        .values(status="closed", closed_at=datetime.now(timezone.utc))
    )
    return result.rowcount


async def delete_old_closed_announcements(session: AsyncSession) -> int:
    """Bugungi kunda yopilgan e'lonlarni o'chirish (00:00 da ishga tushadi)"""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        delete(Announcement).where(
            and_(
                Announcement.status == "closed",
                Announcement.closed_at < midnight
            )
        )
    )
    count = result.rowcount
    if count:
        logger.info(f"{count} ta yopilgan e'lon o'chirildi")
    return count


# ============================================================
# SEND LOG CRUD
# ============================================================

async def create_send_log(
    session: AsyncSession,
    announcement_id: int,
    channel_id: int,
    is_success: bool,
    fail_reason: str = None
) -> SendLog:
    """Yuborish logi yaratish"""
    log = SendLog(
        announcement_id=announcement_id,
        channel_id=channel_id,
        is_success=is_success,
        fail_reason=fail_reason,
    )
    session.add(log)
    await session.flush()
    return log


# ============================================================
# STATISTIKA
# ============================================================

async def get_bot_statistics(session: AsyncSession) -> dict:
    """Bot statistikasini olish"""
    now = datetime.now(timezone.utc)

    total_users = (await session.execute(
        select(func.count(User.id))
    )).scalar_one() or 0

    active_users = (await session.execute(
        select(func.count(User.id)).where(
            and_(User.is_active == True, User.expires_at > now)
        )
    )).scalar_one() or 0

    expired_users = (await session.execute(
        select(func.count(User.id)).where(User.expires_at <= now)
    )).scalar_one() or 0

    inactive_users = (await session.execute(
        select(func.count(User.id)).where(User.is_active == False)
    )).scalar_one() or 0

    connected_sessions = (await session.execute(
        select(func.count(Session.id)).where(Session.is_connected == True)
    )).scalar_one() or 0

    total_announcements = (await session.execute(
        select(func.count(Announcement.id))
    )).scalar_one() or 0

    open_announcements = (await session.execute(
        select(func.count(Announcement.id)).where(Announcement.status == "open")
    )).scalar_one() or 0

    closed_announcements = (await session.execute(
        select(func.count(Announcement.id)).where(Announcement.status == "closed")
    )).scalar_one() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "expired_users": expired_users,
        "connected_sessions": connected_sessions,
        "total_announcements": total_announcements,
        "open_announcements": open_announcements,
        "closed_announcements": closed_announcements,
    }
