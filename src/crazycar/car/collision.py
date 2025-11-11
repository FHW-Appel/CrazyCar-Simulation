# crazycar/car/collision.py
from __future__ import annotations
import os
import logging
from typing import Callable, Iterable, Tuple, Optional, Dict, Any

Color = Tuple[int, int, int, int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]

from .rebound import rebound_action  # lange Mathematik ausgelagert

# Logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.collision")


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

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        # Nur die ersten 4 Punkte loggen (Ecken)
        cs = list(corners)
        log.debug("collision_check: corners=%s", [(int(p[0]), int(p[1])) for p in cs[:4]])

    for nr, pt in enumerate(corners, start=1):
        x, y = int(pt[0]), int(pt[1])
        c = color_at((x, y))

        if nr == 1 and c == finish_color:
            finished = True
            round_time = time_now
            if on_lap_time:
                on_lap_time(round_time)
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.info("finish-line reached: round_time=%.2f s", round_time)

        if c == border_color:
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug("border hit at corner #%d pos=(%d,%d) mode=%d", nr, x, y, collision_status)

            if collision_status == 0:  # rebound
                speed, carangle, (dx, dy), _slowed = rebound_action(pt, nr, carangle, speed, color_at, border_color)
                # Try to ensure the post-rebound displacement actually moves the
                # car out of the wall. In some edge-cases (fast/angled hits)
                # the computed dx/dy may still leave corners inside the border
                # color. Do a few corrective steps: push along the vector from
                # collision-point to car-centroid until corners are clear.
                prop_dx = dx
                prop_dy = dy
                try:
                    # centroid of car corners
                    cx = sum(p[0] for p in corners) / max(1, len(list(corners)))
                    cy = sum(p[1] for p in corners) / max(1, len(list(corners)))
                except Exception:
                    cx = float(pt[0])
                    cy = float(pt[1])

                # iterative correction (small steps) to avoid clipping through walls
                for _attempt in range(6):
                    still_collide = False
                    for cp in corners:
                        tx = int(cp[0] + prop_dx)
                        ty = int(cp[1] + prop_dy)
                        try:
                            if color_at((tx, ty)) == border_color:
                                still_collide = True
                                break
                        except Exception:
                            # Out-of-bounds — treat as collision and attempt to push inwards
                            still_collide = True
                            break
                    if not still_collide:
                        break
                    # compute direction away from collision-point towards car centroid
                    vx = cx - float(pt[0])
                    vy = cy - float(pt[1])
                    nrm = (vx * vx + vy * vy) ** 0.5 or 1.0
                    vx /= nrm; vy /= nrm
                    # push a few pixels inward (tunable). Using 4px steps reduces tunneling.
                    prop_dx += vx * 4.0
                    prop_dy += vy * 4.0

                pos_dx += prop_dx; pos_dy += prop_dy
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("rebound: speed=%.3f angle=%.2f Δpos=(%.2f,%.2f) (corr->(%.2f,%.2f))", speed, carangle, dx, dy, prop_dx, prop_dy)
            elif collision_status == 1:  # stop
                speed = 0.0
                disable_control = True
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("collision stop: control disabled")
            elif collision_status == 2:  # remove
                alive = False
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("collision remove: alive=False")
            break

    flags: Dict[str, Any] = {
        "disable_control": disable_control,
        "pos_delta": (pos_dx, pos_dy),
    }
    return speed, carangle, alive, finished, round_time, flags
