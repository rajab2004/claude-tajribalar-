"""
Yordamchi funksiyalar
"""
import re
import random
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


def parse_bulk_links(text: str) -> tuple[list[str], int]:
    """
    Ko'p qatorli matndan to'g'ri formatdagi linklarni ajratib oladi.
    1 ta link yuborilsa ham, 150 tagacha yuborilsa ham ishlaydi.
    Returns: (noyob to'g'ri linklar ro'yhati, noto'g'ri linklar soni)
    """
    if not text:
        return [], 0
    raw_lines = re.split(r'[\n,]+', text)
    seen = set()
    valid: list[str] = []
    invalid = 0
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        if is_valid_channel_link(line):
            if line not in seen:
                seen.add(line)
                valid.append(line)
        else:
            invalid += 1
    return valid, invalid


def normalize_otp_code(raw: str) -> str:
    """
    Telegramdan keladigan login kodi ba'zan qalbakilashtirishga qarshi
    ichiga nuqta yoki chiziqcha qo'yilgan holda ko'rsatiladi
    (masalan 12345 o'rniga 1.2345 yoki 1234-5).
    Foydalanuvchi shu ko'rinishda nusxalab yuborsa ham, faqat
    raqamlarni ajratib olib, haqiqiy kodni tiklaymiz.
    """
    return re.sub(r'\D', '', raw or "")


def duration_callback_to_days(value: str) -> int:
    """
    Klaviatura callback qiymatini kunlarga o'giradi.
    '3d'  -> 3 kun (bepul sinov)
    '1m'  -> 30 kun, '12m' -> 360 kun va h.k.
    """
    value = value.strip()
    if value.endswith("d"):
        return int(value[:-1])
    if value.endswith("m"):
        return int(value[:-1]) * 30
    return int(value) * 30


def format_duration_label(value: str) -> str:
    if value.endswith("d"):
        return f"{value[:-1]} kun (sinov)"
    if value.endswith("m"):
        return f"{value[:-1]} oy"
    return f"{value} oy"


def random_send_delay() -> float:
    """
    Har bir guruhga xabar yuborishdan oldin/keyin tasodifiy kutish vaqti.
    Akkauntni Telegramning flood/spam aniqlash tizimidan himoya qiladi —
    bir xil, doimiy oraliqda ketma-ket yuborish "bot xatti-harakati"
    sifatida aniqlanib, akkaunt cheklanishiga olib kelishi mumkin.
    """
    return random.uniform(config.SESSION_SEND_DELAY_MIN,
                          config.SESSION_SEND_DELAY_MAX)


# Ko'zga ko'rinmaydigan Unicode belgilar (zero-width)
_ZERO_WIDTH_CHARS = ['\u200b', '\u200c', '\u200d']


def vary_message_text(text: str) -> str:
    """
    Xabar oxiriga tasodifiy, ko'zga ko'rinmaydigan belgi(lar) qo'shadi.
    Natijada bir xil matn har bir guruhga texnik jihatdan bir xil bo'lmagan
    holda yuboriladi (odam ko'zi bilan hech qanday farqni sezmaydi),
    bu esa "aynan bir xil ommaviy xabar" sifatida aniqlanish ehtimolini
    kamaytiradi.
    """
    marker = random.choice(_ZERO_WIDTH_CHARS) * random.randint(1, 3)
    return text + marker
