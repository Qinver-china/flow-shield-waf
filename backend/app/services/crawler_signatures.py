"""Export CrawlerDetect regex config for the OpenResty engine."""
from __future__ import annotations

from functools import lru_cache

from crawlerdetect import CrawlerDetect


@lru_cache(maxsize=1)
def get_crawler_detect_config() -> dict[str, str]:
    """Return combined CrawlerDetect patterns/exclusions (same as Python log enrich)."""
    detector = CrawlerDetect()
    return {
        "patterns": detector.compiledRegex,
        "exclusions": detector.compiledExclusions,
    }
