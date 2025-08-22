import asyncio
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright

def _norm_bool(v, default=False):
    if v is None: 
        return default
    if isinstance(v, bool): 
        return v
    if isinstance(v, str): 
        return v.strip().lower() in {"1","true","yes","y","on"}
    return bool(v)

class ShareKit:
    def __init__(self, settings):
        self.s = settings

    async def _inject_hide_css(self, page):
        """
        Hide only common cookie/consent/ad overlays.
        Do NOT hide every fixed element by default, to avoid blank pages.
        """
        try:
            base_css = """
            /* keep scrolling snappy */
            html, body { scroll-behavior: auto !important; }

            /* cookie / consent banners */
            [id*="cookie" i], [class*="cookie" i],
            [id*="consent" i], [class*="consent" i],
            #consent, .fc-consent-root, .qc-cmp2-container, .osano-cm-dialog,
            .sp_choice_type_11, .cc-window, .cc-banner,

            /* lightweight ad labels */
            .ad-banner, .ads-banner, .advert, .advertisement, .ad-container
            {
                opacity: .0001 !important;
                pointer-events: none !important;
            }
            """
            await page.add_style_tag(content=base_css)
        except:
            pass

        # Optional: hide ALL fixed overlays only if explicitly enabled
        try:
            hide_fixed = _norm_bool(getattr(self.s, "HIDE_FIXED_OVERLAYS", False), False)
            if hide_fixed:
                await page.add_style_tag(content="""
                *[style*="position:fixed" i] {
                    opacity: .0001 !important;
                    pointer-events: none !important;
                }
                """)
        except:
            pass


    async def _pre_scroll(self, page):
        # Trigger lazy-load
        try:
            total = await page.evaluate("() => document.documentElement.scrollHeight")
            step = 1200
            y = 0
            while y < total:
                await page.evaluate(f"window.scrollTo(0, {y});")
                await asyncio.sleep(0.05)
                y += step
            await asyncio.sleep(0.1)
            await page.evaluate("window.scrollTo(0, 0);")
            await asyncio.sleep(0.05)
        except:
            pass

    async def launch_browser(self, viewport, dsf, is_mobile, has_touch, ua, headless=True):
        # Start Playwright without a context manager so it stays alive
        pw = await async_playwright().start()

        chromium_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        try:
            browser = await pw.chromium.launch(headless=headless, args=chromium_args)
            context = await browser.new_context(
                viewport=viewport,
                device_scale_factor=dsf,
                is_mobile=is_mobile,
                has_touch=has_touch,
                user_agent=ua,
                locale="fa-IR",
                timezone_id="Asia/Tehran",
                accept_downloads=True,
            )
            return pw, browser, context
        except Exception:
            # If launch fails, make sure we don’t leak the Playwright driver
            await pw.stop()
            raise
        
    async def capture(
        self, 
        url: str, 
        *, 
        device: str = "mobile",          # "mobile" | "desktop"
        full_page: Optional[bool] = None,
        force_slice: bool = False,
        pdf: bool = False,
        delay_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns a list like:
        [ { "data": bytes, "file_name": "screenshot_01.png", "mime": "image/png" }, ... ]
        or a single PDF item if pdf=True.
        """
        headless = _norm_bool(getattr(self.s, "HEADLESS", True), True)
        nav_timeout = int(getattr(self.s, "NAVIGATION_TIMEOUT_MS", 60000))
        block_types = set(str(getattr(self.s, "BLOCK_RESOURCE_TYPES", "media,font,websocket")).split(","))
        hide_overlays = _norm_bool(getattr(self.s, "HIDE_COMMON_OVERLAYS", True), True)

        # -------- device profiles --------
        if (device or "mobile").lower() == "desktop":
            viewport = {"width": 1920, "height": 1080}   # wide for better readability
            dsf = 2                                      # 2x desktop → 3840 px wide effective
            is_mobile = False; has_touch = False
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        else:
            viewport = {"width": 430, "height": 844}     # real smartphone width
            dsf = 4                                      # ← DPI بالا برای موبایل (شارپ‌تر)
            is_mobile = True; has_touch = True
            ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

        FULLPAGE_MAX = int(getattr(self.s, "FULLPAGE_MAX_HEIGHT_PX", 9000))
        OVERLAP = int(getattr(self.s, "SLICE_OVERLAP_PX", 80))
        MAX_PARTS = int(getattr(self.s, "MAX_SCREENS_PER_JOB", 10))

        async with async_playwright() as pw:
            pw, browser, context = await self.launch_browser(viewport, dsf, is_mobile, has_touch, ua, headless)

            # Block heavy resource types
            async def _router(route, request):
                try:
                    if request.resource_type in block_types:
                        await route.abort()
                        return
                except:
                    pass
                await route.continue_()

            await context.route("**/*", _router)

            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass

            if hide_overlays:
                await self._inject_hide_css(page)

            await self._pre_scroll(page)

            if delay_ms and int(delay_ms) > 0:
                await asyncio.sleep(int(delay_ms) / 1000)

            # PDF path (when explicitly requested)
            if pdf:
                pdf_bytes = await page.pdf(
                    format="A4", print_background=True, 
                    margin={"top":"0","right":"0","bottom":"0","left":"0"}
                )
                await context.close(); await browser.close(); await pw.stop()
                return [{"data": pdf_bytes, "file_name": "page.pdf", "mime": "application/pdf"}]

            # measure total height
            total_h = await page.evaluate("() => document.documentElement.scrollHeight")
            want_full = bool(full_page)
            if force_slice:
                want_full = False
            elif full_page is None:
                # default behavior: try full if short, else slice
                want_full = total_h <= FULLPAGE_MAX

            results: List[Dict[str, Any]] = []

            if want_full:
                png = await page.screenshot(full_page=True, type="png")   # ← اجبار PNG
                results.append({"data": png, "file_name": "screenshot.png", "mime": "image/png"})
            else:
                # viewport slicing (crisp, no scaling)
                vh = viewport["height"]
                y = 0
                i = 1
                while y < total_h and i <= MAX_PARTS:
                    await page.evaluate(f"window.scrollTo(0, {max(0, y)});")
                    await asyncio.sleep(0.12)
                    png = await page.screenshot(type="png")              # ← اجبار PNG
                    results.append({"data": png, "file_name": f"screenshot_{i:02d}.png", "mime": "image/png"})
                    y += (vh - OVERLAP)
                    i += 1

            await context.close()
            await browser.close()
            await pw.stop()
            return results
