"""Simulation Facade - High-Level Simulation Entry Points.

This module bootstraps a full simulation run:
- config/runtime initialization
- pygame window (or headless surface)
- UI widgets (buttons, dialogs, toggles)
- services (MapService, EventSource, ModeManager)
- car spawning
- delegation into the main frame loop (event -> update -> draw)

Main entry points:
- `run_direct(...)`:
    Runs the simulation without any evolutionary/ML machinery.
    This is the typical workflow for running/testing the student C controller
    (via `control/interface.py`) and the Python fallback regulator.

- `run_simulation(genomes, config)`:
    Optional NEAT evaluator entry point (kept for historical experiments).
    It can be used if the project is configured to run an evolutionary search,
    but it is not the default path when DLL-only/direct mode is enabled.

See also:
- [loop] for the per-frame orchestration
- [control/interface] for the C/Python controller integration
"""

from __future__ import annotations
import sys
import os
import logging
from typing import List, Tuple

import neat
import pygame
import pygame.freetype

from ..car.model import Car, WIDTH, HEIGHT, f           # sim_to_real not needed here
from .toggle_button import ToggleButton

# Central states/configuration
from .state import SimConfig, SimRuntime, build_default_config, seed_all
# Event pipeline (pygame/Headless)
from .event_source import EventSource
# Mode/pause logic
from .modes import ModeManager, UIRects
# Map service (background track)
from .map_service import MapService
# Main loop + UI context
from .loop import run_loop, UICtx
from .spawn_utils import spawn_from_map
from .screen_service import get_or_create_screen

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.sim] %(message)s",
    )
log = logging.getLogger("crazycar.sim")

# Performance Monitoring
LOG_THRESHOLD_SECONDS = 20  # Warning threshold for loop duration


def _finalize_exit(hard_kill: bool) -> None:
    """Central exit helper for graceful/forceful process termination.
    
    Ensures pygame cleanup and controlled process exit. Choice between
    hard exit (sys.exit, not catchable) or soft exit (SystemExit, catchable).
    
    Args:
        hard_kill: If True, use sys.exit(0) (hard); if False, raise SystemExit(0) (soft)
        
    Note:
        Calls pygame.quit() and terminates process via sys.exit() or SystemExit.
    """
    log.info("Exit → pygame.quit() + %s",
             "sys.exit(0)" if hard_kill else "SystemExit(0)")
    try:
        pygame.quit()
    finally:
        if hard_kill:
            sys.exit(0)
        else:
            raise SystemExit(0)


# screen creation helper moved to screen_service.get_or_create_screen


# UI Layout Constants
UI_TEXT_BOX_WIDTH = 200  # Width of text input box
UI_TEXT_BOX_HEIGHT = 30  # Height of text input box
UI_SNAPSHOT_BUTTON_WIDTH = 100  # Width of snapshot/recover buttons
UI_SNAPSHOT_BUTTON_HEIGHT = 30  # Height of snapshot/recover buttons
UI_SNAPSHOT_BUTTON_OFFSET = 40  # Vertical offset between snapshot buttons
UI_COLLISION_TOGGLE_X_FACTOR = 1.2  # X position multiplier for collision toggle
UI_COLLISION_TOGGLE_Y_OFFSET = 5  # Vertical spacing between toggles
UI_REGELUNG_BUTTON_X = 1700  # X position for control mode buttons
UI_REGELUNG_BUTTON_Y = 530  # Y position for control mode buttons
UI_REGELUNG_BUTTON_SPACING = 30  # Vertical spacing between control buttons
UI_DIALOG_WIDTH = 500  # Dialog box width
UI_DIALOG_HEIGHT = 200  # Dialog box height
UI_DIALOG_BUTTON_WIDTH = 100  # Dialog button width
UI_DIALOG_BUTTON_HEIGHT = 30  # Dialog button height
UI_DIALOG_BUTTON_PADDING = 30  # Padding around dialog buttons
UI_DIALOG_BUTTON_X_OFFSET = 100  # X offset for first dialog button
UI_DIALOG_BUTTON_SPACING = 100  # Spacing between dialog buttons


def run_simulation(genomes, config):
    """NEAT callback - Execute one simulation run.
    
    This is the main entry point called by NEAT optimizer for each generation.
    Initializes all systems, spawns vehicles with neural networks, and runs
    the main game loop.
    
    Responsibilities:
    1. Configuration: Build SimConfig from environment, set random seeds
    2. Pygame Setup: Initialize pygame, create window (lazy)
    3. UI Setup: Create fonts, buttons, toggles, dialog rects
    4. Services: Initialize EventSource, ModeManager, MapService
    5. Spawning: Create cars and NEAT neural networks
    6. Loop: Delegate to run_loop() for frame-by-frame execution
    7. Exit: Call finalize_exit() on quit
    
    Args:
        genomes: List of (genome_id, genome) tuples from NEAT
        config: NEAT config object with network parameters
        
    Note:
        Initializes/reuses pygame display, seeds random generators,
        may exit process via sys.exit() or SystemExit, writes logs.
        
    See Also:
        - loop.run_loop(): Main frame loop implementation
        - control.interface.Interface: NEAT genome → car control
    """

    # --- Config/Runtime ---
    cfg: SimConfig = build_default_config()
    seed_all(cfg.seed)               # Deterministic RNGs
    rt = SimRuntime()
    rt.start(cfg)                    # Sets window_size, counter etc.

    # --- Pygame init & Window (lazy) ---
    if not pygame.get_init():
        log.debug("pygame.init() (lazy)")
        pygame.init()

    window_size = rt.window_size
    screen = get_or_create_screen(window_size)
    pygame.display.set_caption("CrazyCar Simulation")

    # --- UI-Setup (Fonts/Clock) ---
    font_ft = pygame.freetype.SysFont("Arial", int(19 * f))  # FreeType for HUD text
    font_gen = pygame.font.SysFont("Arial", 15)
    font_alive = pygame.font.SysFont("Arial", 10)
    clock = pygame.time.Clock()

    # --- UI elements/Buttons/Toggles (geometry as in existing code) ---
    positionx = WIDTH * 0.7 * f
    positiony = HEIGHT - 180 * f

    text_box_rect = pygame.Rect(int(positionx * 0.73), int(positiony + 40), 200, 30)
    aufnahmen_button = pygame.Rect(int(positionx), int(positiony), 100, 30)
    recover_button = pygame.Rect(int(positionx), int(positiony + 40), 100, 30)

    collision_button = ToggleButton(
        int(positionx * 1.2),
        int(positiony),
        "Collision-Model: Rebound",
        "Collision-Model: Stop",
        "Collision-Model: Remove",
    )
    sensor_button = ToggleButton(
        collision_button.rect.x,
        int(positiony + collision_button.rect.height + 5),
        "Sensor Enabled",
        "Sensor Unable",
        "",
    )

    button_width = 215
    button_height = 45
    button_color = (0, 255, 0)
    positionx_btn = int(1700 * f)
    positiony_btn = int(530 * f)
    button_regelung1_rect = pygame.Rect(positionx_btn, positiony_btn, button_width, button_height)
    button_regelung2_rect = pygame.Rect(positionx_btn, positiony_btn + button_height + 30, button_width, button_height)

    dialog_width = 500
    dialog_height = 200
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = (HEIGHT - dialog_height) // 2
    button_dialog_width = 100
    button_dialog_height = 30
    button_padding = 30
    button_dialog_x = dialog_x + 100
    button_dialog_y = dialog_y + dialog_height - button_dialog_height - button_padding
    button_yes_rect = pygame.Rect(button_dialog_x, button_dialog_y, button_dialog_width, button_dialog_height)
    button_no_rect = pygame.Rect(
        button_dialog_x + button_dialog_width + 100, button_dialog_y, button_dialog_width, button_dialog_height
    )

    # UI rects bundle for ModeManager (encapsulates click areas for dialog/mode selection/snapshots)
    ui_rects = UIRects(
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
    )

    # Initial toggles (can now be drawn, screen exists)
    collision_button.draw(screen)
    sensor_button.draw(screen)

    # Labels of mode buttons (existing)
    text1 = "c_regelung"
    text2 = "python_regelung"
    text_color = (0, 0, 0)

    # --- Map-Service (loads "Racemap.png", scales/resize, blit) ---
    map_service = MapService(window_size, asset_name="Racemap.png")

    # Spawn/Car factory has been moved to sim.spawn_utils.spawn_from_map

    # --- NEAT-Netze (Bestand) ---
    nets = []
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

    # --- Vehicles (spawn point from MapService) ---
    # Use MapService.get_spawn() instead of hardcoded point
    try:
        cars = spawn_from_map(map_service)
        log.info("Sim-Start: cars=%d size=%sx%s (spawn from MapService) -> pos=%s", len(cars), *window_size, cars[0].position)
    except Exception:
        # Fallback to previous hard spawn if MapService fails
        cars: List[Car] = [Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)]
        log.exception("Sim-Start: MapService.get_spawn() failed — using fallback spawn.")

    rt.current_generation += 1

    # --- Manager (Events/Modus) ---
    es = EventSource(headless=cfg.headless)    # Delivers normalized events + raw events (for widgets)
    # Allow persistent override via marker file or env var so a restart can honor user's choice.
    start_python = None
    try:
        path = os.path.join(os.getcwd(), ".crazycar_start_mode")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as _f:
                    val = _f.read().strip()
                # consume the file so it's one-shot
                try:
                    os.remove(path)
                except Exception:
                    pass
                start_python = (val == "1")
                log.debug("Found start-mode marker file %s -> start_python=%s", path, start_python)
            except Exception as e:
                log.debug("Could not read start-mode file %s: %r", path, e)
    except Exception:
        # fall through to env var default
        start_python = None

    if start_python is None:
        start_python = os.getenv("CRAZYCAR_START_PYTHON", "1") == "1"
    modes = ModeManager(start_python=start_python)     # Manages Pause/Dialog + PY/C control

    # --- UI context for the loop (centralizes everything the loop needs for drawing) ---
    ui = UICtx(
        screen=screen,
        font_ft=font_ft,
        font_gen=font_gen,
        font_alive=font_alive,
        clock=clock,
        text1=text1,
        text2=text2,
        text_color=text_color,
        button_color=button_color,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        text_box_rect=text_box_rect,
        positionx_btn=positionx_btn,
        positiony_btn=positiony_btn,
        button_width=button_width,
        button_height=button_height,
    )

    # --- Hauptschleife (delegiert) ---
    # The loop takes care of:
    #   - Resize-Events (via EventSource.poll_resize → MapService.resize + set_mode-Refresh)
    #   - Active/paused inputs (Modes.apply), Snapshots/Recovery
    #   - Drawing: Map, Cars, Dialog/Buttons, HUD, Toggles
    #   - Exit (QUIT/ESC) via finalize_exit
    run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=_finalize_exit,
    )

    # No auto-quit here: caller may want to reuse window
    return


# -----------------------------------------------------------------------------
# Direct mode for DLL-only (without NEAT)
# Called by optimizer_adapter when CRAZYCAR_ONLY_DLL is active
# and it needs a NEAT-free entry method.
# -----------------------------------------------------------------------------
def run_direct(duration_s: float | None = None) -> None:
    """Start simulation without NEAT (direct C/Python controller).
    
    Uses same UI/service initialization as run_simulation(), but without
    genomes/config/NEAT networks. C controller (DLL) active by default.
    Exits cleanly via ESC/X. Optional runtime limit with duration_s.
    
    Args:
        duration_s: Optional maximum runtime in seconds (soft limit)
    """
    import time as _t

    # --- Config/Runtime ---
    cfg: SimConfig = build_default_config()
    seed_all(cfg.seed)               # Deterministic RNGs
    rt = SimRuntime()
    rt.start(cfg)                    # Sets window_size, counter etc.

    # --- Pygame init & Window (lazy) ---
    if not pygame.get_init():
        log.debug("pygame.init() (lazy, DLL-Only)")
        pygame.init()

    window_size = rt.window_size
    screen = get_or_create_screen(window_size)
    pygame.display.set_caption("CrazyCar – DLL-Only")

    # --- UI-Setup (Fonts/Clock) ---
    font_ft = pygame.freetype.SysFont("Arial", int(19 * f))
    font_gen = pygame.font.SysFont("Arial", 15)
    font_alive = pygame.font.SysFont("Arial", 10)
    clock = pygame.time.Clock()

    # --- UI-Elemente/Buttons/Toggles (wie Bestand) ---
    positionx = WIDTH * 0.7 * f
    positiony = HEIGHT - 180 * f

    text_box_rect = pygame.Rect(int(positionx * 0.73), int(positiony + 40), 200, 30)
    aufnahmen_button = pygame.Rect(int(positionx), int(positiony), 100, 30)
    recover_button = pygame.Rect(int(positionx), int(positiony + 40), 100, 30)

    collision_button = ToggleButton(
        int(positionx * 1.2),
        int(positiony),
        "Collision-Model: Rebound",
        "Collision-Model: Stop",
        "Collision-Model: Remove",
    )
    sensor_button = ToggleButton(
        collision_button.rect.x,
        int(positiony + collision_button.rect.height + 5),
        "Sensor Enabled",
        "Sensor Unable",
        "",
    )

    button_width = 215
    button_height = 45
    button_color = (0, 255, 0)
    positionx_btn = int(1700 * f)
    positiony_btn = int(530 * f)
    button_regelung1_rect = pygame.Rect(positionx_btn, positiony_btn, button_width, button_height)
    button_regelung2_rect = pygame.Rect(positionx_btn, positiony_btn + button_height + 30, button_width, button_height)

    dialog_width = 500
    dialog_height = 200
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = (HEIGHT - dialog_height) // 2
    button_dialog_width = 100
    button_dialog_height = 30
    button_padding = 30
    button_dialog_x = dialog_x + 100
    button_dialog_y = dialog_y + dialog_height - button_dialog_height - button_padding
    button_yes_rect = pygame.Rect(button_dialog_x, button_dialog_y, button_dialog_width, button_dialog_height)
    button_no_rect = pygame.Rect(
        button_dialog_x + button_dialog_width + 100, button_dialog_y, button_dialog_width, button_dialog_height
    )

    # UI rects bundle for ModeManager (encapsulates click areas for dialog/mode selection/snapshots)
    ui_rects = UIRects(
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
    )

    # Initial toggles (can now be drawn, screen exists)
    collision_button.draw(screen)
    sensor_button.draw(screen)

    # Labels of mode buttons (as existing)
    text1 = "c_regelung"
    text2 = "python_regelung"
    text_color = (0, 0, 0)

    # --- Map-Service (loads "Racemap.png", scales/resize, blit) ---
    map_service = MapService(window_size, asset_name="Racemap.png")

    # --- Vehicles (spawn point from MapService) ---
    try:
        cars = spawn_from_map(map_service)
        log.info("Direct-Run (DLL-Only): cars=%d size=%sx%s (spawn from MapService) -> pos=%s", len(cars), *window_size, cars[0].position)
    except Exception:
        cars: List[Car] = [Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)]
        log.exception("Direct-Run: MapService.get_spawn() failed — using fallback spawn.")

    rt.current_generation += 1  # Cosmetic for HUD/counter

    # --- Manager (Events/Modus) ---
    es = EventSource(headless=cfg.headless)

    # Important: Enable **C controller** by default (prefer DLL logic)
    # Allow override by marker file or env var so a restart can start in Python mode if requested.
    start_python = None
    try:
        path = os.path.join(os.getcwd(), ".crazycar_start_mode")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as _f:
                    val = _f.read().strip()
                try:
                    os.remove(path)
                except Exception:
                    pass
                start_python = (val == "1")
                log.debug("Found start-mode marker file %s -> start_python=%s", path, start_python)
            except Exception as e:
                log.debug("Could not read start-mode file %s: %r", path, e)
    except Exception:
        start_python = None

    if start_python is None:
        start_python = os.getenv("CRAZYCAR_START_PYTHON", "0") == "1"
    modes = ModeManager(start_python=start_python)

    # --- UI context for the loop (centralizes everything the loop needs for drawing) ---
    ui = UICtx(
        screen=screen,
        font_ft=font_ft,
        font_gen=font_gen,
        font_alive=font_alive,
        clock=clock,
        text1=text1,
        text2=text2,
        text_color=text_color,
        button_color=button_color,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        text_box_rect=text_box_rect,
        positionx_btn=positionx_btn,
        positiony_btn=positiony_btn,
        button_width=button_width,
        button_height=button_height,
    )

    # --- Main loop ---
    # Note: If your run_loop already supports a "duration", you can
    # add the parameter below (commented line). Otherwise,
    # duration_s only serves as a soft limit for a downstream soft-exit.
    start_t = _t.time()
    run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=_finalize_exit,
        # duration=duration_s,  # Only enable if run_loop(duration=...) exists
    )

    # Fallback soft-exit if run_loop doesn't support duration
    if duration_s is not None and (_t.time() - start_t) >= duration_s:
        try:
            _finalize_exit(hard_kill=False)
        except SystemExit:
            pass

    # No auto-quit here: caller may want to reuse window
    return
