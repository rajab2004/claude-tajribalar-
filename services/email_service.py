import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

from config import config


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    is_html: bool = False
) -> bool:
    """
    Asinxron email yuborish (Gmail SMTP orqali).
    Returns: True (muvaffaqiyatli) | False (xato)
    """
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        logger.error("Gmail sozlamalari .env faylda yo'q!")
        return False

    try:
        message = MIMEMultipart("alternative")
        message["From"] = config.GMAIL_USER
        message["To"] = to_email
        message["Subject"] = subject

        content_type = "html" if is_html else "plain"
        message.attach(MIMEText(body, content_type, "utf-8"))

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=config.GMAIL_USER,
            password=config.GMAIL_APP_PASSWORD,
        )
        logger.info(f"Email yuborildi: {to_email} | {subject}")
        return True

    except aiosmtplib.SMTPException as e:
        logger.error(f"SMTP xatosi: {e}")
        return False
    except Exception as e:
        logger.error(f"Email yuborishda xato: {e}")
        return False


async def send_admin_password_recovery(
    admin_gmail: str,
    admin_username: str,
    new_password: str
) -> bool:
    """
    Admin parolini Gmail ga yuborish
    (10 marta noto'g'ri kiritilganda chaqiriladi)
    """
    subject = "🔐 Telegram Bot — Admin Parol Tiklash"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #e74c3c;">⚠️ Admin Parol Tiklash</h2>
        <p>Salom, <b>@{admin_username}</b>!</p>
        <p>Botga <b>10 marta noto'g'ri parol</b> kiritildi.</p>
        <hr>
        <p>Sizning yangi <b>vaqtinchalik parolingiz</b>:</p>
        <div style="background:#f8f9fa; padding:15px; border-radius:8px;
                    font-size:22px; font-weight:bold; letter-spacing:3px;
                    color:#2c3e50; text-align:center;">
            {new_password}
        </div>
        <hr>
        <p style="color:#e74c3c;">
            ⚠️ Botga kirgandan so'ng darhol parolni o'zgartiring!
        </p>
        <p style="color:#95a5a6; font-size:12px;">
            Bu xabar avtomatik yuborildi. Javob bermang.
        </p>
    </body>
    </html>
    """
    return await send_email(admin_gmail, subject, body, is_html=True)


async def send_user_credentials(
    bot,
    user_telegram_id: int,
    password: str,
    expires_at: str,
    bot_username: str
) -> bool:
    """
    Yangi foydalanuvchiga bot orqali kirish ma'lumotlarini yuborish.
    """
    try:
        text = (
            "🎉 <b>Botga kirish ma'lumotlaringiz tayyor!</b>\n\n"
            f"🔑 <b>Parol:</b> <code>{password}</code>\n"
            f"📅 <b>Muddat:</b> {expires_at} gacha\n\n"
            f"🤖 <b>Botga o'tish:</b> @{bot_username}\n\n"
            "⚠️ <i>Parolingizni hech kimga bermang!</i>"
        )
        await bot.send_message(user_telegram_id, text, parse_mode="HTML")
        logger.info(f"Foydalanuvchiga ma'lumot yuborildi: {user_telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {user_telegram_id} | {e}")
        return False


async def send_expiry_warning(
    bot,
    user_telegram_id: int,
    admin_phone: str,
    admin_username: str
) -> bool:
    """
    Foydalanuvchiga muddat tugagani haqida xabar yuborish.
    """
    try:
        text = (
            "⏰ <b>Botdan foydalanish muddatingiz tugadi!</b>\n\n"
            "Davom etish uchun admin bilan bog'laning:\n\n"
            f"📞 <b>Telefon:</b> {admin_phone}\n"
            f"💬 <b>Telegram:</b> @{admin_username}"
        )
        await bot.send_message(user_telegram_id, text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.error(f"Muddat ogohlantirishi yuborishda xato: {user_telegram_id} | {e}")
        return False


async def send_session_disconnected(
    bot,
    user_telegram_id: int
) -> bool:
    """
    Foydalanuvchiga sessiya uzilgani haqida xabar yuborish.
    """
    try:
        text = (
            "⚠️ <b>Telegram akkauntingiz uzildi!</b>\n\n"
            "E'lonlar yuborishni davom ettirish uchun "
            "akkauntingizni qayta ulang.\n\n"
            "📱 <b>Sozlamalar → Telegram akkauntni ulash</b>"
        )
        await bot.send_message(user_telegram_id, text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.error(f"Sessiya uzilish xabari yuborishda xato: {user_telegram_id} | {e}")
        return False
