"""Compare MapService spawn vs actual Car placement.

Creates a MapService instance, retrieves detect_info and spawn, creates a Car
at the simulation-converted top-left, and computes the projection of the car
center onto the finish-line normal to verify the car is placed in front of
the detected line (as MapService intends).

Prints a compact summary with PASS/FAIL and numeric deltas.
"""
from __future__ import annotations
import os
import sys
import math
import pygame

# Ensure the repository `src/` directory is on sys.path so package imports work
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from crazycar.sim.map_service import MapService
# Import Car (and the model-level CAR_cover_size) first so init_pixels() runs
from crazycar.car.model import Car, CAR_cover_size as MODEL_CAR_cover
from crazycar.car.constants import f, WIDTH, HEIGHT


def main():
    pygame.init()
    # Create a surface matching the sim constants so MapService scales correctly
    window_size = (int(WIDTH), int(HEIGHT))
    screen = pygame.display.set_mode(window_size)

    ms = MapService(window_size)
    info = ms.get_detect_info()
    spawn = ms.get_spawn()

    print("detect_info n=", info.get("n", 0))
    if info.get("n", 0) < 1:
        print("No finish line detected — aborting comparison.")
        return

    cx = float(info["cx"])
    cy = float(info["cy"])
    nx = float(info.get("nx", 0.0))
    ny = float(info.get("ny", 0.0))
    sign = int(info.get("sign", 1))

    print(f"Line center (px) = ({cx:.2f}, {cy:.2f}), normal = ({nx:.3f}, {ny:.3f}), sign={sign}")
    print(f"Spawn (px) = ({spawn.x_px}, {spawn.y_px}), map_angle_deg = {spawn.angle_deg:.3f}")

    # Compute what the simulation now sets: angle that points from spawn to line center
    from math import atan2, degrees
    dx_line = cx - float(spawn.x_px)
    dy_line = cy - float(spawn.y_px)
    sim_ang = (360.0 - degrees(atan2(dy_line, dx_line))) % 360.0
    print(f"Sim-set-angle (point front TO line center) = {sim_ang:.3f}°")

    # Compute the projection of the spawn relative to the line center along the normal
    spawn_dx = float(spawn.x_px) - cx
    spawn_dy = float(spawn.y_px) - cy
    spawn_proj_px = spawn_dx * nx + spawn_dy * ny

    # Convert MapService map angle to the Car's internal angle convention.
    # MapService angle (angle_deg) is atan2(sign*ny, sign*nx) in mathematical
    # coordinates. Car uses a convention where forward = cos(radians(360 - carangle)).
    # Therefore: carangle = (360 - map_angle) % 360
    carangle_from_spawn = (360.0 - float(spawn.angle_deg)) % 360.0
    print(f"Converted carangle (from map angle) = {carangle_from_spawn:.3f}°")

    # Now create the Car using the same conversion as the simulation:
    # MapService returns map/window pixels; convert spawn CENTER -> sprite TOP-LEFT
    # by subtracting half the cover size (cover is already in pixel units).
    half_cover = (MODEL_CAR_cover * 0.5)
    pos_x = spawn.x_px - half_cover
    pos_y = spawn.y_px - half_cover
    # Use the converted carangle here (not the raw map angle)
    car = Car([pos_x, pos_y], float(carangle_from_spawn), 20.0, 0, [], [], 0, 0)

    # Car.center is in the same pixel space as the map (no extra scaling needed)
    car_center_px = car.center[0]
    car_center_py = car.center[1]
    car_dx = car_center_px - cx
    car_dy = car_center_py - cy
    car_proj_px = car_dx * nx + car_dy * ny

    # Expected: car_proj_px ≈ spawn_proj_px and spawn_proj_px should have same sign as `sign` and be positive magnitude
    delta = car_proj_px - spawn_proj_px

    print(f"spawn_proj_px = {spawn_proj_px:.2f} px  (expected sign*offset)")
    print(f"car_center_px = ({car_center_px:.2f}, {car_center_py:.2f})")
    print(f"car_proj_px   = {car_proj_px:.2f} px")
    print(f"delta (car - spawn) = {delta:.4f} px")

    # Heuristics for PASS/FAIL
    pass_cond = (abs(delta) < 1e-6) and (math.copysign(1.0, spawn_proj_px) == float(sign)) and (abs(spawn_proj_px) > 5.0)

    status = "PASS" if pass_cond else "FAIL"
    print(f"RESULT: {status}")

    # Also render debug overlay once so user can visually inspect
    ms.blit(screen)
    ms.draw_finish_debug(screen)
    car.draw(screen)
    pygame.display.flip()

    # keep window open short moment so any screenshot users take will show it
    pygame.time.wait(1500)
    pygame.quit()


if __name__ == "__main__":
    main()
