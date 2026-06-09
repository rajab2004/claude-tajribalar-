from aiogram import Router
from handlers.user import auth, channels, announcements, settings

user_router = Router()
user_router.include_router(auth.router)
user_router.include_router(settings.router)   # settings auth dan oldin (📱 ulash)
user_router.include_router(channels.router)
user_router.include_router(announcements.router)
