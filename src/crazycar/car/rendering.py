# crazycar/car/rendering.py
from __future__ import annotations
import os
import logging
from typing import List, Tuple
from pathlib import Path
import pygame

# Logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.render")

Point = Tuple[float, float]

# ----------------------------
# Helpers
# ----------------------------
def _normalize_size(n: int | float | None) -> int:
    """
    Enforce a sensible sprite size.
    - default 32px
    - minimum 16px
    """
    try:
        v = int(n) if n is not None else 0
    except Exception:
        v = 0
    if v <= 0:
        v = 32
    if v < 16:
        v = 16
    return v


def _make_placeholder(size: int) -> pygame.Surface:
    size = _normalize_size(size)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((255, 0, 255, 255))  # Magenta (fallback color)
    pygame.draw.rect(surf, (0, 0, 0, 255), surf.get_rect(), 2)
    pygame.draw.line(surf, (0, 0, 0, 255), (0, 0), (size - 1, size - 1), 2)
    pygame.draw.line(surf, (0, 0, 0, 255), (size - 1, 0), (0, size - 1), 2)
    return surf


def _assets_dir() -> Path:
    # Datei liegt in: src/crazycar/car/rendering.py
    # Assets liegen in: src/crazycar/assets/
    return Path(__file__).resolve().parents[1] / "assets"


# ----------------------------
# Public API
# ----------------------------
def load_car_sprite(cover_size: int) -> pygame.Surface:
    """
    Loads src/crazycar/assets/car.png and scales to cover_size.
    - Clamped cover_size if 0/negative/too small.
    - Falls back to placeholder if file missing or defective.
    """
    path = _assets_dir() / "car.png"
    size = _normalize_size(cover_size)

    try:
        if not path.is_file():
            raise FileNotFoundError(f"car.png not found: {path}")

        img = pygame.image.load(str(path)).convert_alpha()

        if cover_size != size:
            log.warning("Invalid cover_size=%s → clamped to %d", cover_size, size)

        sprite = pygame.transform.smoothscale(img, (size, size)).convert_alpha()
        log.info("Sprite loaded: %s -> scaled=%s", path, sprite.get_size())

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("sprite alpha=%s colorkey=%s", sprite.get_alpha(), sprite.get_colorkey())

        return sprite

    except Exception as e:
        log.error("Could not load car.png (%r) – using placeholder.", e)
        ph = _make_placeholder(size)
        log.info("Placeholder sprite created: %s", ph.get_size())
        return ph


def rotate_center(image: pygame.Surface, angle: float) -> pygame.Surface:
    """
    Rotates image around its center and returns a surface with **same outer dimensions**
    as the original (crop-back). This keeps the top-left position stable during blit
    and the vehicle 'center' does not shift visually.
    """
    # Remember original size/rect
    rect_orig = image.get_rect()
    # Rotate (yields larger bounding box)
    rotated_full = pygame.transform.rotate(image, angle).convert_alpha()
    # Crop to original size, centered
    rect_crop = rotated_full.get_rect()
    rect_orig.center = rect_crop.center
    rotated_cropped = rotated_full.subsurface(rect_orig).copy()
    return rotated_cropped


def draw_car(screen: pygame.Surface, sprite: pygame.Surface, position: Point) -> None:
    x, y = int(position[0]), int(position[1])
    screen.blit(sprite, (x, y))
    if os.getenv("CRAZYCAR_DEBUG") == "1":
        pygame.draw.rect(screen, (255, 0, 0), sprite.get_rect(topleft=(x, y)), 2)


def draw_radar(
    screen: pygame.Surface,
    center: Point,
    radars: List[Tuple[Point, int]],
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    cx, cy = int(center[0]), int(center[1])
    for (pos, _dist) in radars:
        px, py = int(pos[0]), int(pos[1])
        pygame.draw.line(screen, (0, 255, 0), (cx, cy), (px, py), 1)
        pygame.draw.circle(screen, (0, 255, 0), (px, py), 4)


def draw_track(screen: pygame.Surface, left_rad: Point, right_rad: Point, corners: List[Point]) -> None:
    pygame.draw.circle(screen, (180, 180, 0), (int(left_rad[0]), int(left_rad[1])), 1)
    pygame.draw.circle(screen, (180, 0, 180), (int(right_rad[0]), int(right_rad[1])), 1)
    if len(corners) >= 4:
        pygame.draw.circle(screen, (0, 180, 180), (int(corners[2][0]), int(corners[2][1])), 1)
        pygame.draw.circle(screen, (180, 180, 180), (int(corners[3][0]), int(corners[3][1])), 1)


__all__ = ["load_car_sprite", "rotate_center", "draw_car", "draw_radar", "draw_track"]
