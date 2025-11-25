# tests/car/test_rendering.py
"""Unit-Tests für Rendering-Funktionen (Sprite, Rotation, Drawing).

TESTBASIS (ISTQB):
- Anforderung: Sprite-Laden, Rotation, Zeichnen von Auto/Radar/Track
- Module: crazycar.car.rendering
- Funktionen: load_car_sprite, rotate_center, draw_car, draw_radar, draw_track

TESTVERFAHREN:
- Äquivalenzklassen: Verschiedene Sprite-Größen, Rotationswinkel
- Smoke-Tests: draw_* Funktionen crashen nicht
- Grenzwertanalyse: Minimale Größe (16px), 0° Rotation, leere Listen
"""
import math
import pytest

pytestmark = pytest.mark.unit

import pygame
from crazycar.car.rendering import load_car_sprite, rotate_center


# ===============================================================================
# FIXTURES: Pygame-Surfaces
# ===============================================================================

@pytest.fixture
def mock_surface():
    """Factory für pygame.Surface mit Größe."""
    def _create(w=800, h=600):
        return pygame.Surface((w, h))
    return _create


@pytest.fixture
def mock_sprite():
    """Factory für Test-Sprite."""
    def _create(size=32, color=(255, 0, 0)):
        sprite = pygame.Surface((size, size))
        sprite.fill(color)
        return sprite
    return _create


# ===============================================================================
# TESTGRUPPE 1: load_car_sprite - Sprite-Laden und Skalierung
# ===============================================================================

@pytest.mark.parametrize("size, expected_min", [
    (16, 16),   # Normal
    (32, 32),   # Standard
    (64, 64),   # Groß
    (128, 128), # Sehr groß
    (8, 16),    # Unter Minimum → min 16px
])
def test_load_car_sprite_scales_correctly(size, expected_min):
    """Testbedingung: Sprite-Größe → Skalierung auf size (min 16px).
    
    Erwartung: Sprite hat mindestens expected_min Dimension.
    """
    # ACT
    sprite = load_car_sprite(cover_size=size)
    
    # ASSERT
    assert isinstance(sprite, pygame.Surface)
    assert max(sprite.get_width(), sprite.get_height()) >= expected_min
    assert sprite.get_width() > 0 and sprite.get_height() > 0



# ===============================================================================
# TESTGRUPPE 2: rotate_center - Rotation mit Dimensions-Erhalt
# ===============================================================================

@pytest.mark.parametrize("angle", [0.0, 45.0, 90.0, 180.0, 270.0])
def test_rotate_center_preserves_dimensions(angle):
    """Testbedingung: Rotation um angle° → Dimensionen bleiben erhalten.
    
    Erwartung: rotate_center croppt zurück auf Original-Dimensionen.
    """
    # ARRANGE
    original = pygame.Surface((50, 50))
    original.fill((255, 0, 0))
    
    # ACT
    rotated = rotate_center(original, angle=angle)
    
    # ASSERT
    assert isinstance(rotated, pygame.Surface)
    assert rotated.get_width() == original.get_width()
    assert rotated.get_height() == original.get_height()


def test_rotate_center_identity_at_zero():
    """Testbedingung: 0° Rotation → keine Änderung.
    
    Erwartung: Dimensionen und Typ unverändert.
    """
    # ARRANGE
    original = pygame.Surface((40, 30))
    
    # ACT
    rotated = rotate_center(original, angle=0.0)
    
    # ASSERT
    assert rotated.get_size() == original.get_size()



# ===============================================================================
# TESTGRUPPE 3: Smoke-Tests - draw_* Funktionen crashen nicht
# ===============================================================================

def test_draw_car_smoke(mock_surface, mock_sprite):
    """Testbedingung: draw_car mit gültigen Parametern → keine Exception.
    
    Erwartung: Zeichenoperation erfolgreich.
    """
    # ARRANGE
    from crazycar.car.rendering import draw_car
    screen = mock_surface()
    sprite = mock_sprite()
    
    # ACT & ASSERT
    try:
        draw_car(screen, sprite, position=(100.0, 100.0))
    except Exception as e:
        pytest.fail(f"draw_car sollte nicht crashen: {e}")


@pytest.mark.parametrize("radars", [
    [((150, 200), 50), ((180, 210), 60)],  # Normale Radare
    [],                                     # Leere Liste
])
def test_draw_radar_smoke(mock_surface, radars):
    """Testbedingung: draw_radar mit verschiedenen Radar-Daten → keine Exception.
    
    Erwartung: Auch leere Liste wird behandelt.
    """
    # ARRANGE
    from crazycar.car.rendering import draw_radar
    screen = mock_surface()
    
    # ACT & ASSERT
    try:
        draw_radar(screen, center=(100.0, 100.0), radars=radars)
    except Exception as e:
        pytest.fail(f"draw_radar sollte nicht crashen: {e}")


@pytest.mark.parametrize("corners", [
    [(10, 20), (50, 20), (50, 60), (10, 60)],  # Viereck
    [],                                        # Leere Liste
])
def test_draw_track_smoke(mock_surface, corners):
    """Testbedingung: draw_track mit verschiedenen Corner-Daten → keine Exception.
    
    Erwartung: Auch leere corners-Liste wird behandelt.
    """
    # ARRANGE
    from crazycar.car.rendering import draw_track
    screen = mock_surface()
    
    # ACT & ASSERT
    try:
        draw_track(screen, (10.0, 20.0), (50.0, 20.0), corners)
    except Exception as e:
        pytest.fail(f"draw_track sollte nicht crashen: {e}")
