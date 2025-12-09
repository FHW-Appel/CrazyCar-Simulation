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


@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    """Initialize pygame once per test session."""
    if not pygame.get_init():
        pygame.init()
    yield
    pygame.quit()


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
    """Fixed seed for reproducible integration tests."""
    import random
    import numpy as np
    
    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    return seed
