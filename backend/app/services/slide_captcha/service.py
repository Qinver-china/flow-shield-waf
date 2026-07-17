"""Slide captcha generation and verification via pi-captcha."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from PIL import Image
from pi_captcha import SlideBuilder
from pi_captcha.slide.block import GraphImage
from pi_captcha.slide.validate import validate as slide_validate

from app.core.config import settings
from app.core.redis import get_redis

log = logging.getLogger("waf.slide_captcha")

REDIS_PREFIX = "waf:slide_cap:"
CHALLENGE_TTL = 300
VERIFY_PADDING = 5

_builder_cache: SlideBuilder | None = None
_assets_stamp: float | None = None


def assets_dir() -> Path:
    """Return slide captcha assets root (backgrounds/ + tiles/)."""
    if settings.slide_captcha_assets_dir:
        return Path(settings.slide_captcha_assets_dir)
    # 本地开发：项目根目录 slide_captcha/
    return Path(__file__).resolve().parents[4] / "slide_captcha"


def _load_backgrounds(backgrounds_dir: Path) -> list[Image.Image]:
    images: list[Image.Image] = []
    if backgrounds_dir.is_dir():
        for path in sorted(backgrounds_dir.iterdir()):
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and path.is_file():
                try:
                    with Image.open(path) as img:
                        images.append(img.copy())
                except Exception:  # noqa: BLE001
                    log.warning("skip invalid slide background: %s", path.name)
    if not images:
        images.append(Image.new("RGB", (320, 220), color=(30, 41, 59)))
    return images


def _load_graph_images(tiles_dir: Path) -> list[GraphImage]:
    graph_images: list[GraphImage] = []
    if tiles_dir.is_dir():
        for subdir in sorted(tiles_dir.iterdir()):
            if not subdir.is_dir():
                continue
            overlay_path = subdir / "tile.png"
            shadow_path = subdir / "tile-shadow.png"
            mask_path = subdir / "tile-mask.png"
            if overlay_path.is_file() and shadow_path.is_file() and mask_path.is_file():
                graph_image = GraphImage()
                with Image.open(overlay_path) as img:
                    graph_image.overlay_image = img.copy()
                with Image.open(shadow_path) as img:
                    graph_image.shadow_image = img.copy()
                with Image.open(mask_path) as img:
                    graph_image.mask_image = img.copy()
                graph_images.append(graph_image)
    if not graph_images:
        raise RuntimeError(f"slide captcha tiles are not configured under {tiles_dir}")
    return graph_images


def _assets_stamp_for(root: Path) -> float:
    latest = 0.0
    for path in root.rglob("*"):
        if path.is_file():
            latest = max(latest, path.stat().st_mtime)
    return latest


def _make_builder() -> SlideBuilder:
    global _builder_cache, _assets_stamp
    root = assets_dir()
    stamp = _assets_stamp_for(root)
    if _builder_cache is not None and _assets_stamp == stamp:
        return _builder_cache

    builder = SlideBuilder()
    builder.set_resources(
        SlideBuilder.with_backgrounds(_load_backgrounds(root / "backgrounds")),
        SlideBuilder.with_graph_images(_load_graph_images(root / "tiles")),
    )
    _builder_cache = builder
    _assets_stamp = stamp
    return builder


def warmup() -> None:
    """Preload slide captcha assets during app startup."""
    try:
        _make_builder().make().generate()
    except Exception:  # noqa: BLE001
        log.exception("slide captcha warmup failed")


def _issue_sync() -> dict[str, Any]:
    captcha_data = _make_builder().make().generate()
    block = captcha_data.get_data()
    captcha_key = str(uuid.uuid4())
    payload = {
        "dx": block.dx,
        "dy": block.dy,
    }
    return {
        "captcha_key": captcha_key,
        "payload": payload,
        "image_base64": captcha_data.get_master_image().to_base64(),
        "tile_base64": captcha_data.get_tile_image().to_base64(),
        "tile_x": block.tile_x,
        "tile_y": block.tile_y,
        "tile_width": block.width,
        "tile_height": block.height,
    }


class SlideCaptchaService:
    """Issue and verify slide captcha challenges stored in Redis."""

    @staticmethod
    async def issue() -> dict[str, Any]:
        issued = await asyncio.to_thread(_issue_sync)
        redis = get_redis()
        await redis.set(
            f"{REDIS_PREFIX}{issued['captcha_key']}",
            json.dumps(issued["payload"], ensure_ascii=False),
            ex=CHALLENGE_TTL,
        )
        return {
            "captcha_key": issued["captcha_key"],
            "image_base64": issued["image_base64"],
            "tile_base64": issued["tile_base64"],
            "tile_x": issued["tile_x"],
            "tile_y": issued["tile_y"],
            "tile_width": issued["tile_width"],
            "tile_height": issued["tile_height"],
        }

    @staticmethod
    async def verify(captcha_key: str, x: int, y: int) -> bool:
        if not captcha_key:
            return False
        redis = get_redis()
        raw = await redis.get(f"{REDIS_PREFIX}{captcha_key}")
        if not raw:
            return False
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            await redis.delete(f"{REDIS_PREFIX}{captcha_key}")
            return False
        ok = slide_validate(x, y, int(payload["dx"]), int(payload["dy"]), VERIFY_PADDING)
        await redis.delete(f"{REDIS_PREFIX}{captcha_key}")
        return ok
