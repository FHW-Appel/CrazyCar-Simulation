# =============================================================================
# crazycar/sim/state.py  —  Konfiguration & Laufzeit-Zustände
# -----------------------------------------------------------------------------
# Aufgabe:
# - Kapselt statische Einstellungen (FPS, Seeds, Headless, Hard-Exit) in SimConfig.
# - Kapselt dynamische Laufzeit-Zustände (Fenstergröße, Pause-Flag, Counter, Text-Eingabe,
#   aktuelle Generation, drawtracks) in SimRuntime.
# - Hilfsfunktionen für Defaults und deterministische Seeds.
#
# Öffentliche API:
# - class SimConfig:
#       .fps: int
#       .seed: int
#       .headless: bool
#       .hard_exit: bool
# - class SimRuntime:
#       .window_size: tuple[int,int]
#       .paused: bool
#       .drawtracks: bool
#       .file_text: str
#       .current_generation: int
#       .counter: int
#       start(cfg: SimConfig) -> None
# - build_default_config() -> SimConfig
# - seed_all(seed: int) -> None
#
# Hinweise:
# - SimRuntime hält KEINE Pygame-Objekte; nur simple Python-Daten → gut testbar.
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, Optional, Literal
import os
import random

# Fallback, falls car.model noch nicht importierbar ist
try:
    from ..car.model import WIDTH as DEFAULT_WIDTH, HEIGHT as DEFAULT_HEIGHT
except Exception:
    DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080

EventType = Literal[
    "QUIT", "ESC", "SPACE", "TOGGLE_TRACKS",
    "MOUSE_DOWN", "KEY_CHAR", "BACKSPACE",
    "VIDEORESIZE", "TICK", "BUTTON"
]

@dataclass(slots=True)
class SimEvent:
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class SimConfig:
    headless: bool = False
    fps: int = 100                 # ersetzt time_flip=0.01 → 100 FPS
    seed: int = 1234
    hard_exit: bool = True         # entspricht CRAZYCAR_HARD_EXIT
    window_size: Tuple[int, int] = (DEFAULT_WIDTH, DEFAULT_HEIGHT)
    assets_path: Optional[str] = None
    out_dir: Optional[str] = None
    start_paused: bool = False
    drawtracks_default: bool = False

@dataclass(slots=True)
class SimRuntime:
    tick: int = 0
    dt: float = 0.0                # 1.0 / fps
    quit_flag: bool = False

    # ehemalige Modul-Globals aus simulation.py
    paused: bool = False
    drawtracks: bool = False
    file_text: str = ""
    current_generation: int = 0
    window_size: Tuple[int, int] = field(default_factory=lambda: (DEFAULT_WIDTH, DEFAULT_HEIGHT))

    # Hilfszähler analog zum bisherigen Code
    counter: int = 0

    def start(self, cfg: "SimConfig") -> None:
        self.dt = 1.0 / max(1, int(cfg.fps))
        self.paused = cfg.start_paused
        self.drawtracks = cfg.drawtracks_default
        self.window_size = cfg.window_size
        self.tick = 0
        self.quit_flag = False
        self.counter = 0

def build_default_config(env: Dict[str, str] | None = None) -> SimConfig:
    e = env or os.environ
    headless = e.get("HEADLESS", "0") == "1" or e.get("SDL_VIDEODRIVER") == "dummy"
    fps = int(e.get("CRAZYCAR_FPS", "100"))
    seed = int(e.get("CRAZYCAR_SEED", "1234"))
    hard_exit = e.get("CRAZYCAR_HARD_EXIT", "1") == "1"

    width = int(e.get("CRAZYCAR_WIDTH", str(DEFAULT_WIDTH)))
    height = int(e.get("CRAZYCAR_HEIGHT", str(DEFAULT_HEIGHT)))

    return SimConfig(
        headless=headless,
        fps=fps,
        seed=seed,
        hard_exit=hard_exit,
        window_size=(width, height),
        assets_path=e.get("CRAZYCAR_ASSETS_DIR"),
        out_dir=e.get("CRAZYCAR_OUT_DIR"),
        start_paused=e.get("CRAZYCAR_START_PAUSED", "0") == "1",
        drawtracks_default=e.get("CRAZYCAR_DRAWTRACKS", "0") == "1",
    )

def seed_all(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass

__all__ = [
    "SimConfig", "SimRuntime", "SimEvent",
    "build_default_config", "seed_all",
]
