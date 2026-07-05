"""
Barcha Inline va Reply klaviaturalar
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ═══════════════════════════════════════════════════════
#  KIRISH MENYUSI
# ═══════════════════════════════════════════════════════
def start_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="👤 Foydalanuvchi sifatida kirish")
    kb.button(text="🔐 Admin sifatida kirish")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  FOYDALANUVCHI BOSH MENYUSI
# ═══════════════════════════════════════════════════════
def user_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Telegram akkauntni ulash")
    kb.button(text="📢 Guruh va kanallar")
    kb.button(text="📝 Yangi e'lon yaratish")
    kb.button(text="📋 Mening e'lonlarim")
    kb.button(text="📞 Admin bilan bog'lanish")
    kb.button(text="⚙️ Sozlamalar")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  KANALAR MENYUSI
# ═══════════════════════════════════════════════════════
def channels_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Yangi link qo'shish")
    kb.button(text="📋 Barcha linklarni ko'rish")
    kb.button(text="🏠 Bosh menyu")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  E'LONLAR MENYUSI
# ═══════════════════════════════════════════════════════
def announcements_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📢 Ochiq e'lonlarim")
    kb.button(text="🔒 Yopilgan e'lonlarim")
    kb.button(text="🏠 Bosh menyu")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  SOZLAMALAR — INTERVAL TANLASH
# ═══════════════════════════════════════════════════════
def interval_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    intervals = [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20]
    for m in intervals:
        builder.button(text=f"{m}m", callback_data=f"interval:{m}")
    builder.adjust(4)
    return builder.as_markup()


# ═══════════════════════════════════════════════════════
#  SOZLAMALAR MENYUSI
# ═══════════════════════════════════════════════════════
def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Parolni o'zgartirish", callback_data="settings:change_password")
    builder.button(text="⏱ Interval o'zgartirish", callback_data="settings:interval")
    builder.button(text="🔌 Akkauntni uzish", callback_data="settings:disconnect")
    builder.button(text="🏠 Bosh menyu", callback_data="settings:back")
    builder.adjust(1)
    return builder.as_markup()


# ═══════════════════════════════════════════════════════
#  TASDIQLASH TUGMALARI
# ═══════════════════════════════════════════════════════
def confirm_keyboard(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=yes_cb)
    builder.button(text="❌ Yo'q", callback_data=no_cb)
    builder.adjust(2)
    return builder.as_markup()


def save_cancel_keyboard(save_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Saqlash", callback_data=save_cb)
    builder.button(text="❌ Bekor qilish", callback_data=cancel_cb)
    builder.adjust(2)
    return builder.as_markup()


# ═══════════════════════════════════════════════════════
#  E'LON YOPISH TUGMASI
# ═══════════════════════════════════════════════════════
def close_announcement_keyboard(ann_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Yopish", callback_data=f"ann:close:{ann_id}")
    return builder.as_markup()


# ═══════════════════════════════════════════════════════
#  KONTAKT ULASHISH
# ═══════════════════════════════════════════════════════
def share_contact_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Kontakt ulashish", request_contact=True)
    kb.button(text="❌ Bekor qilish")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ═══════════════════════════════════════════════════════
#  ADMIN BOSH MENYUSI
# ═══════════════════════════════════════════════════════
def admin_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Foydalanuvchi qo'shish")
    kb.button(text="👥 Foydalanuvchilar ro'yhati")
    kb.button(text="📊 Bot statistikasi")
    kb.button(text="⚙️ Admin sozlamalari")
    kb.button(text="🚪 Chiqish")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  ADMIN — FOYDALANUVCHILAR RO'YHATI
# ═══════════════════════════════════════════════════════
def users_list_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="👥 Barcha foydalanuvchilar")
    kb.button(text="🟢 Faol foydalanuvchilar")
    kb.button(text="⏰ Muddati tugaganlar")
    kb.button(text="🔙 Admin menyu")
    kb.adjust(2, 1, 1)
    return kb.as_markup(resize_keyboard=True)


# ═══════════════════════════════════════════════════════
#  OY TANLASH
# ═══════════════════════════════════════════════════════
def months_keyboard(prefix: str = "months") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in range(1, 13):
        builder.button(text=f"{m} oy", callback_data=f"{prefix}:{m}")
    builder.adjust(4)
    return builder.as_markup()


# ═══════════════════════════════════════════════════════
#  FOYDALANUVCHI KARTASI (Admin uchun)
# ═══════════════════════════════════════════════════════
def user_action_keyboard(user_id: int,
                          show_extend: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if show_extend:
        builder.button(
            text="📅 Muddatni uzaytirish",
            callback_data=f"admin_user:extend:{user_id}"
        )
    builder.button(
        text="🗑 O'chirish",
        callback_data=f"admin_user:delete:{user_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
