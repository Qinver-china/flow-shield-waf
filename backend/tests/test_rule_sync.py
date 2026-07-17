"""Rule sync publish tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import rule_sync


@pytest.mark.asyncio
async def test_publish_uses_atomic_pipeline():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=redis)
    redis.execute = AsyncMock(return_value=[True, True, 7])
    db = AsyncMock()

    with (
        patch("app.services.rule_sync.get_redis", return_value=redis),
        patch("app.services.rule_sync.build_config", AsyncMock(return_value={"rules": []})),
        patch("app.services.rule_sync.publish_baselines_to_redis", AsyncMock()),
    ):
        version = await rule_sync.publish(db)

    assert version == 7
    assert redis.set.await_count == 1
    assert redis.rename.await_count == 1
    assert redis.incr.await_count == 1
    redis.delete.assert_awaited_with(rule_sync.DIRTY_KEY)


@pytest.mark.asyncio
async def test_publish_sets_dirty_on_failure():
    redis = AsyncMock()
    redis.pipeline = MagicMock(side_effect=RuntimeError("redis down"))
    db = AsyncMock()

    with (
        patch("app.services.rule_sync.get_redis", return_value=redis),
        patch("app.services.rule_sync.build_config", AsyncMock(return_value={"rules": []})),
        pytest.raises(RuntimeError),
    ):
        await rule_sync.publish(db)

    redis.set.assert_awaited_with(rule_sync.DIRTY_KEY, "1")
