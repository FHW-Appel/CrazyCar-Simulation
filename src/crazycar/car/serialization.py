# crazycar/car/serialization.py
"""Vehicle state serialization (pygame-free).

Creates a JSON/pickle-compatible dictionary from vehicle state.
Allows saving snapshots and restoring them later.

Note "Recover more accurate":
In addition to previous fields, now optionally outputs `power`, `radangle`,
`fwert` and `swert` if present. This allows more exact state reconstruction.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import json

# Typen
Point = Sequence[float]            # (x, y)
Radar = Tuple[Point, int]          # ((x, y), dist_px)


def _listify_point(p: Point) -> List[float]:
    """Safely convert point to list with float values.
    
    Args:
        p: Point as (x, y) sequence
        
    Returns:
        List [x, y] with float values
    """
    return [float(p[0]), float(p[1])]


def _listify_radars(radars: Iterable[Radar]) -> List[List[Any]]:
    """Convert radar data to JSON-friendly format.
    
    Args:
        radars: Iterable of ((x,y), dist) tuples
        
    Returns:
        List of [ [x,y], dist ] for JSON serialization
    """
    out: List[List[Any]] = []
    for (pt, dist) in radars:
        out.append([_listify_point(pt), int(dist)])
    return out


def serialize_state(
    position_px: Point,
    carangle_deg: float,
    speed_px: float,
    speed_set: float,
    radars: Iterable[Radar],
    bit_volt_wert_list: Iterable[Tuple[int, float]],
    distance_px: float,
    time_s: float,
    *,
    f_scale: float = 1.0,  # Position scaled by f as in original
    # ---- NEW/optional: more precise recovery ----
    power: float | None = None,
    radangle: float | None = None,
    fwert: float | None = None,
    swert: float | None = None,
) -> Dict[str, Any]:
    """Build JSON/pickle-compatible dict from vehicle state values.
    
    Creates serializable dictionary with required and optional fields.
    Optional fields are only added if not None for backward compatibility.
    
    Args:
        position_px: Vehicle position (x, y) in pixels
        carangle_deg: Heading angle in degrees
        speed_px: Current speed in pixels per step
        speed_set: Target speed setting
        radars: Radar sensor data as ((x, y), dist) tuples
        bit_volt_wert_list: Linearized ADC values as (bit, volt) tuples
        distance_px: Total distance traveled in pixels
        time_s: Elapsed simulation time in seconds
        f_scale: Scaling factor for position (default 1.0)
        power: Optional motor power value
        radangle: Optional steering angle
        fwert: Optional forward control value
        swert: Optional steering control value
        
    Returns:
        Dictionary with vehicle state suitable for JSON/pickle serialization
    """
    pos_out = (
        [float(position_px[0]) / f_scale, float(position_px[1]) / f_scale]
        if f_scale
        else _listify_point(position_px)
    )

    out: Dict[str, Any] = {
        "position": pos_out,
        "carangle": float(carangle_deg),
        "speed": float(speed_px),
        "speed_set": float(speed_set),
        "radars": _listify_radars(radars),
        "analog_wert_list": [[int(b), float(v)] for (b, v) in bit_volt_wert_list],
        "distance": float(distance_px),
        "time": float(time_s),
    }

    # Optionally append (only if set), so old snapshots remain valid
    if power is not None:
        out["power"] = float(power)
    if radangle is not None:
        out["radangle"] = float(radangle)
    if fwert is not None:
        out["fwert"] = float(fwert)
    if swert is not None:
        out["swert"] = float(swert)

    return out


def serialize_car(car: Any, *, f_scale: float = 1.0) -> Dict[str, Any]:
    """Convenient wrapper for serializing a Car object.
    
    Extracts attributes from Car instance and delegates to serialize_state().
    Uses getattr(..., None) for optional fields - missing attributes are
    simply not included in the result dict.
    
    Args:
        car: Car object with expected attributes (position, carangle, etc.)
        f_scale: Scaling factor for position (default 1.0)
        
    Returns:
        Dictionary with vehicle state suitable for JSON/pickle serialization
    """
    return serialize_state(
        position_px=car.position,
        carangle_deg=car.carangle,
        speed_px=car.speed,
        speed_set=car.speed_set,
        radars=car.radars,
        bit_volt_wert_list=car.bit_volt_wert_list,
        distance_px=car.distance,
        time_s=car.time,
        f_scale=f_scale,
        # ---- NEW/optional for "recover correctly" ----
        power=getattr(car, "power", None),
        radangle=getattr(car, "radangle", None),
        fwert=getattr(car, "fwert", None),
        swert=getattr(car, "swert", None),
    )


def to_json(data: Dict[str, Any], *, indent: int | None = None) -> str:
    """Optional: Output dict as JSON string (for logging/debugging)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), indent=indent)


__all__ = ["serialize_state", "serialize_car", "to_json", "Point", "Radar"]
