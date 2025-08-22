from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")

HELP_TEXT = (
    "📸 راهنمای سریع:\n"
    "• نمونه: `/shot https://example.com`\n"
    "• گزینه‌ها: `--mobile` (نمای موبایل)، `--full` (تمام‌صفحه)، `--pdf`، "
    "`--slow` (برای اینترنت کند ایران)، `--delay=7000`\n\n"
    "مثال‌ها:\n"
    "`/shot https://bbc.com --mobile`\n"
    "`/shot https://example.com --full --slow`\n"
)
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")
