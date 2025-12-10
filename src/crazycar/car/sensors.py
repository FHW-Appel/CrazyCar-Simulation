# crazycar/car/sensors.py
"""Sensor system (pygame-free):
- Raycasts for radar sensors (map access via color_at callback)
- Radars scan across an angle range
- Distance extraction
- AD linearization (Bit/Volt) as in original code
"""

from __future__ import annotations
import math
from typing import Callable, List, Tuple, Iterable

from .constants import WIDTH, BORDER_COLOR, RADAR_SWEEP_DEG, MAX_RADAR_LEN_RATIO

# Typen
Color = Tuple[int, int, int, int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]


def cast_radar(
    center: Point,
    carangle_deg: float,
    degree_offset: int,
    color_at: ColorAtFn,
    *,
    max_len_px: float,
    border_color: Color = BORDER_COLOR,
) -> Tuple[Point, int]:
    """Cast single radar beam in specified direction.
    
    Samples pixel-by-pixel until border color is reached or max distance exceeded.
    
    Args:
        center: Start point (x, y) in pixels
        carangle_deg: Vehicle heading angle in degrees
        degree_offset: Angle offset from heading (e.g., -60, 0, +60)
        color_at: Function to get pixel color at (x, y)
        max_len_px: Maximum beam length in pixels
        border_color: RGB(A) color indicating wall/border
        
    Returns:
        Tuple of ((x, y), dist_px) - endpoint coordinates and measured distance
    """
    length = 0
    cx, cy = center

    # Start point
    x = int(cx + math.cos(math.radians(360 - (carangle_deg + degree_offset))) * length)
    y = int(cy + math.sin(math.radians(360 - (carangle_deg + degree_offset))) * length)

    # Probe forward until border or maximum distance
    while color_at((x, y)) != border_color and length < int(max_len_px):
        length += 1
        x = int(cx + math.cos(math.radians(360 - (carangle_deg + degree_offset))) * length)
        y = int(cy + math.sin(math.radians(360 - (carangle_deg + degree_offset))) * length)

    dist_px = int(math.hypot(x - cx, y - cy))
    return (x, y), dist_px


def collect_radars(
    center: Point,
    carangle_deg: float,
    sweep_deg: int = RADAR_SWEEP_DEG,
    *,
    step_deg: int = RADAR_SWEEP_DEG,
    color_at: ColorAtFn,
    max_len_px: float | None = None,
    border_color: Color = BORDER_COLOR,
) -> List[Tuple[Point, int]]:
    """Collect multiple radar beams across an angle range.
    
    Casts radars from -sweep_deg to +sweep_deg with step_deg increments.
    For example: sweep_deg=60, step_deg=60 yields [-60°, 0°, +60°].
    
    Args:
        center: Vehicle center point (x, y)
        carangle_deg: Vehicle heading angle in degrees
        sweep_deg: Sweep range in degrees (default: RADAR_SWEEP_DEG=60)
        step_deg: Angular step size between beams (default: RADAR_SWEEP_DEG=60)
        color_at: Function to get pixel color at (x, y)
        max_len_px: Maximum beam length, defaults to WIDTH * MAX_RADAR_LEN_RATIO
        border_color: RGB(A) color indicating wall/border
        
    Returns:
        List of ((x, y), dist_px) tuples for each radar beam
    """
    # Normalize to float (good for type checker & calls)
    limit: float = float(max_len_px) if max_len_px is not None else float(WIDTH * MAX_RADAR_LEN_RATIO)

    radars: List[Tuple[Point, int]] = []
    for deg in range(-sweep_deg, sweep_deg + 1, step_deg):
        radars.append(
            cast_radar(center, carangle_deg, deg, color_at, max_len_px=limit, border_color=border_color)
        )
    return radars


def distances(radars: Iterable[Tuple[Point, int]]) -> List[int]:
    """Extract distance values from radar data.
    
    Args:
        radars: Iterable of ((x, y), dist_px) tuples
        
    Returns:
        List of distances in pixels
    """
    return [int(r[1]) for r in radars]


def linearize_DA(dist_list_cm: Iterable[float]) -> List[Tuple[int, float]]:
    """Convert distance measurements to digital/analog sensor values.
    
    Applies DA linearization (Bit/Volt) according to original formulas:
    - digital_bit = int((A / d_cm) + B)  with A=23962, B=-20
    - analog_volt = (AV / d_cm) + BV     with AV=58.5, BV=-0.05
    
    Args:
        dist_list_cm: Iterable of distances in centimeters
        
    Returns:
        List of (digital_bit, analog_volt) tuples
        
    Note:
        Returns (0, 0.0) for zero distance to avoid division by zero
    """
    A, B = 23962.0, -20.0
    AV, BV = 58.5, -0.05

    out: List[Tuple[int, float]] = []
    for d_cm in dist_list_cm:
        if d_cm == 0:
            out.append((0, 0.0))
        else:
            digital_bit = int((A / d_cm) + B)
            analog_volt = (AV / d_cm) + BV
            out.append((digital_bit, analog_volt))
    return out


__all__ = ["cast_radar", "collect_radars", "distances", "linearize_DA", "Color", "Point", "ColorAtFn"]
