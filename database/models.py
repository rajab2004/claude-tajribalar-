from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime,
    ForeignKey, Integer, String, Text, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class AnnouncementStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


# ─── Admin ─────────────────────────────────────────────────────────────
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    gmail = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    username = Column(String(100), nullable=True)
    wrong_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── User ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    wrong_attempts = Column(Integer, default=0)
    interval_minutes = Column(Integer, default=5)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)

    session = relationship("UserSession", back_populates="user",
                           uselist=False, cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="user",
                            cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="user",
                                  cascade="all, delete-orphan")


# ─── Session ───────────────────────────────────────────────────────────
class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    session_string_enc = Column(Text, nullable=False)   # AES-256 encrypted
    phone = Column(String(20), nullable=True)
    is_connected = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    disconnected_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="session")


# ─── Channel ───────────────────────────────────────────────────────────
class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    link = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="channels")


# ─── Announcement ──────────────────────────────────────────────────────
class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    message_text = Column(Text, nullable=False)
    bot_message_id = Column(BigInteger, nullable=True)  # bot chatidagi xabar ID
    status = Column(Enum(AnnouncementStatus), default=AnnouncementStatus.open)
    interval_minutes = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="announcements")
    send_logs = relationship("SendLog", back_populates="announcement",
                              cascade="all, delete-orphan")


# ─── SendLog ───────────────────────────────────────────────────────────
class SendLog(Base):
    __tablename__ = "send_logs"

    id = Column(Integer, primary_key=True)
    announcement_id = Column(Integer,
                              ForeignKey("announcements.id", ondelete="CASCADE"),
                              nullable=False)
    channel_id = Column(Integer,
                         ForeignKey("channels.id", ondelete="SET NULL"),
                         nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_success = Column(Boolean, default=True)
    fail_reason = Column(String(255), nullable=True)

    announcement = relationship("Announcement", back_populates="send_logs")
