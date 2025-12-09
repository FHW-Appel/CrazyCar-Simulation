# crazycar/car/state.py
"""Vehicle State Container - Data-only (no pygame dependencies, no logic)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]
Radar = Tuple[Point, int]

@dataclass
class CarState:
    """Vehicle state snapshot containing position, motion, and sensor data.
    
    Pure data container with no pygame dependencies or business logic.
    Used for serialization, state recovery, and physics calculations.
    
    Attributes:
        position: [x, y] coordinates in simulation pixels
        carangle: Heading angle in degrees (0° = right/east)
        speed: Current velocity in pixels per timestep
        power: Throttle setting [-max, +max]
        radangle: Steering angle in degrees
        time: Elapsed simulation time in seconds
        distance: Total distance traveled in pixels
        center: Geometric center point [x, y]
        corners: Four corner points [(x,y), ...] for collision detection
        left_rad/center_rad/right_rad: Radar sensor endpoints and distances
    """
    # Core state
    position: List[float]           # [x, y]
    carangle: float                 # ° (0 = right)
    speed: float                    # px/step
    power: float                    # throttle [-max, +max]
    radangle: float                 # ° steering angle
    time: float                     # s
    distance: float                 # px

    # Derived / helper values
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])
    corners: List[Point] = field(default_factory=list)
    left_rad: Point | None = None
    right_rad: Point | None = None

    # Flags
    alive: bool = True
    finished: bool = False
    round_time: float = 0.0
    regelung_enable: bool = True

    # Sensors
    radar_angle: int = 60
    radars: List[Radar] = field(default_factory=list)
    radar_dist: List[int] = field(default_factory=list)
    bit_volt_wert_list: List[Tuple[int, float]] = field(default_factory=list)

__all__ = ["CarState", "Point", "Radar"]
