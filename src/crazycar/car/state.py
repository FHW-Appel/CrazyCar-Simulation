# crazycar/car/state.py
"""Zustandsträger für das Fahrzeug (pygame-frei). Keine Logik, nur Daten."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]
Radar = Tuple[Point, int]

@dataclass
class CarState:
    # Grundzustand
    position: List[float]           # [x, y]
    carangle: float                 # ° (0 rechts)
    speed: float                    # px/step
    power: float                    # throttle [-max, +max]
    radangle: float                 # ° Lenkung
    time: float                     # s
    distance: float                 # px

    # Abgeleitet / Hilfswerte
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    corners: List[Point] = field(default_factory=list)
    left_rad: Point | None = None
    right_rad: Point | None = None

    # Flags
    alive: bool = True
    finished: bool = False
    round_time: float = 0.0
    regelung_enable: bool = True

    # Sensorik
    radar_angle: int = 60
    radars: List[Radar] = field(default_factory=list)
    radar_dist: List[int] = field(default_factory=list)
    bit_volt_wert_list: List[Tuple[int, float]] = field(default_factory=list)

__all__ = ["CarState", "Point", "Radar"]
