# tests/conftest.py
import os
import sys
import types
import importlib.util
from pathlib import Path
import pytest
import pygame

#Testen mit pytest -vv

# --- Headless Pygame ---
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "py"
sys.path.insert(0, str(SRC))  # damit "import interface" etc. klappt

def _load_as_top_level(modname: str, filepath: Path):
    spec = importlib.util.spec_from_file_location(modname, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {modname} from {filepath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)
    return module

# --- Zirkular-Import auflösen: zuerst Dummy 'simulation' eintragen ---
if "simulation" not in sys.modules:
    sys.modules["simulation"] = types.ModuleType("simulation")  # Platzhalter

# car zuerst laden (benötigt evtl. 'simulation', die aktuell Dummy ist)
CAR_PY = SRC / "car.py"
_load_as_top_level("car", CAR_PY)

# jetzt echtes simulation nachladen und Dummy ersetzen
SIM_PY = SRC / "simulation.py"
if SIM_PY.exists():
    _load_as_top_level("simulation", SIM_PY)  # überschreibt den Dummy

@pytest.fixture(scope="session", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()
    pygame.quit()
