# crazycar/car/units.py
"""Regelt die Einheitenumrechnung zwischen Simulation und “realer” Welt. 
    sim_to_real(px) wandelt Pixel in Zentimeter, real_to_sim(cm) zurück in Pixel. 
    So bleibt der Rest des Codes unabhängig von der Zeichenauflösung.
"""

from __future__ import annotations
from .constants import WIDTH

_TRACK_WIDTH_CM: float = 1900.0  # Referenzbreite in cm


def sim_to_real(simpx: float) -> float:
    """Pixel -> cm (bezogen auf 1900 cm ≙ WIDTH px)."""
    return (float(simpx) * _TRACK_WIDTH_CM) / float(WIDTH)


def real_to_sim(realcm: float) -> float:
    """cm -> Pixel (bezogen auf 1900 cm ≙ WIDTH px)."""
    return (float(realcm) * float(WIDTH)) / _TRACK_WIDTH_CM


__all__ = ["sim_to_real", "real_to_sim"]
