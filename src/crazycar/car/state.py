# crazycar/car/state.py


from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

"""
Datenklasse für den Fahrzeugzustand (pygame-frei, reine Daten).

Felder (Einheiten & Bedeutung):
- position: [x, y] in px (Top-Left), center: [cx, cy] in px
- carangle: ° (0 = rechts, Uhrzeigersinn +), radangle: °
- speed: px/step, power: Throttle (−max … +max)
- time: s, distance: px, round_time: s
- corners: List[Point] (Sprite-Ecken), left_rad/right_rad: Rand-/Referenzpunkte
- alive, finished, regelung_enable: Laufzeit-Flags
- Sensorik:
  - radar_angle: ° Öffnungswinkel
  - radars: List[(Point, int)] → (Endpunkt, Distanz)
  - radar_dist: List[int] → Distanzen je Strahl
  - bit_volt_wert_list: List[(ADC-Bits, Volt)]

Hinweis: Keine Logik; Mutationen/Updates erfolgen in Motion/Sensor-Modulen.
"""


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
