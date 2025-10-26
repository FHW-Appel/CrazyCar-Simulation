# tests/car/test_kinematics.py
import math
import pytest
pytestmark = pytest.mark.unit

from crazycar.car.kinematics import normalize_angle, steer_step

TOL = 1e-9

# ------------------- normalize_angle -------------------

@pytest.mark.parametrize(
    "inp,exp",
    [
        (0.0, 0.0),
        (360.0, 0.0),
        (720.0, 0.0),
        (721.0, 1.0),
        (-1.0, 359.0),
        (45.5, 45.5),
        (-720.0 + 12.3, 12.3),
    ],
)
def test_normalize_angle_range(inp, exp):
    # GIVEN
    angle = inp
    # WHEN
    out = normalize_angle(angle)
    # THEN
    assert 0.0 <= out < 360.0
    assert math.isclose(out, exp, abs_tol=1e-12)

# ------------------- steer_step -------------------

def _expected_step(carangle_deg, radangle_deg, speed_px, L, W):
    # Repliziert die Gleichungen aus dem Code (inkl. Clamp 89°).
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
    R = (float(L) / tanv) + (float(W)/2.0)
    if abs(R) < 1e-6 or math.isnan(R) or math.isinf(R):
        return normalize_angle(angle0)
    dtheta_rad = float(speed_px) / R
    dtheta_deg = math.degrees(dtheta_rad)
    new_angle = angle0 + (k0 * dtheta_deg if speed_px > 0.0 else -k0 * dtheta_deg)
    return normalize_angle(new_angle)

@pytest.mark.parametrize("rad,spd", [(0.0, 10.0), (1e-12, 10.0), (10.0, 0.0)])
def test_steer_step_noop_conditions(rad, spd):
    # GIVEN
    args = dict(carangle_deg=123.4, radangle_deg=rad, speed_px=spd, radstand_px=100.0, spurweite_px=50.0)
    # WHEN
    out = steer_step(**args)
    # THEN
    exp = _expected_step(123.4, rad, spd, 100.0, 50.0)
    assert math.isclose(out, exp, abs_tol=1e-12)

def test_steer_step_forward_positive_vs_negative_steer():
    # GIVEN
    L, W = 100.0, 50.0
    spd = 10.0
    a0 = 0.0
    # WHEN
    out_pos = steer_step(a0, radangle_deg=+10.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    out_neg = steer_step(a0, radangle_deg=-10.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    # THEN
    exp_pos = _expected_step(a0, +10.0, spd, L, W)
    exp_neg = _expected_step(a0, -10.0, spd, L, W)
    assert math.isclose(out_pos, exp_pos, abs_tol=1e-9)
    assert math.isclose(out_neg, exp_neg, abs_tol=1e-9)

def test_steer_step_backward_inverts_direction():
    # GIVEN
    L, W = 120.0, 40.0
    spd = -8.0
    a0 = 30.0
    # WHEN
    out = steer_step(a0, radangle_deg=15.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    # THEN
    exp = _expected_step(a0, 15.0, spd, L, W)
    assert math.isclose(out, exp, abs_tol=1e-9)

@pytest.mark.parametrize("steer_small, steer_big", [(5.0, 10.0), (7.5, 20.0)])
def test_turn_amount_monotone_in_abs_steer(steer_small, steer_big):
    # GIVEN
    L, W, spd = 100.0, 60.0, 12.0
    a0 = 0.0
    # WHEN
    o_small = steer_step(a0, steer_small, spd, L, W)
    o_big   = steer_step(a0, steer_big,   spd, L, W)
    # THEN (Winkelabstände auf dem Kreis)
    d_small = min((o_small - a0) % 360, (a0 - o_small) % 360)
    d_big   = min((o_big   - a0) % 360, (a0 - o_big)   % 360)
    assert d_big > d_small

def test_steer_step_clamps_extreme_steer_for_numerical_safety():
    # GIVEN
    L, W, spd, a0 = 90.0, 55.0, 7.0, 270.0
    # WHEN
    out = steer_step(a0, radangle_deg=120.0, speed_px=spd, radstand_px=L, spurweite_px=W)
    # THEN (Clamp auf 89° wird erwartet)
    exp = _expected_step(a0, 89.0, spd, L, W)
    assert math.isclose(out, exp, abs_tol=1e-9)

def test_steer_step_is_finite_and_in_range():
    # GIVEN
    L, W, spd, a0 = 100.0, 50.0, 15.0, 359.5
    # WHEN
    out = steer_step(a0, 12.0, spd, L, W)
    # THEN
    assert 0.0 <= out < 360.0
    assert math.isfinite(out)
