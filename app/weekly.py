"""Weekly digest sender for non-priority USCIS WatchBot updates."""

from __future__ import annotations

import logging

from .config import get_settings
from .database import get_unsent_weekly_updates, init_db, mark_weekly_sent
from .notifier import format_weekly_digest_messages, send_telegram_message


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Send a weekly digest for unsent general immigration updates."""

    settings = get_settings()
    init_db(settings)

    updates = get_unsent_weekly_updates(settings)
    if not updates:
        LOGGER.info("No weekly digest updates waiting to be sent.")
        return

    messages = format_weekly_digest_messages(updates)
    for message in messages:
        send_telegram_message(message, settings)

    mark_weekly_sent(settings, [int(update["id"]) for update in updates])
    LOGGER.info("Sent %s weekly digest updates across %s message(s).", len(updates), len(messages))


if __name__ == "__main__":
    main()
