# crazycar/car/rebound.py
from __future__ import annotations
import math
from typing import Callable, Tuple
import os
import numpy as np

Color = Tuple[int, int, int,  int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]


def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    den = float(np.linalg.norm(v1) * np.linalg.norm(v2))
    if den == 0.0:
        return 0.0
    cosv = max(-1.0, min(1.0, float(np.dot(v1, v2)) / den))
    return float(np.degrees(np.arccos(cosv)))


def rebound_action(
    point0: Point,
    nr: int,
    carangle: float,
    speed: float,
    color_at: ColorAtFn,
    border_color: Color,
    radius_px: float = 15.0,
    probe_step_deg: int = 10,
) -> Tuple[float, float, Tuple[float, float], bool]:
    """Calculate rebound behavior during wall collision (physically approximated).
    
    Algorithm (3 phases):
    1. FIND WALL NORMAL: Circular scan around collision point (radius_px)
       → Finds border→free transition (approximates wall direction)
    2. REFLECTION ANGLE: Incident angle between driving direction & wall normal
       → Velocity damping: 0° (tangential) → 90° (frontal)
    3. DISPLACEMENT: Push vehicle out of wall (opposite to driving direction)
       → Prevents tunneling through thin walls
    
    Args:
        point0: Collision point (px)
        nr: Corner number (1=front-right, 2=front-left, 3/4=rear)
        carangle: Vehicle orientation [°]
        speed: Velocity [px/frame]
        color_at: Map access callback
        border_color: Wall color (RGB+A)
        radius_px: Scan radius for wall normal
        probe_step_deg: Angular step size during scan
    
    Returns:
        (new_speed, new_angle, (dx, dy), damped)
        - new_speed: Velocity after reflection [px/frame]
        - new_angle: New orientation [°]
        - (dx, dy): Displacement [px] (to exit wall)
        - damped: True if velocity was reduced
    
    Note:
        Rear wheels (nr=3,4) during backward driving (speed<0) → no rebound
        (only front wheels should collide when driving backward)
    """
    # Special case: Ignore rear wheel collision during backward driving
    if nr in (3, 4) and speed < 0:
        return 0.0, carangle, (0.0, 0.0), False

    x0, y0 = point0
    x1 = x0 + radius_px
    y1 = y0

    # === PHASE 1: APPROXIMATE WALL NORMAL ===
    # Circular scan around collision point (10° steps, 15px radius)
    # Goal: Find point where wall→free transition occurs
    # → Vector (x0,y0)→(x1,y1) approximates wall normal (points into free space)
    for vi in range(0, 360 + probe_step_deg, probe_step_deg):
        a = math.radians(vi)
        a2 = a + math.radians(15)
        px1 = x0 + radius_px * math.cos(a)
        py1 = y0 + radius_px * math.sin(a)
        px2 = x0 + radius_px * math.cos(a2)
        py2 = y0 + radius_px * math.sin(a2)
        if color_at((int(px1), int(py1))) == border_color and color_at((int(px2), int(py2))) != border_color:
            x1, y1 = px1, py1
            break

    # === PHASE 2: CALCULATE REFLECTION ANGLE ===
    # vi_vec = Driving direction vector (unit vector in carangle direction)
    vi_vec = np.array([math.cos(math.radians(carangle)), math.sin(math.radians(carangle))], float)
    # vw_vec = Wall normal vector (points from collision point into free space)
    vw_vec = np.array([x1 - x0, y1 - y0], float)
    # ang = Incident angle between driving direction & wall normal
    # 0° = parallel (tangential), 90° = perpendicular (frontal)
    ang = _angle_between(vw_vec, vi_vec)
    if ang > 90.0:
        ang = 180.0 - ang  # Normalize to acute angle (0°..90°)

    # Velocity damping based on incident angle
    # Physical model:
    # - 0° (tangential):  no damping (1.0) → sliding
    # - <30° (shallow):   low damping (0.8) → grazing hit
    # - 30-60° (oblique): medium damping (0.5) → oblique impact
    # - >60° (frontal):   strong damping (0.2) → near-stop
    # (Parameterized via ENV for tuning, e.g. CRAZYCAR_REBOUND_DAMP_SMALL=0.85)
    try:
        damp_small = float(os.getenv("CRAZYCAR_REBOUND_DAMP_SMALL", "0.8"))
        damp_med = float(os.getenv("CRAZYCAR_REBOUND_DAMP_MED", "0.5"))
        damp_large = float(os.getenv("CRAZYCAR_REBOUND_DAMP_LARGE", "0.2"))
    except Exception:
        damp_small, damp_med, damp_large = 0.8, 0.5, 0.2

    if ang == 0:
        new_speed = speed * 1.0  # Exactly tangential (theoretical)
    elif ang < 30:
        new_speed = speed * damp_small  # Shallow impact
    elif ang < 60:
        new_speed = speed * damp_med  # Oblique impact
    else:
        new_speed = speed * damp_large  # Frontal impact

    # === PHASE 3: DISPLACEMENT & TORQUE ===
    # Displacement (dx, dy): Push vehicle out of wall (opposite to driving direction)
    # Formula: s = Displacement strength ~ speed * sin(ang)
    #          → At 90° (frontal): maximum displacement
    #          → At 0° (tangential): no displacement
    # k0 = -1.7: Negative factor → Displacement AGAINST driving direction
    # (Parameterized via ENV for tuning, e.g. CRAZYCAR_REBOUND_K0=-2.0)
    try:
        k0 = float(os.getenv("CRAZYCAR_REBOUND_K0", "-1.7"))
        s_factor = float(os.getenv("CRAZYCAR_REBOUND_S_FACTOR", "8.0"))
        turn_factor = float(os.getenv("CRAZYCAR_REBOUND_TURN_FACTOR", "7.0"))
        turn_offset = float(os.getenv("CRAZYCAR_REBOUND_TURN_OFFSET", "1.0"))
    except Exception:
        k0 = -1.7
        s_factor = 8.0
        turn_factor = 7.0
        turn_offset = 1.0

    # Calculate displacement strength (proportional to velocity & incident angle)
    s = s_factor * max(speed, 0.0) * math.sin(math.radians(ang))
    # Displacement vector in vehicle coordinates (opposite to carangle)
    dx = k0 * math.cos(math.radians(360 - carangle)) * s
    dy = k0 * math.sin(math.radians(360 - carangle)) * s

    # Torque: Vehicle rotates away from wall during oblique collisions
    # kt = Sign depends on collision corner:
    #      Corner #1 (front-right): kt=-1 → rotate left
    #      Corner #2+ (front-left):  kt=+1 → rotate right
    kt = -1.0 if nr == 1 else 1.0
    # Rotation angle ~ sin(2*ang): Maximum rotation at 45° incident angle
    turn = turn_factor * math.sin(math.radians(2 * ang)) + turn_offset
    new_angle = (carangle + kt * turn) % 360.0

    return new_speed, new_angle, (dx, dy), True


__all__ = ["rebound_action", "_angle_between", "Color", "Point", "ColorAtFn"]
