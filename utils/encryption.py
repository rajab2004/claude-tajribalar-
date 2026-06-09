import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger

from config import config


def _get_key() -> bytes:
    """AES-256 kalitini olish (32 bayt)"""
    key = base64.b64decode(config.ENCRYPTION_KEY)
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY 32 bayt bo'lishi kerak (AES-256)!")
    return key


def encrypt_session(plaintext: str) -> str:
    """
    Sessiya stringini AES-256-GCM bilan shifrlash.
    Qaytaradigan: base64 encoded (nonce + ciphertext)
    """
    try:
        key = _get_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce (GCM uchun standart)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # nonce + ciphertext birlashtirish
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")
    except Exception as e:
        logger.error(f"Shifrlashda xato: {e}")
        raise


def decrypt_session(encrypted: str) -> str:
    """
    Shifrlangan sessiya stringini ochish.
    Qaytaradigan: asl sessiya string
    """
    try:
        key = _get_key()
        aesgcm = AESGCM(key)
        combined = base64.b64decode(encrypted.encode("utf-8"))
        nonce = combined[:12]
        ciphertext = combined[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.error(f"Shifr ochishda xato: {e}")
        raise


def generate_encryption_key() -> str:
    """
    Yangi AES-256 kalit generatsiya qilish.
    .env faylga yozish uchun ishlatiladi (bir marta).
    """
    key = os.urandom(32)
    return base64.b64encode(key).decode("utf-8")
