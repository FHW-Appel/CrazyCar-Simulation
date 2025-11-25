# crazycar/car/rebound.py
from __future__ import annotations
import math
from typing import Callable, Tuple
import os
import numpy as np

Color = Tuple[int, int, int,  int]
Point = Tuple[float, float]
ColorAtFn = Callable[[Tuple[int, int]], Color]


def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    den = float(np.linalg.norm(v1) * np.linalg.norm(v2))
    if den == 0.0:
        return 0.0
    cosv = max(-1.0, min(1.0, float(np.dot(v1, v2)) / den))
    return float(np.degrees(np.arccos(cosv)))


def rebound_action(
    point0: Point,
    nr: int,
    carangle: float,
    speed: float,
    color_at: ColorAtFn,
    border_color: Color,
    radius_px: float = 15.0,
    probe_step_deg: int = 10,
) -> Tuple[float, float, Tuple[float, float], bool]:
    """
    Berechnet Rebound-Verhalten bei Wandkollision (physikalisch approximiert).
    
    Algorithmus (3 Phasen):
    1. WANDNORMALE FINDEN: Kreis-Scan um Kollisionspunkt (radius_px)
       → Findet Übergang border→frei (approximiert Wandrichtung)
    2. REFLEXIONSWINKEL: Einfallswinkel zwischen Fahrtrichtung & Wandnormale
       → Geschwindigkeits-Dämpfung: 0° (tangential) → 90° (frontal)
    3. RÜCKVERSATZ: Fahrzeug aus Wand schieben (entgegen Fahrtrichtung)
       → Verhindert Tunneling durch dünne Wände
    
    Args:
        point0: Kollisionspunkt (px)
        nr: Ecken-Nummer (1=vorne-rechts, 2=vorne-links, 3/4=hinten)
        carangle: Fahrzeug-Orientierung [°]
        speed: Geschwindigkeit [px/frame]
        color_at: Map-Zugriff Callback
        border_color: Wand-Farbe (RGB+A)
        radius_px: Scan-Radius für Wandnormale
        probe_step_deg: Winkel-Schrittweite beim Scan
    
    Returns:
        (new_speed, new_angle, (dx, dy), damped)
        - new_speed: Geschwindigkeit nach Reflexion [px/frame]
        - new_angle: Neue Orientierung [°]
        - (dx, dy): Rückversatz [px] (um aus Wand zu kommen)
        - damped: True falls Geschwindigkeit reduziert wurde
    
    Note:
        Hinterräder (nr=3,4) bei Rückwärtsfahrt (speed<0) → kein Rebound
        (nur Vorderräder sollen bei Rückwärts kollidieren)
    """
    # Sonderfall: Hinterräder-Kollision bei Rückwärtsfahrt ignorieren
    if nr in (3, 4) and speed < 0:
        return 0.0, carangle, (0.0, 0.0), False

    x0, y0 = point0
    x1 = x0 + radius_px
    y1 = y0

    # === PHASE 1: WANDNORMALE APPROXIMIEREN ===
    # Kreisförmiger Scan um Kollisionspunkt (10°-Schritte, 15px Radius)
    # Ziel: Punkt finden, wo Wand→Frei-Übergang stattfindet
    # → Vektor (x0,y0)→(x1,y1) approximiert Wandnormale (zeigt ins Freie)
    for vi in range(0, 360 + probe_step_deg, probe_step_deg):
        a = math.radians(vi)
        a2 = a + math.radians(15)
        px1 = x0 + radius_px * math.cos(a)
        py1 = y0 + radius_px * math.sin(a)
        px2 = x0 + radius_px * math.cos(a2)
        py2 = y0 + radius_px * math.sin(a2)
        if color_at((int(px1), int(py1))) == border_color and color_at((int(px2), int(py2))) != border_color:
            x1, y1 = px1, py1
            break

    # === PHASE 2: REFLEXIONSWINKEL BERECHNEN ===
    # vi_vec = Fahrtrichtungsvektor (Einheitsvektor in carangle-Richtung)
    vi_vec = np.array([math.cos(math.radians(carangle)), math.sin(math.radians(carangle))], float)
    # vw_vec = Wandnormalenvektor (zeigt vom Kollisionspunkt ins Freie)
    vw_vec = np.array([x1 - x0, y1 - y0], float)
    # ang = Einfallswinkel zwischen Fahrtrichtung & Wandnormale
    # 0° = parallel (tangential), 90° = senkrecht (frontal)
    ang = _angle_between(vw_vec, vi_vec)
    if ang > 90.0:
        ang = 180.0 - ang  # Auf spitzen Winkel normalisieren (0°..90°)

    # Geschwindigkeits-Dämpfung abhängig vom Einfallswinkel
    # Physikalisches Modell:
    # - 0° (tangential):  keine Dämpfung (1.0) → Abgleiten
    # - <30° (flach):     geringe Dämpfung (0.8) → Streifschuss
    # - 30-60° (schräg):  mittlere Dämpfung (0.5) → Schräg-Aufprall
    # - >60° (frontal):   starke Dämpfung (0.2) → Fast-Stopp
    # (Parameterisiert via ENV für Tuning, z.B. CRAZYCAR_REBOUND_DAMP_SMALL=0.85)
    try:
        damp_small = float(os.getenv("CRAZYCAR_REBOUND_DAMP_SMALL", "0.8"))
        damp_med = float(os.getenv("CRAZYCAR_REBOUND_DAMP_MED", "0.5"))
        damp_large = float(os.getenv("CRAZYCAR_REBOUND_DAMP_LARGE", "0.2"))
    except Exception:
        damp_small, damp_med, damp_large = 0.8, 0.5, 0.2

    if ang == 0:
        new_speed = speed * 1.0  # Exakt tangential (theoretisch)
    elif ang < 30:
        new_speed = speed * damp_small  # Flacher Aufprall
    elif ang < 60:
        new_speed = speed * damp_med  # Schräger Aufprall
    else:
        new_speed = speed * damp_large  # Frontaler Aufprall

    # === PHASE 3: RÜCKVERSATZ & DREHMOMENT ===
    # Rückversatz (dx, dy): Fahrzeug aus Wand schieben (entgegen Fahrtrichtung)
    # Formel: s = Versatz-Stärke ~ speed * sin(ang)
    #         → Bei 90° (frontal): maximaler Versatz
    #         → Bei 0° (tangential): kein Versatz
    # k0 = -1.7: Negativer Faktor → Versatz GEGEN Fahrtrichtung
    # (Parameterisiert via ENV für Tuning, z.B. CRAZYCAR_REBOUND_K0=-2.0)
    try:
        k0 = float(os.getenv("CRAZYCAR_REBOUND_K0", "-1.7"))
        s_factor = float(os.getenv("CRAZYCAR_REBOUND_S_FACTOR", "8.0"))
        turn_factor = float(os.getenv("CRAZYCAR_REBOUND_TURN_FACTOR", "7.0"))
        turn_offset = float(os.getenv("CRAZYCAR_REBOUND_TURN_OFFSET", "1.0"))
    except Exception:
        k0 = -1.7
        s_factor = 8.0
        turn_factor = 7.0
        turn_offset = 1.0

    # Versatz-Stärke berechnen (proportional zu Geschwindigkeit & Einfallswinkel)
    s = s_factor * max(speed, 0.0) * math.sin(math.radians(ang))
    # Versatz-Vektor in Fahrzeugkoordinaten (entgegen carangle)
    dx = k0 * math.cos(math.radians(360 - carangle)) * s
    dy = k0 * math.sin(math.radians(360 - carangle)) * s

    # Drehmoment: Fahrzeug dreht sich bei schrägen Kollisionen weg von Wand
    # kt = Vorzeichen abhängig von Kollisions-Ecke:
    #      Ecke #1 (vorne-rechts): kt=-1 → Drehung nach links
    #      Ecke #2+ (vorne-links):  kt=+1 → Drehung nach rechts
    kt = -1.0 if nr == 1 else 1.0
    # Drehwinkel ~ sin(2*ang): Maximale Drehung bei 45° Einfallswinkel
    turn = turn_factor * math.sin(math.radians(2 * ang)) + turn_offset
    new_angle = (carangle + kt * turn) % 360.0

    return new_speed, new_angle, (dx, dy), True


__all__ = ["rebound_action", "_angle_between", "Color", "Point", "ColorAtFn"]
