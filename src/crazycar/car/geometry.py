# crazycar/car/geometry.py
"""Vehicle Geometry - Corner and Wheel Position Calculation (pygame-free)."""

from __future__ import annotations
import math
from typing import List, Tuple

Point = Tuple[float, float]


def compute_corners(center: Point, carangle: float, length: float, width: float) -> List[Point]:
    """Compute the four corner points of the vehicle.

    Args:
        center:   Center point of the vehicle (x,y)
        carangle: Vehicle angle in degrees (0° = right)
        length:   Half length in pixels
        width:    Half width in pixels

    Returns:
        [left_top, right_top, left_bottom, right_bottom] as list of (x,y) tuples
    """
    diag = math.sqrt(length ** 2 + width ** 2)
    # Angle offset ~23°/157°/203° as in original code
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
    """Calculate wheel positions (left/right front).

    Args:
        center:     Vehicle center point (x,y)
        carangle:   Vehicle angle in degrees
        diag_minus: Distance to corner minus small offset (~6px in original)

    Returns:
        (left_rad, right_rad) as (x,y) tuple
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
