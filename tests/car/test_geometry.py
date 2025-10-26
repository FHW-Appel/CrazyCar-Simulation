# tests/car/test_geometry.py
import math
import pytest
pytestmark = pytest.mark.unit

from crazycar.car.geometry import compute_corners, compute_wheels

TOL = 1e-9

def _rot(point, center, deg):
    (cx, cy) = center
    x, y = point[0]-cx, point[1]-cy
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    xr, yr = x*c - y*s, x*s + y*c
    return (cx + xr, cy + yr)

def _diag(L, W):
    return math.hypot(L, W)

def _angles_from_center(center, pts):
    cx, cy = center
    out = []
    for (x, y) in pts:
        ang = (math.degrees(math.atan2(y-cy, x-cx)) % 360.0)
        out.append(ang)
    return out

# ------------------- Basis / Smoke -------------------

def test_corners_returns_four_points_and_finite():
    # GIVEN
    ctr = (10.0, -5.0)
    # WHEN
    pts = compute_corners(ctr, carangle=0.0, length=4.0, width=2.0)
    # THEN
    assert isinstance(pts, list) and len(pts) == 4
    for p in pts:
        assert math.isfinite(p[0]) and math.isfinite(p[1])

# ------------------- Eigenschaften passend zur Implementierung -------------------

def test_all_corners_have_same_radius_diag():
    # GIVEN
    ctr = (0.0, 0.0)
    L, W = 4.0, 2.0
    d = _diag(L, W)
    # WHEN / THEN
    for ang in [0.0, 30.0, 180.0, 359.0]:
        pts = compute_corners(ctr, carangle=ang, length=L, width=W)
        for x, y in pts:
            r = math.hypot(x-ctr[0], y-ctr[1])
            assert math.isclose(r, d, rel_tol=0, abs_tol=1e-12)

def test_rotation_covariance_matches_formula():
    # GIVEN
    ctr = (3.0, 4.0)
    L, W = 7.0, 3.0
    p0 = compute_corners(ctr, carangle=0.0, length=L, width=W)
    # WHEN
    a = 73.0
    pa = compute_corners(ctr, carangle=a, length=L, width=W)
    expected = [_rot(p, ctr, -a) for p in p0]  # deine Vorzeichenkonvention
    # THEN
    for (ex, ey), (ax, ay) in zip(expected, pa):
        assert math.isclose(ex, ax, abs_tol=1e-9)
        assert math.isclose(ey, ay, abs_tol=1e-9)

def test_full_circle_equals_zero():
    # GIVEN
    ctr = (0.0, 0.0)
    L, W = 5.0, 1.5
    # WHEN
    p0   = compute_corners(ctr, 0.0,  L, W)
    p360 = compute_corners(ctr, 360.0, L, W)
    # THEN
    for (a, b) in zip(p0, p360):
        assert math.isclose(a[0], b[0], abs_tol=TOL)
        assert math.isclose(a[1], b[1], abs_tol=TOL)

def test_centroid_equals_center_due_to_symmetry():
    # GIVEN
    ctr = (12.0, -8.0)
    L, W = 4.0, 2.0
    # WHEN
    pts = compute_corners(ctr, 123.0, L, W)
    mx = sum(p[0] for p in pts)/4.0
    my = sum(p[1] for p in pts)/4.0
    # THEN
    assert math.isclose(mx, ctr[0], abs_tol=1e-12)
    assert math.isclose(my, ctr[1], abs_tol=1e-12)

def test_corners_angles_match_expected_offsets_at_zero_angle():
    # GIVEN
    ctr = (0.0, 0.0)
    # WHEN
    pts = compute_corners(ctr, 0.0, length=5.0, width=2.0)
    angs = sorted(_angles_from_center(ctr, pts))
    # THEN (wegen implementiertem 23°-Offset)
    expected = sorted([(-23) % 360, (23) % 360, (157) % 360, (203) % 360])
    for a, b in zip(expected, angs):
        assert math.isclose(a, b, abs_tol=1e-9)

def test_corners_only_depend_on_diag_in_this_implementation():
    # GIVEN
    ctr = (1.0, 2.0)
    # Zwei Paare mit gleicher Diagonale
    L1, W1 = 4.0, 3.0  # diag = 5
    L2, W2 = 5.0, 0.0  # diag = 5
    # WHEN
    p1 = compute_corners(ctr, 33.0, L1, W1)
    p2 = compute_corners(ctr, 33.0, L2, W2)
    # THEN
    for (a, b) in zip(p1, p2):
        assert math.isclose(a[0], b[0], abs_tol=1e-9)
        assert math.isclose(a[1], b[1], abs_tol=1e-9)

# ------------------- Räder -------------------

def test_compute_wheels_positions_match_expected_directions():
    # GIVEN
    ctr = (0.0, 0.0)
    a = 75.0
    diag_minus = 42.5
    # WHEN
    wl, wr = compute_wheels(ctr, a, diag_minus)
    # THEN
    ang_l = (360.0 - (a + 23.0)) % 360.0
    ang_r = (360.0 - (a - 23.0)) % 360.0
    ex_l = (ctr[0] + math.cos(math.radians(ang_l))*diag_minus,
            ctr[1] + math.sin(math.radians(ang_l))*diag_minus)
    ex_r = (ctr[0] + math.cos(math.radians(ang_r))*diag_minus,
            ctr[1] + math.sin(math.radians(ang_r))*diag_minus)
    assert math.isclose(wl[0], ex_l[0], abs_tol=1e-9)
    assert math.isclose(wl[1], ex_l[1], abs_tol=1e-9)
    assert math.isclose(wr[0], ex_r[0], abs_tol=1e-9)
    assert math.isclose(wr[1], ex_r[1], abs_tol=1e-9)

# ------------------- Verträge (optional XFAIL) -------------------

@pytest.mark.xfail(reason="Negative L/W sind aktuell erlaubt – wenn untersagt, Exception werfen.", strict=False)
def test_negative_half_extents_xfail():
    # GIVEN / WHEN / THEN (xfail – aktuelle Implementierung erlaubt es)
    compute_corners((0, 0), 0.0, length=-1.0, width=2.0)

@pytest.mark.xfail(reason="Negative diag_minus sind aktuell erlaubt – wenn untersagt, Exception werfen.", strict=False)
def test_negative_diag_minus_xfail():
    # GIVEN / WHEN / THEN (xfail – aktuelle Implementierung erlaubt es)
    compute_wheels((0, 0), 0.0, diag_minus=-10.0)
