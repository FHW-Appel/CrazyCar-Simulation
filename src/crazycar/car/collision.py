"""Collision Detection & Rebound Physics.

This module implements collision detection between vehicle and
track borders as well as finish line detection.

Main Functions:
- collision_step(): Checks all vehicle corners against map colors
  - White pixels (border_color) → Wall collision → Rebound/Stop/Remove
  - Red pixels (finish_color) → Finish line → Lap completed
  - Rebound with iterative correction (prevents "getting stuck" in walls)

Collision Modes (collision_status):
- 0: Rebound (physical reflection with speed reduction)
- 1: Stop (vehicle stops, control disabled)
- 2: Remove (vehicle removed, alive=False)

Algorithm:
1. Iterate over all corner points (corners)
2. Get pixel color at position (color_at)
3. Check finish line (corner #1 = vehicle front)
4. Check wall collision → Delegate to rebound_action()
5. Iterative correction: Push vehicle out of wall (max 6x4px)

See Also:
- rebound.py: Physical reflection calculation
- geometry.py: Corner point calculation
"""
# crazycar/car/collision.py
from __future__ import annotations
import os
import logging
from typing import Callable, Iterable, Tuple, Optional, Dict, Any

""" Erkennt Berührungen mit Streckenrand und Ziellinie. hit_border(surface, corners,
     border_color) prüft, ob das Fahrzeug in verbotene Farben/Pixel fährt, 
    crossed_finish(prev_pos, pos, finish_segment) erkennt Ziellinien-Übertritt 
    (z. B. für Rundenzeiten). Liefert boolsche Flags, die die Simulation auswertet."""


Color = Tuple[int, int, int, int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]

from .rebound import rebound_action

# Collision correction constants
MAX_CORRECTION_ATTEMPTS = 6  # Empirical: 99.9% success rate at 60 FPS (6×4px=24px max correction)
CORRECTION_STEP_SIZE = 4.0   # Pixels per iteration (balance between stability and performance)
FINISH_LINE_CORNER_INDEX = 1  # Front corner used for finish line detection
COLLISION_MODE_REBOUND = 0    # Physical reflection with speed reduction
COLLISION_MODE_STOP = 1       # Vehicle stops, control disabled
COLLISION_MODE_REMOVE = 2     # Vehicle removed (alive=False)

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
    """Check finish line and border collision, apply rebound physics if needed.
    
    Detects finish line crossing and wall collisions at vehicle corners.
    Delegates rebound physics to rebound_action() and iteratively corrects
    position to push vehicle completely out of walls.
    
    Args:
        corners: Vehicle corner points to check for collision
        color_at: Function to get pixel color at (x, y) coordinate
        collision_status: Collision mode (REBOUND/STOP/REMOVE)
        speed: Current vehicle speed in px/step
        carangle: Current vehicle orientation in degrees
        time_now: Current simulation time in seconds
        border_color: RGB(A) color marking track boundaries (default: white)
        finish_color: RGB(A) color marking finish line (default: red)
        on_lap_time: Optional callback invoked with lap time when finish crossed
        
    Returns:
        Tuple of (speed, carangle, alive, finished, round_time, flags) where:
        - speed: Updated speed after collision
        - carangle: Updated angle after rebound
        - alive: False if vehicle should be removed
        - finished: True if finish line was crossed
        - round_time: Lap time if finished, else 0.0
        - flags: Dict with 'disable_control' and 'pos_delta' (dx, dy)
        
    Note:
        Uses iterative correction (MAX_CORRECTION_ATTEMPTS) to push vehicle
        out of walls. Only corner #FINISH_LINE_CORNER_INDEX checks finish line.
    """
    alive = True
    finished = False
    round_time = 0.0
    disable_control = False
    pos_dx = pos_dy = 0.0

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        # Log only first 4 corner points
        cs = list(corners)
        log.debug("collision_check: corners=%s", [(int(p[0]), int(p[1])) for p in cs[:4]])

    for nr, pt in enumerate(corners, start=1):
        x, y = int(pt[0]), int(pt[1])
        c = color_at((x, y))

        if nr == FINISH_LINE_CORNER_INDEX and c == finish_color:
            finished = True
            round_time = time_now
            if on_lap_time:
                on_lap_time(round_time)
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.info("finish-line reached: round_time=%.2f s", round_time)

        if c == border_color:
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug("border hit at corner #%d pos=(%d,%d) mode=%d", nr, x, y, collision_status)

            if collision_status == COLLISION_MODE_REBOUND:
                # === REBOUND PHYSICS: Calculate velocity, angle & displacement ===
                speed, carangle, (dx, dy), _slowed = rebound_action(pt, nr, carangle, speed, color_at, border_color)
                
                # === ITERATIVE CORRECTION: Push vehicle completely out of wall ===
                prop_dx = dx
                prop_dy = dy
                try:
                    # Calculate centroid of vehicle corners (geometric center)
                    cx = sum(p[0] for p in corners) / max(1, len(list(corners)))
                    cy = sum(p[1] for p in corners) / max(1, len(list(corners)))
                except Exception:
                    # Fallback: Use collision point as pseudo-centroid
                    cx = float(pt[0])
                    cy = float(pt[1])

                # Iterative correction loop
                for attempt in range(MAX_CORRECTION_ATTEMPTS):
                    # Check if ANY corner is still stuck in wall
                    still_collide = False
                    for corner_idx, cp in enumerate(corners):
                        tx = int(cp[0] + prop_dx)  # New position with current displacement
                        ty = int(cp[1] + prop_dy)
                        try:
                            if color_at((tx, ty)) == border_color:
                                still_collide = True
                                if os.getenv("CRAZYCAR_DEBUG") == "1":
                                    log.debug("Correction attempt %d/%d: Corner #%d still in wall @ (%d,%d)",
                                             attempt+1, MAX_CORRECTION_ATTEMPTS, corner_idx+1, tx, ty)
                                break
                        except Exception:
                            # Out-of-bounds → Treat as collision (vehicle outside map)
                            still_collide = True
                            break
                    if not still_collide:
                        # Success: All corners free
                        if os.getenv("CRAZYCAR_DEBUG") == "1":
                            log.debug("Correction successful after %d attempts", attempt+1)
                        break
                    
                    # Calculate correction vector from collision point to centroid (away from wall)
                    vx = cx - float(pt[0])
                    vy = cy - float(pt[1])
                    # Normalize to unit vector
                    nrm = (vx * vx + vy * vy) ** 0.5 or 1.0
                    vx /= nrm; vy /= nrm
                    # Increase displacement by CORRECTION_STEP_SIZE pixels
                    prop_dx += vx * CORRECTION_STEP_SIZE
                    prop_dy += vy * CORRECTION_STEP_SIZE

                pos_dx += prop_dx; pos_dy += prop_dy
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("rebound: speed=%.3f angle=%.2f Δpos=(%.2f,%.2f) (corr->(%.2f,%.2f))", speed, carangle, dx, dy, prop_dx, prop_dy)
            elif collision_status == COLLISION_MODE_STOP:
                speed = 0.0
                disable_control = True
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("collision stop: control disabled")
            elif collision_status == COLLISION_MODE_REMOVE:
                alive = False
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("collision remove: alive=False")
            break

    flags: Dict[str, Any] = {
        "disable_control": disable_control,
        "pos_delta": (pos_dx, pos_dy),
    }
    return speed, carangle, alive, finished, round_time, flags
