"""Generate debug screenshot of spawn location on race map.

Initializes pygame, loads the race map, draws finish line debug overlay,
spawns a car, and saves a screenshot showing the initial car placement.
Useful for verifying spawn location accuracy.

Usage:
    python tools/gen_spawn_debug_screenshot.py

Output:
    spawn_debug.png in current directory
"""
import os
import pygame
from crazycar.sim import map_service, simulation

# Initialize pygame and create a surface matching typical runtime
pygame.init()
# Ensure a video mode is set because some surfaces use convert()/convert_alpha()
# which require a display. Use a windowed mode; it's fine for headless quick debug.
size = (1536, 864)
_ = pygame.display.set_mode(size)
surface = pygame.Surface(size)

ms = map_service.MapService(size, asset_name="Racemap.png")
# Ensure ms.surface is scaled correctly
ms.resize(size)

# Blit the map onto our surface
surface.blit(ms.surface, (0, 0))

# Draw finish-line debug overlay
try:
    ms.draw_finish_debug(surface)
except Exception as e:
    print('draw_finish_debug failed:', e)

# Spawn car via the simulation helper
cars = simulation._spawn_car_from_map(ms)
car = cars[0]

# Rotate sprite appropriately and blit
try:
    rotated = car.rotate_center(car.sprite, car.carangle)
    surface.blit(rotated, (int(car.position[0]), int(car.position[1])))
    # draw bounding box around sprite
    pygame.draw.rect(surface, (255, 0, 0), rotated.get_rect(topleft=(int(car.position[0]), int(car.position[1]))), 2)
except Exception as e:
    print('drawing car failed:', e)

# Save screenshot
out = os.path.join(os.getcwd(), 'tools', 'spawn_debug.png')
try:
    pygame.image.save(surface, out)
    print('Saved debug screenshot to', out)
except Exception as e:
    print('Failed to save screenshot:', e)

pygame.quit()
