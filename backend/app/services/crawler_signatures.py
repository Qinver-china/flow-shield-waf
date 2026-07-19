"""Export CrawlerDetect regex config for the OpenResty engine."""
from __future__ import annotations

from functools import lru_cache

from crawlerdetect.crawlerdetect import (
    get_compiled_crawler_regex,
    get_compiled_exclusions_regex,
)


@lru_cache(maxsize=1)
def get_crawler_detect_config() -> dict[str, str]:
    """Return combined CrawlerDetect patterns/exclusions (same as Python log enrich)."""
    return {
        "patterns": get_compiled_crawler_regex().pattern,
        "exclusions": get_compiled_exclusions_regex().pattern,
    }
