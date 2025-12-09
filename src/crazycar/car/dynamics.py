"""Vehicle dynamics: Target speed & speed update (pygame-free).

Mappings from original:
- soll_speed(power)                -> Target speed (sim pixels/step)
- step_speed(v_px, power, rad_deg) -> New speed (sim pixels/step)

Notes:
- Calculates internally in real-world units (cm/s) via units.py
- Time increment dt defaults to 0.01 (as in original code)
- Formulas derived from empirical measurements
- Handles straight vs. curve driving with different physics models
"""

from __future__ import annotations
from typing import Tuple

from .units import sim_to_real, real_to_sim


# Physics constants from empirical measurements
# Acceleration formula: a = c0*v + c1*p² + c2*p (in cm/s²/100)
ACCEL_SPEED_COEFF = -2.179    # Speed damping
ACCEL_POWER_QUAD = 0.155      # Quadratic power term
ACCEL_POWER_LINEAR = 7.015    # Linear power term
ACCEL_SCALE_FACTOR = 100.0    # Scaling factor

# Maximum speed (straight): v_max = c0*p² + c1*p + c2 (in cm/s/100)
VMAX_STRAIGHT_QUAD = -0.0496
VMAX_STRAIGHT_LINEAR = 9.008
VMAX_STRAIGHT_CONST = 31.8089
VMAX_STRAIGHT_SCALE = 100.0

# Maximum speed (curve): v_max = c0*p^c1 + c2 (in cm/s/100)
VMAX_CURVE_COEFF = -81562.0
VMAX_CURVE_EXP = -2.47
VMAX_CURVE_CONST = 215.5123
VMAX_CURVE_SCALE = 100.0

# Threshold for straight vs. curve driving
STEERING_THRESHOLD_DEG = 5  # At 5° steering angle → curve formula


def _max_speed_cm_s(power: float, radangle_deg: float) -> float:
    """Compute maximum speed in cm/s based on power and steering angle.
    
    Uses different formulas for straight (< 5°) vs. curve driving (>= 5°).
    Formulas derived from empirical measurements of the physical model.
    
    Args:
        power: Drive power (0-100)
        radangle_deg: Steering angle in degrees
        
    Returns:
        Float: Maximum achievable speed in cm/s.
    """
    p = abs(power)
    if radangle_deg < STEERING_THRESHOLD_DEG:
        # Straight formula: Quadratic regression
        vmax = VMAX_STRAIGHT_QUAD * (p ** 2) + VMAX_STRAIGHT_LINEAR * p + VMAX_STRAIGHT_CONST
        vmax /= VMAX_STRAIGHT_SCALE
    else:
        # Curve formula: Power law with negative exponent
        vmax = VMAX_CURVE_COEFF * (p ** VMAX_CURVE_EXP) + VMAX_CURVE_CONST
        vmax /= VMAX_CURVE_SCALE
    return float(vmax)


def _acceleration_cm_s2(speed_cm_s: float, power: float) -> float:
    """Compute acceleration in cm/s² from current speed and power.
    
    Linear in speed (damping), quadratic in power (drive force).
    Formula: a = c0*v + c1*p² + c2*p
    
    Args:
        speed_cm_s: Current speed in cm/s
        power: Drive power (0-100)
        
    Returns:
        Float: Acceleration in cm/s².
    """
    p = abs(power)
    a = ACCEL_SPEED_COEFF * speed_cm_s + ACCEL_POWER_QUAD * (p ** 2) + ACCEL_POWER_LINEAR * p
    a /= ACCEL_SCALE_FACTOR
    return float(a)


def soll_speed(power: float) -> float:
    """Compute target speed in sim-pixels per frame for given power.
    
    Uses straight-line formula only (legacy behavior for target speed).
    Sign of power is preserved (negative → reverse).
    
    Args:
        power: Drive power (-100 to 100)
        
    Returns:
        Float: Target speed in simulation pixels per frame.
    """
    # Straight formula (original behavior)
    v_cm_s = (VMAX_STRAIGHT_QUAD * (power ** 2) + VMAX_STRAIGHT_LINEAR * power + VMAX_STRAIGHT_CONST) / VMAX_STRAIGHT_SCALE
    return real_to_sim(v_cm_s)


def step_speed(
    current_speed_px: float,
    power: float,
    radangle_deg: float,
    *,
    dt: float = 0.01,  # Standard time step in seconds (10ms)
) -> float:
    """Update speed for one simulation step using Euler integration.
    
    Integrates acceleration with velocity clamping at v_max. Handles both
    forward (power > 0) and reverse (power < 0) driving.
    
    Args:
        current_speed_px: Current speed in sim-pixels per frame
        power: Drive power (-100 to 100, sign determines direction)
        radangle_deg: Steering angle in degrees (affects v_max)
        dt: Time step in seconds (default 0.01 = 10ms per frame)
        
    Returns:
        Float: New speed in sim-pixels per frame.
        
    Note:
        Uses Euler integration: v_new = v + a*dt, clamped to [-v_max, v_max].
    """
    # Convert to real size (cm/s)
    v = sim_to_real(current_speed_px)

    # Sign logic as in original: negative power inverts sign calculation
    turnback = False
    p = power
    if p < 0:
        p = -p
        v = -v
        turnback = True

    if p == 0:
        v_new = 0.0
    else:
        vmax = _max_speed_cm_s(p, radangle_deg)
        a = _acceleration_cm_s2(v, p)

        # Euler integration step with clamping to vmax (absolute value)
        v_candidate = v + a * dt
        if abs(v_candidate) <= abs(vmax):
            v_new = v_candidate
        else:
            # If exceeding, simply clamp at limit
            v_new = vmax if v >= 0 else -vmax

    # Back to sim units
    sim_v = real_to_sim(v_new if not turnback else -v_new)
    return float(sim_v)


__all__ = ["soll_speed", "step_speed"]
