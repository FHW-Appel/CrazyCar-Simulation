# --- Backcompat: run_simulation(steps=..., headless=...)
import os as _os
import pygame as _pg
_run_sim_prev = locals().get("run_simulation", None)

def run_simulation(*args, **kwargs):
    steps = kwargs.pop("steps", None)
    headless = bool(kwargs.pop("headless", False))

    if steps is None and not headless and _run_sim_prev is not None:
        return _run_sim_prev(*args, **kwargs)

    if headless:
        _os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        _os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    _pg.init()
    _pg.display.init()
    _pg.display.set_mode((1, 1))
    clock = _pg.time.Clock()

    n = int(steps or 1)
    for _ in range(n):
        # No-Op Step – genügt für Smoke-Test
        clock.tick(240)

    _pg.display.quit()
    _pg.quit()
    return {"steps": n, "headless": headless}
