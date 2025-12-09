# tests/car/test_kinematics.py
"""Unit-Tests für Kinematik (Winkel-Normalisierung, Ackermann-Lenkung).

TESTBASIS (ISTQB):
- Anforderung: Präzise Fahrzeugkinematik für realistische Bewegung
- Module: crazycar.car.kinematics
- Funktionen: normalize_angle (Winkel [0°, 360°)), steer_step (Ackermann-Geometrie)

TESTVERFAHREN:
- Äquivalenzklassen: Winkel <0, [0,360), ≥360; Lenkwinkel positiv/negativ/null
- Grenzwertanalyse: 0°, 360°, 720°, Lenkwinkel-Clamp bei ±89°
- Kinematische Invarianten: Kurvenradius, Drehraten
"""
import math
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.kinematics import normalize_angle, steer_step

TOL = 1e-9


# ===============================================================================
# FIXTURES: Ackermann-Geometrie Referenzimplementierung
# ===============================================================================

@pytest.fixture
def ackermann_reference():
    """Referenzimplementierung für steer_step (mit Clamp 89°)."""
    def _expected_step(carangle_deg, radangle_deg, speed_px, L, W):
        angle0 = float(carangle_deg)
        if abs(radangle_deg) < 1e-6 or abs(speed_px) < 1e-6:
            return normalize_angle(angle0)
        
        a = float(radangle_deg)
        if abs(a) > 89.0:
            a = math.copysign(89.0, a)
        
        k0 = -1.0 if a < 0.0 else 1.0
        tanv = math.tan(math.radians(abs(a)))
        if abs(tanv) < 1e-6:
            return normalize_angle(angle0)
        
        R = (float(L) / tanv) + (float(W) / 2.0)
        if abs(R) < 1e-6 or math.isnan(R) or math.isinf(R):
            return normalize_angle(angle0)
        
        dtheta_rad = float(speed_px) / R
        dtheta_deg = math.degrees(dtheta_rad)
        new_angle = angle0 + (k0 * dtheta_deg if speed_px > 0.0 else -k0 * dtheta_deg)
        return normalize_angle(new_angle)
    
    return _expected_step


# ===============================================================================
# TESTGRUPPE 1: normalize_angle - Winkel-Normalisierung [0°, 360°)
# ===============================================================================
# Testbedingung: Beliebiger Winkel → Bereich [0°, 360°)
# Äquivalenzklassen: negativ, [0,360), ≥360, Vielfache von 360°

@pytest.mark.parametrize("inp, exp", [
    (0.0, 0.0),              # Grenzwert: Minimum
    (360.0, 0.0),            # Grenzwert: volle Drehung
    (720.0, 0.0),            # 2× Drehung
    (721.0, 1.0),            # 2× + 1°
    (-1.0, 359.0),           # Negativ → Wrap-Around
    (45.5, 45.5),            # Normalfall innerhalb Range
    (-707.7, 12.3),          # Mehrfach negativ
])
def test_normalize_angle_maps_to_valid_range(inp, exp):
    """Testbedingung: Beliebiger Winkel wird auf [0°, 360°) normalisiert.
    
    Erwartung: Ausgabe im gültigen Bereich, mathematisch äquivalenter Winkel.
    """
    # ACT
    out = normalize_angle(inp)
    
    # ASSERT
    assert 0.0 <= out < 360.0, "Winkel muss in [0, 360) liegen"
    assert math.isclose(out, exp, abs_tol=1e-12)



# ===============================================================================
# TESTGRUPPE 2: steer_step - Ackermann-Lenkung
# ===============================================================================
# TESTBASIS: Ackermann-Lenkgeometrie mit Kurvenradius R = L/tan(α) + W/2
# Testbedingungen:
#   - No-Op: radangle=0 oder speed=0 → keine Winkeländerung
#   - Vorwärts vs Rückwärts: speed-Vorzeichen invertiert Drehrichtung
#   - Clamp: |radangle| > 89° → auf ±89° begrenzt
# Grenzwertanalyse: radangle=0, ±89°, ±120°

@pytest.mark.parametrize("rad, spd", [(0.0, 10.0), (1e-12, 10.0), (10.0, 0.0)])
def test_steer_step_noop_conditions(rad, spd, ackermann_reference):
    """Testbedingung: radangle≈0 oder speed≈0 → keine Lenkwirkung.
    
    Erwartung: carangle bleibt unverändert (normalisiert).
    """
    # ARRANGE
    args = dict(carangle_deg=123.4, radangle_deg=rad, speed_px=spd, 
                radstand_px=100.0, spurweite_px=50.0)
    
    # ACT
    out = steer_step(**args)
    
    # ASSERT
    exp = ackermann_reference(123.4, rad, spd, 100.0, 50.0)
    assert math.isclose(out, exp, abs_tol=1e-12)


def test_steer_step_forward_positive_vs_negative_steer(ackermann_reference):
    """Testbedingung: Vorwärtsfahrt mit positivem/negativem Lenkwinkel.
    
    Erwartung: Unterschiedliche Winkeländerungen (Links-/Rechtskurve).
    """
    # ARRANGE
    L, W, spd, a0 = 100.0, 50.0, 10.0, 0.0
    
    # ACT
    out_pos = steer_step(a0, radangle_deg=+10.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    out_neg = steer_step(a0, radangle_deg=-10.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    
    # ASSERT
    exp_pos = ackermann_reference(a0, +10.0, spd, L, W)
    exp_neg = ackermann_reference(a0, -10.0, spd, L, W)
    assert math.isclose(out_pos, exp_pos, abs_tol=1e-9)
    assert math.isclose(out_neg, exp_neg, abs_tol=1e-9)


def test_steer_step_backward_inverts_direction(ackermann_reference):
    """Testbedingung: Rückwärtsfahrt (speed<0) → invertierte Lenkung.
    
    Erwartung: Winkeländerung mit umgekehrtem Vorzeichen.
    """
    # ARRANGE
    L, W, spd, a0 = 120.0, 40.0, -8.0, 30.0
    
    # ACT
    out = steer_step(a0, radangle_deg=15.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    
    # ASSERT
    exp = ackermann_reference(a0, 15.0, spd, L, W)
    assert math.isclose(out, exp, abs_tol=1e-9)


@pytest.mark.parametrize("steer_small, steer_big", [(5.0, 10.0), (7.5, 20.0)])
def test_turn_amount_monotone_in_abs_steer(steer_small, steer_big):
    """Testbedingung: Größerer Lenkwinkel → größere Winkeländerung (Monotonie).
    
    Erwartung: Winkelabstand wächst mit |radangle|.
    """
    # ARRANGE
    L, W, spd, a0 = 100.0, 60.0, 12.0, 0.0
    
    # ACT
    o_small = steer_step(a0, steer_small, spd, L, W)
    o_big = steer_step(a0, steer_big, spd, L, W)
    
    # ASSERT: Winkelabstände auf dem Kreis
    d_small = min((o_small - a0) % 360, (a0 - o_small) % 360)
    d_big = min((o_big - a0) % 360, (a0 - o_big) % 360)
    assert d_big > d_small


def test_steer_step_clamps_extreme_steer_for_numerical_safety(ackermann_reference):
    """Testbedingung: |radangle| > 89° → Clamp auf ±89° (Grenzwert).
    
    Erwartung: Vermeidung von tan(90°) = inf.
    """
    # ARRANGE
    L, W, spd, a0 = 90.0, 55.0, 7.0, 270.0
    
    # ACT
    out = steer_step(a0, radangle_deg=120.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    
    # ASSERT: Clamp auf 89° wird erwartet
    exp = ackermann_reference(a0, 89.0, spd, L, W)
    assert math.isclose(out, exp, abs_tol=1e-9)


def test_steer_step_is_finite_and_in_range():
    """Testbedingung: Ausgabe immer finit und normalisiert [0°, 360°).
    
    Erwartung: Keine NaN/Inf, gültiger Winkelbereich.
    """
    # ARRANGE
    L, W, spd, a0 = 100.0, 50.0, 15.0, 359.5
    
    # ACT
    out = steer_step(a0, 12.0, spd, L, W)
    
    # ASSERT
    assert 0.0 <= out < 360.0
    assert math.isfinite(out)
