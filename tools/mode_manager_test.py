"""Quick test to simulate ModeManager button clicks without full GUI.

Tests the ModeManager's handling of regulator toggle buttons (Python/C)
by simulating mouse click events without launching the full simulation.

Usage:
    python tools/mode_manager_test.py
"""
import sys
from pathlib import Path
_THIS = Path(__file__).resolve()
_SRC = str(_THIS.parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from crazycar.sim.modes import ModeManager, UIRects
from crazycar.sim.state import SimRuntime, SimEvent
import pygame

# create rects: button_regelung1 at (1000,100), button_regelung2 at (1000,160)
button_regelung1 = pygame.Rect(1000,100,200,40)
button_regelung2 = pygame.Rect(1000,160,200,40)
ui = UIRects(
    aufnahmen_button=pygame.Rect(0,0,10,10),
    recover_button=pygame.Rect(0,0,10,10),
    button_yes_rect=pygame.Rect(1100,400,80,30),
    button_no_rect=pygame.Rect(1200,400,80,30),
    button_regelung1_rect=button_regelung1,
    button_regelung2_rect=button_regelung2,
)
rt = SimRuntime()
rt.paused = False
m = ModeManager(start_python=False)
print('initial regelung_py=', m.regelung_py)
# simulate clicking python button
ev1 = SimEvent('MOUSE_DOWN', {'pos': (1010,165)})
actions = m.apply([ev1], rt, ui, [])
print('after click open dialog: show_dialog=', m.show_dialog, 'paused=', rt.paused, 'button_py=', m._button_py)
# simulate clicking yes inside dialog
# ensure yes button collides
yes_pos = (ui.button_yes_rect.x + 1, ui.button_yes_rect.y + 1)
ev2 = SimEvent('MOUSE_DOWN', {'pos': yes_pos})
class CarStub:
    def __init__(self):
        self.alive = True

cars = [CarStub()]
actions = m.apply([ev2], rt, ui, cars)
print('after yes: regelung_py=', m.regelung_py, 'show_dialog=', m.show_dialog, 'paused=', rt.paused, 'car0.alive=', cars[0].alive)
print('after yes: regelung_py=', m.regelung_py, 'show_dialog=', m.show_dialog, 'paused=', rt.paused)
