from datetime import datetime

from app.services.notifications.certificate_expiry import (
    NOTIFY_DAYS_BEFORE,
    days_until_expiry,
    should_notify_today,
)


def test_days_until_expiry_shanghai():
    # 2026-08-07 02:00 UTC = 2026-08-07 10:00 Asia/Shanghai
    now = datetime(2026, 8, 7, 2, 0, 0)
    not_after = datetime(2026, 8, 14, 15, 59, 59)  # 2026-08-14 23:59:59 CST
    assert days_until_expiry(
        not_after_utc=not_after,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    ) == 7


def test_should_notify_within_window_once_per_day():
    now = datetime(2026, 8, 7, 2, 30, 0)  # 10:30 Shanghai
    not_after = datetime(2026, 8, 10, 15, 59, 59)
    assert should_notify_today(
        enabled=True,
        channel_ids=[1, 2],
        not_after=not_after,
        last_notified_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )
    assert not should_notify_today(
        enabled=True,
        channel_ids=[1, 2],
        not_after=not_after,
        last_notified_on="2026-08-07",
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_should_not_notify_before_local_10():
    now = datetime(2026, 8, 7, 1, 0, 0)  # 09:00 Shanghai
    not_after = datetime(2026, 8, 10, 15, 59, 59)
    assert not should_notify_today(
        enabled=True,
        channel_ids=[1],
        not_after=not_after,
        last_notified_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_should_not_notify_outside_window():
    now = datetime(2026, 8, 7, 2, 30, 0)
    not_after = datetime(2026, 8, 20, 15, 59, 59)  # > 7 days
    assert (
        days_until_expiry(
            not_after_utc=not_after,
            now_utc=now,
            timezone_name="Asia/Shanghai",
        )
        > NOTIFY_DAYS_BEFORE
    )
    assert not should_notify_today(
        enabled=True,
        channel_ids=[1],
        not_after=not_after,
        last_notified_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_should_not_notify_after_expired():
    now = datetime(2026, 8, 7, 2, 30, 0)
    not_after = datetime(2026, 8, 6, 15, 59, 59)
    assert not should_notify_today(
        enabled=True,
        channel_ids=[1],
        not_after=not_after,
        last_notified_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_should_not_notify_without_channels():
    now = datetime(2026, 8, 7, 2, 30, 0)
    not_after = datetime(2026, 8, 10, 15, 59, 59)
    assert not should_notify_today(
        enabled=True,
        channel_ids=[],
        not_after=not_after,
        last_notified_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )
