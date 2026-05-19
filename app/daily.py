"""Daily scraper run for priority USCIS WatchBot alerts."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from .classifier import classify_update
from .config import get_settings
from .database import init_db, insert_update, mark_daily_sent
from .notifier import format_daily_message, send_telegram_message
from .scraper import scrape_all_sources


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Run the daily scraper and send priority Telegram alerts."""

    settings = get_settings()
    init_db(settings)

    scraped_updates = scrape_all_sources(settings)
    LOGGER.info("Fetched %s update candidates from official sources.", len(scraped_updates))

    new_priority_updates: list[dict[str, object]] = []
    first_seen_at = datetime.now(timezone.utc).isoformat()

    for scraped_update in scraped_updates:
        classification = classify_update(
            title=str(scraped_update["title"]),
            url=str(scraped_update["url"]),
            snippet=scraped_update.get("snippet"),
        )

        stored_update: dict[str, object] = {
            "title": scraped_update["title"],
            "url": scraped_update["url"],
            "source": scraped_update["source"],
            "category": classification.category,
            "matched_topics": ", ".join(classification.matched_topics),
            "update_type": classification.update_type,
            "first_seen_at": first_seen_at,
            "sent_daily": 0,
            "sent_weekly": 0,
        }

        inserted_id = insert_update(settings, stored_update)
        if inserted_id is None:
            continue

        stored_update["id"] = inserted_id
        if classification.update_type == "daily_priority":
            new_priority_updates.append(stored_update)

    if not new_priority_updates:
        LOGGER.info("No new priority updates to send today.")
        return

    sent_ids: list[int] = []
    for update in new_priority_updates:
        send_telegram_message(format_daily_message(update), settings)
        sent_ids.append(int(update["id"]))
        LOGGER.info("Sent daily alert for %s", update["url"])

    mark_daily_sent(settings, sent_ids)
    LOGGER.info("Marked %s daily alerts as sent.", len(sent_ids))


if __name__ == "__main__":
    main()
