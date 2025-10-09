# tests/conftest.py
import os
import sys
import random
from pathlib import Path
import pytest

# -----------------------------
# Headless-Schalter per ENV
#   CAR_SIM_HEADLESS = 1/true  -> dummy (Default)
#   CAR_SIM_HEADLESS = 0/false -> echtes Fenster
# -----------------------------
def _truthy(s: str) -> bool:
    return str(s).strip().lower() not in ("0", "false", "no", "off", "")

HEADLESS = _truthy(os.getenv("CAR_SIM_HEADLESS", "1"))
if HEADLESS:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# -----------------------------
# src/py ODER src auf PYTHONPATH (beides unterstützen)
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]
for cand in (ROOT / "src" / "py", ROOT / "src"):
    if cand.exists() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

# -----------------------------
# (Optional) Windows: DLL/Native-Builds auffindbar machen
# -----------------------------
if os.name == "nt":
    for d in (ROOT / "dll", ROOT / "build" / "native"):
        if d.exists():
            try:
                os.add_dll_directory(str(d))  # Py>=3.8
            except Exception:
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")

import pygame

# -----------------------------
# Pygame-Init (Display nötig für .convert())
# -----------------------------
@pytest.fixture(scope="session", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()
    pygame.quit()

# -----------------------------
# Reproduzierbarkeit: Seeds
#   CAR_SIM_SEED=1337 (Default)
# -----------------------------
@pytest.fixture(scope="session", autouse=True)
def _seed_session():
    seed = int(os.getenv("CAR_SIM_SEED", "1337"))
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    yield

# -----------------------------
# Debug-Schalter durchreichen
#   CAR_SIM_DEBUG=1 -> ausführliches Logging in App
# -----------------------------
@pytest.fixture(autouse=True)
def _debug_flag(monkeypatch):
    monkeypatch.setenv("CAR_SIM_DEBUG", os.getenv("CAR_SIM_DEBUG", "0"))
    yield
