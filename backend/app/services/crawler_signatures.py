"""Export vendored Crawler-Detect regex config for the OpenResty engine."""
from __future__ import annotations

from app.services.crawler_vendored.store import load_compiled_config


def get_crawler_detect_config() -> dict[str, str]:
    """Return combined vendored patterns/exclusions for engine rule sync."""
    return load_compiled_config()
