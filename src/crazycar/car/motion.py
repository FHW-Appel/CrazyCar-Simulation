# crazycar/car/motion.py
from __future__ import annotations
import os
import math
import logging
from crazycar.car.constants import f, WIDTH, HEIGHT, CAR_cover_size, CAR_Radstand, CAR_Spurweite
from crazycar.car.kinematics import steer_step

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.motion")

def step_motion(state):
    # Zeit/Distanz
    state.distance += state.speed
    state.time += 0.01

    # Lenkung → Kursänderung
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
    state.position[0] += math.cos(math.radians(360 - state.carangle)) * state.speed
    state.position[1] += math.sin(math.radians(360 - state.carangle)) * state.speed

    # Begrenzen
    state.position[0] = max(state.position[0], 10 * f)
    state.position[0] = min(state.position[0], WIDTH - 10 * f)
    state.position[1] = max(state.position[1], 10 * f)
    state.position[1] = min(state.position[1], HEIGHT - 10 * f)

    # Center aktualisieren
    state.center = [
        int(state.position[0]) + CAR_cover_size / 2,
        int(state.position[1]) + CAR_cover_size / 2,
    ]

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        log.debug("motion: pos (%.1f,%.1f)→(%.1f,%.1f) center=(%.1f,%.1f)",
                  oldx, oldy, state.position[0], state.position[1], state.center[0], state.center[1])
