# --- Backcompat: steer_step(x,y,heading, speed, steer_deg, dt, wheelbase)
import math as _km
_steer_step_prev = locals().get("steer_step", None)

def _steer_step_bicycle(x, y, heading, speed, steer_deg, dt, wheelbase):
    beta = _km.radians(steer_deg)
    if abs(beta) < 1e-12:
        nx = x + speed * dt * _km.cos(heading)
        ny = y + speed * dt * _km.sin(heading)
        return nx, ny, heading
    omega = speed * _km.tan(beta) / float(wheelbase)
    nh = heading + omega * dt
    if abs(omega) < 1e-12:
        nx = x + speed * dt * _km.cos(heading)
        ny = y + speed * dt * _km.sin(heading)
        return nx, ny, nh
    R = speed / omega
    nx = x + R * (_km.sin(nh) - _km.sin(heading))
    ny = y + R * (_km.cos(heading) - _km.cos(nh))
    return nx, ny, nh

def steer_step(*args, **kwargs):
    keys = set(kwargs)
    if keys & {"speed","steer_deg","wheelbase","dt"} or len(args) >= 7:
        if len(args) >= 7:
            x, y, heading, speed, steer_deg, dt, wheelbase = args[:7]
        else:
            x = kwargs.get("x", args[0] if args else 0.0)
            y = kwargs.get("y", args[1] if len(args)>1 else 0.0)
            heading  = kwargs.get("heading", args[2] if len(args)>2 else 0.0)
            speed    = kwargs["speed"]
            steer_deg= kwargs.get("steer_deg", 0.0)
            dt       = kwargs.get("dt", 0.016)
            wheelbase= kwargs["wheelbase"]
        return _steer_step_bicycle(float(x), float(y), float(heading),
                                   float(speed), float(steer_deg),
                                   float(dt), float(wheelbase))
    if _steer_step_prev is not None:
        return _steer_step_prev(*args, **kwargs)
    raise TypeError("steer_step called with unexpected signature")
