# tests/car/test_sensors_unit.py
from math import isclose
from crazycar.car.sensors import linearize_DA, cast_radar, distances

def test_linearize_DA_bitvolt_minimal():
    out = linearize_DA([10.0, 0.0])  # cm -> (bit, volt)
    assert out[0][0] == int((23962.0 / 10.0) - 20.0)
    assert isclose(out[0][1], (58.5 / 10.0) - 0.05, rel_tol=1e-9)
    assert out[1] == (0, 0.0)

def test_distances_extracts_ints():
    assert distances([((0,0), 3), ((1,1), 7), ((2,2), 0)]) == [3, 7, 0]

def test_cast_radar_hits_border_fast():
    BORDER = (255, 0, 0, 255)
    def color_at(pos):  # Border ab x >= 5
        x, y = pos
        return BORDER if x >= 5 else (0, 0, 0, 255)
    (_, _), d = cast_radar(center=(0.0, 0.0), carangle_deg=0.0, degree_offset=0,
                           color_at=color_at, max_len_px=50, border_color=BORDER)
    assert 4 <= d <= 6
