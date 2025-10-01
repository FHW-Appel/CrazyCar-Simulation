# crazycar/car/collision.py
from __future__ import annotations
from typing import Callable, Iterable, Tuple, Optional, Dict, Any
Color = Tuple[int, int, int, int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]

from .rebound import rebound_action  # lange Mathematik ausgelagert

def collision_step(
    corners: Iterable[Point],
    color_at: ColorAtFn,
    collision_status: int,
    speed: float,
    carangle: float,
    time_now: float,
    *,
    border_color: Color = (255, 255, 255, 255),
    finish_color: Color = (237, 28, 36, 255),
    on_lap_time: Optional[Callable[[float], None]] = None,
):
    """Prüft Ziellinie & Randkollision; Rebound delegiert an rebound_action."""
    alive = True
    finished = False
    round_time = 0.0
    disable_control = False
    pos_dx = pos_dy = 0.0

    for nr, pt in enumerate(corners, start=1):
        x, y = int(pt[0]), int(pt[1])
        c = color_at((x, y))

        if nr == 1 and c == finish_color:
            finished = True
            round_time = time_now
            if on_lap_time:
                on_lap_time(round_time)

        if c == border_color:
            if collision_status == 0:
                speed, carangle, (dx, dy), _slowed = rebound_action(pt, nr, carangle, speed, color_at, border_color)
                pos_dx += dx; pos_dy += dy
            elif collision_status == 1:
                speed = 0.0; disable_control = True
            elif collision_status == 2:
                alive = False
            break

    flags: Dict[str, Any] = {
        "disable_control": disable_control,
        "pos_delta": (pos_dx, pos_dy),
    }
    return speed, carangle, alive, finished, round_time, flags
