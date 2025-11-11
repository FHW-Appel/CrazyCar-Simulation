from __future__ import annotations
from typing import List
import logging

import pygame

from ..car.model import Car

log = logging.getLogger("crazycar.sim.spawn_utils")


def spawn_from_map(map_service) -> List[Car]:
    """
    Create a list with a single Car using MapService.get_spawn() and the
    project's conversion rules. This was extracted from simulation._spawn_car_from_map
    so the simulation module stays small.
    Returns: [Car]
    """
    try:
        from ..car.constants import CAR_cover_size
    except Exception:
        CAR_cover_size = 32

    spawn = map_service.get_spawn()
    half_px = (CAR_cover_size * 0.5)
    pos = [spawn.x_px - half_px, spawn.y_px - half_px]

    # Prefer the angle computed by MapService (it already derives the normal
    # / forward direction from the finish-line). Only fall back to the raw
    # Spawn.angle_deg if detection info is not available. Avoid recomputing
    # the angle from spawn->center here because that vector is typically the
    # inverse of the driving normal (spawn is offset from the line center).
    map_angle = float(spawn.angle_deg)
    info = None
    try:
        info = map_service.get_detect_info()
        if info and info.get("n", 0) > 0 and "angle_deg" in info:
            map_angle = float(info["angle_deg"])
            log.info("Spawn angle from MapService.detect_info used: angle=%.1f°", map_angle)
    except Exception:
        info = None

    # Prefer to compute the car angle so the car nose points TO the detected
    # finish-line center: this guarantees the vehicle will face the red line
    # and (when throttled) drive over it. We compute sim_ang from spawn->line
    # center and then apply the same probe-flip (180°) decision above if it
    # indicated a flip was necessary.
    try:
        sim_ang = None
        if info and info.get("n", 0) > 0:
            cx = float(info.get("cx", 0.0))
            cy = float(info.get("cy", 0.0))
            # vector from spawn -> line center
            from math import atan2, degrees
            dx_line = cx - float(spawn.x_px)
            dy_line = cy - float(spawn.y_px)
            sim_ang = (360.0 - degrees(atan2(dy_line, dx_line))) % 360.0
            angle = float(sim_ang)
            log.info("Spawn angle computed from spawn->line center: %.3f° (cx,cy)=(%.1f,%.1f)", angle, cx, cy)
        else:
            # Fallback to MapService angle conversion if detect_info missing
            angle = (360.0 - float(map_angle)) % 360.0
            log.info("Spawn angle fallback from map_angle -> carangle: %.1f -> %.1f", float(map_angle), angle)
    except Exception:
        # last-resort: convert map_angle
        try:
            angle = (360.0 - float(map_angle)) % 360.0
        except Exception:
            angle = 0.0

    return [Car(pos, angle, 20, False, [], [], 0, 0)]
