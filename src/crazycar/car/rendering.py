# crazycar/car/rendering.py
"""Vehicle Rendering Functions (pygame-dependent).

Provides sprite loading, rotation, and drawing utilities for CrazyCar visualization.

Main Functions:
- load_car_sprite(cover_size): Loads assets/car.png, normalizes size (>=16px),
  scales to cover_size; fallback to placeholder; includes logging
- rotate_center(image, angle): Rotates around center, crops to original size
- draw_car(screen, sprite, position): Draws sprite with optional debug border
- draw_radar(screen, center, radars, enabled): Visualizes sensor beams + endpoints
- draw_track(screen, left_rad, right_rad, corners): Debug points for tracking

Internal Helpers:
- _normalize_size(), _make_placeholder(), _assets_dir()
- Assets located under src/crazycar/assets/

Type Aliases:
- Point = Tuple[float, float]
"""
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
    """Enforce a sensible sprite size.
    
    Args:
        n: Requested size (can be None)
        
    Returns:
        Normalized size: default 32px, minimum 16px
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
    """Load and scale vehicle sprite from assets.
    
    Loads src/crazycar/assets/car.png and scales to specified size.
    Automatically clamps size to safe minimum and falls back to
    placeholder if file is missing or corrupted.
    
    Args:
        cover_size: Target sprite size in pixels (will be clamped to minimum)
        
    Returns:
        pygame.Surface with alpha channel, scaled to normalized size
        
    Note:
        Creates magenta placeholder sprite if car.png cannot be loaded
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
    """Rotate image around center and crop back to original dimensions.
    
    Performs rotation around image center, then crops result back to
    original size. This keeps top-left position stable during blit
    and prevents visual shifting of vehicle center.
    
    Args:
        image: Source pygame.Surface to rotate
        angle: Rotation angle in degrees (counter-clockwise)
        
    Returns:
        Rotated and cropped pygame.Surface with same dimensions as input
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
    """Draw vehicle sprite at specified position.
    
    Blits sprite to screen at given position. In debug mode (CRAZYCAR_DEBUG=1),
    also draws red rectangle around sprite for collision debugging.
    
    Args:
        screen: Target pygame.Surface to draw on
        sprite: Pre-rotated vehicle sprite
        position: Top-left corner (x, y) for sprite placement
    """
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
    """Visualize radar sensor beams and endpoints.
    
    Draws green lines from vehicle center to radar endpoints with
    circles marking detection points. Used for debugging and visualization.
    
    Args:
        screen: Target pygame.Surface to draw on
        center: Vehicle center point (x, y)
        radars: List of ((x, y), dist_px) radar measurements
        enabled: If False, skip drawing entirely
    """
    if not enabled:
        return
    cx, cy = int(center[0]), int(center[1])
    for (pos, _dist) in radars:
        px, py = int(pos[0]), int(pos[1])
        pygame.draw.line(screen, (0, 255, 0), (cx, cy), (px, py), 1)
        pygame.draw.circle(screen, (0, 255, 0), (px, py), 4)


def draw_track(screen: pygame.Surface, left_rad: Point, right_rad: Point, corners: List[Point]) -> None:
    """Draw debug points for wheel positions and rear corners.
    
    Visualizes vehicle geometry with colored circles:
    - Yellow: left wheel
    - Magenta: right wheel  
    - Cyan/Gray: rear corners (if available)
    
    Args:
        screen: Target pygame.Surface to draw on
        left_rad: Left wheel position (x, y)
        right_rad: Right wheel position (x, y)
        corners: List of corner points (uses indices 2-3 for rear corners)
    """
    pygame.draw.circle(screen, (180, 180, 0), (int(left_rad[0]), int(left_rad[1])), 1)
    pygame.draw.circle(screen, (180, 0, 180), (int(right_rad[0]), int(right_rad[1])), 1)
    if len(corners) >= 4:
        pygame.draw.circle(screen, (0, 180, 180), (int(corners[2][0]), int(corners[2][1])), 1)
        pygame.draw.circle(screen, (180, 180, 180), (int(corners[3][0]), int(corners[3][1])), 1)


__all__ = ["load_car_sprite", "rotate_center", "draw_car", "draw_radar", "draw_track"]
