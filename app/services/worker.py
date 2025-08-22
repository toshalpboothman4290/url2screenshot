import asyncio, time, traceback, json
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from app.config import settings
from app.services.db import next_queued_job, complete_job
from app.services.sharekit.core import ShareKit
from app.services.alerts import AdminAlerter

async def job_worker(worker_id: int, bot: Bot):
    kit = ShareKit(settings)
    alerter = AdminAlerter(bot, settings)
    print(f"[worker:{worker_id}] started.")

    while True:
        job = next_queued_job()
        if not job:
            await asyncio.sleep(2)
            continue

        job_id = job["id"]
        user_id = job["user_id"]
        url = job["url"]
        t0 = time.time()
        print(f"[worker:{worker_id}] picked job #{job_id} for user {user_id}: {url}")

        try:
            # خواندن پارامترهای کاربر از params_json
            try:
                opts = json.loads(job.get("params_json") or "{}")
            except Exception:
                opts = {}

            device = "desktop" if opts.get("desktop") else "mobile"
            force_slice = bool(opts.get("slice", False))
            full_page = bool(opts.get("full", False))
            pdf = bool(opts.get("pdf", False))
            delay_ms = int(opts.get("delay_ms")) if str(opts.get("delay_ms", "")).isdigit() else None

            # فراخوانی ShareKit.capture با فلگ‌های واقعی
            items = await kit.capture(
                url,
                device=device,
                full_page=full_page,
                force_slice=force_slice,
                pdf=pdf,
                delay_ms=delay_ms,
            )

            sent_any = False
            total = len(items)
            for idx, it in enumerate(items, start=1):
                data = it["data"]
                filename = it.get("file_name") or ("page.pdf" if pdf else f"screenshot_{job_id}_{idx:02d}.png")
                try:
                    await bot.send_document(
                        user_id,
                        BufferedInputFile(data, filename),
                        caption=(f"Part {idx}/{total}" if total > 1 else None),
                        disable_content_type_detection=True,
                    )
                    sent_any = True
                except TelegramBadRequest as e:
                    print(f"[worker:{worker_id}] send_document failed for job {job_id}: {e!r}")
                    try:
                        await alerter.send_error("SendDocumentFailed", str(e), url=url, user_id=user_id)
                    except Exception:
                        pass

            # ❗ complete_job همگام (sync) است → نباید await شود
            complete_job(job_id, ok=sent_any, error=None if sent_any else "send failed")
            print(f"[worker:{worker_id}] job #{job_id} done in {time.time()-t0:.1f}s")

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[worker:{worker_id}] job #{job_id} FAILED: {e}\n{tb}")
            try:
                await bot.send_message(
                    user_id,
                    f"❌ خطا در گرفتن اسکرین‌شات:\n`{str(e)[:300]}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            try:
                await alerter.send_error("WorkerCaptureFailed", str(e), url=url, user_id=user_id, traceback=tb)
            except Exception:
                pass
            # ❗ این‌جا هم بدون await
            complete_job(job_id, ok=False, error=str(e))
