# crazycar/car/rebound.py
from __future__ import annotations
import math
from typing import Callable, Tuple
import numpy as np

"""Berechnet ein “Abprallen” nach Kollision. compute_rebound(vel, normal, damping) 
    spiegelt die Geschwindigkeit an der Kollisionsnormalen und dämpft sie, separate_from_wall(center, normal, depth) 
    schiebt das Fahrzeug minimal aus der Wand heraus. 
    Damit lassen sich weiche Crash-Reaktionen modellieren (alternativ zu “sofort stoppen”)."""

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
    if nr in (3, 4) and speed < 0:
        return 0.0, carangle, (0.0, 0.0), False

    x0, y0 = point0
    x1 = x0 + radius_px
    y1 = y0

    # Suche Kanten-Übergang grob
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

    vi_vec = np.array([math.cos(math.radians(carangle)), math.sin(math.radians(carangle))], float)
    vw_vec = np.array([x1 - x0, y1 - y0], float)
    ang = _angle_between(vw_vec, vi_vec)
    if ang > 90.0:
        ang = 180.0 - ang

    # Dämpfung
    if ang == 0:
        new_speed = speed * 1.0
    elif ang < 30:
        new_speed = speed * 0.8
    elif ang < 60:
        new_speed = speed * 0.5
    else:
        new_speed = speed * 0.2

    # Rückversatz + Drehen
    k0 = -1.7
    s = 8.0 * max(speed, 0.0) * math.sin(math.radians(ang))
    dx = k0 * math.cos(math.radians(360 - carangle)) * s
    dy = k0 * math.sin(math.radians(360 - carangle)) * s

    kt = -1.0 if nr == 1 else 1.0
    turn = 7.0 * math.sin(math.radians(2 * ang)) + 1.0
    new_angle = (carangle + kt * turn) % 360.0

    return new_speed, new_angle, (dx, dy), True


__all__ = ["rebound_action", "_angle_between", "Color", "Point", "ColorAtFn"]
