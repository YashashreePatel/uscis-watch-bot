"""Telegram notification helpers."""

from __future__ import annotations

import json
from typing import Iterable

import requests

from .config import Settings, require_telegram_settings


TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_DIGEST_ITEMS = 20
MAX_TELEGRAM_MESSAGE_LENGTH = 4000


class TelegramNotificationError(RuntimeError):
    """Raised when Telegram rejects a notification."""


def _topics_text(update: dict[str, object]) -> str:
    raw_topics = str(update.get("matched_topics") or "").strip()
    return raw_topics if raw_topics else "General Immigration"


def format_daily_message(update: dict[str, object]) -> str:
    """Create the daily priority Telegram message text."""

    message = (
        "🚨 New USCIS Priority Update\n\n"
        f"Topic: {_topics_text(update)}\n"
        f"Source: {update['source']}\n\n"
        "Title:\n"
        f"{update['title']}\n\n"
        "Link:\n"
        f"{update['url']}"
    )
    return _fit_message(message)


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
            current_message = _fit_message(header + entry)
        else:
            current_message += entry

    if current_message.strip():
        messages.append(current_message.rstrip())

    return messages


def send_telegram_message(message: str, settings: Settings) -> None:
    """Send a plain-text Telegram message."""

    require_telegram_settings(settings)
    prepared_message = _fit_message(message)

    response = requests.post(
        f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage",
        data={
            "chat_id": settings.telegram_chat_id,
            "text": prepared_message,
            "disable_web_page_preview": "true",
        },
        timeout=settings.request_timeout,
    )
    if response.ok:
        return

    description = _telegram_error_description(response)
    raise TelegramNotificationError(
        f"Telegram sendMessage failed with status {response.status_code}: {description}. "
        "Check TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and whether the bot can message that chat."
    )


def _fit_message(message: str) -> str:
    """Trim oversized plain-text messages to stay within Telegram limits."""

    if len(message) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return message

    suffix = "\n\n[Message truncated to fit Telegram limits]"
    allowed_length = MAX_TELEGRAM_MESSAGE_LENGTH - len(suffix)
    return message[:allowed_length].rstrip() + suffix


def _telegram_error_description(response: requests.Response) -> str:
    """Extract a readable Telegram API error message from the response."""

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        description = payload.get("description")
        if description:
            return str(description)

    text = response.text.strip()
    return text or "Unknown Telegram API error"
