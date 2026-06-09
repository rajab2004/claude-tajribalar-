import re
from datetime import datetime, timezone
from typing import Optional
from loguru import logger


# ============================================================
# TELEFON RAQAM YORDAMCHILARI
# ============================================================

def normalize_phone(phone: str) -> Optional[str]:
    """
    Telefon raqamni standart formatga o'tkazish.
    Qabul qilinadigan: '99 123 45 67', '+998 99 123 45 67', '998991234567'
    Qaytaradigan: '+998991234567' yoki None (noto'g'ri format)
    """
    # Faqat raqamlarni olish
    digits = re.sub(r"\D", "", phone)

    # 9 raqam (mahalliy format): 991234567
    if len(digits) == 9:
        return f"+998{digits}"

    # 12 raqam (998 bilan): 998991234567
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits}"

    # 13 raqam (+998 bilan): +998991234567
    if len(digits) == 13 and digits.startswith("998"):
        return f"+{digits}"

    return None


def is_valid_phone(phone: str) -> bool:
    """Telefon raqam formati to'g'riligini tekshirish"""
    return normalize_phone(phone) is not None


# ============================================================
# SANA VA VAQT YORDAMCHILARI
# ============================================================

def format_datetime(dt: Optional[datetime], fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Sanani o'zbek formatida chiqarish"""
    if not dt:
        return "Noma'lum"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(fmt)


def format_date(dt: Optional[datetime]) -> str:
    """Faqat sanani chiqarish"""
    return format_datetime(dt, fmt="%d.%m.%Y")


def is_expired(expires_at: Optional[datetime]) -> bool:
    """Muddat o'tganligini tekshirish"""
    if not expires_at:
        return True
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


def days_until_expiry(expires_at: Optional[datetime]) -> int:
    """Muddatgacha qolgan kunlar soni"""
    if not expires_at:
        return 0
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    delta = expires_at - now
    return max(0, delta.days)


# ============================================================
# MATN YORDAMCHILARI
# ============================================================

def truncate_text(text: str, max_length: int = 50) -> str:
    """Matnni qisqartirish"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_html(text: str) -> str:
    """HTML belgilarini escape qilish"""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def mask_password() -> str:
    """Parolni yashirish"""
    return "••••••••"


# ============================================================
# LINK TEKSHIRUVI
# ============================================================

def is_valid_telegram_link(link: str) -> bool:
    """
    Telegram guruh/kanal linkini tekshirish.
    Qabul qilinadigan formatlar:
    - https://t.me/username
    - https://t.me/+hashcode
    - @username
    - t.me/username
    """
    link = link.strip()

    # @username formati
    if link.startswith("@") and len(link) > 1:
        return True

    # https://t.me/ yoki t.me/ formati
    patterns = [
        r"^https?://t\.me/[a-zA-Z0-9_+/]{5,}$",
        r"^t\.me/[a-zA-Z0-9_+/]{5,}$",
    ]
    for pattern in patterns:
        if re.match(pattern, link):
            return True

    return False


def normalize_link(link: str) -> str:
    """Linkni standart formatga o'tkazish"""
    link = link.strip()
    # @username -> to'g'ridan-to'g'ri ishlatiladi
    if link.startswith("@"):
        return link
    # t.me/ -> https://t.me/ ga o'tkazish
    if link.startswith("t.me/"):
        return f"https://{link}"
    return link


# ============================================================
# XABAR FORMATLASH
# ============================================================

def format_user_info(user, show_phone: bool = True) -> str:
    """Foydalanuvchi ma'lumotlarini formatlash"""
    status = "🟢 Faol" if user.is_active and not is_expired(user.expires_at) else "🔴 Nofaol"
    expires = format_date(user.expires_at)

    lines = [
        f"👤 <b>Telegram ID:</b> <code>{user.telegram_id}</code>",
        f"📅 <b>Muddat:</b> {expires}",
        f"📊 <b>Holat:</b> {status}",
    ]
    if show_phone and user.phone:
        lines.insert(1, f"📞 <b>Telefon:</b> {user.phone}")

    return "\n".join(lines)


def format_announcement_status(announcement) -> str:
    """E'lon holatini formatlash"""
    if announcement.status == "open":
        return f"📦 Yuk ochiq | ⏱ Har {announcement.interval_minutes} daqiqada"
    return "🔒 Yuk yopildi"


def format_stats(stats: dict) -> str:
    """Bot statistikasini chiroyli formatlash"""
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>BOT STATISTIKASI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b> ta\n"
        f"🟢 Faol foydalanuvchilar: <b>{stats['active_users']}</b> ta\n"
        f"🔴 Nofaol foydalanuvchilar: <b>{stats['inactive_users']}</b> ta\n"
        f"⏰ Muddati tugaganlar: <b>{stats['expired_users']}</b> ta\n"
        f"📱 Ulangan akkauntlar: <b>{stats['connected_sessions']}</b> ta\n"
        f"📝 Jami e'lonlar: <b>{stats['total_announcements']}</b> ta\n"
        f"📢 Ochiq e'lonlar: <b>{stats['open_announcements']}</b> ta\n"
        f"🔒 Yopilgan e'lonlar: <b>{stats['closed_announcements']}</b> ta\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# FSM STATE TOZALASH
# ============================================================

async def clear_state(state) -> None:
    """FSM holatini tozalash"""
    try:
        await state.clear()
    except Exception as e:
        logger.warning(f"State tozalashda xato: {e}")
