"""Tests for alert policy evaluator cooldown / last_fired behavior."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.notifications.evaluator import AlertPolicyEvaluator


def _policy(*, last_fired_at=None, cooldown_sec=300):
    policy = MagicMock()
    policy.id = 1
    policy.enabled = True
    policy.name = "测试"
    policy.condition_type = "security.block_count"
    policy.condition_params = {"window_min": 30, "threshold": 5}
    policy.channel_ids = [1]
    policy.cooldown_sec = cooldown_sec
    policy.last_fired_at = last_fired_at
    return policy


@pytest.mark.asyncio
async def test_run_sets_last_fired_even_when_dispatch_fails():
    evaluator = AlertPolicyEvaluator()
    policy = _policy()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[policy]))))
    )

    with (
        patch.object(evaluator, "_evaluate", AsyncMock(return_value="触发")),
        patch.object(evaluator, "_dispatch", AsyncMock(return_value=False)),
    ):
        fired = await evaluator.run(db)

    assert fired == 1
    assert policy.last_fired_at is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_in_cooldown_respects_last_fired_at():
    evaluator = AlertPolicyEvaluator()
    policy = _policy(last_fired_at=datetime.utcnow() - timedelta(seconds=60), cooldown_sec=300)
    assert await evaluator._in_cooldown(policy) is True

    policy.last_fired_at = datetime.utcnow() - timedelta(seconds=400)
    assert await evaluator._in_cooldown(policy) is False


@pytest.mark.asyncio
async def test_run_skips_policy_in_cooldown():
    evaluator = AlertPolicyEvaluator()
    policy = _policy(last_fired_at=datetime.utcnow(), cooldown_sec=300)
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[policy]))))
    )

    with (
        patch.object(evaluator, "_evaluate", AsyncMock(return_value="触发")) as evaluate,
        patch.object(evaluator, "_dispatch", AsyncMock(return_value=True)) as dispatch,
    ):
        fired = await evaluator.run(db)

    assert fired == 0
    evaluate.assert_not_called()
    dispatch.assert_not_called()
