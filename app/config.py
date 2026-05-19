"""Application configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "updates.db"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = (
    "USCIS-WatchBot/1.0 (+https://github.com/YashashreePatel/uscis-watch-bot)"
)


class ConfigError(ValueError):
    """Raised when required application configuration is missing."""


@dataclass(frozen=True)
class SourceConfig:
    """Metadata for one official source page."""

    name: str
    url: str
    allowed_url_fragments: tuple[str, ...]
    emit_page_snapshot: bool = False
    max_results: int = 25


OFFICIAL_SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        name="USCIS Alerts",
        url="https://www.uscis.gov/newsroom/alerts",
        allowed_url_fragments=("/newsroom/alerts/", "/newsroom/"),
        max_results=25,
    ),
    SourceConfig(
        name="USCIS All News",
        url="https://www.uscis.gov/newsroom/all-news",
        allowed_url_fragments=("/newsroom/",),
        max_results=25,
    ),
    SourceConfig(
        name="USCIS News Releases",
        url="https://www.uscis.gov/newsroom/news-releases",
        allowed_url_fragments=("/newsroom/news-releases/",),
        max_results=25,
    ),
    SourceConfig(
        name="USCIS Policy Manual Updates",
        url="https://www.uscis.gov/policy-manual/updates",
        allowed_url_fragments=("/sites/default/files/document/policy-manual-updates/",),
        max_results=40,
    ),
    SourceConfig(
        name="USCIS Adjustment of Status Filing Charts",
        url=(
            "https://www.uscis.gov/green-card/green-card-processes-and-procedures/"
            "visa-availability-priority-dates/adjustment-of-status-filing-charts-"
            "from-the-visa-bulletin"
        ),
        allowed_url_fragments=(
            "/green-card/green-card-processes-and-procedures/"
            "visa-availability-priority-dates/adjustment-of-status-filing-charts-"
            "from-the-visa-bulletin",
        ),
        emit_page_snapshot=True,
        max_results=5,
    ),
    SourceConfig(
        name="Department of State Visa Bulletin",
        url="https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
        allowed_url_fragments=(
            "/content/travel/en/legal/visa-law0/visa-bulletin/",
            "/content/travel/en/legal/visa-law0/visa-bulletin.html",
        ),
        emit_page_snapshot=True,
        max_results=12,
    ),
)


@dataclass(frozen=True)
class Settings:
    """Loaded environment settings."""

    telegram_bot_token: str | None
    telegram_chat_id: str | None
    database_path: Path
    request_timeout: int
    user_agent: str
    sources: tuple[SourceConfig, ...]


def _get_env(name: str) -> str | None:
    """Return a stripped environment variable or None when blank."""

    value = os.getenv(name)
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load environment variables once for the current process."""

    load_dotenv()

    database_path = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH))).expanduser()
    request_timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    user_agent = os.getenv("USER_AGENT", DEFAULT_USER_AGENT)

    return Settings(
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_get_env("TELEGRAM_CHAT_ID"),
        database_path=database_path,
        request_timeout=request_timeout,
        user_agent=user_agent,
        sources=OFFICIAL_SOURCES,
    )


def require_telegram_settings(settings: Settings) -> None:
    """Ensure Telegram credentials are present before sending notifications."""

    missing: list[str] = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        raise ConfigError(
            "Missing required environment variables: " + ", ".join(sorted(missing))
        )
