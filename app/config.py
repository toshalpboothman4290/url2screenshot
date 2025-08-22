from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --------------------وقتی در رندر آپلود کردیم باید از کار بیفتد-----------------------------------
    SKIP_CHANNEL_CHECK: bool = False
    ALLOW_ADMINS_BYPASS: bool = True
    SKIP_CHANNEL_CHECK_ON_ERROR: bool = False
    # -----------------------------------------------------------------------------------------------

    BOT_TOKEN: str
    ADMIN_IDs: str = ""
    CHANNEL_ID: Optional[str] = None
    CHANNEL_USERNAME: Optional[str] = None
    SECRET_KEY: str = "change-me"

    # storage
    DATABASE_URL: str = "sqlite:///./data/users.db"
    LOCAL_STORAGE_DIR: str = "./data/shots"

    # network/webhook
    USE_WEBHOOK: bool = False
    SERVER_URL: str = ""
    WEBHOOK_SECRET: str = ""
    HTTPS_PROXY: str = ""

    # screenshot defaults
    DEFAULT_VIEWPORT_WIDTH: int = 390
    DEFAULT_VIEWPORT_HEIGHT: int = 844
    DEFAULT_DEVICE: str = "mobile"            # desktop|mobile
    DEFAULT_COLOR_SCHEME: str = "light"       # light|dark
    DEFAULT_DELAY_MS: int = 4000
    NAVIGATION_TIMEOUT_MS: int = 25000
    OVERALL_TIMEOUT_MS: int = 40000
    FULLPAGE_MAX_HEIGHT_PX: int = 15000
    SLICE_WINDOW_HEIGHT_PX: int = 5000
    SLICE_OVERLAP_PX: int = 80
    MAX_SCREENS_PER_JOB: int = 10
    MAX_IMAGE_BYTES: int = 9_500_000
    DEFAULT_IMAGE_FORMAT: str = "png"         # png|jpeg
    JPEG_QUALITY: int = 80
    RESIZE_IF_TOO_LARGE: bool = True
    BLOCK_PRIVATE_NETWORK: bool = True
    MAX_REDIRECTS: int = 10
    BLOCK_RESOURCE_TYPES: str = "media,font"
    DISABLE_WINDOW_OPEN: bool = True
    AUTO_DISMISS_DIALOGS: bool = True
    COOKIE_BANNER_CLICK_ATTEMPTS: int = 3
    COOKIE_BANNER_RETRY_MS: int = 800
    HIDE_COMMON_OVERLAYS: bool = True

    # playwright / browser
    HEADLESS: bool = True
    SLOW_MODE: bool = False  # اگر خواستی حالت کند را globally فعال کنی

    # alerts
    ADMIN_ALERTS_ENABLED: bool = True
    ADMIN_ALERTS_LEVEL: str = "error"         # critical|error|warn|info
    ADMIN_ALERTS_DEBOUNCE_SEC: int = 60
    ADMIN_ALERTS_BATCH_WINDOW_SEC: int = 900
    ADMIN_ALERTS_DESTINATION: str = "dm"      # dm|group
    ADMIN_ALERTS_GROUP_ID: Optional[str] = None
    MASK_URLS_IN_ALERTS: bool = True
    TRACE_ID_LENGTH: int = 8
    QUEUE_WARN_DEPTH: int = 50
    QUEUE_WARN_AGE_SEC: int = 60
    DOMAIN_CIRCUIT_BREAK_THRESHOLD: int = 5
    DOMAIN_CIRCUIT_BREAK_WINDOW_SEC: int = 300

    # workers
    WORKER_COUNT: int = 5

    DEFAULT_LANG: str = "fa"

    @property
    def admin_ids(self) -> List[int]:
        ids: List[int] = []
        for part in self.ADMIN_IDs.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

settings = Settings()
