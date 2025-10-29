# crazycar/car/rendering.py
from __future__ import annotations
import os
import logging
from typing import List, Tuple
from pathlib import Path
import pygame

"""
Rendering-Hilfsfunktionen für CrazyCar.

Funktionen:
- load_car_sprite(cover_size): Lädt assets/car.png, normalisiert Größe (>=16px), skaliert; Fallback: Platzhalter; Logging.
- rotate_center(image, angle): Rotiert um Bildmitte und beschneidet auf Originalmaß → Top-Left bleibt stabil.
- draw_car(screen, sprite, position): Zeichnet Sprite; bei CRAZYCAR_DEBUG mit rotem Rahmen.
- draw_radar(screen, center, radars, enabled): Sensorstrahlen + Endpunkte (Debug/Visualisierung).
- draw_track(screen, left_rad, right_rad, corners): Debug-Punkte für Track-/Rand-Erkennung.

Interne Helfer:
- _normalize_size(), _make_placeholder(), _assets_dir() (Assets liegen unter src/crazycar/assets/)

Typalias:
- Point = Tuple[float, float]
"""

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
    Erzwingt eine sinnvolle Sprite-Größe.
    - default 32px
    - mindestens 16px
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
    surf.fill((255, 0, 255, 255))  # Magenta auffällig
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
    Lädt src/crazycar/assets/car.png und skaliert auf cover_size.
    - Clamped cover_size, falls 0/negativ/zu klein.
    - Fällt auf Platzhalter zurück, wenn Datei fehlt oder defekt.
    """
    path = _assets_dir() / "car.png"
    size = _normalize_size(cover_size)

    try:
        if not path.is_file():
            raise FileNotFoundError(f"car.png nicht gefunden: {path}")

        img = pygame.image.load(str(path)).convert_alpha()

        if cover_size != size:
            log.warning("Ungültige cover_size=%s → clamp auf %d", cover_size, size)

        sprite = pygame.transform.smoothscale(img, (size, size)).convert_alpha()
        log.info("Sprite geladen: %s -> scaled=%s", path, sprite.get_size())

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("sprite alpha=%s colorkey=%s", sprite.get_alpha(), sprite.get_colorkey())

        return sprite

    except Exception as e:
        log.error("Konnte car.png nicht laden (%r) – benutze Platzhalter.", e)
        ph = _make_placeholder(size)
        log.info("Platzhalter-Sprite erzeugt: %s", ph.get_size())
        return ph


def rotate_center(image: pygame.Surface, angle: float) -> pygame.Surface:
    """
    Dreht das Bild um seine Mitte und gibt eine Surface mit **gleicher Außenabmessung**
    wie das Original zurück (Rückbeschnitt). So bleibt die Top-Left-Position beim Blit
    stabil und das 'Center' des Fahrzeugs verändert sich optisch nicht.
    """
    # Originalgröße/Rect merken
    rect_orig = image.get_rect()
    # Drehen (liefert größere Bounding-Box)
    rotated_full = pygame.transform.rotate(image, angle).convert_alpha()
    # Zuschneiden auf Originalgröße, zentriert
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
