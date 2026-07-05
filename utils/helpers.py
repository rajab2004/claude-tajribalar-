"""
Yordamchi funksiyalar
"""
import re
from datetime import datetime
import pytz
import config


def normalize_phone(phone: str) -> str | None:
    """
    Telefon raqamni standart formatga o'tkazadi: +998XXXXXXXXX
    Qabul qilinadigan formatlar:
      - 99 123 45 67
      - +998 99 123 45 67
      - 998991234567
      - 0991234567
    """
    digits = re.sub(r'\D', '', phone)

    if len(digits) == 9:
        return f"+998{digits}"
    elif len(digits) == 10 and digits.startswith('0'):
        return f"+998{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('998'):
        return f"+{digits}"
    elif len(digits) == 13 and digits.startswith('998'):
        return f"+{digits}"
    return None


def format_datetime(dt: datetime) -> str:
    """UTC datetime ni Toshkent vaqtiga o'giradi"""
    tz = pytz.timezone(config.TIMEZONE)
    local = dt.replace(tzinfo=pytz.utc).astimezone(tz)
    return local.strftime("%d.%m.%Y %H:%M")


def format_expiry(expires_at: datetime) -> str:
    remaining = expires_at - datetime.utcnow()
    if remaining.days < 0:
        return "❌ Muddati tugagan"
    elif remaining.days == 0:
        hours = remaining.seconds // 3600
        return f"⚠️ {hours} soat qoldi"
    else:
        return f"✅ {remaining.days} kun qoldi ({format_datetime(expires_at)})"


def is_valid_channel_link(link: str) -> bool:
    """Telegram link formatini tekshiradi"""
    patterns = [
        r'^https://t\.me/[a-zA-Z0-9_]+$',
        r'^https://t\.me/\+[a-zA-Z0-9_-]+$',
        r'^@[a-zA-Z0-9_]+$',
        r'^-100\d+$',
    ]
    return any(re.match(p, link.strip()) for p in patterns)


def truncate(text: str, max_len: int = 50) -> str:
    return text if len(text) <= max_len else text[:max_len] + "..."
