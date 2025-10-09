# --- Backcompat: compute_corners(x, y, heading, length, width, unit_scale)
import math as _gm
_compute_corners_prev = locals().get("compute_corners", None)

def _compute_corners_rect__bb(x, y, heading, length, width, unit_scale=1.0):
    L = float(length) * float(unit_scale)
    W = float(width)  * float(unit_scale)
    hx, hy = L/2.0, W/2.0
    pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    if abs(heading) > 1e-12:
        c, s = _gm.cos(heading), _gm.sin(heading)
        pts = [(px*c - py*s, px*s + py*c) for (px, py) in pts]
    return [(x + px, y + py) for (px, py) in pts]

def compute_corners(*args, **kwargs):
    if (len(args) >= 5) or ({'length','width'} & set(kwargs)):
        if len(args) >= 5:
            x, y, heading, length, width = args[:5]
            unit_scale = args[5] if len(args) >= 6 else kwargs.get("unit_scale", 1.0)
        else:
            x = kwargs.get("x"); y = kwargs.get("y")
            heading = kwargs.get("heading", 0.0)
            length = kwargs["length"]; width = kwargs["width"]
            unit_scale = kwargs.get("unit_scale", 1.0)
        return _compute_corners_rect__bb(x, y, heading, length, width, unit_scale)
    if _compute_corners_prev is not None:
        return _compute_corners_prev(*args, **kwargs)
    raise TypeError("compute_corners called with unexpected signature")
