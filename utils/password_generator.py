import secrets
import string
import bcrypt
from loguru import logger


# Parol uchun ishlatiladigan belgilar
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def generate_password(length: int = 10) -> str:
    """
    Tasodifiy xavfsiz parol generatsiya qilish.
    A-Z, a-z, 0-9, !@#$% belgilaridan iborat.
    """
    while True:
        password = "".join(secrets.choice(ALPHABET) for _ in range(length))
        # Har turdagi belgidan kamida bittasi bo'lishini tekshirish
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%" for c in password)
        if has_upper and has_lower and has_digit and has_special:
            return password


def hash_password(password: str) -> str:
    """Parolni bcrypt bilan hash qilish"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Parol tekshirishda xato: {e}")
        return False


def is_valid_password(password: str, min_length: int = 6) -> bool:
    """Parol minimal talablarga javob beradimi?"""
    return len(password) >= min_length
