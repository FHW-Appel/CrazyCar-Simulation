# crazycar/car/geometry.py
"""Fahrzeuggeometrie: Berechnung von Ecken und Radpositionen (pygame-frei)."""

from __future__ import annotations
import math
from typing import List, Tuple

Point = Tuple[float, float]


def compute_corners(center: Point, carangle: float, length: float, width: float) -> List[Point]:
    """Berechnet die vier Eckpunkte des Fahrzeugs.

    Args:
        center:   Mittelpunkt des Fahrzeugs (x,y)
        carangle: Fahrzeugwinkel in Grad (0° = nach rechts)
        length:   halbe Länge in Pixel
        width:    halbe Breite in Pixel

    Returns:
        [left_top, right_top, left_bottom, right_bottom] als Liste von (x,y)
    """
    diag = math.sqrt(length ** 2 + width ** 2)
    # Winkelversatz ~23°/157°/203° wie im Original
    left_top = (
        center[0] + math.cos(math.radians(360 - (carangle + 23))) * diag,
        center[1] + math.sin(math.radians(360 - (carangle + 23))) * diag,
    )
    right_top = (
        center[0] + math.cos(math.radians(360 - (carangle - 23))) * diag,
        center[1] + math.sin(math.radians(360 - (carangle - 23))) * diag,
    )
    left_bottom = (
        center[0] + math.cos(math.radians(360 - (carangle + 157))) * diag,
        center[1] + math.sin(math.radians(360 - (carangle + 157))) * diag,
    )
    right_bottom = (
        center[0] + math.cos(math.radians(360 - (carangle + 203))) * diag,
        center[1] + math.sin(math.radians(360 - (carangle + 203))) * diag,
    )
    return [left_top, right_top, left_bottom, right_bottom]


def compute_wheels(center: Point, carangle: float, diag_minus: float) -> Tuple[Point, Point]:
    """Berechnet die Radpositionen (links/rechts vorne).

    Args:
        center:     Mittelpunkt des Fahrzeugs (x,y)
        carangle:   Fahrzeugwinkel in Grad
        diag_minus: Abstand zur Ecke minus kleiner Offset (~6px im Original)

    Returns:
        (left_rad, right_rad) als (x,y)-Tupel
    """
    left_rad = (
        center[0] + math.cos(math.radians(360 - (carangle + 23))) * diag_minus,
        center[1] + math.sin(math.radians(360 - (carangle + 23))) * diag_minus,
    )
    right_rad = (
        center[0] + math.cos(math.radians(360 - (carangle - 23))) * diag_minus,
        center[1] + math.sin(math.radians(360 - (carangle - 23))) * diag_minus,
    )
    return left_rad, right_rad


__all__ = ["compute_corners", "compute_wheels"]
