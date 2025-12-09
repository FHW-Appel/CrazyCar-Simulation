"""
Ein kleines Debug-Tool: zeigt die Map, zeichnet das Finish-Line-Debug-Overlay
für 5 Sekunden und gibt das Ergebnis von get_spawn() in der Konsole aus.

Aufruf: Aus dem Projektroot mit der Projekt-venv laufen lassen, z.B.
& venv/Scripts/python.exe tools/run_map_debug.py
"""
from __future__ import annotations
import time
import logging
import pygame
import sys
from pathlib import Path

# Ensure `src` is on sys.path (same logic as main.py)
_THIS = Path(__file__).resolve()
_SRC_DIR = _THIS.parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from crazycar.sim.map_service import MapService

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

def main() -> int:
    pygame.init()
    try:
        window_size = (1024, 768)
        screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Map Debug (5s)")

        ms = MapService(window_size)

        # eine Sekunde warten, damit evtl. Assets geladen sind
        clock = pygame.time.Clock()
        start = time.time()
        duration = 5.0

        # Logge das ermittelte Spawn (auch wenn None internally)
        spawn = ms.get_spawn()
        logging.info("get_spawn() → %s", spawn)

        while time.time() - start < duration:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return 0
            ms.blit(screen)
            # Debug-Overlay zeichnen
            try:
                ms.draw_finish_debug(screen)
            except Exception as e:
                logging.exception("Fehler beim draw_finish_debug: %s", e)
            pygame.display.flip()
            clock.tick(30)

        # Kurz warten, dann Exit
        logging.info("Fertig (5s). Beende.")
        return 0
    finally:
        pygame.quit()

if __name__ == '__main__':
    raise SystemExit(main())
