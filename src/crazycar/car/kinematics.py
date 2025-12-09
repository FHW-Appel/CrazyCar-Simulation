# crazycar/car/kinematics.py
"""Vehicle kinematics: Steering -> course change (pygame-free).

This module encapsulates the calculation of how the vehicle angle (carangle)
changes with given steering angle (radangle) and speed.
"""

from __future__ import annotations
import math
import os
import logging
from typing import Final

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.kin")

# Small number to guard against division by zero
_EPS: Final[float] = 1e-6
# Soft clamp for extreme steering angles (tan() explodes numerically otherwise)
_MAX_STEER_ABS_DEG: Final[float] = 89.0


def normalize_angle(deg: float) -> float:
    """Normalize an angle in degrees to range [0, 360)."""
    return float(deg % 360.0)


def _clamp_steer(radangle_deg: float) -> float:
    """Limit absolute steering angle to numerically stable range."""
    a = float(radangle_deg)
    if abs(a) > _MAX_STEER_ABS_DEG:
        a_clamped = math.copysign(_MAX_STEER_ABS_DEG, a)
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer: clamp |rad| %.2f° -> %.2f° (numerical safety)", a, a_clamped)
        return a_clamped
    return a


def steer_step(
    carangle_deg: float,
    radangle_deg: float,
    speed_px: float,
    radstand_px: float,
    spurweite_px: float,
) -> float:
    """Single step of course change due to steering.
    
    Args:
        carangle_deg: current vehicle angle [°]
        radangle_deg: steering angle of front wheels [°] (sign: left/right)
        speed_px:     speed [px per tick] (sign: forward/backward)
        radstand_px:  wheelbase of vehicle [px]
        spurweite_px: track width [px]
    
    Returns:
        New vehicle angle [°] in [0, 360)
    """
    angle0 = float(carangle_deg)

    # 1) No steering or no speed -> no rotation
    if abs(radangle_deg) < _EPS:
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer: no-op (|rad|<eps): car=%.4f rad=%.4f speed=%.4f", angle0, radangle_deg, speed_px)
        return normalize_angle(angle0)
    if abs(speed_px) < _EPS:
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer: no-op (|speed|<eps): car=%.4f rad=%.4f speed=%.4f", angle0, radangle_deg, speed_px)
        return normalize_angle(angle0)

    # 2) Clamp steering angle (numerics)
    radangle_deg = _clamp_steer(radangle_deg)

    # 3) Sign for left/right
    k0 = -1.0 if radangle_deg < 0.0 else 1.0
    angle_rad = math.radians(abs(radangle_deg))

    # 4) Check tan()
    tanv = math.tan(angle_rad)
    if abs(tanv) < _EPS:
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer: no-op (tan(angle)≈0): car=%.4f rad=%.4f°", angle0, radangle_deg)
        return normalize_angle(angle0)

    # 5) Curve radius
    #    R = L / tan(delta) + W/2
    car_radius = (float(radstand_px) / tanv) + (float(spurweite_px) / 2.0)
    if abs(car_radius) < _EPS or math.isnan(car_radius) or math.isinf(car_radius):
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer: no-op (invalid R): car=%.4f rad=%.4f° R=%.6f", angle0, radangle_deg, car_radius)
        return normalize_angle(angle0)

    # 6) Angle change Δθ ≈ s / R
    dtheta_rad = float(speed_px) / car_radius
    dtheta_deg = math.degrees(dtheta_rad)

    # Reverse driving rotates opposite
    new_angle = angle0 + (k0 * dtheta_deg if speed_px > 0.0 else -k0 * dtheta_deg)

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        log.debug(
            "steer: in=%.4f rad=%.2f° speed=%.3f L=%.3f W=%.3f -> R=%.6f Δθ=%.5f° out=%.4f",
            angle0, radangle_deg, speed_px, radstand_px, spurweite_px,
            car_radius, dtheta_deg, new_angle % 360.0
        )

    return normalize_angle(new_angle)


__all__ = ["normalize_angle", "steer_step"]
