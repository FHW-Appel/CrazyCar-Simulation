# tests/car/test_sensors_unit.py
# -----------------------------------------------------------------------------
# Unit-Tests für das Sensor-Modul (rein numerisch, ohne Map/Raycasting).
# Fokus:
#   1) linearize_DA(dist, max_px): Distanz -> normierter Wert [0..1]
#   2) Winkel-Konfiguration (SENSOR.angles_deg) und Mathe-Konsistenz
#
# Ziele:
# - keine Abhängigkeit von Pygame, Rendering oder Kollision
# - deterministisch, schnell, minimal
# -----------------------------------------------------------------------------

import math
from crazycar.car import sensors


def test_linearize_DA_edges_and_values():
    """
    Prüft Kanten- und Zwischenwerte der Normalisierung:
    - Distanz < 0 → 0 (Clamp unten)
    - Distanz = 0 → 0
    - Distanz = max_px → 1
    - Distanz > max_px → 1 (Clamp oben)
    - mehrere Zwischenwerte -> erwartete lineare Skalierung
    """
    max_px = 100  # angenommene maximale Sensorreichweite in Pixel

    # --- Kantenfälle -------------------------------------------------------
    assert sensors.linearize_DA(0, max_px) == 0
    assert sensors.linearize_DA(max_px, max_px) == 1
    assert sensors.linearize_DA(max_px + 10, max_px) == 1   # Clamp oben
    assert sensors.linearize_DA(-5, max_px) == 0            # Clamp unten

    # --- Zwischenwerte: reine Zahlenlogik ----------------------------------
    # Erwartung: lineare Abbildung dist/max_px
    assert math.isclose(sensors.linearize_DA(25, max_px), 0.25, rel_tol=1e-9)
    assert math.isclose(sensors.linearize_DA(50, max_px), 0.50, rel_tol=1e-9)
    assert math.isclose(sensors.linearize_DA(75, max_px), 0.75, rel_tol=1e-9)


def test_sensor_config_angles_basic():
    """
    Prüft die reine Winkel-Konfiguration aus sensors.SENSOR:
    - 'angles_deg' existiert und ist eine Liste
    - Länge passt zu 'count'
    - keine doppelten Winkel (Eindeutigkeit)
    - 'max_px' ist positiv
    """
    angles = sensors.SENSOR.get("angles_deg", [])
    count  = sensors.SENSOR.get("count", len(angles))
    max_px = sensors.SENSOR.get("max_px", 0)

    # angles_deg sollte Liste sein und mit count zusammenpassen
    assert isinstance(angles, list)
    assert len(angles) == count

    # mindestens ein Winkel vorhanden
    assert len(angles) > 0

    # keine Duplikate (verhindert doppelte Strahlen in die gleiche Richtung)
    assert len(set(angles)) == len(angles)

    # sinnvolle Reichweite
    assert isinstance(max_px, (int, float)) and max_px > 0


def test_angle_to_direction_vector_math():
    """
    Reine Mathe-Kontrolle:
    Aus Winkel (Grad) muss ein erwartbarer Richtungsvektor (cos/sin) entstehen.
    Wir prüfen exemplarisch 0°, 90°, 180°, 270° mit Toleranz (Floating Point).
    Hinweis: Das testet NICHT das Raycasting, nur die Winkelinterpretation.
    """
    # (Winkel in Grad, erwarteter (cos, sin))
    cases = [
        (0,   (1.0,  0.0)),
        (90,  (0.0,  1.0)),
        (180, (-1.0, 0.0)),
        (270, (0.0, -1.0)),
    ]
    for deg, (ex_cos, ex_sin) in cases:
        r = math.radians(deg)
        assert math.isclose(math.cos(r), ex_cos, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(math.sin(r), ex_sin, rel_tol=1e-9, abs_tol=1e-9)


def test_sensor_angles_distribution_if_three():
    """
    Optionale Plausibilitätsprüfung:
    Falls genau 3 Sensorwinkel konfiguriert sind, erwarten wir eine
    monotone Sortierung und eine sinnvolle Öffnung (span > 0).
    (Greift NICHT in die Implementierung ein; dokumentiert nur Erwartung.)
    """
    angles = sensors.SENSOR.get("angles_deg", [])
    if len(angles) == 3:
        # sortiert (z. B. [-30, 0, +30]); wenn nicht sortiert, ist das kein Fail
        # in der Produktlogik, aber ein nützlicher Hinweis für Konsistenz.
        assert angles == sorted(angles)
        span = angles[-1] - angles[0]
        assert span > 0
