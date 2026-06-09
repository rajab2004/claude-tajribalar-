from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Admin(Base):
    """Adminlar jadvali"""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    wrong_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship
    users: Mapped[list["User"]] = relationship("User", back_populates="creator", lazy="select")

    def __repr__(self) -> str:
        return f"<Admin id={self.id} telegram_id={self.telegram_id}>"


class User(Base):
    """Foydalanuvchilar jadvali"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wrong_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    creator: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="users")
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    channels: Mapped[list["Channel"]] = relationship(
        "Channel", back_populates="user", cascade="all, delete-orphan"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} active={self.is_active}>"


class Session(Base):
    """Pyrogram sessiyalar jadvali"""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # AES-256 bilan shifrlangan sessiya string
    session_string: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} connected={self.is_connected}>"


class Channel(Base):
    """Guruh/Kanal linklari jadvali"""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    link: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="channels")
    send_logs: Mapped[list["SendLog"]] = relationship(
        "SendLog", back_populates="channel", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Channel id={self.id} user_id={self.user_id} link={self.link[:30]}>"


class Announcement(Base):
    """E'lonlar jadvali"""
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    # 'open' yoki 'closed'
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="announcements")
    send_logs: Mapped[list["SendLog"]] = relationship(
        "SendLog", back_populates="announcement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Announcement id={self.id} status={self.status}>"


class SendLog(Base):
    """Xabar yuborish logi jadvali"""
    __tablename__ = "send_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    is_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fail_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="send_logs")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="send_logs")

    def __repr__(self) -> str:
        return f"<SendLog id={self.id} success={self.is_success}>"
