"""Topic classification for USCIS and Department of State updates."""

from __future__ import annotations

from dataclasses import dataclass
import re


DAILY_KEYWORDS = {
    "I-130": ["I-130", "Form I-130", "Petition for Alien Relative"],
    "I-485": ["I-485", "Form I-485", "Adjustment of Status", "AOS"],
    "I-765": ["I-765", "Form I-765", "EAD", "Employment Authorization"],
    "I-864": ["I-864", "Form I-864", "Affidavit of Support"],
    "I-131": ["I-131", "Form I-131", "Advance Parole", "Travel Document"],
    "I-94": ["I-94", "Arrival/Departure Record"],
    "F-1": ["F-1", "F1", "student visa", "international student"],
    "H-1B": ["H-1B", "H1B", "specialty occupation"],
    "OPT": ["OPT", "Optional Practical Training"],
    "STEM OPT": ["STEM OPT", "STEM Optional Practical Training"],
}


@dataclass(frozen=True)
class ClassificationResult:
    """Classification output stored in the database."""

    category: str
    matched_topics: list[str]
    update_type: str


def _normalize_text(*parts: str | None) -> str:
    text = " ".join(part.strip() for part in parts if part and part.strip())
    return re.sub(r"\s+", " ", text).strip()


def _keyword_matches(haystack: str, keyword: str) -> bool:
    escaped_keyword = re.escape(keyword)
    pattern = rf"(?<![A-Za-z0-9]){escaped_keyword}(?![A-Za-z0-9])"
    return re.search(pattern, haystack, flags=re.IGNORECASE) is not None


def classify_update(title: str, url: str, snippet: str | None = None) -> ClassificationResult:
    """
    Classify an update using the title, URL, and optional nearby page text.

    The weekly bucket is the default. Any keyword hit moves the update into the
    daily priority bucket and stores every matched topic.
    """

    searchable_text = _normalize_text(title, url, snippet)
    matched_topics: list[str] = []

    for topic, keywords in DAILY_KEYWORDS.items():
        if any(_keyword_matches(searchable_text, keyword) for keyword in keywords):
            matched_topics.append(topic)

    if matched_topics:
        return ClassificationResult(
            category=matched_topics[0],
            matched_topics=matched_topics,
            update_type="daily_priority",
        )

    return ClassificationResult(
        category="general_immigration",
        matched_topics=[],
        update_type="weekly_general",
    )
