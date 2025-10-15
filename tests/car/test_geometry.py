# src/crazycar/car/geometry.py
from __future__ import annotations
from math import cos, sin, radians
from typing import List, Tuple

Point = tuple[float, float]

def compute_corners(
    x: float,
    y: float,
    heading: float,
    length: float,
    width: float,
    unit_scale: float = 1.0,
    *,
    degrees: bool = False,
) -> List[Point]:
    """
    Liefert die 4 Eckpunkte eines Rechtecks (Fahrzeug), dessen Mittelpunkt bei (x, y) liegt.

    Parameter
    ---------
    x, y        : Mittelpunkt (Pixel oder beliebige Einheiten)
    heading     : Ausrichtung (Standard: Radiant; `degrees=True` für Grad)
    length      : Fahrzeuglänge (wird mit `unit_scale` skaliert)
    width       : Fahrzeugbreite (wird mit `unit_scale` skaliert)
    unit_scale  : Skala (z. B. cm→px). Default 1.0.
    degrees     : Wenn True, ist `heading` in Grad; sonst Radiant.

    Rückgabe
    --------
    Liste aus 4 Punkten [(x1,y1), (x2,y2), (x3,y3), (x4,y4)].
    Reihenfolge bei heading=0: [(-L/2,-W/2), (L/2,-W/2), (L/2,W/2), (-L/2,W/2)] um (x,y) rotiert.
    """
    if degrees:
        heading = radians(heading)

    L = float(length) * float(unit_scale)
    W = float(width)  * float(unit_scale)
    hx, hy = L / 2.0, W / 2.0

    # Lokale Eckpunkte (Body-Frame, heading=0)
    local = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]

    c, s = cos(heading), sin(heading)
    world = []
    for px, py in local:
        rx = px * c - py * s
        ry = px * s + py * c
        world.append((x + rx, y + ry))
    return world

__all__ = ["compute_corners", "Point"]
