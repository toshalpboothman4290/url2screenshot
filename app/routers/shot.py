# shot.py  (additions + tiny refactor)

import json
import re
from aiogram import Router, F
from aiogram.types import Message, ForceReply
from aiogram.filters import Command

from app.services.db import enqueue_job, get_queue_position, get_queue_depth
from app.services.parse import parse_shot_args

router = Router()

# Regex برای تشخیص URL خام (وقتی کاربر مستقیم لینک می‌فرسته)
URL_REGEX = re.compile(r"^https?://", re.I)

# --- NEW: shared prompt texts so we can distinguish which reply is for what ---
PROMPT_IMAGE = "لطفاً لینک خود را اینجا بچسبانید 👇"
PROMPT_PDF   = "لطفاً لینک خود را برای خروجی PDF اینجا بچسبانید 👇"

# --- NEW: helper to force pdf flag ---
def force_pdf_flag(params_json: str) -> str:
    try:
        data = json.loads(params_json or "{}")
    except Exception:
        data = {}
    data["pdf"] = True
    return json.dumps(data, ensure_ascii=False)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("دستور العمل کار با بات")


@router.message(Command("getshotimage"))
async def cmd_shot_image(message: Message):
    """
    کاربر /getshotimage می‌زند.
    - اگر بدون آرگومان باشد → ForceReply
    - اگر لینک همراه باشد → enqueue
    """
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        await message.answer(PROMPT_IMAGE, reply_markup=ForceReply(selective=True))
        return

    the_url = args[1].strip()
    if not URL_REGEX.match(the_url):
        await message.answer("❌ لینک معتبر نیست. باید با http:// یا https:// شروع شود.")
        return

    params_json = parse_shot_args(message.text or "")
    job_id = enqueue_job(user_id=message.from_user.id, url=the_url, params_json=params_json)

    pos = get_queue_position(job_id)
    depth = get_queue_depth()
    await message.answer(f"✅ درخواست شما ثبت شد.\nجایگاه شما در صف: {pos} از {depth}")


# --- NEW: /getshotpdf behaves like /getshotimage but forces pdf flag ---
@router.message(Command("getshotpdf"))
async def cmd_shot_pdf(message: Message):
    """
    کاربر /getshotpdf می‌زند.
    - اگر بدون آرگومان باشد → ForceReply (پیام متفاوت برای تشخیص)
    - اگر لینک همراه باشد → enqueue با pdf=True
    """
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        await message.answer(PROMPT_PDF, reply_markup=ForceReply(selective=True))
        return

    the_url = args[1].strip()
    if not URL_REGEX.match(the_url):
        await message.answer("❌ لینک معتبر نیست. باید با http:// یا https:// شروع شود.")
        return

    params_json = parse_shot_args(message.text or "")
    params_json = force_pdf_flag(params_json)  # enforce pdf
    job_id = enqueue_job(user_id=message.from_user.id, url=the_url, params_json=params_json)

    pos = get_queue_position(job_id)
    depth = get_queue_depth()
    await message.answer(f"✅ درخواست PDF شما ثبت شد.\nجایگاه شما در صف: {pos} از {depth}")


@router.message(F.reply_to_message, F.reply_to_message.text.contains(PROMPT_IMAGE))
async def handle_force_reply_image(message: Message):
    """
    وقتی کاربر در پاسخ به ForceReply (تصویر) لینکش را می‌فرستد
    """
    the_url = message.text.strip()
    if not URL_REGEX.match(the_url):
        await message.answer("❌ لینک معتبر نیست. باید با http:// یا https:// شروع شود.")
        return

    params_json = parse_shot_args(message.text or "")
    job_id = enqueue_job(user_id=message.from_user.id, url=the_url, params_json=params_json)

    pos = get_queue_position(job_id)
    depth = get_queue_depth()
    await message.answer(f"✅ درخواست شما ثبت شد.\nجایگاه شما در صف: {pos} از {depth}")


# --- NEW: separate reply handler for the PDF prompt so we can force pdf flag ---
@router.message(F.reply_to_message, F.reply_to_message.text.contains(PROMPT_PDF))
async def handle_force_reply_pdf(message: Message):
    """
    وقتی کاربر در پاسخ به ForceReply (PDF) لینکش را می‌فرستد
    """
    the_url = message.text.strip()
    if not URL_REGEX.match(the_url):
        await message.answer("❌ لینک معتبر نیست. باید با http:// یا https:// شروع شود.")
        return

    params_json = parse_shot_args(message.text or "")
    params_json = force_pdf_flag(params_json)  # enforce pdf
    job_id = enqueue_job(user_id=message.from_user.id, url=the_url, params_json=params_json)

    pos = get_queue_position(job_id)
    depth = get_queue_depth()
    await message.answer(f"✅ درخواست PDF شما ثبت شد.\nجایگاه شما در صف: {pos} از {depth}")


@router.message(F.text.regexp(URL_REGEX))
async def handle_raw_url(message: Message):
    """
    وقتی کاربر مستقیم لینک خام بفرستد
    (حالت عمومی – اگر کاربر بخواهد PDF، بهتر است از /getshotpdf استفاده کند
     یا در متن لینک فلگ --pdf را اضافه کند)
    """
    the_url = message.text.strip()
    if not URL_REGEX.match(the_url):
        await message.answer("❌ لینک معتبر نیست. باید با http:// یا https:// شروع شود.")
        return

    params_json = parse_shot_args(message.text or "")
    job_id = enqueue_job(user_id=message.from_user.id, url=the_url, params_json=params_json)

    pos = get_queue_position(job_id)
    depth = get_queue_depth()
    await message.answer(f"✅ درخواست شما ثبت شد.\nجایگاه شما در صف: {pos} از {depth}")
