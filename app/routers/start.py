import os
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram import Bot
from app.config import settings
from app.services.db import upsert_user
import asyncio
from aiogram.types import CallbackQuery
from app.handlers.upload_to_supabase_s3 import upload_file_to_s3
from app.handlers.database import upsert_user_to_psql

router = Router(name="start")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROFILE_PICS_PATH = os.path.join(ROOT_DIR, "static/profile_pics")

async def _is_member(bot: Bot, user_id: int) -> bool:
    # بای‌پس در حالت توسعه
    if settings.SKIP_CHANNEL_CHECK:
        return True
    if settings.ALLOW_ADMINS_BYPASS and user_id in settings.admin_ids:
        return True

    chat_id = settings.CHANNEL_ID or settings.CHANNEL_USERNAME
    if not chat_id:
        return True  # اگر کانال تنظیم نشده، اجازه بده

    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        # در لوکال ممکن است دسترسی نداشته باشد
        if settings.SKIP_CHANNEL_CHECK_ON_ERROR:
            return True
        print("get_chat_member error:", repr(e), "chat_id=", chat_id, "user_id=", user_id)
        return False

# --------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    is_mem = await _is_member(bot, user.id)

    # دریافت و آپلود عکس پروفایل (اختیاری)
    try:
        photos = await message.bot.get_user_profile_photos(message.from_user.id)
        if photos.total_count > 0:
            file = await message.bot.get_file(photos.photos[0][-1].file_id)
            os.makedirs(PROFILE_PICS_PATH, exist_ok=True)
            local_path = f"{PROFILE_PICS_PATH}/{message.from_user.id}.jpg"
            remote_key = f"profile_pics/{message.from_user.id}.jpg"

            await message.bot.download_file(file.file_path, local_path)
            upload_file_to_s3(local_path, remote_key)
            os.remove(local_path)
    except Exception as e:
        print(f"⚠️ Failed to fetch profile picture: {e}")

    # ثبت/به‌روزرسانی کاربر
    upsert_user_to_psql(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username or "",
        f"{message.from_user.id}.jpg",
    )

    upsert_user(user.model_dump(), is_mem)

    if not is_mem:
        join_url = (
            f"https://t.me/{settings.CHANNEL_USERNAME.lstrip('@')}" if settings.CHANNEL_USERNAME else "https://t.me/"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[ 
            InlineKeyboardButton(text="عضویت در کانال", url=join_url),
        ],[
            InlineKeyboardButton(text="✅ بررسی عضویت", callback_data="check_membership")
        ]])
        await message.answer("برای استفاده از بات لازم است ابتدا عضو کانال اصلی شوید.", reply_markup=kb)
        return

    suffix = " (DEV: عضویت چک نمی‌شود)" if settings.SKIP_CHANNEL_CHECK else ""
    await message.answer(
        "خوش آمدی! برای اسکرین‌شات:\n"
        "`/getshotimage <url>` - اسکرین به عکس\n"
        "`/getshotpdf <url>` - اسکرین به pdf\n" + suffix,
        parse_mode="Markdown",
    )

@router.callback_query(F.data == "check_membership")
async def cb_check_membership(cb: CallbackQuery, bot: Bot):
    is_mem = await _is_member(bot, cb.from_user.id)
    upsert_user(cb.from_user.model_dump(), is_mem)
    if is_mem:
        suffix = " (DEV)" if settings.SKIP_CHANNEL_CHECK else ""
        await cb.message.edit_text("عضویت تأیید شد. حالا می‌توانید از دستور /shot استفاده کنید." + suffix)
    else:
        await cb.answer("هنوز عضو کانال شناسایی نشدید.", show_alert=True)

