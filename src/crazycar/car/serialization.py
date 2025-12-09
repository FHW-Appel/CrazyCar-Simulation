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
    """Safely output as [x, y] with float values."""
    return [float(p[0]), float(p[1])]


def _listify_radars(radars: Iterable[Radar]) -> List[List[Any]]:
    """[ ((x,y), dist), ... ] -> [ [ [x,y], dist ], ... ] (JSON-freundlich)."""
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
    """Build JSON/pickle-compatible dict from provided values.
    
    Required fields remain unchanged, optional fields are only added if not None
    → backward compatible.
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
    """Convenient wrapper for a Car object (expected attributes as in model).
    
    Uses getattr(..., None) for optional fields → if an attribute is missing,
    it is simply not included in the result dict.
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
