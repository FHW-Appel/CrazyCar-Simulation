# tests/car/test_dynamics.py
import math
from crazycar.car.dynamics import step_speed

def test_step_speed_smoke():
    # Versuche gängige Signaturen in kurzer Reihenfolge
    try:
        v = step_speed(0.0, 1.0, 0.1)                   # (v, power, dt)
    except TypeError:
        try:
            v = step_speed(0.0, 1.0, 0.02, 10.0, 0.1)   # (v, power, drag, max_speed, dt)
        except TypeError:
            v = step_speed(speed=0.0, power=1.0, dt=0.1)  # keywords (falls so benannt)

    assert isinstance(v, (int, float)) and math.isfinite(v)
