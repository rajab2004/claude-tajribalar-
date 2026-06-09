from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ============================================================
# START MENYUSI
# ============================================================

def get_start_keyboard() -> ReplyKeyboardMarkup:
    """Boshlang'ich menyu - 2 ta tugma"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👤 Foydalanuvchi sifatida kirish"),
        KeyboardButton(text="🔐 Admin sifatida kirish"),
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ============================================================
# UMUMIY TUGMALAR
# ============================================================

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Faqat 'Orqaga' tugmasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⬅️ Orqaga"))
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Tasdiqlash inline tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
    )
    return builder.as_markup()


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Ha / Yo'q inline tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data="yes"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="no"),
    )
    return builder.as_markup()


def get_save_cancel_keyboard() -> InlineKeyboardMarkup:
    """Saqlash / Bekor qilish inline tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Saqlash", callback_data="save"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
    )
    return builder.as_markup()


# ============================================================
# FOYDALANUVCHI MENYUSI
# ============================================================

def get_user_main_menu() -> ReplyKeyboardMarkup:
    """Foydalanuvchi bosh menyusi - 6 ta bo'lim"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📱 Telegram akkauntni ulash"),
        KeyboardButton(text="📢 Guruh va kanallar"),
    )
    builder.row(
        KeyboardButton(text="📝 Yangi e'lon yaratish"),
        KeyboardButton(text="📋 Mening e'lonlarim"),
    )
    builder.row(
        KeyboardButton(text="📞 Admin bilan bog'lanish"),
        KeyboardButton(text="⚙️ Sozlamalar"),
    )
    return builder.as_markup(resize_keyboard=True)


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqam ulashish tugmasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Kontakt ulashish", request_contact=True))
    builder.row(KeyboardButton(text="⬅️ Orqaga"))
    return builder.as_markup(resize_keyboard=True)


# ============================================================
# KANAL MENYUSI
# ============================================================

def get_channels_menu() -> ReplyKeyboardMarkup:
    """Kanallar boshqaruvi menyusi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Yangi link qo'shish"))
    builder.row(KeyboardButton(text="📋 Barcha linklarni ko'rish"))
    builder.row(KeyboardButton(text="🏠 Bosh menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True)


def get_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Kanallar ro'yxati - har birida O'chirish tugmasi"""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        # Link ko'rsatish (uzun bo'lsa qisqartirish)
        link_text = channel.link if len(channel.link) <= 35 else channel.link[:32] + "..."
        builder.row(InlineKeyboardButton(
            text=f"🔗 {link_text}",
            callback_data=f"channel_info_{channel.id}"
        ))
        builder.row(InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=f"delete_channel_{channel.id}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="channels_back"))
    return builder.as_markup()


def get_channel_delete_confirm(channel_id: int) -> InlineKeyboardMarkup:
    """Kanalni o'chirishni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"confirm_delete_channel_{channel_id}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="channels_list"),
    )
    return builder.as_markup()


# ============================================================
# E'LON MENYUSI
# ============================================================

def get_announcement_confirm_keyboard() -> InlineKeyboardMarkup:
    """E'lonni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="send_announcement"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_announcement"),
    )
    return builder.as_markup()


def get_close_announcement_keyboard(announcement_id: int) -> InlineKeyboardMarkup:
    """E'lonni yopish tugmasi (bot chatida ko'rsatiladi)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔒 Yopish",
            callback_data=f"close_ann_{announcement_id}"
        )
    )
    return builder.as_markup()


def get_my_announcements_menu() -> ReplyKeyboardMarkup:
    """Mening e'lonlarim menyusi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📢 Ochiq e'lonlarim"))
    builder.row(KeyboardButton(text="🔒 Yopilgan e'lonlarim"))
    builder.row(KeyboardButton(text="🏠 Bosh menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True)


def get_open_announcements_keyboard(announcements: list) -> InlineKeyboardMarkup:
    """Ochiq e'lonlar ro'yxati - har birida Yopish tugmasi"""
    builder = InlineKeyboardBuilder()
    for ann in announcements:
        text_preview = ann.message_text[:30] + "..." if len(ann.message_text) > 30 else ann.message_text
        builder.row(
            InlineKeyboardButton(
                text=f"📢 {text_preview}",
                callback_data=f"ann_preview_{ann.id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔒 Yopish",
                callback_data=f"close_ann_{ann.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="my_ann_back"))
    return builder.as_markup()


def get_closed_announcements_keyboard(announcements: list) -> InlineKeyboardMarkup:
    """Yopilgan e'lonlar ro'yxati (faqat ko'rish)"""
    builder = InlineKeyboardBuilder()
    for ann in announcements:
        text_preview = ann.message_text[:30] + "..." if len(ann.message_text) > 30 else ann.message_text
        builder.row(
            InlineKeyboardButton(
                text=f"🔒 {text_preview}",
                callback_data=f"closed_ann_preview_{ann.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="my_ann_back"))
    return builder.as_markup()


# ============================================================
# SOZLAMALAR MENYUSI
# ============================================================

def get_settings_keyboard() -> ReplyKeyboardMarkup:
    """Foydalanuvchi sozlamalari"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔄 Parolni o'zgartirish"))
    builder.row(KeyboardButton(text="⏱ Yuborish intervalini o'zgartirish"))
    builder.row(KeyboardButton(text="🔌 Telegram akkauntni uzish"))
    builder.row(KeyboardButton(text="🏠 Bosh menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True)


def get_interval_keyboard() -> InlineKeyboardMarkup:
    """Interval tanlash tugmalari"""
    intervals = [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20]
    builder = InlineKeyboardBuilder()
    row = []
    for i, minutes in enumerate(intervals):
        row.append(
            InlineKeyboardButton(
                text=f"{minutes}m",
                callback_data=f"interval_{minutes}"
            )
        )
        if len(row) == 4 or i == len(intervals) - 1:
            builder.row(*row)
            row = []
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


# ============================================================
# ADMIN MENYUSI
# ============================================================

def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Admin bosh menyusi"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="➕ Foydalanuvchi qo'shish"),
        KeyboardButton(text="👥 Foydalanuvchilar ro'yhati"),
    )
    builder.row(
        KeyboardButton(text="📊 Bot statistikasi"),
        KeyboardButton(text="⚙️ Admin sozlamalari"),
    )
    return builder.as_markup(resize_keyboard=True)


def get_users_list_menu() -> ReplyKeyboardMarkup:
    """Foydalanuvchilar ro'yxati menyusi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👥 Barcha foydalanuvchilar"))
    builder.row(KeyboardButton(text="🟢 Faol foydalanuvchilar"))
    builder.row(KeyboardButton(text="⏰ Muddati tugagan foydalanuvchilar"))
    builder.row(KeyboardButton(text="🏠 Bosh menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True)


def get_months_keyboard() -> InlineKeyboardMarkup:
    """Oy tanlash tugmalari (1-12)"""
    builder = InlineKeyboardBuilder()
    row = []
    for i in range(1, 13):
        row.append(
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"months_{i}"
            )
        )
        if len(row) == 4:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


def get_user_actions_keyboard(user_id: int, is_expired: bool = False) -> InlineKeyboardMarkup:
    """Foydalanuvchi amallari tugmalari"""
    builder = InlineKeyboardBuilder()
    if is_expired:
        builder.row(
            InlineKeyboardButton(
                text="📅 Muddatni uzaytirish",
                callback_data=f"extend_user_{user_id}"
            ),
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=f"delete_user_{user_id}"
            ),
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=f"delete_user_{user_id}"
            )
        )
    return builder.as_markup()


def get_admin_settings_keyboard() -> ReplyKeyboardMarkup:
    """Admin sozlamalari"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔑 Parolni o'zgartirish"))
    builder.row(KeyboardButton(text="📧 Gmail manzilini o'zgartirish"))
    builder.row(KeyboardButton(text="📞 Bog'lanish ma'lumotlarini o'zgartirish"))
    builder.row(KeyboardButton(text="👤 Foydalanuvchi parolini o'zgartirish"))
    builder.row(KeyboardButton(text="🏠 Bosh menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True)


def get_extend_months_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Muddatni uzaytirish uchun oy tanlash"""
    builder = InlineKeyboardBuilder()
    row = []
    for i in range(1, 13):
        row.append(
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"extend_months_{user_id}_{i}"
            )
        )
        if len(row) == 4:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()
