"""JS challenge PoW helpers — mirrors engine/lua/waf/js_pow.lua for regression tests."""

from __future__ import annotations

import hashlib

BLOCK_SCORE = 80


def count_leading_zero_hex(hex_digest: str) -> int:
    n = 0
    for ch in hex_digest:
        if ch == "0":
            n += 1
        else:
            break
    return n


def sha256_hex(msg: str) -> str:
    return hashlib.sha256(msg.encode()).hexdigest()


def verify_pow(cid: str, seed: str, nonce: int, difficulty: int) -> bool:
    digest = sha256_hex(f"{cid}:{seed}:{nonce}")
    return count_leading_zero_hex(digest) >= difficulty


def effective_difficulty(base: int, fp_score: int, *, block_score: int = BLOCK_SCORE) -> int | None:
    if fp_score >= block_score:
        return None
    extra = fp_score // 25
    difficulty = base + extra
    if difficulty < base:
        difficulty = base
    return max(3, min(7, difficulty))


def base_difficulty_from_server_score(score: int) -> int:
    if score < 10:
        return 3
    if score < 25:
        return 4
    if score < 40:
        return 5
    return 6


def solve_pow(cid: str, seed: str, difficulty: int, limit: int = 5_000_000) -> int | None:
    for nonce in range(limit):
        if verify_pow(cid, seed, nonce, difficulty):
            return nonce
    return None
