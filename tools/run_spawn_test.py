# Focused runtime test: init pygame display, create MapService, get spawn, create Car at that spawn
import sys
sys.path.insert(0, r'e:\PY_Pojekte\CrazyCar-Simulation\src')
import pygame
pygame.init()
# minimal display for convert_alpha support
pygame.display.set_mode((1,1))
from crazycar.sim.map_service import MapService
from crazycar.car.model import Car, f

print('--- MAPSERVICE+CAR RUNTIME CHECK ---')
ms = MapService((1024,768))
spawn = ms.get_spawn()
info = ms.get_detect_info()
print('get_spawn ->', spawn)
print('detect_info n=', info.get('n', 0), 'cx,cy=', info.get('cx'), info.get('cy'))
pos = [spawn.x_px * f, spawn.y_px * f]
print('computed sim-pos (px*f) ->', pos, 'angle=', spawn.angle_deg)
car = Car(pos, float(spawn.angle_deg), 20, False, [], [], 0, 0)
print('Car created: position=', car.position, 'carangle=', car.carangle)
print('sprite size =', car.sprite.get_size())
pygame.quit()
