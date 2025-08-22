from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .config import settings

def build_bot() -> Bot:
    return Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def build_dispatcher() -> Dispatcher:
    return Dispatcher()
