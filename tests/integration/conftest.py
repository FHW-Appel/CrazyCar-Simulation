# tests/integration/conftest.py
"""Fixtures für Integration Tests.

TESTBASIS:
- Shared fixtures für Komponentenintegration
- Headless pygame setup
- Car/Map/Config factories
"""
import os
import pytest
import pygame

# Headless pygame für schnelle Tests
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ⚠️ NOTE: Pygame-Initialisierung auch in tests/conftest.py (Session-Autouse)
#          Diese Fixture ist DUPLICATE und DEPRECATED - wird entfernt in zukünftiger Version.
#          Verwende tests/conftest.py::pygame_headless stattdessen.

@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    """Initialize pygame once per test session.
    
    ⚠️ DEPRECATED: Diese Fixture ist redundant.
    ⚠️ tests/conftest.py hat bereits pygame_headless (session, autouse).
    ⚠️ Diese Fixture bleibt nur für Rückwärtskompatibilität und wird in Zukunft entfernt.
    ⚠️ Migration: Verwende headless_display Fixture aus conftest.py statt pygame_init.
    """
    # Nicht nochmal init - bereits durch tests/conftest.py::pygame_headless
    # if not pygame.get_init():
    #     pygame.init()
    yield
    # Nicht quit - wird durch zentrale Fixture gehandhabt
    # pygame.quit()


@pytest.fixture
def headless_display():
    """Create a minimal headless display surface."""
    if not pygame.display.get_surface():
        surface = pygame.display.set_mode((800, 600))
    else:
        surface = pygame.display.get_surface()
    yield surface
    # Keep display alive for other tests in session


@pytest.fixture
def sample_car_position():
    """Standard starting position for car tests."""
    return [400.0, 300.0]  # Center of 800x600 screen


@pytest.fixture
def sample_car_angle():
    """Standard starting angle for car tests."""
    return 0.0  # Facing right


@pytest.fixture
def default_car_config():
    """Default configuration for car initialization."""
    return {
        'power': 20.0,
        'speed_set': 50,
        'radars': [([0, 0], 0) for _ in range(5)],
        'bit_volt_wert_list': [(0, 0.0) for _ in range(5)],
        'distance': 0.0,
        'time': 0.0
    }


@pytest.fixture
def integration_seed():
    """Fixed seed for reproducible integration tests.
    
    ⚠️ FIX: numpy mit try/except guarded - verhindert Suite-Crash wenn numpy fehlt.
    """
    import random
    
    seed = 42
    random.seed(seed)
    
    # ⚠️ FIX: numpy optional - nicht alle Setups haben es installiert
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass  # numpy optional
    
    return seed
