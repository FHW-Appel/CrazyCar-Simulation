import os
from pathlib import Path
import sys

# Ensure src on sys.path
_ROOT = Path(__file__).resolve().parents[1]
_SRC = str(_ROOT / 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from crazycar.car.rebound import rebound_action


def color_at_dummy(pt):
    return (0, 0, 0, 0)


def test_rebound_reduces_speed_and_small_position_shift():
    # Pick tuned params (recommended by tuner)
    os.environ["CRAZYCAR_REBOUND_DAMP_SMALL"] = "0.1"
    os.environ["CRAZYCAR_REBOUND_DAMP_MED"] = "0.5"
    os.environ["CRAZYCAR_REBOUND_DAMP_LARGE"] = "0.2"
    os.environ["CRAZYCAR_REBOUND_K0"] = "-0.2"
    os.environ["CRAZYCAR_REBOUND_S_FACTOR"] = "1.0"
    os.environ["CRAZYCAR_REBOUND_TURN_FACTOR"] = "1.0"
    os.environ["CRAZYCAR_REBOUND_TURN_OFFSET"] = "0.5"

    speed = 5.0
    new_speed, new_angle, (dx, dy), slowed = rebound_action(
        (100.0, 100.0), 1, 20.0, speed, color_at_dummy, (255, 255, 255, 255)
    )

    # With damping < 1 new_speed should be lower than original speed
    assert new_speed < speed

    # Position delta should be small with s_factor=1 and k0=-0.2
    assert abs(dx) + abs(dy) < 10.0
