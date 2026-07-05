import secrets
import string
import bcrypt
from cryptography.fernet import Fernet
import base64
from config import ENCRYPTION_KEY


def generate_password(length: int = 10) -> str:
    """Tasodifiy kuchli parol generatsiya qilish"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        # Kamida 1 ta katta harf, 1 ta kichik, 1 ta raqam, 1 ta belgi bo'lishi kerak
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%" for c in password)
        if has_upper and has_lower and has_digit and has_special:
            return password


def hash_password(password: str) -> str:
    """Parolni bcrypt bilan hash qilish"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Parolni tekshirish"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _get_fernet() -> Fernet:
    """Fernet instance olish"""
    key = base64.urlsafe_b64encode(bytes.fromhex(ENCRYPTION_KEY)[:32])
    return Fernet(key)


def encrypt_session(session_string: str) -> str:
    """Session stringni shifrlash"""
    f = _get_fernet()
    return f.encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str) -> str:
    """Session stringni deshifrlash"""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()
