import asyncio
import random
from typing import Optional, Tuple
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeExpired,
    PhoneCodeInvalid, FloodWait, BadRequest,
    AuthKeyUnregistered, UserDeactivated
)
from loguru import logger

from config import config
from utils.encryption import encrypt_session, decrypt_session


# Aktiv Pyrogram clientlar: {user_id: Client}
_active_clients: dict[int, Client] = {}


# ============================================================
# CLIENT YARATISH VA ULANISH
# ============================================================

async def create_client_from_session(
    user_id: int,
    session_string: str
) -> Optional[Client]:
    """
    Saqlangan sessiya string orqali Client yaratib ulash.
    session_string — shifrlangan holda keladi, ichida decrypt qilinadi.
    """
    try:
        plain_session = decrypt_session(session_string)
        client = Client(
            name=f"user_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=plain_session,
            in_memory=True,
        )
        await client.start()
        _active_clients[user_id] = client
        logger.info(f"Client ulandi: user_id={user_id}")
        return client
    except (AuthKeyUnregistered, UserDeactivated) as e:
        logger.warning(f"Sessiya eskirgan yoki o'chirilgan: user_id={user_id} | {e}")
        return None
    except Exception as e:
        logger.error(f"Client yaratishda xato: user_id={user_id} | {e}")
        return None


async def get_client(user_id: int) -> Optional[Client]:
    """Aktiv clientni olish"""
    return _active_clients.get(user_id)


async def disconnect_client(user_id: int) -> bool:
    """Clientni o'chirish"""
    client = _active_clients.pop(user_id, None)
    if client:
        try:
            await client.stop()
            logger.info(f"Client uzildi: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"Client uzishda xato: user_id={user_id} | {e}")
    return False


# ============================================================
# TELEFON ORQALI YANGI AKKOUNT ULASH
# ============================================================

# Vaqtinchalik ulanish jarayoni uchun: {user_id: {"client": Client, "phone": str}}
_pending_auth: dict[int, dict] = {}


async def start_phone_auth(
    user_id: int,
    phone: str
) -> Tuple[bool, str]:
    """
    Telefon raqam orqali autentifikatsiya boshlash.
    Returns: (success, message/phone_code_hash)
    """
    try:
        # Eski pending auth tozalash
        if user_id in _pending_auth:
            try:
                await _pending_auth[user_id]["client"].stop()
            except Exception:
                pass
            del _pending_auth[user_id]

        client = Client(
            name=f"auth_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            in_memory=True,
        )
        await client.connect()
        sent = await client.send_code(phone)
        _pending_auth[user_id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
            "attempts": 0,
        }
        logger.info(f"Kod yuborildi: user_id={user_id}, phone={phone}")
        return True, sent.phone_code_hash

    except FloodWait as e:
        logger.warning(f"FloodWait: {e.value}s | user_id={user_id}")
        return False, f"flood:{e.value}"
    except BadRequest as e:
        logger.error(f"Noto'g'ri telefon: user_id={user_id} | {e}")
        return False, "invalid_phone"
    except Exception as e:
        logger.error(f"Kod yuborishda xato: user_id={user_id} | {e}")
        return False, "error"


async def verify_phone_code(
    user_id: int,
    code: str
) -> Tuple[str, Optional[str]]:
    """
    SMS/Telegram kodni tekshirish.
    Returns: ("success", session_string) | ("2fa", None) | ("invalid", None) |
             ("expired", None) | ("max_attempts", None) | ("error", None)
    """
    auth_data = _pending_auth.get(user_id)
    if not auth_data:
        return "error", None

    auth_data["attempts"] += 1
    if auth_data["attempts"] > 3:
        await cancel_auth(user_id)
        return "max_attempts", None

    client: Client = auth_data["client"]
    phone = auth_data["phone"]
    phone_code_hash = auth_data["phone_code_hash"]

    try:
        await client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code,
        )
        session_string = await client.export_session_string()
        encrypted = encrypt_session(session_string)

        # Clientni aktiv qilish
        _active_clients[user_id] = client
        del _pending_auth[user_id]

        logger.info(f"Muvaffaqiyatli kirish: user_id={user_id}")
        return "success", encrypted

    except SessionPasswordNeeded:
        logger.info(f"2FA talab qilinadi: user_id={user_id}")
        return "2fa", None
    except PhoneCodeInvalid:
        logger.warning(f"Noto'g'ri kod: user_id={user_id}, urinish={auth_data['attempts']}")
        return "invalid", None
    except PhoneCodeExpired:
        await cancel_auth(user_id)
        logger.warning(f"Kod eskirgan: user_id={user_id}")
        return "expired", None
    except Exception as e:
        logger.error(f"Kod tekshirishda xato: user_id={user_id} | {e}")
        await cancel_auth(user_id)
        return "error", None


async def verify_2fa_password(
    user_id: int,
    password: str
) -> Tuple[str, Optional[str]]:
    """
    2FA parolini tekshirish.
    Returns: ("success", session_string) | ("invalid", None) | ("error", None)
    """
    auth_data = _pending_auth.get(user_id)
    if not auth_data:
        return "error", None

    client: Client = auth_data["client"]

    try:
        await client.check_password(password)
        session_string = await client.export_session_string()
        encrypted = encrypt_session(session_string)

        _active_clients[user_id] = client
        del _pending_auth[user_id]

        logger.info(f"2FA muvaffaqiyatli: user_id={user_id}")
        return "success", encrypted

    except BadRequest:
        logger.warning(f"2FA noto'g'ri parol: user_id={user_id}")
        return "invalid", None
    except Exception as e:
        logger.error(f"2FA xato: user_id={user_id} | {e}")
        return "error", None


async def cancel_auth(user_id: int) -> None:
    """Autentifikatsiya jarayonini bekor qilish"""
    auth_data = _pending_auth.pop(user_id, None)
    if auth_data:
        try:
            await auth_data["client"].disconnect()
        except Exception:
            pass
    logger.info(f"Auth bekor qilindi: user_id={user_id}")


# ============================================================
# XABAR YUBORISH
# ============================================================

async def send_message_to_channel(
    user_id: int,
    channel_link: str,
    text: str
) -> Tuple[bool, Optional[str]]:
    """
    Kanal/guruhga xabar yuborish.
    Returns: (success, fail_reason)
    """
    client = _active_clients.get(user_id)
    if not client:
        return False, "no_client"

    try:
        await client.send_message(channel_link, text)
        return True, None

    except FloodWait as e:
        logger.warning(f"FloodWait {e.value}s: user_id={user_id}, link={channel_link}")
        await asyncio.sleep(e.value)
        # Bir marta qayta urinish
        try:
            await client.send_message(channel_link, text)
            return True, None
        except Exception as retry_err:
            return False, f"flood_retry: {str(retry_err)[:100]}"

    except Exception as e:
        error_msg = str(e)[:150]
        logger.warning(f"Yuborishda xato: user_id={user_id}, link={channel_link} | {error_msg}")
        return False, error_msg


async def send_to_all_channels(
    user_id: int,
    channels: list,
    text: str,
    delay_min: float = 0.5,
    delay_max: float = 1.0,
) -> Tuple[int, int, list[int]]:
    """
    Barcha kanallarga xabar yuborish (flood limit himoyasi bilan).
    Returns: (success_count, fail_count, failed_channel_ids)
    """
    success_count = 0
    fail_count = 0
    failed_channel_ids = []

    for channel in channels:
        ok, reason = await send_message_to_channel(user_id, channel.link, text)
        if ok:
            success_count += 1
        else:
            fail_count += 1
            failed_channel_ids.append(channel.id)
            logger.warning(
                f"Kanal yuborilmadi: id={channel.id}, "
                f"link={channel.link}, sabab={reason}"
            )

        # Flood limit uchun tasodifiy kechikish
        await asyncio.sleep(random.uniform(delay_min, delay_max))

    return success_count, fail_count, failed_channel_ids


async def check_client_alive(user_id: int) -> bool:
    """Client hali ham ulangan yoki yo'qligini tekshirish"""
    client = _active_clients.get(user_id)
    if not client:
        return False
    try:
        await client.get_me()
        return True
    except Exception:
        _active_clients.pop(user_id, None)
        return False


async def stop_all_clients() -> None:
    """Barcha clientlarni to'xtatish (bot o'chganda)"""
    for user_id, client in list(_active_clients.items()):
        try:
            await client.stop()
            logger.info(f"Client to'xtatildi: user_id={user_id}")
        except Exception as e:
            logger.error(f"Client to'xtatishda xato: user_id={user_id} | {e}")
    _active_clients.clear()
