"""Crawler/bot detection via vendored JayBizzle Crawler-Detect rules."""
from __future__ import annotations

from app.services.crawler_vendored.match import is_crawler_ua

__all__ = ["is_crawler_ua"]
