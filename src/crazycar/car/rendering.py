# crazycar/car/rendering.py
"""Rendering (pygame-abhängig): Sprite laden, drehen und zeichnen."""

from __future__ import annotations
from typing import List, Tuple
import pygame
from importlib import resources

Point = Tuple[float, float]

def load_car_sprite(cover_size: int) -> pygame.Surface:
    """Lädt 'car.png' aus crazycar/assets und skaliert auf cover_size."""
    car_image_path = resources.files("crazycar.assets") / "car.png"
    img = pygame.image.load(str(car_image_path)).convert_alpha()
    sprite = pygame.transform.scale(img, (cover_size, cover_size))
    return sprite

def rotate_center(image: pygame.Surface, angle: float) -> pygame.Surface:
    """Rotiert ein Bild um seinen Mittelpunkt und gibt die beschnittene Surface zurück."""
    rectangle = image.get_rect()
    rotated_image = pygame.transform.rotate(image, angle)
    rotated_image = rotated_image.convert_alpha()
    rotated_image.set_colorkey((255, 255, 255, 255))
    rotated_rectangle = rectangle.copy()
    rotated_rectangle.center = rotated_image.get_rect().center
    rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
    return rotated_image

def draw_car(screen: pygame.Surface, sprite: pygame.Surface, position: Point) -> None:
    screen.blit(sprite, position)

def draw_radar(screen: pygame.Surface, center: Point, radars: List[Tuple[Point, int]], enabled: bool = True) -> None:
    if not enabled:
        return
    for (pos, _dist) in radars:
        pygame.draw.line(screen, (0, 255, 0), center, pos, 1)
        pygame.draw.circle(screen, (0, 255, 0), pos, 5)

def draw_track(screen: pygame.Surface, left_rad: Point, right_rad: Point, corners: List[Point]) -> None:
    pygame.draw.circle(screen, (180, 180, 0), left_rad, 1)
    pygame.draw.circle(screen, (180, 0, 180), right_rad, 1)
    if len(corners) >= 4:
        pygame.draw.circle(screen, (0, 180, 180), corners[2], 1)
        pygame.draw.circle(screen, (180, 180, 180), corners[3], 1)

__all__ = ["load_car_sprite", "rotate_center", "draw_car", "draw_radar", "draw_track"]
