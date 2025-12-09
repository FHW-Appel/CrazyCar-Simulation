"""Vehicle Motion - Position, Rotation, Boundaries.

This module implements the motion update step of a vehicle.

Main Function:
- step_motion(state): Updates position, angle, distance, time

Process:
1. Distance += Speed (tracking)
2. Time += 0.01s (fixed timestep, 100 FPS)
3. Steering → Course change via steer_step() (Ackermann kinematics)
4. Translation: Position += (cos(angle), sin(angle)) * speed
5. Clamping to map dimensions (10px margin)
6. Center update for rendering

Coordinate System:
- Pygame: (0,0) = top left, Y downward
- Angle: 0° = right, 90° = down (mathematically negative = pygame positive)
- Angle inversion: 360° - carangle for correct trigonometry

Boundaries:
- Min: 10 * f (f = scaling factor from constants)
- Max: WIDTH/HEIGHT - 10 * f

See Also:
- kinematics.py: steer_step() steering geometry
- constants.py: WIDTH, HEIGHT, CAR_cover_size
"""
# crazycar/car/motion.py
from __future__ import annotations
import os
import math
import logging
from crazycar.car.constants import f, WIDTH, HEIGHT, CAR_cover_size, CAR_Radstand, CAR_Spurweite
from crazycar.car.kinematics import steer_step

# Physics timestep constants
TIMESTEP_SECONDS = 0.01  # Fixed timestep for motion update (100 FPS)
BOUNDARY_MARGIN_FACTOR = 10  # Pixels × scaling factor for edge margin
ANGLE_INVERSION = 360  # Pygame angle convention (360° - angle for correct trig)
CENTER_OFFSET_DIVISOR = 2  # Divide cover_size by 2 for center calculation

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.motion")

def step_motion(state):
    """Update vehicle position and rotation for one timestep.
    
    Performs single physics step:
    1. Advance distance and time counters
    2. Update heading angle via Ackermann steering
    3. Translate position based on heading and speed
    4. Clamp position to world boundaries
    5. Update center point for rendering
    
    Args:
        state: CarState object with position, speed, angles, etc.
        
    Note:
        Modifies state in-place:
        - Updates state.distance, state.time
        - Changes state.carangle based on steering
        - Modifies state.position coordinates
        - Recalculates state.center
        - Clamps position to [10*f, WIDTH/HEIGHT - 10*f]
        - Logs debug info if CRAZYCAR_DEBUG=1
        
        Physics:
        - Time step: 0.01 seconds per call
        - Uses steer_step() for Ackermann kinematics
        - Angle convention: 0° = right, 90° = up
        - Position boundaries: 10*f margin from edges
    """
    # Time/distance
    state.distance += state.speed
    state.time += TIMESTEP_SECONDS

    # Steering → Course change
    if abs(state.radangle) > 0:
        old = state.carangle
        state.carangle = steer_step(
            carangle_deg=state.carangle,
            radangle_deg=state.radangle,
            speed_px=state.speed,
            radstand_px=CAR_Radstand,
            spurweite_px=CAR_Spurweite,
        )
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("motion: angle %.2f→%.2f (rad=%.2f° speed=%.3f)",
                      old, state.carangle, state.radangle, state.speed)

    # Translation
    oldx, oldy = state.position[0], state.position[1]
    state.position[0] += math.cos(math.radians(ANGLE_INVERSION - state.carangle)) * state.speed
    state.position[1] += math.sin(math.radians(ANGLE_INVERSION - state.carangle)) * state.speed

    # Clamp to boundaries
    margin = BOUNDARY_MARGIN_FACTOR * f
    state.position[0] = max(state.position[0], margin)
    state.position[0] = min(state.position[0], WIDTH - margin)
    state.position[1] = max(state.position[1], margin)
    state.position[1] = min(state.position[1], HEIGHT - margin)

    # Update center point
    state.center = [
        int(state.position[0]) + CAR_cover_size / CENTER_OFFSET_DIVISOR,
        int(state.position[1]) + CAR_cover_size / CENTER_OFFSET_DIVISOR,
    ]

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        log.debug("motion: pos (%.1f,%.1f)→(%.1f,%.1f) center=(%.1f,%.1f)",
                  oldx, oldy, state.position[0], state.position[1], state.center[0], state.center[1])
