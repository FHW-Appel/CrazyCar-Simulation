# tests/conftest.py
import os
import sys
from pathlib import Path
import pytest
import pygame

# Headless Pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# src/py ins PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

@pytest.fixture(scope="session", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()
    pygame.quit()
