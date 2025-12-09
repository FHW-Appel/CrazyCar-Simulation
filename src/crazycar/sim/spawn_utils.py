"""Vehicle Spawn Utilities - Initialization at Start Position.

This module creates Car instances from MapService spawn data.

Main Function:
- spawn_from_map(): Converts spawn point → Car instance

Coordinate Conversion:
- MapService provides CENTER position (midpoint)
- Car constructor expects TOP-LEFT (upper left corner)
- Conversion: pos = [spawn.x - cover_size/2, spawn.y - cover_size/2]

Angle Calculation:
1. Preferred: angle_deg from MapService.detect_info (finish line detection)
2. Fallback: spawn.angle_deg (configuration file)
3. Car nose points TOWARDS finish line (important for correct direction)

Constants:
- DEFAULT_CAR_COVER_SIZE: 32px (fallback sprite size)
- MIN_PIXELS_FOR_DETECTION: 0 (minimum pixels for valid detection)

See Also:
- map_service.py: get_spawn(), get_detect_info()
- model.py: Car.__init__()
- finish_detection.py: principal_direction(), choose_forward_sign()
"""
from __future__ import annotations
from typing import List
import logging

import pygame

from ..car.model import Car

# Constants for spawn logic
DEFAULT_CAR_COVER_SIZE = 32  # Pixels - Fallback if constants not available
MIN_PIXELS_FOR_DETECTION = 0  # Minimum pixels for valid finish line detection
PYGAME_ANGLE_OFFSET = 360.0  # Pygame angle convention (0°=right, counterclockwise)
CENTER_TO_TOPLEFT_DIVISOR = 2  # Divide cover_size by 2 to convert center to top-left
DEFAULT_CAR_INITIAL_POWER = 20  # Default power setting for spawned cars
DEFAULT_CARANGLE_FALLBACK = 0.0  # Safety fallback angle if all detection fails (0° = right)

log = logging.getLogger("crazycar.sim.spawn_utils")


def spawn_from_map(map_service) -> List[Car]:
    """Create Car instance from MapService spawn point with proper coordinate conversion.
    
    Converts MapService spawn data (center-point coordinates + angle) to Car constructor
    format (top-left coordinates + angle). Prefers angle computed from finish-line
    detection for accurate forward direction.
    
    Args:
        map_service: MapService instance with spawn point and detection info
        
    Returns:
        List containing single Car instance positioned at spawn point.
        
    Note:
        - Spawn coordinates are center-based, Car expects top-left corner
        - Angle conversion: MapService uses atan2 convention, Car uses pygame convention
        - Falls back to spawn.angle_deg if detection info unavailable
    """
    # Get car cover size from constants (fallback for old setups).
    try:
        from ..car.constants import CAR_cover_size
    except Exception:
        CAR_cover_size = DEFAULT_CAR_COVER_SIZE  # Default size for car sprite

    spawn = map_service.get_spawn()
    
    # Coordinate conversion: Spawn is center point, Car needs top-left corner
    half_px = CAR_cover_size / CENTER_TO_TOPLEFT_DIVISOR
    pos = [spawn.x_px - half_px, spawn.y_px - half_px]

    # Prefer angle from MapService (correct direction from finish line detection)
    # DO NOT recalculate from spawn→center vector (often gives inverse direction)
    map_angle = float(spawn.angle_deg)
    info = None
    try:
        info = map_service.get_detect_info()
        if info and info.get("n", 0) > 0 and "angle_deg" in info:
            map_angle = float(info["angle_deg"])
            log.debug("Spawn angle from MapService.detect_info used: angle=%.1f°", map_angle)
    except Exception:
        info = None

    # Car nose points TOWARDS finish line (guarantees approach to red line)
    try:
        sim_ang = None
        if info and info.get("n", 0) > MIN_PIXELS_FOR_DETECTION:
            cx = float(info.get("cx", 0.0))
            cy = float(info.get("cy", 0.0))
            
            # Vector spawn → line center
            from math import atan2, degrees
            dx_line = cx - float(spawn.x_px)
            dy_line = cy - float(spawn.y_px)
            
            # Pygame convention: 0° = right, 90° = down (Y-axis downward)
            sim_ang = (PYGAME_ANGLE_OFFSET - degrees(atan2(dy_line, dx_line))) % PYGAME_ANGLE_OFFSET
            angle = float(sim_ang)
            log.debug("Spawn angle computed from spawn->line center: %.3f° (cx,cy)=(%.1f,%.1f)", angle, cx, cy)
        else:
            # Fallback: Convert MapService angle (if detection info missing)
            angle = (PYGAME_ANGLE_OFFSET - float(map_angle)) % PYGAME_ANGLE_OFFSET
            log.debug("Spawn angle fallback from map_angle -> carangle: %.1f -> %.1f", float(map_angle), angle)
    except Exception:
        # Last fallback: Convert map_angle directly
        try:
            angle = (PYGAME_ANGLE_OFFSET - float(map_angle)) % PYGAME_ANGLE_OFFSET
        except Exception:
            angle = DEFAULT_CARANGLE_FALLBACK

    return [Car(pos, angle, DEFAULT_CAR_INITIAL_POWER, False, [], [], 0, 0)]
