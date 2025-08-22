import asyncio, os

from .services.db import init_db
from app.config import settings
from app.bot import build_bot, build_dispatcher
from app.routers import start, shot
from app.services.worker import job_worker   # 🔹 اضافه شد
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, \
                           BotCommandScopeAllPrivateChats, \
                           BotCommandScopeAllGroupChats, \
                           BotCommandScopeAllChatAdministrators

COMMANDS = [
    BotCommand(command="getshotimage", description="اسکرین -> عکس"),
    BotCommand(command="getshotpdf",   description="اسکرین -> PDF"),
    BotCommand(command="help",         description="توضیحات کار با بات"),
]

async def reset_and_set_commands(bot: Bot):
    # 1) پاک کردن همهٔ اسکوپ‌های رایج
    #await bot.delete_my_commands(scope=BotCommandScopeDefault())
    #await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    #await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
    #await bot.delete_my_commands(scope=BotCommandScopeAllChatAdministrators())

    # 2) تنظیم دستورات برای اسکوپ‌هایی که استفاده می‌کنی
    await bot.set_my_commands(COMMANDS)

async def main():
    # Init DB
    init_db("sqlite:///./data/users.db")

    bot = build_bot()
    dp = build_dispatcher()

    await reset_and_set_commands(bot)

    dp.include_router(start.router)
    dp.include_router(shot.router)
       
    me = await bot.get_me()
    print(f"✅ Bot {me.username} is running and listening for updates...")

    # 🔹 استارت Workerها (پیش‌فرض 5 از .env)
    worker_count = int(getattr(settings, "WORKER_COUNT", 5))
    for i in range(worker_count):
        asyncio.create_task(job_worker(i, bot))

    # Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
