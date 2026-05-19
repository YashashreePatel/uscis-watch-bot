"""Scrape official USCIS and Department of State update sources."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1
from typing import Iterable
import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .config import Settings, SourceConfig


LOGGER = logging.getLogger(__name__)
GENERIC_LINK_TEXT = {
    "read more",
    "learn more",
    "more",
    "more info",
    "subscribe",
    "share",
    "here",
    "click here",
    "view all",
}
SKIP_TEXT_PATTERNS = (
    "facebook",
    "twitter",
    "linkedin",
    "instagram",
    "youtube",
    "footer",
    "breadcrumb",
    "privacy policy",
    "accessibility",
    "contact us",
)
DATE_PATTERN = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+\d{4}",
    flags=re.IGNORECASE,
)
MONTH_YEAR_PATTERN = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{4}",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ScrapedUpdate:
    """One scraped update candidate."""

    title: str
    url: str
    source: str
    published_at: str | None
    snippet: str | None


def scrape_all_sources(settings: Settings) -> list[dict[str, str | None]]:
    """Fetch and normalize updates from every official source."""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": settings.user_agent,
            "Accept": "text/html,application/xhtml+xml",
        }
    )

    results: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()

    for source in settings.sources:
        for update in _safe_fetch_source_updates(source, session, settings):
            if update.url in seen_urls:
                continue
            seen_urls.add(update.url)
            results.append(asdict(update))

    return results


def _safe_fetch_source_updates(
    source: SourceConfig,
    session: requests.Session,
    settings: Settings,
) -> list[ScrapedUpdate]:
    try:
        return fetch_source_updates(source, session, settings)
    except requests.RequestException as exc:
        LOGGER.warning("Request failed for %s: %s", source.url, exc)
    except Exception as exc:  # noqa: BLE001 - keep one bad source from stopping the run
        LOGGER.exception("Unexpected scraping failure for %s: %s", source.url, exc)
    return []


def fetch_source_updates(
    source: SourceConfig,
    session: requests.Session,
    settings: Settings,
) -> list[ScrapedUpdate]:
    """Fetch and parse one source page."""

    response = session.get(source.url, timeout=settings.request_timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("main") or soup.body or soup
    candidates: list[ScrapedUpdate] = []
    seen_urls: set[str] = set()

    for anchor in container.find_all("a", href=True):
        update = _build_update_from_anchor(anchor, source)
        if update is None or update.url in seen_urls:
            continue
        seen_urls.add(update.url)
        candidates.append(update)
        if len(candidates) >= source.max_results:
            break

    if source.emit_page_snapshot:
        snapshot = _build_page_snapshot_update(soup, source)
        if snapshot and snapshot.url not in seen_urls:
            candidates.append(snapshot)

    return candidates


def _build_update_from_anchor(anchor: Tag, source: SourceConfig) -> ScrapedUpdate | None:
    href = (anchor.get("href") or "").strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None

    absolute_url = urljoin(source.url, href)
    if not _is_allowed_source_url(absolute_url, source):
        return None

    anchor_text = _clean_text(anchor.get_text(" ", strip=True))
    title = anchor_text if _looks_like_title(anchor_text) else _extract_context_title(anchor)
    title = _normalize_title(title)
    if not _looks_like_title(title):
        return None

    lower_title = title.lower()
    if any(pattern in lower_title for pattern in SKIP_TEXT_PATTERNS):
        return None

    container = _candidate_container(anchor)
    context_text = _clean_text(container.get_text(" ", strip=True))
    published_at = _extract_date(context_text) or _extract_date(absolute_url)
    snippet = _extract_snippet(context_text, title)

    return ScrapedUpdate(
        title=title,
        url=absolute_url,
        source=source.name,
        published_at=published_at,
        snippet=snippet,
    )


def _build_page_snapshot_update(soup: BeautifulSoup, source: SourceConfig) -> ScrapedUpdate | None:
    title = _clean_text((soup.find("h1") or soup.title).get_text(" ", strip=True))
    if not title:
        return None

    container = soup.find("main") or soup.body or soup
    text = _clean_text(container.get_text(" ", strip=True))
    if not text:
        return None

    published_at = _extract_date(text)
    marker = published_at or _extract_month_year(text)
    snippet = _extract_snippet(text, title)
    fingerprint = sha1(text.encode("utf-8")).hexdigest()[:12]
    snapshot_url = f"{source.url}#snapshot-{fingerprint}"
    snapshot_title = f"{title} ({marker})" if marker and marker.lower() not in title.lower() else title

    return ScrapedUpdate(
        title=snapshot_title,
        url=snapshot_url,
        source=source.name,
        published_at=published_at or marker,
        snippet=snippet,
    )


def _candidate_container(anchor: Tag) -> Tag:
    for tag_name in ("article", "li", "tr", "section", "div", "p"):
        parent = anchor.find_parent(tag_name)
        if parent is not None:
            return parent
    return anchor


def _extract_context_title(anchor: Tag) -> str:
    title_attribute = _normalize_title(_clean_text(anchor.get("title", "")))
    if _looks_like_title(title_attribute):
        return title_attribute

    container = _candidate_container(anchor)
    heading = container.find(["h1", "h2", "h3", "h4"])
    if heading:
        heading_text = _clean_text(heading.get_text(" ", strip=True))
        if _looks_like_title(heading_text):
            return heading_text

    lines = [_clean_text(value) for value in container.stripped_strings]
    for line in lines:
        if _looks_like_title(line):
            return line

    return ""


def _extract_snippet(text: str, title: str) -> str | None:
    cleaned_text = text.replace(title, "").strip(" -:\n")
    if not cleaned_text:
        return None
    return cleaned_text[:280]


def _normalize_title(text: str) -> str:
    normalized = _clean_text(text)
    prefixes = (
        "Select to read more about ",
        "Read more about ",
    )
    for prefix in prefixes:
        if normalized.lower().startswith(prefix.lower()):
            return normalized[len(prefix) :].strip()
    return normalized


def _extract_date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_month_year(text: str) -> str | None:
    match = MONTH_YEAR_PATTERN.search(text)
    return match.group(0) if match else None


def _is_allowed_source_url(url: str, source: SourceConfig) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"www.uscis.gov", "travel.state.gov", "uscis.gov"}:
        return False

    source_parsed = urlparse(source.url)
    if parsed.path == source_parsed.path and parsed.query:
        return False

    if parsed.path.rstrip("/") == source_parsed.path.rstrip("/"):
        return False

    path = parsed.path
    return any(fragment in path or fragment in url for fragment in source.allowed_url_fragments)


def _looks_like_title(text: str) -> bool:
    if not text:
        return False

    normalized = text.strip()
    if len(normalized) < 12:
        return False

    lowered = normalized.lower()
    if lowered in GENERIC_LINK_TEXT:
        return False

    if any(pattern in lowered for pattern in SKIP_TEXT_PATTERNS):
        return False

    return True


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
