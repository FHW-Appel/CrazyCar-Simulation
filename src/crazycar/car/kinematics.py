# crazycar/car/kinematics.py
"""Fahrzeugkinematik: Lenkung -> Kursänderung (pygame-frei).

Dieses Modul kapselt die Berechnung, wie sich der Fahrzeugwinkel (carangle)
bei gegebenem Lenkwinkel (radangle) und Geschwindigkeit ändert.
"""

from __future__ import annotations
import math
from typing import Final

# kleine Zahl zum Absichern gegen Division durch 0
_EPS: Final[float] = 1e-6


def normalize_angle(deg: float) -> float:
    """Normalisiert einen Winkel in Grad in den Bereich [0, 360)."""
    return float(deg % 360.0)


def steer_step(
    carangle_deg: float,
    radangle_deg: float,
    speed_px: float,
    radstand_px: float,
    spurweite_px: float,
) -> float:
    """Ein Schritt Kursänderung aufgrund von Lenkung.

    Args:
        carangle_deg: aktueller Fahrzeugwinkel [°]
        radangle_deg: Lenkwinkel der Vorderräder [°] (Vorzeichen: links/rechts)
        speed_px:     Geschwindigkeit [px pro Tick] (Vorzeichen: vorwärts/rückwärts)
        radstand_px:  Radstand des Fahrzeugs [px]
        spurweite_px: Spurweite [px]

    Returns:
        Neuer Fahrzeugwinkel [°] in [0, 360)
    """
    # keine Bewegung oder keine Lenkung → keine Kursänderung
    if abs(radangle_deg) < _EPS or abs(speed_px) < _EPS:
        return normalize_angle(carangle_deg)

    # Vorzeichen: lenkt nach links (negativ) oder rechts (positiv)
    k0 = -1.0 if radangle_deg < 0.0 else 1.0
    angle_rad = math.radians(abs(radangle_deg))

    # Kurvenradius R = L / tan(delta) + W/2
    tanv = math.tan(angle_rad)
    if abs(tanv) < _EPS:
        return normalize_angle(carangle_deg)

    car_radius = (radstand_px / tanv) + (spurweite_px / 2.0)
    if abs(car_radius) < _EPS:
        return normalize_angle(carangle_deg)

    # Änderung des Fahrzeugwinkels: Δθ ≈ s / R (s = Weg pro Tick = speed_px)
    dtheta_rad = speed_px / car_radius
    dtheta_deg = math.degrees(dtheta_rad)

    # Bei Rückwärtsfahrt dreht sich das Fahrzeug entgegengesetzt
    if speed_px > 0:
        new_angle = carangle_deg + (k0 * dtheta_deg)
    else:
        new_angle = carangle_deg - (k0 * dtheta_deg)

    return normalize_angle(new_angle)


__all__ = ["normalize_angle", "steer_step"]
