"""
Parol hashlash va sessiya shifrlash
"""
import base64
import bcrypt
from cryptography.fernet import Fernet
import config


def _get_fernet() -> Fernet:
    key = config.ENCRYPTION_KEY.encode()[:32]
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def encrypt_text(text: str) -> str:
    return _get_fernet().encrypt(text.encode()).decode()


def decrypt_text(enc: str) -> str:
    return _get_fernet().decrypt(enc.encode()).decode()
