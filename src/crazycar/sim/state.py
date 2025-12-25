"""Simulation Configuration and Runtime State.

Responsibilities:
- SimConfig: Static settings (FPS, seeds, headless mode, exit behavior)
- SimRuntime: Dynamic runtime state (window size, pause flag, counter, text input,
               current generation, track drawing)
- Helper functions for defaults and deterministic seeding

Public API:
- class SimConfig:
      fps: int              # Target frames per second
      seed: int             # Random seed for reproducibility
      headless: bool        # Run without display
      hard_exit: bool       # Force sys.exit() on quit
      
- class SimRuntime:
      window_size: tuple[int,int]    # Current display resolution
      paused: bool                   # Simulation paused flag
      drawtracks: bool               # Show vehicle trails
      file_text: str                 # Text input buffer
      current_generation: int        # NEAT generation number
      counter: int                   # Frame counter
      quit_flag: bool                # Quit requested
      
      start(cfg: SimConfig) -> None  # Initialize from config
      
- build_default_config() -> SimConfig
      Creates default configuration from environment variables
      
- seed_all(seed: int) -> None
      Seeds random and numpy for reproducibility

Usage:
    cfg = build_default_config()
    rt = SimRuntime()
    rt.start(cfg)
    seed_all(cfg.seed)
    
Notes:
- SimRuntime holds NO pygame objects, only Python primitives → easily testable
- Reads environment variables for defaults (SEED, HEADLESS, HARD_EXIT)
- DEFAULT_WIDTH/HEIGHT imported from car.model (fallback: 1920x1080)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, Optional, Literal
import os
import random

# Fallback if car.model not yet importable.
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
    """Normalized simulation event with type and payload data.
    
    Attributes:
        type: Event category (QUIT, KEYDOWN, VIDEORESIZE, etc.)
        payload: Additional event data (key codes, dimensions, etc.)
    """
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class SimConfig:
    """Simulation configuration loaded from environment variables.
    
    Attributes:
        headless: Run without pygame display (default: False)
        fps: Target frame rate (default: 100 FPS, replaces time_flip=0.01)
        seed: Random seed for reproducibility (default: 1234)
        hard_exit: Call sys.exit() on quit (default: True)
        window_size: Initial window dimensions (default: 1920x1080)
        assets_path: Override assets directory (optional)
        regelung_py: Start in Python controller mode (default: True)
        map_asset: Map filename (default: "Racemap.png")
    """
    headless: bool = False
    fps: int = 100                 # Replaces time_flip=0.01 → 100 FPS
    seed: int = 1234
    hard_exit: bool = True         # Corresponds to CRAZYCAR_HARD_EXIT
    window_size: Tuple[int, int] = (DEFAULT_WIDTH, DEFAULT_HEIGHT)
    assets_path: Optional[str] = None
    out_dir: Optional[str] = None
    start_paused: bool = False
    drawtracks_default: bool = False

@dataclass(slots=True)
class SimRuntime:
    """Runtime state tracking simulation progress and global flags.
    
    Mutable container for frame counter, pause state, and UI toggles.
    Replaces former module-level globals from simulation.py.
    
    Attributes:
        tick: Frame counter (incremented each update)
        dt: Timestep in seconds (1.0 / fps)
        quit_flag: Signals exit request
        paused: Simulation pause toggle
        drawtracks: Draw trajectory trails toggle
        file_text: Status text for UI display
        current_generation: NEAT generation counter (for HUD)
        window_size: Current window dimensions (width, height)
    """
    tick: int = 0
    dt: float = 0.0                # 1.0 / fps
    quit_flag: bool = False

    # Former module-level globals from simulation.py
    paused: bool = False
    drawtracks: bool = False
    file_text: str = ""
    current_generation: int = 0
    window_size: Tuple[int, int] = field(default_factory=lambda: (DEFAULT_WIDTH, DEFAULT_HEIGHT))

    # Helper counter analogous to previous code
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
    """Build SimConfig from environment variables.
    
    Reads configuration from environment with sensible defaults:
    - CRAZYCAR_HEADLESS / HEADLESS, SDL_VIDEODRIVER: Headless mode toggle
    - CRAZYCAR_FPS: Frame rate (default 100)
    - CRAZYCAR_SEED: Random seed (default 1234) [backcompat: CAR_SIM_SEED]
    - CRAZYCAR_HARD_EXIT: Hard exit on crash (default 1)
    - CRAZYCAR_WIDTH/HEIGHT: Window dimensions
    - CRAZYCAR_ASSETS_DIR: Asset folder path
    - CRAZYCAR_OUT_DIR: Output folder path
    - CRAZYCAR_START_PAUSED: Start in paused state
    - CRAZYCAR_DRAWTRACKS: Enable driving traces
    
    Args:
        env: Environment dict (defaults to os.environ)
        
    Returns:
        SimConfig instance with merged settings.
    """
    e = env or os.environ
    headless_flag = e.get("CRAZYCAR_HEADLESS", e.get("HEADLESS", "0"))
    headless = str(headless_flag).strip().lower() not in ("0", "false", "no", "off", "") or e.get("SDL_VIDEODRIVER") == "dummy"
    fps = int(e.get("CRAZYCAR_FPS", "100"))
    seed = int(e.get("CRAZYCAR_SEED", e.get("CAR_SIM_SEED", "1234")))
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
    """Seed all random number generators for reproducibility.
    
    Seeds both Python's random and NumPy (if available) with the same seed
    to ensure deterministic behavior across runs.
    
    Args:
        seed: Integer seed value (typically from SimConfig.seed)
        
    Note:
        Sets global RNG state for random and numpy.random
    """
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
