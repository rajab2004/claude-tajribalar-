"""
Gmail orqali email yuborish
"""
import aiosmtplib
from email.mime.text import MIMEText
import config
import logging

logger = logging.getLogger(__name__)


async def send_password_email(to_email: str, password: str) -> bool:
    if not config.GMAIL_APP_PASSWORD:
        logger.warning("GMAIL_APP_PASSWORD sozlanmagan!")
        return False
    try:
        msg = MIMEText(
            f"Salom Admin!\n\n"
            f"Sizning bot admin parolingiz:\n\n"
            f"🔑 Parol: {password}\n\n"
            f"Bu xabar parol 10 marta noto'g'ri kiritilgani uchun "
            f"avtomatik yuborildi.\n\n"
            f"Xavfsizlik uchun parolni o'zgartirishni tavsiya etamiz.",
            "plain", "utf-8"
        )
        msg["Subject"] = "⚠️ Bot Admin Parol Eslatmasi"
        msg["From"] = config.ADMIN_GMAIL
        msg["To"] = to_email

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=config.ADMIN_GMAIL,
            password=config.GMAIL_APP_PASSWORD,
        )
        logger.info(f"Email yuborildi: {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email yuborishda xato: {e}")
        return False
