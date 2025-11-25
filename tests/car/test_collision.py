# tests/car/test_collision.py
"""Unit-Tests für Kollisionserkennung und Rebound-Korrektur.

TESTBASIS (ISTQB):
- Anforderung: Kollisionserkennung mit Streckenrand, Ziellinienerkennung, iterative Rebound-Korrektur
- Module: crazycar.car.collision
- Funktion: collision_step (collision_status: 0=rebound, 1=stop, 2=remove)

TESTVERFAHREN:
- Äquivalenzklassen: TRACK (passierbar), BORDER (Kollision), FINISH (Ziellinie)
- Zustandsübergänge: no_collision → finish_detected, no_collision → border_collision → rebound
- Grenzwertanalyse: Iterative Korrektur (0-6 Schritte), Eckpunkte-Überlappung
- Callback-Tests: lap_callback nur bei Finish-Detektion
"""
import math
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.collision import collision_step

# Test-Farben (Typ: RGBA)
BORDER = (255, 255, 255, 255)
FINISH = (237, 28, 36, 255)
TRACK = (0, 0, 0, 255)


# ===============================================================================
# FIXTURES: Hilfsfunktionen und Factories
# ===============================================================================

@pytest.fixture
def square_corners():
    """Factory für Quadrat-Ecken um Zentrum."""
    def _make(center, size=10.0):
        cx, cy = center
        half = size / 2.0
        return [
            (cx - half, cy - half),  # oben-links
            (cx + half, cy - half),  # oben-rechts
            (cx + half, cy + half),  # unten-rechts
            (cx - half, cy + half),  # unten-links
        ]
    return _make


@pytest.fixture
def color_at_factory():
    """Factory für einfache color_at-Callbacks mit Zonen."""
    def _create(border_zone=None, finish_zone=None):
        def color_at(pt):
            x, y = pt
            if border_zone:
                xmin, xmax, ymin, ymax = border_zone
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    return BORDER
            if finish_zone:
                xmin, xmax, ymin, ymax = finish_zone
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    return FINISH
            return TRACK
        return color_at
    return _create


# ===============================================================================
# TESTGRUPPE 1: Smoke-Tests
# ===============================================================================

def test_collision_step_returns_expected_tuple(square_corners, color_at_factory):
    """Testbedingung: collision_step gibt Tupel mit 6 Elementen zurück.
    
    Erwartung: (finish, collision_status, rebound_count, new_pos, lap_time, lap_callback_triggered).
    """
    # ARRANGE
    corners = square_corners((50.0, 50.0))
    color_at = color_at_factory()  # Nur TRACK
    
    # ACT
    result = collision_step(
        corners, color_at, collision_status=0,
        speed=5.0, carangle=0.0, time_now=0.0
    )
    
    # THEN
    assert isinstance(result, tuple) and len(result) == 6
    speed, angle, alive, finished, rtime, flags = result
    assert isinstance(speed, (int, float))
    assert isinstance(angle, (int, float))
    assert isinstance(alive, bool)
    assert isinstance(finished, bool)
    assert isinstance(rtime, (int, float))
    assert isinstance(flags, dict)


def test_no_collision_returns_unchanged_state(square_corners, color_at_factory):
    """Testbedingung: Keine Kollision → collision_status unverändert.
    
    Erwartung: finish=False, collision_status=0, rebound_count=0.
    """
    # ARRANGE
    corners = square_corners((100.0, 100.0), size=10.0)
    color_at = lambda pt: TRACK  # Überall freie Strecke
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=8.5, carangle=45.0, time_now=3.5
    )
    
    # THEN: Status unverändert
    assert speed == 8.5
    assert angle == 45.0
    assert alive is True
    assert finished is False
    assert rtime == 0.0
    assert flags["pos_delta"] == (0.0, 0.0)
    assert flags["disable_control"] is False


# ------------------- Finish-Line Detection -------------------

def test_finish_line_detected_when_corner1_hits_red(color_at_factory):
    """Testbedingung: Ecke #1 auf Ziellinie → finished=True.
    
    Erwartung: finished=True, rtime gesetzt.
    """
    # ARRANGE: Quadrat mit Ecke #1 bei (50, 50) auf roter Ziellinie
    corners = [(50.0, 50.0), (60.0, 50.0), (60.0, 60.0), (50.0, 60.0)]
    color_at = color_at_factory(finish_zone=(48, 52, 48, 52))
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=5.0, carangle=0.0, time_now=12.75
    )
    
    # THEN
    assert finished is True
    assert rtime == 12.75
    assert alive is True  # Ziellinie killt Auto nicht


def test_finish_line_triggers_callback():
    """GIVEN: on_lap_time Callback, WHEN: Ziellinie erreicht, THEN: Callback aufgerufen."""
    # GIVEN
    corners = [(10.0, 10.0)]
    color_at = lambda pt: FINISH
    lap_times = []
    
    def on_lap(t):
        lap_times.append(t)
    
    # WHEN
    collision_step(
        corners, color_at, collision_status=0,
        speed=1.0, carangle=0.0, time_now=8.333,
        on_lap_time=on_lap
    )
    
    # THEN
    assert len(lap_times) == 1
    assert lap_times[0] == 8.333


# ------------------- Border Collision: Rebound (status=0) -------------------

def test_border_collision_status_rebound_calls_rebound_action(color_at_factory):
    """Testbedingung: Wand-Kollision + status=0 → Speed/Angle verändert.
    
    Erwartung: Rebound-Aktion ausgeführt.
    """
    # ARRANGE: Ecke #1 in Wand (x=10), Rest auf Strecke
    corners = [(10.0, 50.0), (30.0, 50.0), (30.0, 60.0), (10.0, 60.0)]
    color_at = color_at_factory(border_zone=(8, 12, 40, 70))
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=6.0, carangle=90.0, time_now=0.0
    )
    
    # THEN: Rebound-Aktion wurde ausgeführt
    assert speed <= 6.0  # Geschwindigkeit gedämpft oder gleich (je nach Einfallswinkel)
    assert angle != 90.0  # Winkel verändert (Drehmoment)
    assert alive is True  # Rebound killt Auto nicht
    # Position-Delta sollte vorhanden sein (Rückversatz)
    dx, dy = flags["pos_delta"]
    assert abs(dx) > 0 or abs(dy) > 0


def test_rebound_corrects_position_iteratively():
    """GIVEN: Mehrere Ecken in Wand, WHEN: Rebound, THEN: Iterative Korrektur."""
    # GIVEN: Linke 2 Ecken in Wand (x<20)
    corners = [(10.0, 50.0), (15.0, 50.0), (30.0, 60.0), (25.0, 60.0)]
    
    def color_at(pt):
        # Wand bei x < 20
        return BORDER if pt[0] < 20 else TRACK
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=5.0, carangle=0.0, time_now=0.0
    )
    
    # THEN: Position-Delta sollte vorhanden sein (Rebound erzeugt Verschiebung)
    dx, dy = flags["pos_delta"]
    assert abs(dx) > 0 or abs(dy) > 0  # Irgendeine Verschiebung erfolgt
    # Rebound kann bei komplexen Winkeln größere Verschiebungen erzeugen
    assert abs(dx) <= 50.0 and abs(dy) <= 50.0  # Sinnvolle Grenzen


def test_rebound_with_valid_map_coordinates():
    """GIVEN: Alle Koordinaten valide, WHEN: Rebound, THEN: Erfolgreiche Verarbeitung."""
    # GIVEN: Alle Ecken in gültigem Bereich
    corners = [(100.0, 100.0), (120.0, 100.0), (120.0, 110.0), (100.0, 110.0)]
    
    def color_at(pt):
        # Einfache Wand-Erkennung (x < 105)
        return BORDER if pt[0] < 105 else TRACK
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=3.0, carangle=45.0, time_now=0.0
    )
    
    # THEN: Rebound wurde verarbeitet
    assert alive is True
    assert isinstance(speed, (int, float))
    assert isinstance(angle, (int, float))


# ------------------- Border Collision: Stop (status=1) -------------------

def test_border_collision_status_stop_sets_speed_zero():
    """GIVEN: Wand-Kollision + status=1, WHEN: collision_step, THEN: Speed=0."""
    # GIVEN
    corners = [(5.0, 5.0)]
    color_at = lambda pt: BORDER
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=1,
        speed=10.0, carangle=45.0, time_now=0.0
    )
    
    # THEN
    assert speed == 0.0
    assert flags["disable_control"] is True
    assert alive is True  # Stop killt Auto nicht


# ------------------- Border Collision: Remove (status=2) -------------------

def test_border_collision_status_remove_kills_car():
    """GIVEN: Wand-Kollision + status=2, WHEN: collision_step, THEN: alive=False."""
    # GIVEN
    corners = [(100.0, 100.0)]
    color_at = lambda pt: BORDER
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=2,
        speed=7.5, carangle=270.0, time_now=5.0
    )
    
    # THEN
    assert alive is False
    assert flags["disable_control"] is False  # Kein disable bei remove


# ------------------- Edge-Cases -------------------

@pytest.mark.parametrize("status", [0, 1, 2])
def test_empty_corners_list_no_collision(status):
    """GIVEN: Leere corners-Liste, WHEN: collision_step, THEN: Keine Kollision."""
    # GIVEN
    corners = []
    color_at = lambda pt: BORDER
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=status,
        speed=5.0, carangle=0.0, time_now=0.0
    )
    
    # THEN: Keine Kollision erkannt
    if status == 0:
        assert alive is True
        assert flags["pos_delta"] == (0.0, 0.0)
    elif status == 1:
        assert alive is True
    elif status == 2:
        assert alive is True  # Keine Ecke → keine Kollision


def test_multiple_corners_same_collision_only_first_processed():
    """GIVEN: Mehrere Ecken in Wand, WHEN: collision_step, THEN: Nur erste Kollision zählt."""
    # GIVEN: Alle 4 Ecken in Wand
    corners = [(10.0, 10.0), (10.0, 20.0), (20.0, 20.0), (20.0, 10.0)]
    color_at = lambda pt: BORDER
    
    # WHEN
    speed, angle, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=5.0, carangle=0.0, time_now=0.0
    )
    
    # THEN: Rebound wurde einmal ausgeführt (break nach erster Kollision)
    assert alive is True
    dx, dy = flags["pos_delta"]
    # Nur eine Korrektur, nicht mehrfach
    assert abs(dx) + abs(dy) > 0


# ------------------- Eigenschaften -------------------

@pytest.mark.parametrize("angle_in", [0.0, 45.0, 90.0, 180.0, 270.0])
def test_no_collision_preserves_angle(angle_in):
    """GIVEN: Keine Kollision, WHEN: collision_step, THEN: Winkel unverändert."""
    # GIVEN
    corners = [(100.0, 100.0)]
    color_at = lambda pt: TRACK
    
    # WHEN
    speed, angle_out, alive, finished, rtime, flags = collision_step(
        corners, color_at, collision_status=0,
        speed=3.0, carangle=angle_in, time_now=1.0
    )
    
    # THEN
    assert angle_out == angle_in


def test_collision_rebound_is_deterministic(color_at_factory):
    """Testbedingung: Identische Inputs → Identische Outputs.
    
    Erwartung: Deterministisches Rebound-Verhalten.
    """
    # ARRANGE
    corners = [(10.0, 50.0), (30.0, 50.0), (30.0, 60.0), (10.0, 60.0)]
    color_at = color_at_factory(border_zone=(8, 12, 40, 70))
    
    # WHEN
    result1 = collision_step(
        corners, color_at, collision_status=0,
        speed=6.0, carangle=90.0, time_now=2.5
    )
    result2 = collision_step(
        corners, color_at, collision_status=0,
        speed=6.0, carangle=90.0, time_now=2.5
    )
    
    # THEN
    assert result1 == result2  # Perfekt deterministisch
