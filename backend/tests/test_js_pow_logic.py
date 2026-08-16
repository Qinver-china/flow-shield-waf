from tests.js_pow_logic import (
    BLOCK_SCORE,
    base_difficulty_from_server_score,
    count_leading_zero_hex,
    effective_difficulty,
    solve_pow,
    verify_pow,
)


def test_count_leading_zero_hex():
    assert count_leading_zero_hex("000abc") == 3
    assert count_leading_zero_hex("abc") == 0


def test_effective_difficulty_blocks_high_fp():
    assert effective_difficulty(4, BLOCK_SCORE) is None
    assert effective_difficulty(4, BLOCK_SCORE - 1) == 7
    # Soft domestic-shell stack (chrome-gap skipped + empty plugins) stays under block.
    assert effective_difficulty(3, 30 + 10) == 4
    assert effective_difficulty(3, 55) == 5


def test_base_difficulty_tiers():
    assert base_difficulty_from_server_score(0) == 3
    assert base_difficulty_from_server_score(20) == 4
    assert base_difficulty_from_server_score(30) == 5
    assert base_difficulty_from_server_score(50) == 6


def test_pow_roundtrip_low_difficulty():
    cid = "test-cid"
    seed = "test-seed"
    difficulty = 3
    nonce = solve_pow(cid, seed, difficulty)
    assert nonce is not None
    assert verify_pow(cid, seed, nonce, difficulty)
