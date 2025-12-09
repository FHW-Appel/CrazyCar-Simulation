# tests/car/test_geometry.py
"""Unit-Tests für Fahrzeug-Geometrie (Ecken, Räder).

TESTBASIS (ISTQB):
- Anforderung: Präzise Geometrie-Berechnung für Kollisionserkennung
- Module: crazycar.car.geometry
- Funktionen: compute_corners (4 Ecken), compute_wheels (2 Radpositionen)

TESTVERFAHREN:
- Eigenschaften: Rotationsinvarianz, symmetrische Verteilung um Zentrum
- Grenzwertanalyse: angle=0°, 360°, negative L/W (xfail)
- Mathematische Invarianten: Konstanter Radius (Diagonale), Zentroid=Center
"""
import math
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.geometry import compute_corners, compute_wheels

TOL = 1e-9


# ===============================================================================
# FIXTURES: Geometrie-Hilfsfunktionen
# ===============================================================================

@pytest.fixture
def geometry_helpers():
    """Sammlung geometrischer Hilfsfunktionen für Tests."""
    def _rot(point, center, deg):
        """Rotiert Punkt um Zentrum."""
        (cx, cy) = center
        x, y = point[0] - cx, point[1] - cy
        rad = math.radians(deg)
        c, s = math.cos(rad), math.sin(rad)
        xr, yr = x * c - y * s, x * s + y * c
        return (cx + xr, cy + yr)
    
    def _diag(L, W):
        """Berechnet Diagonale."""
        return math.hypot(L, W)
    
    def _angles_from_center(center, pts):
        """Berechnet Winkel aller Punkte vom Zentrum."""
        cx, cy = center
        return [(math.degrees(math.atan2(y - cy, x - cx)) % 360.0) 
                for (x, y) in pts]
    
    class Helpers:
        rot = staticmethod(_rot)
        diag = staticmethod(_diag)
        angles_from_center = staticmethod(_angles_from_center)
    
    return Helpers()


# ===============================================================================
# TESTGRUPPE 1: compute_corners - Basis-Funktionalität
# ===============================================================================


def test_corners_returns_four_finite_points():
    """Testbedingung: compute_corners liefert 4 Eckpunkte (Smoke-Test).
    
    Erwartung: Liste mit 4 Tupeln, alle Koordinaten finit.
    """
    # ARRANGE
    ctr = (10.0, -5.0)
    
    # ACT
    pts = compute_corners(ctr, carangle=0.0, length=4.0, width=2.0)
    
    # ASSERT
    assert isinstance(pts, list) and len(pts) == 4
    for p in pts:
        assert math.isfinite(p[0]) and math.isfinite(p[1])


# ===============================================================================
# TESTGRUPPE 2: Mathematische Eigenschaften
# ===============================================================================

@pytest.mark.parametrize("angle", [0.0, 30.0, 180.0, 359.0])
def test_all_corners_have_same_radius_diag(geometry_helpers, angle):
    """Testbedingung: Alle Ecken haben konstanten Abstand (Diagonale) zum Zentrum.
    
    Erwartung: radius = hypot(length, width) für alle 4 Ecken.
    """
    # ARRANGE
    ctr = (0.0, 0.0)
    L, W = 4.0, 2.0
    d = geometry_helpers.diag(L, W)
    
    # ACT
    pts = compute_corners(ctr, carangle=angle, length=L, width=W)
    
    # ASSERT
    for x, y in pts:
        r = math.hypot(x - ctr[0], y - ctr[1])
        assert math.isclose(r, d, abs_tol=1e-12)

def test_rotation_covariance_matches_formula(geometry_helpers):
    """Testbedingung: Rotation um angle verhält sich wie mathematische Drehmatrix.
    
    Erwartung: compute_corners(angle=a) ≡ rotate(compute_corners(0°), -a).
    """
    # ARRANGE
    ctr = (3.0, 4.0)
    L, W = 7.0, 3.0
    p0 = compute_corners(ctr, carangle=0.0, length=L, width=W)
    a = 73.0
    
    # ACT
    pa = compute_corners(ctr, carangle=a, length=L, width=W)
    expected = [geometry_helpers.rot(p, ctr, -a) for p in p0]
    
    # ASSERT
    for (ex, ey), (ax, ay) in zip(expected, pa):
        assert math.isclose(ex, ax, abs_tol=1e-9)
        assert math.isclose(ey, ay, abs_tol=1e-9)


def test_full_circle_equals_zero():
    """Testbedingung: angle=0° und angle=360° sind äquivalent (Grenzwert).
    
    Erwartung: Identische Eckpunkte.
    """
    # ARRANGE
    ctr = (0.0, 0.0)
    L, W = 5.0, 1.5
    
    # ACT
    p0 = compute_corners(ctr, 0.0, L, W)
    p360 = compute_corners(ctr, 360.0, L, W)
    
    # ASSERT
    for (a, b) in zip(p0, p360):
        assert math.isclose(a[0], b[0], abs_tol=TOL)
        assert math.isclose(a[1], b[1], abs_tol=TOL)


def test_centroid_equals_center_due_to_symmetry():
    """Testbedingung: Schwerpunkt der 4 Ecken = Zentrum (Symmetrie).
    
    Erwartung: mean(corners) = center für beliebigen Winkel.
    """
    # ARRANGE
    ctr = (12.0, -8.0)
    L, W = 4.0, 2.0
    
    # ACT
    pts = compute_corners(ctr, 123.0, L, W)
    mx = sum(p[0] for p in pts) / 4.0
    my = sum(p[1] for p in pts) / 4.0
    
    # ASSERT
    assert math.isclose(mx, ctr[0], abs_tol=1e-12)
    assert math.isclose(my, ctr[1], abs_tol=1e-12)

def test_corners_angles_match_expected_offsets_at_zero_angle(geometry_helpers):
    """Testbedingung: Bei angle=0° liegen Ecken bei ±23° und 157°/203° (Implementierung).
    
    Erwartung: Spezifischer 23°-Offset der Implementierung.
    """
    # ARRANGE
    ctr = (0.0, 0.0)
    
    # ACT
    pts = compute_corners(ctr, 0.0, length=5.0, width=2.0)
    angs = sorted(geometry_helpers.angles_from_center(ctr, pts))
    
    # ASSERT: Implementierungsspezifischer 23°-Offset
    expected = sorted([(-23) % 360, (23) % 360, (157) % 360, (203) % 360])
    for a, b in zip(expected, angs):
        assert math.isclose(a, b, abs_tol=1e-9)


def test_corners_only_depend_on_diag_in_this_implementation():
    """Testbedingung: Implementierung nutzt nur Diagonale, nicht L/W einzeln.
    
    Erwartung: Gleiche Diagonale → identische Eckpunkte.
    """
    # ARRANGE: Zwei Paare mit gleicher Diagonale
    ctr = (1.0, 2.0)
    L1, W1 = 4.0, 3.0  # diag = 5
    L2, W2 = 5.0, 0.0  # diag = 5
    
    # ACT
    p1 = compute_corners(ctr, 33.0, L1, W1)
    p2 = compute_corners(ctr, 33.0, L2, W2)
    
    # ASSERT
    for (a, b) in zip(p1, p2):
        assert math.isclose(a[0], b[0], abs_tol=1e-9)
        assert math.isclose(a[1], b[1], abs_tol=1e-9)


# ===============================================================================
# TESTGRUPPE 3: compute_wheels - Radpositionen
# ===============================================================================

def test_compute_wheels_positions_match_expected_directions():
    """Testbedingung: Räder liegen bei ±23° Offset (Implementierung).
    
    Erwartung: Links/Rechts-Rad bei korrekten Winkeln.
    """
    # ARRANGE
    ctr = (0.0, 0.0)
    a = 75.0
    diag_minus = 42.5
    
    # ACT
    wl, wr = compute_wheels(ctr, a, diag_minus)
    
    # ASSERT: Erwartete Winkel (360° - (a ± 23°))
    ang_l = (360.0 - (a + 23.0)) % 360.0
    ang_r = (360.0 - (a - 23.0)) % 360.0
    ex_l = (ctr[0] + math.cos(math.radians(ang_l)) * diag_minus,
            ctr[1] + math.sin(math.radians(ang_l)) * diag_minus)
    ex_r = (ctr[0] + math.cos(math.radians(ang_r)) * diag_minus,
            ctr[1] + math.sin(math.radians(ang_r)) * diag_minus)
    
    assert math.isclose(wl[0], ex_l[0], abs_tol=1e-9)
    assert math.isclose(wl[1], ex_l[1], abs_tol=1e-9)
    assert math.isclose(wr[0], ex_r[0], abs_tol=1e-9)
    assert math.isclose(wr[1], ex_r[1], abs_tol=1e-9)


# ===============================================================================
# TESTGRUPPE 4: Verträge (xfail - zukünftige Validierung)
# ===============================================================================

@pytest.mark.xfail(reason="Negative L/W erlaubt – bei Validierung Exception werfen", strict=False)
def test_negative_half_extents_xfail():
    """Testbedingung: Negative Abmessungen → ValueError (zukünftig).
    
    Erwartung: Aktuell erlaubt, sollte aber validiert werden.
    """
    # ACT/ASSERT (xfail)
    compute_corners((0, 0), 0.0, length=-1.0, width=2.0)


@pytest.mark.xfail(reason="Negative diag_minus erlaubt – bei Validierung Exception werfen", strict=False)
def test_negative_diag_minus_xfail():
    """Testbedingung: Negative diag_minus → ValueError (zukünftig).
    
    Erwartung: Aktuell erlaubt, sollte aber validiert werden.
    """
    # ACT/ASSERT (xfail)
    compute_wheels((0, 0), 0.0, diag_minus=-10.0)
