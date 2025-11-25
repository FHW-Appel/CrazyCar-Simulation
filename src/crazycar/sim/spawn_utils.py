from __future__ import annotations
from typing import List
import logging

import pygame

from ..car.model import Car

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
    # Auto-Cover-Size aus Konstanten holen (Fallback 32px für alte Setups)
    try:
        from ..car.constants import CAR_cover_size
    except Exception:
        CAR_cover_size = 32  # Standard-Größe für Auto-Sprite

    spawn = map_service.get_spawn()
    
    # Koordinatenumrechnung: Spawn ist Mittelpunkt, Car braucht linke obere Ecke
    half_px = (CAR_cover_size * 0.5)
    pos = [spawn.x_px - half_px, spawn.y_px - half_px]

    # Winkel bevorzugt aus MapService holen (hat bereits korrekte Fahrtrichtung
    # aus Ziellinienerkennung berechnet). Nur bei Fehler auf spawn.angle_deg
    # zurückfallen. NICHT neu aus spawn→center berechnen, da dieser Vektor
    # oft die inverse Fahrtrichtung ist (Spawn liegt versetzt zur Linie).
    map_angle = float(spawn.angle_deg)
    info = None
    try:
        info = map_service.get_detect_info()
        if info and info.get("n", 0) > 0 and "angle_deg" in info:
            map_angle = float(info["angle_deg"])
            log.debug("Spawn angle from MapService.detect_info used: angle=%.1f°", map_angle)
    except Exception:
        info = None

    # Auto-Nase soll ZUR erkannten Ziellinie zeigen: Garantiert, dass Fahrzeug
    # die rote Linie anfährt. Winkel aus spawn→Linienmittelpunkt berechnen,
    # dann ggf. 180°-Flip aus Probe-Sampling anwenden.
    try:
        sim_ang = None
        MIN_PIXELS_FOR_DETECTION = 0  # Mindestanzahl roter Pixel für valide Detection
        if info and info.get("n", 0) > MIN_PIXELS_FOR_DETECTION:
            cx = float(info.get("cx", 0.0))
            cy = float(info.get("cy", 0.0))
            
            # Vektor spawn → Linienmittelpunkt
            from math import atan2, degrees
            dx_line = cx - float(spawn.x_px)
            dy_line = cy - float(spawn.y_px)
            
            # Pygame-Konvention: 0° = rechts, 90° = unten (Y-Achse nach unten)
            PYGAME_ANGLE_OFFSET = 360.0
            sim_ang = (PYGAME_ANGLE_OFFSET - degrees(atan2(dy_line, dx_line))) % 360.0
            angle = float(sim_ang)
            log.debug("Spawn angle computed from spawn->line center: %.3f° (cx,cy)=(%.1f,%.1f)", angle, cx, cy)
        else:
            # Fallback: MapService-Winkel konvertieren (wenn Detection-Info fehlt)
            angle = (360.0 - float(map_angle)) % 360.0
            log.debug("Spawn angle fallback from map_angle -> carangle: %.1f -> %.1f", float(map_angle), angle)
    except Exception:
        # Letzter Fallback: map_angle direkt konvertieren
        try:
            angle = (360.0 - float(map_angle)) % 360.0
        except Exception:
            angle = 0.0  # Sicherheits-Fallback: 0° = nach rechts

    return [Car(pos, angle, 20, False, [], [], 0, 0)]
