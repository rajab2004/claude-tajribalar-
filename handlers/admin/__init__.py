from aiogram import Router
from handlers.admin import auth, users, stats, settings

admin_router = Router()
admin_router.include_router(auth.router)
admin_router.include_router(settings.router)
admin_router.include_router(users.router)
admin_router.include_router(stats.router)
