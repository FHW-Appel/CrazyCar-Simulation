"""Test MapService spawn detection and car initialization.

Verifies that MapService correctly detects the spawn location from the race map
and that the car is properly initialized at that location with correct orientation.

Prints spawn coordinates, detection info, and car position/angle to console.

Usage:
    python tools/test_spawn_map.py
"""
import os
import pygame
from crazycar.sim import map_service, simulation

# initialize pygame and a dummy display
pygame.init()
# choose a window size consistent with SimRuntime default; small is fine
size = (1200, 800)
pygame.display.set_mode(size)

ms = map_service.MapService(size, asset_name="Racemap.png")
spawn = ms.get_spawn()
print('MapService.get_spawn():', spawn)
info = ms.get_detect_info()
print('MapService.get_detect_info(): n=%d cx=%.1f cy=%.1f angle_deg=%.1f' % (info.get('n',0), info.get('cx',0), info.get('cy',0), info.get('angle_deg',0)))

cars = simulation._spawn_car_from_map(ms)
print('Spawn -> Car pos, angle:', cars[0].position, cars[0].carangle)

pygame.quit()
