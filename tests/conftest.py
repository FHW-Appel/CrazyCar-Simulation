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

# ===============================================================================
# pytest Fixtures für Wiederverwendbarkeit (Okken, Kap. 3 - "Fixtures")
# ===============================================================================
# Zentrale Fixtures reduzieren Code-Duplikation in der Arrange-Phase und
# entsprechen dem DRY-Prinzip (Beck, TDD).
# ===============================================================================

@pytest.fixture
def mock_car():
    """Factory für Car-Objekt mit Standard-Parametern.
    
    Testbasis: Wiederverwendbares Setup für Car-basierte Unit-Tests
    
    Verwendung:
        def test_something(mock_car):
            car = mock_car(position=[100, 200], carangle=45.0)
            ...
    
    Begründung (TDD/Beck): Reduziert Duplikation in Arrange-Phase.
    """
    def _make_car(position=None, carangle=0.0, power=0.0, speed_set=False,
                  radars=None, bit_volt_wert_list=None, distance=0.0, time=0.0):
        from crazycar.car.model import Car
        return Car(
            position=position or [100.0, 100.0],
            carangle=carangle,
            power=power,
            speed_set=speed_set,
            radars=radars or [],
            bit_volt_wert_list=bit_volt_wert_list or [],
            distance=distance,
            time=time
        )
    return _make_car


@pytest.fixture
def mock_map_service():
    """Factory für MapService-Mock mit konfigurierbarem Spawn-Point.
    
    Testbasis: Spawn-Logik aus sim/spawn_utils.py
    
    Verwendung:
        def test_spawn(mock_map_service):
            map_svc = mock_map_service(spawn_x=100, spawn_y=200, angle=45)
            ...
    """
    from unittest.mock import Mock
    
    def _make_map_service(spawn_x=100.0, spawn_y=100.0, angle_deg=0.0,
                         detect_info=None):
        mock = Mock()
        mock_spawn = Mock()
        mock_spawn.x_px = spawn_x
        mock_spawn.y_px = spawn_y
        mock_spawn.angle_deg = angle_deg
        mock.get_spawn.return_value = mock_spawn
        mock.get_detect_info.return_value = detect_info
        return mock
    return _make_map_service


@pytest.fixture
def color_factory():
    """Factory für color_at Callbacks mit konfigurierbaren Zonen.
    
    Testbasis: Collision-/Sensor-Tests benötigen verschiedene Farbzonen
    
    Verwendung:
        def test_collision(color_factory):
            color_at = color_factory(border_zone=(0, 10, 0, 100))
            ...
    
    Begründung (pytest/Okken): Reduziert Code-Duplikation in Test-Setup.
    """
    def _make_color_at(border_zone=None, finish_zone=None, track_color=(0, 0, 0, 255)):
        BORDER = (255, 255, 255, 255)
        FINISH = (237, 28, 36, 255)
        
        def color_at(pt):
            x, y = pt
            if border_zone:
                xmin, xmax, ymin, ymax = border_zone
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    return BORDER
            if finish_zone:
                xmin, xmax, ymin, ymax = finish_zone
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    return FINISH
            return track_color
        return color_at
    return _make_color_at


# ===============================================================================
# Marker für Testpyramide (ISTQB/Linz - Testebenen)
# ===============================================================================

def pytest_configure(config):
    """Registriert Custom-Marker für Testarten nach ISTQB-Testpyramide."""
    config.addinivalue_line(
        "markers", "unit: Unit-Tests (schnell, isoliert, Basis der Testpyramide)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration-Tests (mehrere Komponenten)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-End-Tests (volle Simulation)"
    )


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
