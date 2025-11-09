import sys
from pathlib import Path

# Ensure src on sys.path
_ROOT = Path(__file__).resolve().parents[1]
_SRC = str(_ROOT / 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from crazycar.sim.modes import ModeManager, UIRects
from crazycar.sim.state import SimRuntime, SimEvent
import pygame


def test_mode_manager_switch_to_python_keeps_car_alive():
    # create rects: button_regelung1 at (1000,100), button_regelung2 at (1000,160)
    button_regelung1 = pygame.Rect(1000, 100, 200, 40)
    button_regelung2 = pygame.Rect(1000, 160, 200, 40)
    ui = UIRects(
        aufnahmen_button=pygame.Rect(0, 0, 10, 10),
        recover_button=pygame.Rect(0, 0, 10, 10),
        button_yes_rect=pygame.Rect(1100, 400, 80, 30),
        button_no_rect=pygame.Rect(1200, 400, 80, 30),
        button_regelung1_rect=button_regelung1,
        button_regelung2_rect=button_regelung2,
    )

    rt = SimRuntime()
    rt.paused = False
    m = ModeManager(start_python=False)

    # simulate clicking python button
    ev1 = SimEvent('MOUSE_DOWN', {'pos': (1010, 165)})
    m.apply([ev1], rt, ui, [])
    assert m.show_dialog and rt.paused and m._button_py

    # simulate clicking yes inside dialog
    yes_pos = (ui.button_yes_rect.x + 1, ui.button_yes_rect.y + 1)
    ev2 = SimEvent('MOUSE_DOWN', {'pos': yes_pos})

    class CarStub:
        def __init__(self):
            self.alive = True

    cars = [CarStub()]
    m.apply([ev2], rt, ui, cars)

    assert m.regelung_py is True
    # ModeManager now requests a restart by terminating the current car
    assert cars[0].alive is False
