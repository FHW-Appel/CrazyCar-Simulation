# tests/car/test_sensor.py
# AAA/GWT-Style Tests für crazycar.car.sensors

import math
import pytest
pytestmark = pytest.mark.unit

import crazycar.car.sensors as S
from crazycar.car.sensors import cast_radar, collect_radars, distances, linearize_DA

# Eigene Randfarbe für Tests, um Unabhängigkeit von der Prod-Konstante zu behalten
BORDER = (1, 2, 3, 4)


def _endpoint(center, carangle_deg, degree_offset, length):
    """Hilfsfunktion: berechnet das Endpixel exakt wie im Produktionscode (int-Koords!)."""
    cx, cy = center
    ang = 360.0 - (carangle_deg + degree_offset)
    x = int(cx + math.cos(math.radians(ang)) * length)
    y = int(cy + math.sin(math.radians(ang)) * length)
    return (x, y)


# ----------------------------- cast_radar -----------------------------

def test_cast_radar_hits_border_at_expected_pixel():
    # GIVEN
    center = (10.0, 20.0)
    carangle = 30.0
    degree_offset = -15
    target_len = 25  # erstes Pixel, das als Rand markiert wird
    target_xy = _endpoint(center, carangle, degree_offset, target_len)

    def color_at(pt):
        # Nur genau am Zielpixel melden wir "Rand"
        return BORDER if pt == target_xy else (0, 0, 0, 255)

    # WHEN
    (end_xy, dist_px) = cast_radar(
        center, carangle, degree_offset, color_at,
        max_len_px=1000, border_color=BORDER
    )

    # THEN
    assert end_xy == target_xy
    assert dist_px == int(math.hypot(end_xy[0] - center[0], end_xy[1] - center[1]))


def test_cast_radar_respects_max_len_if_no_border_seen():
    # GIVEN
    center = (0.0, 0.0)
    carangle = 0.0
    degree_offset = 0
    max_len = 17

    def color_at(_):
        # Niemals Rand → Abbruch über max_len
        return (0, 0, 0, 255)

    # WHEN
    (end_xy, dist_px) = cast_radar(
        center, carangle, degree_offset, color_at,
        max_len_px=max_len, border_color=BORDER
    )

    # THEN
    exp_xy = _endpoint(center, carangle, degree_offset, max_len)
    assert end_xy == exp_xy
    assert dist_px == max_len


# ----------------------------- collect_radars -----------------------------

def test_collect_radars_count_and_default_limit(monkeypatch):
    # GIVEN: default limit = WIDTH * MAX_RADAR_LEN_RATIO (gepatcht)
    monkeypatch.setattr(S, "WIDTH", 100, raising=True)
    monkeypatch.setattr(S, "MAX_RADAR_LEN_RATIO", 0.1, raising=True)  # → limit = 10
    center = (0.0, 0.0)
    carangle = 0.0
    sweep, step = 60, 30  # → -60,-30,0,+30,+60
    limit = int(S.WIDTH * S.MAX_RADAR_LEN_RATIO)

    def color_at(_):
        # Niemals Rand → Abbruch über max_len
        return (0, 0, 0, 255)

    # WHEN
    radars = collect_radars(
        center, carangle, sweep_deg=sweep, step_deg=step,
        color_at=color_at, border_color=BORDER
    )

    # THEN
    degrees = list(range(-sweep, sweep + 1, step))
    assert isinstance(radars, list) and len(radars) == len(degrees)

    # Erwartete Endpunkte und Distanzen exakt wie im Produktionscode:
    expected = []
    for deg in degrees:
        end_xy = _endpoint(center, carangle, deg, limit)
        exp_d = int(math.hypot(end_xy[0] - center[0], end_xy[1] - center[1]))
        expected.append((end_xy, exp_d))

    for (xy, d), (ex_xy, ex_d) in zip(radars, expected):
        assert xy == ex_xy
        assert d == ex_d

    # sanity: mindestens ein Strahl (deg=0) erreicht exakt die volle Limit-Distanz
    assert max(d for _, d in radars) == limit


def test_collect_radars_endpoints_match_degrees_when_border_set():
    # GIVEN: wir setzen für jede Richtungsstufe genau ein Zielpixel als Rand
    center = (5.0, 5.0)
    carangle = 10.0
    sweep, step, L = 40, 20, 13  # Richtungen: -40,-20,0,+20,+40 (5 Stück)
    degrees = list(range(-sweep, sweep + 1, step))
    targets = {_endpoint(center, carangle, deg, L) for deg in degrees}

    def color_at(pt):
        return BORDER if pt in targets else (0, 0, 0, 255)

    # WHEN
    radars = collect_radars(
        center, carangle, sweep_deg=sweep, step_deg=step,
        color_at=color_at, max_len_px=L + 50, border_color=BORDER
    )

    # THEN: alle Strahlen stoppen exakt auf unseren Zielpixeln mit Distanz ~ L (Rastereffekt via int)
    assert len(radars) == len(degrees)
    for (xy, dist) in radars:
        assert xy in targets
        assert dist == int(math.hypot(xy[0] - center[0], xy[1] - center[1]))


# ----------------------------- distances -----------------------------

def test_distances_extracts_only_int_distances():
    # GIVEN
    radars = [(((0, 0), 7)), (((1, 1), 9)), (((2, 3), 0))]
    # WHEN
    out = distances(radars)
    # THEN
    assert out == [7, 9, 0]
    assert all(isinstance(x, int) for x in out)


# ----------------------------- linearize_DA -----------------------------

@pytest.mark.parametrize("vals", [[0.0], [0.0, 10.0, 20.0]])
def test_linearize_DA_zero_and_positive(vals):
    # GIVEN
    A, B = 23962.0, -20.0
    AV, BV = 58.5, -0.05
    # WHEN
    out = linearize_DA(vals)
    # THEN
    for d_cm, (bits, volt) in zip(vals, out):
        if d_cm == 0:
            assert bits == 0 and math.isclose(volt, 0.0, abs_tol=1e-12)
        else:
            exp_bits = int((A / d_cm) + B)
            exp_volt = (AV / d_cm) + BV
            assert bits == exp_bits
            assert math.isclose(volt, exp_volt, rel_tol=0, abs_tol=1e-12)
