"""Telegram notification helpers."""

from __future__ import annotations

from typing import Iterable

import requests

from .config import Settings, require_telegram_settings


TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_DIGEST_ITEMS = 20
MAX_TELEGRAM_MESSAGE_LENGTH = 4000


def _topics_text(update: dict[str, object]) -> str:
    raw_topics = str(update.get("matched_topics") or "").strip()
    return raw_topics if raw_topics else "General Immigration"


def format_daily_message(update: dict[str, object]) -> str:
    """Create the daily priority Telegram message text."""

    return (
        "🚨 New USCIS Priority Update\n\n"
        f"Topic: {_topics_text(update)}\n"
        f"Source: {update['source']}\n\n"
        "Title:\n"
        f"{update['title']}\n\n"
        "Link:\n"
        f"{update['url']}"
    )


def format_weekly_digest_messages(updates: list[dict[str, object]]) -> list[str]:
    """Split weekly digest content into Telegram-friendly messages."""

    messages: list[str] = []
    chunk: list[dict[str, object]] = []

    for update in updates:
        chunk.append(update)
        if len(chunk) == MAX_DIGEST_ITEMS:
            messages.extend(_flush_digest_chunk(chunk))
            chunk = []

    if chunk:
        messages.extend(_flush_digest_chunk(chunk))

    return messages


def _flush_digest_chunk(updates: Iterable[dict[str, object]]) -> list[str]:
    header = (
        "📌 Weekly USCIS Immigration Digest\n\n"
        "Here are the latest non-priority USCIS updates this week:\n\n"
    )
    messages: list[str] = []
    current_message = header

    for index, update in enumerate(updates, start=1):
        entry = f"{index}. {update['title']}\n{update['source']}\n{update['url']}\n\n"
        if len(current_message) + len(entry) > MAX_TELEGRAM_MESSAGE_LENGTH:
            messages.append(current_message.rstrip())
            current_message = header + entry
        else:
            current_message += entry

    if current_message.strip():
        messages.append(current_message.rstrip())

    return messages


def send_telegram_message(message: str, settings: Settings) -> None:
    """Send a plain-text Telegram message."""

    require_telegram_settings(settings)

    response = requests.post(
        f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
        data={
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        },
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
