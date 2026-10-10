"""
Pyrogram client boshqaruvi
— foydalanuvchi o'z Telegram akkauntini ulaydi
— xabarlar BOT nomidan EMAS, foydalanuvchi akkauntidan yuboriladi
"""
import asyncio
import re
import logging
from typing import Optional
from pyrogram import Client
from pyrogram.errors import (
    FloodWait, ChatWriteForbidden, UserBannedInChannel,
    ChannelPrivate, PeerIdInvalid, SessionPasswordNeeded,
    PhoneCodeInvalid, PhoneCodeExpired, PhoneNumberInvalid,
    UserNotParticipant, ChatAdminRequired
)
import config

logger = logging.getLogger(__name__)

# Aktiv user clientlar: {user_id: Client}
_active_clients: dict[int, Client] = {}


def parse_chat_id(link: str) -> str:
    """
    Pyrogram uchun link/username ni to'g'ri formatga o'tkazadi.

    Qabul qilinadigan formatlar:
      https://t.me/guruhadi   → guruhadi
      https://t.me/+XXXX      → invite link (join kerak, to'g'ridan xabar yuborib bo'lmaydi)
      @guruhadi               → guruhadi
      guruhadi                → guruhadi
      -1001234567890          → -1001234567890  (chat ID)
    """
    link = link.strip()

    # Raqamli chat ID (masalan: -1001234567890)
    if re.match(r'^-?\d+$', link):
        return link

    # https://t.me/+invite_hash — invite link
    if re.match(r'^https?://t\.me/\+', link):
        return link  # Pyrogram ba'zi versiyalarda invite linkni ham tushunadi

    # https://t.me/username
    match = re.match(r'^https?://t\.me/([a-zA-Z0-9_]+)$', link)
    if match:
        return match.group(1)

    # @username
    if link.startswith('@'):
        return link[1:]

    # Faqat username
    return link


async def get_client(user_id: int, session_string: str) -> Optional[Client]:
    """
    Foydalanuvchi akkauntining aktiv Pyrogram clientini qaytaradi.
    Agar mavjud bo'lmasa — yangi yaratadi.
    """
    # Mavjud client bor va ulanganmi?
    if user_id in _active_clients:
        client = _active_clients[user_id]
        try:
            if client.is_connected:
                return client
        except Exception:
            pass
        # Uzilgan — o'chirib yangi ochamiz
        try:
            await client.stop()
        except Exception:
            pass
        del _active_clients[user_id]

    # Yangi client yaratish — foydalanuvchi SESSION dan
    try:
        client = Client(
            name=f"user_session_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
            no_updates=True,        # Updatelarni olmaydi, faqat xabar yuboradi
        )
        await client.start()
        _active_clients[user_id] = client
        logger.info(f"✅ User {user_id} Pyrogram client ulandi (akkaunt nomidan yuboradi)")
        return client
    except Exception as e:
        logger.error(f"❌ User {user_id} Pyrogram client xatosi: {e}")
        return None


async def disconnect_client(user_id: int):
    """Foydalanuvchi clientini to'xtatadi"""
    if user_id in _active_clients:
        try:
            await _active_clients[user_id].stop()
        except Exception:
            pass
        del _active_clients[user_id]
        logger.info(f"User {user_id} client uzildi")


async def send_to_channel(client: Client, link: str,
                           text: str) -> tuple[bool, str, bool]:
    """
    Foydalanuvchi akkauntidan guruh/kanalga xabar yuboradi.
    (Bot nomidan EMAS — foydalanuvchi o'z akkauntidan yuboradi)
    Bot hech qachon guruhga o'zi qo'shilmaydi — faqat foydalanuvchi
    allaqachon a'zo bo'lgan guruhlarga yozadi.

    Returns: (muvaffaqiyatli, xato_sababi, doimiy_xatomi)
        doimiy_xato=True bo'lsa — guruh haqiqatan ham yaroqsiz
                     (masalan a'zo emas / bloklangan) — ro'yhatdan olib
                     tashlash mumkin.
        doimiy_xato=False bo'lsa — vaqtinchalik holat (masalan
                     guruh vaqtincha band/flood-wait) — guruh
                     o'chirilmaydi, keyingi rejalashtirilgan
                     yuborishda avtomatik qayta urinadi.
    """
    chat_id = parse_chat_id(link)

    try:
        await client.send_message(chat_id, text)
        return True, "", False

    except FloodWait as e:
        # Qisqa kutish (masalan 2 daqiqagacha) — shu yerning o'zida kutib,
        # keyin yuboramiz. Uzoqroq bo'lsa — hozircha o'tkazib yuboramiz,
        # guruh o'chirilmaydi, keyingi safar avtomatik qayta urinadi.
        if e.value <= config.FLOOD_WAIT_INLINE_MAX:
            logger.info(f"FloodWait {e.value}s — {link}, kutilmoqda...")
            await asyncio.sleep(e.value + 1)
            try:
                await client.send_message(chat_id, text)
                return True, "", False
            except FloodWait as e2:
                return False, f"Guruh vaqtincha band ({e2.value}s)", False
            except Exception as e2:
                return False, f"Kutishdan keyin xato: {e2}", False
        else:
            logger.info(
                f"FloodWait {e.value}s — {link}, keyingi safar urinib ko'riladi"
            )
            return False, f"Guruh vaqtincha band ({e.value}s), navbatda kutmoqda", False

    except (ChatWriteForbidden, ChatAdminRequired):
        return False, "Yozish huquqi yo'q", True

    except UserBannedInChannel:
        return False, "Akkaunt kanalda bloklangan", True

    except ChannelPrivate:
        return False, "Kanal yopiq yoki akkaunt a'zo emas", True

    except UserNotParticipant:
        return False, "Akkaunt guruh/kanalga a'zo emas", True

    except PeerIdInvalid:
        return False, "Noto'g'ri link yoki akkaunt bu guruhni topa olmaydi", True

    except Exception as e:
        logger.error(f"Xabar yuborishda xato ({link}): {type(e).__name__}: {e}")
        return False, str(e), False


# ─── Telegram akkaunt ulash (OTP jarayoni) ─────────────────────────────

async def start_phone_auth(phone: str) -> tuple[bool, str, str]:
    """
    Telefon raqami orqali OTP yuboradi.
    Returns: (muvaffaqiyatli, phone_code_hash, xato_xabari)
    """
    # Avvalgi temp client ni tozalash
    temp_key = f"temp_{phone}"
    if temp_key in _active_clients:
        try:
            await _active_clients[temp_key].disconnect()
        except Exception:
            pass
        del _active_clients[temp_key]

    try:
        client = Client(
            name=f"temp_auth_{phone}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            in_memory=True,
        )
        await client.connect()
        sent = await client.send_code(phone)
        _active_clients[temp_key] = client
        logger.info(f"OTP kod yuborildi: {phone}")
        return True, sent.phone_code_hash, ""

    except PhoneNumberInvalid:
        return False, "", "Noto'g'ri telefon raqam."
    except FloodWait as e:
        return False, "", f"Juda ko'p urinish. {e.value} soniya kuting."
    except Exception as e:
        logger.error(f"start_phone_auth xatosi: {e}")
        return False, "", f"Xatolik: {e}"


async def verify_otp(phone: str, code: str,
                     phone_code_hash: str) -> tuple[bool, str, str]:
    """
    OTP kodni tekshiradi.
    Returns: (muvaffaqiyatli, session_string_yoki_xato, "2fa_needed" yoki "")
    """
    temp_key = f"temp_{phone}"
    client = _active_clients.get(temp_key)

    if not client:
        return False, "Sessiya muddati tugadi. Qayta boshlang.", ""

    try:
        await client.sign_in(phone, phone_code_hash, code)
        session_string = await client.export_session_string()
        await client.disconnect()
        del _active_clients[temp_key]
        logger.info(f"OTP muvaffaqiyatli: {phone}")
        return True, session_string, ""

    except SessionPasswordNeeded:
        # 2FA yoqilgan — client saqlab turamiz
        return True, "", "2fa_needed"

    except PhoneCodeInvalid:
        return False, "Noto'g'ri kod. Qayta kiriting.", ""

    except PhoneCodeExpired:
        if temp_key in _active_clients:
            try:
                await _active_clients[temp_key].disconnect()
            except Exception:
                pass
            del _active_clients[temp_key]
        return False, "Kod muddati tugadi. Qayta boshlang.", ""

    except Exception as e:
        logger.error(f"verify_otp xatosi: {e}")
        return False, str(e), ""


async def verify_2fa(phone: str, password_2fa: str) -> tuple[bool, str, str]:
    """
    2FA parolni tekshiradi.
    Returns: (muvaffaqiyatli, session_string, xato_xabari)
    """
    temp_key = f"temp_{phone}"
    client = _active_clients.get(temp_key)

    if not client:
        return False, "", "Sessiya muddati tugadi. Qayta boshlang."

    try:
        await client.check_password(password_2fa)
        session_string = await client.export_session_string()
        await client.disconnect()
        del _active_clients[temp_key]
        logger.info(f"2FA muvaffaqiyatli: {phone}")
        return True, session_string, ""

    except Exception as e:
        logger.error(f"verify_2fa xatosi: {e}")
        return False, "", f"2FA parol noto'g'ri: {e}"


async def load_all_sessions(db_sessions: list[tuple[int, str]]):
    """
    Bot ishga tushganda barcha foydalanuvchilar sessionlarini yuklaydi.
    db_sessions: [(user_id, session_string), ...]
    """
    logger.info(f"Sessionlar yuklanmoqda: {len(db_sessions)} ta...")
    for user_id, sess_str in db_sessions:
        try:
            client = await get_client(user_id, sess_str)
            if client:
                logger.info(f"✅ User {user_id} session yuklandi")
            else:
                logger.warning(f"⚠️ User {user_id} session yuklanmadi")
        except Exception as e:
            logger.error(f"User {user_id} session xatosi: {e}")
