# crazycar/car/serialization.py
"""Serialisierung des Fahrzeugzustands (pygame-frei)."""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import json

# Typen
Point = Sequence[float]            # (x, y)
Radar = Tuple[Point, int]          # ((x, y), dist_px)


def _listify_point(p: Point) -> List[float]:
    """Sicher als [x, y] mit float-Werten ausgeben."""
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
    f_scale: float = 1.0,  # Position wie im Original durch f skalieren
) -> Dict[str, Any]:
    """Baut ein JSON-taugliches Dict aus den übergebenen Werten."""
    pos_out = [
        float(position_px[0]) / f_scale,
        float(position_px[1]) / f_scale,
    ] if f_scale else _listify_point(position_px)

    return {
        "position": pos_out,
        "carangle": float(carangle_deg),
        "speed": float(speed_px),
        "speed_set": float(speed_set),
        "radars": _listify_radars(radars),
        "analog_wert_list": [[int(b), float(v)] for (b, v) in bit_volt_wert_list],
        "distance": float(distance_px),
        "time": float(time_s),
    }


def serialize_car(car: Any, *, f_scale: float = 1.0) -> Dict[str, Any]:
    """Bequemer Wrapper für ein Car-Objekt (erwartete Attribute wie im Modell)."""
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
    )


def to_json(data: Dict[str, Any], *, indent: int | None = None) -> str:
    """Optional: Dict als JSON-String ausgeben (für Logging/Debug)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), indent=indent)


__all__ = ["serialize_state", "serialize_car", "to_json", "Point", "Radar"]
