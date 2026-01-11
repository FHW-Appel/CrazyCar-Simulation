"""CrazyCar Main Entry Point - Build Native Controller + Run Simulation.

This module is the official entry point for the CrazyCar project.
Its primary purpose is to build the native C controller library and then
run the (optional) parameter-tuning / simulation workflow.

Typical workflow:
1. Configure logging (DEBUG_DEFAULT / CRAZYCAR_DEBUG)
2. Build the native CFFI extension (run_build_native)
3. Install a global Pygame quit guard (ESC/X -> clean exit)
4. Run an optional parameter optimization (SciPy-based) that repeatedly
     launches the simulation to evaluate controller behavior

Important project intent:
- The native library is built from the C sources (see build_native.py / src/c)
    so student-provided controller code can be executed inside the simulator.
- The simulation loop itself uses the controller via control/interface.py
    (C controller via `carsim_native`, with a Python fallback regulator).

Environment variables:
- CRAZYCAR_DEBUG: "1" enables debug logging
- CRAZYCAR_NATIVE_PATH: path to the built extension added to sys.path
- SDL_VIDEODRIVER: set to "dummy" for headless runs/tests

Exit codes:
- 0: success or clean abort
- 1: unexpected error
- 130: Ctrl+C (KeyboardInterrupt)

Usage:
        python -m crazycar.main

Notes:
- The quit guard patches pygame.event.get/poll so ESC and the window close
    button work reliably even in deep loops.
"""
# src/crazycar/main.py
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict

# Simple debug switch: 0 = off, 1 = on
# In debug mode, global log levels and verbose traces are activated.
# Set to 1 here if you want to see debug logs by default.
DEBUG_DEFAULT = 1

_THIS = Path(__file__).resolve()
_SRC_DIR = _THIS.parents[1]  # .../src
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Initialize logging early
log = logging.getLogger(__name__)
log.info("sys.path add: %s", _SRC_DIR)

from crazycar.interop.build_tools import run_build_native  # Import build tool early


# ---------------------------------------------------------------------------
# Global quit guard for Pygame
# ---------------------------------------------------------------------------
def _install_pygame_quit_guard() -> None:
    """
    Forces immediate, clean program exit as soon as ANY code location
    receives a window QUIT or ESC event – even if deeper loops don't
    handle the event correctly.
    """
    try:
        import pygame  # May be imported first in sim/optimizer
    except Exception:
        return  # No pygame available -> nothing to do

    # Already patched?
    if getattr(pygame.event, "_crazycar_quit_guard_installed", False):
        return

    _orig_get = pygame.event.get
    _orig_poll = pygame.event.poll

    def _wrap_events(events):
        """
        Monitors all events:
        - X button (pygame.QUIT)
        - ESC key (pygame.KEYDOWN with K_ESCAPE)
        and terminates program cleanly immediately.
        """
        for ev in events:
            try:
                if ev.type == pygame.QUIT or (
                    ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE
                ):
                    logging.info("[Quit-Guard] Exit by user (X or ESC).")
                    try:
                        pygame.quit()
                    finally:
                        # Hard but clean exit → no Ctrl+C needed
                        raise SystemExit(0)
            except Exception:
                # If ev has no .type or .key
                pass
        return events

    def _get_wrapper(*args, **kwargs):
        return _wrap_events(_orig_get(*args, **kwargs))

    def _poll_wrapper(*args, **kwargs):
        ev = _orig_poll(*args, **kwargs)
        return _wrap_events([ev])[0] if ev else ev

    pygame.event.get = _get_wrapper
    pygame.event.poll = _poll_wrapper
    pygame.event._crazycar_quit_guard_installed = True

    logging.info("[Quit-Guard] Activated – ESC and X terminate program.")
# ---------------------------------------------------------------------------


def _print_result(res: Dict[str, Any]) -> None:
    """Format output of optimization results."""
    log = logging.getLogger(__name__)
    log.info("Optimized Parameters:")
    log.info("K1:  %s", res['k1'])
    log.info("K2:  %s", res['k2'])
    log.info("K3:  %s", res['k3'])
    log.info("KP1: %s", res['kp1'])
    log.info("KP2: %s", res['kp2'])
    log.info("Optimal Lap Time: %s", res['optimal_lap_time'])


def main() -> int:
    """Main entry point for CrazyCar."""
    # Initialize debug (only via switch above)
    debug = bool(int(DEBUG_DEFAULT))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s"
    )
    logging.info("Starting CrazyCar (debug=%s)", debug)
    os.environ["CRAZYCAR_DEBUG"] = "1" if debug else "0"

    # Optional: Enable headless option to avoid window flood during testing
    # os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    # -----------------------------------------------------------------------
    # Prepare native build
    # -----------------------------------------------------------------------
    try:
        rc, build_out_dir = run_build_native()
        if rc != 0:
            logging.error("Native build failed (Exit 1).")
        else:
            if build_out_dir and build_out_dir not in sys.path:
                sys.path.insert(0, build_out_dir)
                logging.info("sys.path add build: %s", build_out_dir)
            os.environ["CRAZYCAR_NATIVE_PATH"] = build_out_dir or ""
    except Exception as e:
        logging.error("Native build exception: %s", e)

    # -----------------------------------------------------------------------
    # Start optimizer (after successful build)
    # -----------------------------------------------------------------------
    # NOTE: Import directly from optimizer_api so optimizer.py can be removed.
    from crazycar.control.optimizer_api import run_optimization

    # Activate quit guard NOW – Pygame is relevant from here
    _install_pygame_quit_guard()

    try:
        res = run_optimization()
    except KeyboardInterrupt:
        # Clean abort without long traceback (Ctrl+C)
        logging.info("Aborted (Ctrl+C).")
        return 130
    except SystemExit as se:
        # If quit guard fires in parent (unusual), respect exit code
        return int(getattr(se, "code", 0) or 0)
    except Exception as e:
        logging.exception("Unexpected error during optimization: %r", e)
        return 1

    # Evaluate result robustly
    if not isinstance(res, dict):
        logging.error("[optimizer] Invalid return (not a dict).")
        return 1

    if not res.get("success", False):
        # Abort path (e.g., ESC from simulation)
        msg = res.get("message", "Aborted.")
        logging.warning("[optimizer] Abort or error: %s", msg)
        return 0

    # Success → output parameters
    _print_result(res)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Clean abort without long traceback (Ctrl+C)
        logging.info("Aborted (Ctrl+C).")
        sys.exit(130)
