# crazycar/car/sensors.py
"""Sensorik (pygame-frei):
- Raycasts für Radare (Map-Zugriff via Callback color_at)
- Radare sammeln über einen Winkelbereich
- Distanzen extrahieren
- DA-Linearisierung (Bit/Volt) wie im Originalcode

Simuliert die Abstandssensoren. cast_radars(surface, center, angle, spec) 
feuert die Sensorstrahlen in die Karte und ermittelt Treffpunkte und Distanzen, 
px_to_volt(px) linearisiert eine Pixel-Distanz zu einer “Analogspannung”, und 
digits_from_volt(v) macht daraus die “Digitalbits”. Ergebnis sind Listen aus 
Radar-Treffern, Distanzen und A/D-Werten für den Regler.
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
    """Ein Radarstrahl in Richtung (carangle + degree_offset).

    Tastet Pixel für Pixel vor, bis Randfarbe erreicht ist oder max_len_px überschritten wird.

    Returns:
        ((x, y), dist_px)  Endpunkt & gemessene Distanz in Pixel
    """
    length = 0
    cx, cy = center

    # Startpunkt
    x = int(cx + math.cos(math.radians(360 - (carangle_deg + degree_offset))) * length)
    y = int(cy + math.sin(math.radians(360 - (carangle_deg + degree_offset))) * length)

    # Vorwärts tasten bis Rand oder Maximaldistanz
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
    """Sammelt Radare über einen Winkelbereich (z. B. -60°, 0°, +60°)."""
    # auf float normalisieren (gut für Type-Checker & Aufrufe)
    limit: float = float(max_len_px) if max_len_px is not None else float(WIDTH * MAX_RADAR_LEN_RATIO)

    radars: List[Tuple[Point, int]] = []
    for deg in range(-sweep_deg, sweep_deg + 1, step_deg):
        radars.append(
            cast_radar(center, carangle_deg, deg, color_at, max_len_px=limit, border_color=border_color)
        )
    return radars


def distances(radars: Iterable[Tuple[Point, int]]) -> List[int]:
    """Extrahiert nur die Distanzen in Pixel aus der Radar-Liste."""
    return [int(r[1]) for r in radars]


def linearize_DA(dist_list_cm: Iterable[float]) -> List[Tuple[int, float]]:
    """DA-Linearisierung (Bit/Volt) gemäß Originalformeln.

    Formeln:
        digital_bit = int((A / d_cm) + B)        mit A=23962, B=-20
        analog_volt = (AV / d_cm) + BV           mit AV=58.5, BV=-0.05
        Bei d_cm == 0 → (0, 0.0)
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
