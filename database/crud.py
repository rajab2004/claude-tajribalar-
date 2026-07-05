"""
CRUD operatsiyalar — barcha database amallar shu yerda
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Admin, User, UserSession, Channel,
    Announcement, SendLog, AnnouncementStatus
)
from services.crypto import hash_password, verify_password, encrypt_text, decrypt_text
import config


# ═══════════════════════════════════════════════════════
#  ADMIN CRUD
# ═══════════════════════════════════════════════════════

async def get_admin_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[Admin]:
    result = await db.execute(
        select(Admin).where(Admin.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_admin(db: AsyncSession) -> Admin:
    """Birinchi marta ishga tushganda admin yaratiladi"""
    existing = await get_admin_by_telegram_id(db, config.ADMIN_TELEGRAM_ID)
    if existing:
        return existing
    admin = Admin(
        telegram_id=config.ADMIN_TELEGRAM_ID,
        password_hash=hash_password(config.ADMIN_PASSWORD),
        gmail=config.ADMIN_GMAIL,
        phone=config.ADMIN_PHONE,
        username=config.ADMIN_USERNAME,
    )
    db.add(admin)
    await db.flush()
    return admin


async def verify_admin_password(db: AsyncSession, telegram_id: int,
                                 password: str) -> tuple[bool, Admin | None]:
    """
    Returns: (success, admin_obj)
    """
    admin = await get_admin_by_telegram_id(db, telegram_id)
    if not admin:
        return False, None
    if verify_password(password, admin.password_hash):
        # Reset wrong attempts
        await db.execute(
            update(Admin).where(Admin.id == admin.id)
            .values(wrong_attempts=0)
        )
        return True, admin
    else:
        new_attempts = admin.wrong_attempts + 1
        await db.execute(
            update(Admin).where(Admin.id == admin.id)
            .values(wrong_attempts=new_attempts)
        )
        await db.refresh(admin)
        admin.wrong_attempts = new_attempts
        return False, admin


async def update_admin_password(db: AsyncSession, admin_id: int,
                                 new_password: str):
    await db.execute(
        update(Admin).where(Admin.id == admin_id)
        .values(password_hash=hash_password(new_password), wrong_attempts=0)
    )


async def update_admin_info(db: AsyncSession, admin_id: int, **kwargs):
    await db.execute(
        update(Admin).where(Admin.id == admin_id).values(**kwargs)
    )


# ═══════════════════════════════════════════════════════
#  USER CRUD
# ═══════════════════════════════════════════════════════

async def create_user(db: AsyncSession, telegram_id: int, phone: str,
                       password: str, months: int,
                       admin_id: int) -> tuple[User, str]:
    """
    Returns: (user, plain_password)
    """
    expires_at = datetime.utcnow() + timedelta(days=30 * months)
    user = User(
        telegram_id=telegram_id,
        phone=phone,
        password_hash=hash_password(password),
        expires_at=expires_at,
        created_by=admin_id,
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_by_telegram_id(db: AsyncSession,
                                   telegram_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.session))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
        .options(selectinload(User.session))
    )
    return result.scalar_one_or_none()


async def verify_user_password(db: AsyncSession, telegram_id: int,
                                password: str) -> tuple[bool, User | None]:
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return False, None
    if not user.is_active:
        return False, user
    if user.expires_at < datetime.utcnow():
        return False, user
    if verify_password(password, user.password_hash):
        await db.execute(
            update(User).where(User.id == user.id)
            .values(wrong_attempts=0)
        )
        return True, user
    else:
        new_attempts = user.wrong_attempts + 1
        await db.execute(
            update(User).where(User.id == user.id)
            .values(wrong_attempts=new_attempts)
        )
        await db.refresh(user)
        user.wrong_attempts = new_attempts
        return False, user


async def update_user_password(db: AsyncSession, user_id: int,
                                new_password: str):
    await db.execute(
        update(User).where(User.id == user_id)
        .values(password_hash=hash_password(new_password), wrong_attempts=0)
    )


async def extend_user_expiry(db: AsyncSession, user_id: int, months: int):
    user = await get_user_by_id(db, user_id)
    if not user:
        return
    base = max(user.expires_at, datetime.utcnow())
    new_expiry = base + timedelta(days=30 * months)
    await db.execute(
        update(User).where(User.id == user_id)
        .values(expires_at=new_expiry, is_active=True, wrong_attempts=0)
    )


async def deactivate_user(db: AsyncSession, user_id: int):
    await db.execute(
        update(User).where(User.id == user_id).values(is_active=False)
    )


async def delete_user(db: AsyncSession, user_id: int):
    await db.execute(delete(User).where(User.id == user_id))


async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def get_active_users(db: AsyncSession) -> List[User]:
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.expires_at > datetime.utcnow()
        )
    )
    return list(result.scalars().all())


async def get_expired_users(db: AsyncSession) -> List[User]:
    result = await db.execute(
        select(User).where(
            User.expires_at <= datetime.utcnow(),
            User.is_active == True
        )
    )
    return list(result.scalars().all())


async def update_user_interval(db: AsyncSession, user_id: int, minutes: int):
    await db.execute(
        update(User).where(User.id == user_id)
        .values(interval_minutes=minutes)
    )


async def reset_wrong_attempts(db: AsyncSession, user_id: int):
    await db.execute(
        update(User).where(User.id == user_id).values(wrong_attempts=0)
    )


# ═══════════════════════════════════════════════════════
#  SESSION CRUD
# ═══════════════════════════════════════════════════════

async def save_session(db: AsyncSession, user_id: int,
                        session_string: str, phone: str) -> UserSession:
    enc = encrypt_text(session_string)
    existing = await db.execute(
        select(UserSession).where(UserSession.user_id == user_id)
    )
    sess = existing.scalar_one_or_none()
    if sess:
        sess.session_string_enc = enc
        sess.phone = phone
        sess.is_connected = True
        sess.connected_at = datetime.utcnow()
        sess.disconnected_at = None
    else:
        sess = UserSession(
            user_id=user_id,
            session_string_enc=enc,
            phone=phone,
        )
        db.add(sess)
    await db.flush()
    return sess


async def get_session(db: AsyncSession, user_id: int) -> Optional[str]:
    """Decrypted session string qaytaradi"""
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_connected == True
        )
    )
    sess = result.scalar_one_or_none()
    if sess:
        return decrypt_text(sess.session_string_enc)
    return None


async def disconnect_session(db: AsyncSession, user_id: int):
    await db.execute(
        update(UserSession).where(UserSession.user_id == user_id)
        .values(is_connected=False, disconnected_at=datetime.utcnow())
    )


# ═══════════════════════════════════════════════════════
#  CHANNEL CRUD
# ═══════════════════════════════════════════════════════

async def add_channel(db: AsyncSession, user_id: int,
                       link: str) -> Optional[Channel]:
    count_result = await db.execute(
        select(func.count(Channel.id)).where(
            Channel.user_id == user_id,
            Channel.is_active == True
        )
    )
    count = count_result.scalar()
    if count >= config.MAX_CHANNELS:
        return None
    ch = Channel(user_id=user_id, link=link)
    db.add(ch)
    await db.flush()
    return ch


async def get_user_channels(db: AsyncSession, user_id: int) -> List[Channel]:
    result = await db.execute(
        select(Channel).where(
            Channel.user_id == user_id,
            Channel.is_active == True
        ).order_by(Channel.added_at.desc())
    )
    return list(result.scalars().all())


async def delete_channel(db: AsyncSession, channel_id: int, user_id: int):
    await db.execute(
        delete(Channel).where(
            Channel.id == channel_id,
            Channel.user_id == user_id
        )
    )


async def deactivate_channel(db: AsyncSession, channel_id: int):
    """Yuborib bo'lmaydigan linkni o'chirib tashlaydi"""
    await db.execute(
        delete(Channel).where(Channel.id == channel_id)
    )


# ═══════════════════════════════════════════════════════
#  ANNOUNCEMENT CRUD
# ═══════════════════════════════════════════════════════

async def create_announcement(db: AsyncSession, user_id: int,
                               text: str, interval: int) -> Announcement:
    ann = Announcement(
        user_id=user_id,
        message_text=text,
        interval_minutes=interval,
    )
    db.add(ann)
    await db.flush()
    return ann


async def save_announcement_message_id(db: AsyncSession, ann_id: int,
                                        msg_id: int):
    await db.execute(
        update(Announcement).where(Announcement.id == ann_id)
        .values(bot_message_id=msg_id)
    )


async def get_open_announcements(db: AsyncSession) -> List[Announcement]:
    result = await db.execute(
        select(Announcement)
        .where(Announcement.status == AnnouncementStatus.open)
        .options(selectinload(Announcement.user).selectinload(User.session))
    )
    return list(result.scalars().all())


async def get_user_open_announcements(db: AsyncSession,
                                       user_id: int) -> List[Announcement]:
    result = await db.execute(
        select(Announcement).where(
            Announcement.user_id == user_id,
            Announcement.status == AnnouncementStatus.open
        ).order_by(Announcement.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_closed_announcements(db: AsyncSession,
                                         user_id: int) -> List[Announcement]:
    result = await db.execute(
        select(Announcement).where(
            Announcement.user_id == user_id,
            Announcement.status == AnnouncementStatus.closed
        ).order_by(Announcement.closed_at.desc())
    )
    return list(result.scalars().all())


async def close_announcement(db: AsyncSession, ann_id: int):
    await db.execute(
        update(Announcement).where(Announcement.id == ann_id)
        .values(
            status=AnnouncementStatus.closed,
            closed_at=datetime.utcnow()
        )
    )


async def close_all_user_announcements(db: AsyncSession, user_id: int):
    await db.execute(
        update(Announcement).where(
            Announcement.user_id == user_id,
            Announcement.status == AnnouncementStatus.open
        ).values(
            status=AnnouncementStatus.closed,
            closed_at=datetime.utcnow()
        )
    )


async def update_last_sent(db: AsyncSession, ann_id: int):
    await db.execute(
        update(Announcement).where(Announcement.id == ann_id)
        .values(last_sent_at=datetime.utcnow())
    )


async def get_announcement_by_id(db: AsyncSession,
                                   ann_id: int) -> Optional[Announcement]:
    result = await db.execute(
        select(Announcement).where(Announcement.id == ann_id)
    )
    return result.scalar_one_or_none()


async def delete_old_closed_announcements(db: AsyncSession):
    """Har kecha 00:00 da yopilgan e'lonlarni o'chiradi"""
    from datetime import date
    today_midnight = datetime.combine(date.today(), datetime.min.time())
    await db.execute(
        delete(Announcement).where(
            Announcement.status == AnnouncementStatus.closed,
            Announcement.closed_at < today_midnight
        )
    )


async def add_send_log(db: AsyncSession, ann_id: int, ch_id: int,
                        success: bool, reason: str = None):
    log = SendLog(
        announcement_id=ann_id,
        channel_id=ch_id,
        is_success=success,
        fail_reason=reason,
    )
    db.add(log)
    await db.flush()


# ═══════════════════════════════════════════════════════
#  STATISTIKA
# ═══════════════════════════════════════════════════════

async def get_statistics(db: AsyncSession) -> dict:
    now = datetime.utcnow()

    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    active_users = (await db.execute(
        select(func.count(User.id)).where(
            User.is_active == True, User.expires_at > now
        )
    )).scalar()
    expired_users = (await db.execute(
        select(func.count(User.id)).where(
            User.expires_at <= now, User.is_active == True
        )
    )).scalar()
    inactive_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == False)
    )).scalar()
    connected_sessions = (await db.execute(
        select(func.count(UserSession.id)).where(
            UserSession.is_connected == True
        )
    )).scalar()
    total_announcements = (await db.execute(
        select(func.count(Announcement.id))
    )).scalar()
    open_announcements = (await db.execute(
        select(func.count(Announcement.id)).where(
            Announcement.status == AnnouncementStatus.open
        )
    )).scalar()
    closed_announcements = (await db.execute(
        select(func.count(Announcement.id)).where(
            Announcement.status == AnnouncementStatus.closed
        )
    )).scalar()

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "expired_users": expired_users or 0,
        "inactive_users": inactive_users or 0,
        "connected_sessions": connected_sessions or 0,
        "total_announcements": total_announcements or 0,
        "open_announcements": open_announcements or 0,
        "closed_announcements": closed_announcements or 0,
    }
