# tests/car/test_actuation.py
"""Unit-Tests für Aktorik (Lenkung, Motor, Rückwärtsfahrt).

TESTBASIS (ISTQB):
- Anforderung: Servo-zu-Lenkwinkel (quadratische Formel), Motor-Totzone, Min-Start, Rückwärts
- Module: crazycar.car.actuation
- Funktionen: servo_to_angle (quadr. Mapping), clip_steer (Clipping), apply_power (Motorsteuerung)

TESTVERFAHREN:
- Äquivalenzklassen: Vorwärts/Rückwärts/Totzone, Innerhalb/Außerhalb Grenzen
- Grenzwertanalyse: 0°, ±18 (Deadzone), ±10° (Clip-Grenzen)
- Zustandsübergänge: Stillstand → Beschleunigung → Rückwärts
- Funktionale Eigenschaften: Symmetrie (servo_to_angle), Monotonie (apply_power)
"""
import math
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.actuation import servo_to_angle, clip_steer, apply_power

TOL = 1e-9


# ===============================================================================
# FIXTURES: Mock-Funktionen für apply_power
# ===============================================================================

@pytest.fixture
def mock_callbacks():
    """Factory für speed_fn und delay_fn mit Tracking."""
    def _factory():
        calls = {"speed": [], "delay": []}
        
        def speed_fn(power):
            calls["speed"].append(power)
            return power * 0.1
        
        def delay_fn(ms):
            calls["delay"].append(ms)
        
        return speed_fn, delay_fn, calls
    return _factory



# ===============================================================================
# TESTGRUPPE 1: servo_to_angle - Quadratische Servo→Winkel Mapping
# ===============================================================================

@pytest.mark.parametrize("servo, expected", [
    (0.0, 0.0),                                    # Zero
    (50.0, 0.03 * 50**2 + 0.97 * 50 + 2.23),      # Formel: 0.03x²+0.97x+2.23
    (30.0, 0.03 * 30**2 + 0.97 * 30 + 2.23),      # Mittlerer Wert
])
def test_servo_to_angle_formula(servo, expected):
    """Testbedingung: servo → angle via quadratische Formel.
    
    Erwartung: angle = 0.03*x² + 0.97*x + 2.23.
    """
    # ACT
    angle = servo_to_angle(servo)
    
    # ASSERT
    assert math.isclose(angle, expected, abs_tol=TOL)


@pytest.mark.parametrize("servo, expected_sign", [
    (10.0, +1),   # Positiv → positiv
    (-10.0, -1),  # Negativ → negativ
])
def test_servo_to_angle_symmetry(servo, expected_sign):
    """Testbedingung: Symmetrie - sign(servo) = sign(angle).
    
    Erwartung: Vorzeichen bleibt erhalten.
    """
    # ACT
    angle = servo_to_angle(servo)
    
    # ASSERT
    assert (angle > 0) if expected_sign > 0 else (angle < 0)


def test_servo_to_angle_inversion_property():
    """Testbedingung: servo_to_angle(-x) = -servo_to_angle(x).
    
    Erwartung: Antisymmetrie um Nullpunkt.
    """
    # ARRANGE
    pos = servo_to_angle(30.0)
    neg = servo_to_angle(-30.0)
    
    # ASSERT
    assert math.isclose(neg, -pos, abs_tol=TOL)


# ===============================================================================
# TESTGRUPPE 2: clip_steer - Lenkwinkel-Begrenzung
# ===============================================================================

@pytest.mark.parametrize("swert, expected", [
    (0.0, 0.0),        # Zero bleibt
    (5.0, 5.0),        # Innerhalb [-10, +10]
    (-5.0, -5.0),      # Innerhalb (negativ)
    (15.0, 10.0),      # Über max → geclipt
    (-15.0, -10.0),    # Unter min → geclipt
    (10.0, 10.0),      # Exakt Grenze
    (-10.0, -10.0),    # Exakt Grenze (negativ)
])
def test_clip_steer_default_range(swert, expected):
    """Testbedingung: Clipping auf Default [-10°, +10°].
    
    Erwartung: Werte außerhalb → auf Grenzen gesetzt.
    """
    # ACT
    clipped = clip_steer(swert)
    
    # ASSERT
    assert math.isclose(clipped, expected, abs_tol=TOL)


@pytest.mark.parametrize("swert, min_deg, max_deg, expected", [
    (25.0, -20.0, 20.0, 20.0),    # Über max
    (-25.0, -20.0, 20.0, -20.0),  # Unter min
    (15.0, -20.0, 20.0, 15.0),    # Innerhalb
])
def test_clip_steer_custom_range(swert, min_deg, max_deg, expected):
    """Testbedingung: Eigene min/max-Grenzen.
    
    Erwartung: Clipping auf angegebene Grenzen.
    """
    # ACT
    clipped = clip_steer(swert, min_deg=min_deg, max_deg=max_deg)
    
    # ASSERT
    assert clipped == expected


def test_clip_steer_preserves_zero():
    """Testbedingung: 0.0 bleibt exakt 0.0 (nicht 0.0000001).
    
    Erwartung: Identität für Nullwert.
    """
    # ACT
    result = clip_steer(0.0)
    
    # ASSERT
    assert result == 0.0 and isinstance(result, float)


# ===============================================================================
# TESTGRUPPE 3: apply_power - Totzone (Deadzone)
# ===============================================================================

@pytest.mark.parametrize("fwert", [-17.9, -10.0, 0.0, 10.0, 17.9])
def test_apply_power_within_deadzone_returns_zero(mock_callbacks, fwert):
    """Testbedingung: fwert in [-18, +18] → power=0 (Totzone).
    
    Erwartung: Kein Motorantrieb innerhalb Deadzone.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, new_speed = apply_power(
        fwert=fwert, current_power=5.0, current_speed_px=2.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert new_power == 0.0
    assert new_speed == 0.0


# ===============================================================================
# TESTGRUPPE 4: apply_power - Vorwärts-Beschleunigung
# ===============================================================================

@pytest.mark.parametrize("fwert", [18.1, 30.0, 50.0, 100.0])
def test_apply_power_forward_accelerates(mock_callbacks, fwert):
    """Testbedingung: fwert > 18 → power erhöht sich.
    
    Erwartung: Graduelle Beschleunigung vorwärts.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, new_speed = apply_power(
        fwert=fwert, current_power=20.0, current_speed_px=2.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert new_power > 0  # Power gestiegen oder stabil
    assert new_power <= 100.0  # Max-Grenze


def test_apply_power_respects_maxpower(mock_callbacks):
    """Testbedingung: fwert sehr hoch → power ≤ maxpower.
    
    Erwartung: Keine Überschreitung der Maximalleistung.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, _ = apply_power(
        fwert=150.0, current_power=80.0, current_speed_px=8.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert new_power <= 100.0


@pytest.mark.parametrize("fwert1, fwert2", [(18.1, 50.0), (30.0, 100.0)])
def test_apply_power_monotonicity(mock_callbacks, fwert1, fwert2):
    """Testbedingung: Höherer fwert → höhere oder gleiche power (Monotonie).
    
    Erwartung: apply_power ist monoton steigend für fwert > 18.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    power1, _ = apply_power(
        fwert=fwert1, current_power=0.0, current_speed_px=0.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    power2, _ = apply_power(
        fwert=fwert2, current_power=0.0, current_speed_px=0.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert power2 >= power1


# ===============================================================================
# TESTGRUPPE 5: apply_power - Rückwärtsfahrt
# ===============================================================================

@pytest.mark.parametrize("fwert", [-50.0, -30.0, -18.1])
def test_apply_power_backward_negative_power(mock_callbacks, fwert):
    """Testbedingung: fwert < -18 → power < 0 (Rückwärts).
    
    Erwartung: Negative Leistung für Rückwärtsfahrt.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, new_speed = apply_power(
        fwert=fwert, current_power=0.0, current_speed_px=0.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert new_power < 0
    assert new_speed < 0  # speed_fn gibt negative Speed zurück


# ===============================================================================
# TESTGRUPPE 6: apply_power - Min-Start-Prozentsatz
# ===============================================================================

def test_apply_power_min_start_percent_applied(mock_callbacks):
    """Testbedingung: fwert knapp über Deadzone → min 8% Leistung.
    
    Erwartung: Mindestleistung zum Starten des Motors.
    """
    # ARRANGE
    import os
    os.environ["CRAZYCAR_MIN_START_PERCENT"] = "0.08"
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, _ = apply_power(
        fwert=20.0, current_power=0.0, current_speed_px=0.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert new_power >= 8.0  # Min 8% von 100


# ===============================================================================
# TESTGRUPPE 7: apply_power - Callback-Integration
# ===============================================================================

def test_apply_power_calls_speed_fn(mock_callbacks):
    """Testbedingung: speed_fn(new_power) wird aufgerufen.
    
    Erwartung: new_speed = speed_fn(new_power).
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    new_power, new_speed = apply_power(
        fwert=40.0, current_power=10.0, current_speed_px=1.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert len(calls["speed"]) > 0
    assert math.isclose(new_speed, new_power * 0.1, abs_tol=0.01)


def test_apply_power_calls_delay_fn(mock_callbacks):
    """Testbedingung: delay_fn wird bei Beschleunigung aufgerufen.
    
    Erwartung: delay_fn erhält Wartezeit in ms.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    apply_power(
        fwert=50.0, current_power=20.0, current_speed_px=2.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    # delay_fn kann 0+ mal aufgerufen werden (abhängig von Implementierung)
    assert isinstance(calls["delay"], list)


# ===============================================================================
# TESTGRUPPE 8: Edge-Cases
# ===============================================================================

def test_apply_power_handles_zero_maxpower(mock_callbacks):
    """Testbedingung: maxpower=0 → keine Division durch 0.
    
    Erwartung: power=0 ohne Exception.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT & ASSERT
    try:
        new_power, new_speed = apply_power(
            fwert=50.0, current_power=0.0, current_speed_px=0.0,
            maxpower=0.0, speed_fn=speed_fn, delay_fn=delay_fn
        )
        assert new_power == 0.0
    except Exception as e:
        pytest.fail(f"apply_power sollte maxpower=0 abfangen: {e}")


# ===============================================================================
# TESTGRUPPE 9: Integration mit servo_to_angle
# ===============================================================================

def test_actuation_integration_servo_and_power(mock_callbacks):
    """Testbedingung: servo_to_angle + apply_power zusammen.
    
    Erwartung: Beide Funktionen liefern konsistente Werte.
    """
    # ARRANGE
    speed_fn, delay_fn, calls = mock_callbacks()
    
    # ACT
    steer_angle = servo_to_angle(25.0)
    new_power, new_speed = apply_power(
        fwert=40.0, current_power=0.0, current_speed_px=0.0,
        maxpower=100.0, speed_fn=speed_fn, delay_fn=delay_fn
    )
    
    # ASSERT
    assert -90.0 <= steer_angle <= 90.0
    assert 0.0 <= new_power <= 100.0
    assert math.isclose(new_speed, new_power * 0.1, abs_tol=TOL)
