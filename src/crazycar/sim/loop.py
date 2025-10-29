# src/crazycar/sim/loop.py
# Hinweis:
# - Keine Pygame-Initialisierung auf Modulebene.
# - Keine Ressourcen-Ladevorgänge (Map, Fonts etc.) hier drin.
# - Die Schleife ist absichtlich generisch gehalten: Status-Provider/Callbacks
#   können aus simulation.py (z. B. ToggleButtons) injiziert werden.
# - Nichts wird „hart“ beendet (kein pygame.quit / sys.exit) – das macht der Aufrufer.

from __future__ import annotations
from typing import Callable, Optional, List
import logging
import pygame

from .state import SimState
from .modes import apply_control as _default_apply_control
from ..car.model import Car

log = logging.getLogger("crazycar.sim.loop")
if not logging.getLogger().handlers:
    import os
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.loop] %(message)s",
    )

# Typen für optionale Callbacks/Provider
StatusProvider = Callable[[], int]
ApplyControlFn = Callable[[bool, List[Car]], None]
OnEventFn = Callable[[pygame.event.Event, SimState], None]
OnTickFn = Callable[[pygame.Surface, SimState], None]


def run(
    state: SimState,
    cars: List[Car],
    screen_service,
    map_service,
    *,
    get_sensor_status: Optional[StatusProvider] = None,
    get_collision_status: Optional[StatusProvider] = None,
    apply_control: Optional[ApplyControlFn] = None,
    on_event: Optional[OnEventFn] = None,
    on_tick: Optional[OnTickFn] = None,
    fps: int = 100,
    max_ticks: Optional[int] = None,
) -> None:
    """
    Haupt-Schleife der Simulation.

    Parameter
    ---------
    state : SimState
        Gemeinsamer, veränderlicher Simulationszustand (paused, drawtracks, mode_python, window_size, …).
    cars : List[Car]
        Aktive Fahrzeuge – deren update()/draw() werden hier aufgerufen.
    screen_service :
        Muss ein Objekt mit .screen (pygame.Surface) und .resize((w,h)) bereitstellen.
    map_service :
        Muss .surface() -> pygame.Surface und .rescale((w,h)) bereitstellen.
    get_sensor_status : Callable[[], int], optional
        Liefert 0/1/2… je nach Toggle – falls None, wird 1 verwendet.
    get_collision_status : Callable[[], int], optional
        Liefert 0/1/2… je nach Toggle – falls None, wird 1 verwendet.
    apply_control : Callable[[bool, List[Car]], None], optional
        Steuerungsfunktion (Python/C). Default: modes._default_apply_control.
    on_event : Callable[[pygame.event.Event, SimState], None], optional
        Zusatz-Event-Handling (Buttons/Dialogs) – wird pro Event zusätzlich aufgerufen.
    on_tick : Callable[[pygame.Surface, SimState], None], optional
        Zusatz-Zeichnen pro Frame (HUD/Overlays).
    fps : int
        Ziel-FPS (tick).
    max_ticks : int | None
        Optionales Frame-Limit (z. B. für Tests).
    """
    clock = pygame.time.Clock()
    do_apply_control = apply_control or _default_apply_control

    running = True
    tick_count = 0

    log.debug("Loop start: window_size=%s cars=%d fps=%d", state.window_size, len(cars), fps)

    while running:
        # -----------------------------------------------------
        # Resize-Events separat ziehen (so wie im bisherigen Code)
        # -----------------------------------------------------
        for evt in pygame.event.get(pygame.VIDEORESIZE):
            state.window_size = evt.size
            screen_service.resize(state.window_size)
            map_service.rescale(state.window_size)
            log.debug("VIDEORESIZE → window_size=%s", state.window_size)

        # -----------------------------------------------------
        # Normale Events
        # -----------------------------------------------------
        for evt in pygame.event.get():
            # Erst optionales Zusatz-Handling (Buttons/GUI) aufrufen
            if on_event is not None:
                try:
                    on_event(evt, state)
                except Exception as ex:
                    log.exception("on_event() exception: %s", ex)

            if evt.type == pygame.QUIT:
                log.info("QUIT erhalten → Loop-Ende")
                running = False

            elif evt.type == pygame.KEYDOWN:
                if evt.key == pygame.K_ESCAPE:
                    log.info("ESC erhalten → Loop-Ende")
                    running = False
                elif evt.key == pygame.K_SPACE:
                    state.paused = not state.paused
                    log.debug("Pause toggled → %s", state.paused)

        # -----------------------------------------------------
        # Pause-Schleife (minimal): verarbeitet nur Events & ESC/SPACE
        # -----------------------------------------------------
        while running and state.paused:
            for evt in pygame.event.get():
                if on_event is not None:
                    try:
                        on_event(evt, state)
                    except Exception:
                        log.exception("on_event() exception in pause")
                if evt.type == pygame.QUIT:
                    log.info("QUIT während Pause → Loop-Ende")
                    running = False
                elif evt.type == pygame.KEYDOWN:
                    if evt.key == pygame.K_ESCAPE:
                        log.info("ESC während Pause → Loop-Ende")
                        running = False
                    elif evt.key == pygame.K_SPACE:
                        state.paused = False
                        log.debug("Pause beendet (SPACE)")
            # kurze Entlastung der CPU im Pausemodus
            clock.tick(30)

        if not running:
            break

        # -----------------------------------------------------
        # Hintergrund (Map)
        # -----------------------------------------------------
        screen = screen_service.screen
        screen.blit(map_service.surface(), (0, 0))

        # -----------------------------------------------------
        # Update/Draw aller Cars
        # -----------------------------------------------------
        sensor_status = get_sensor_status() if get_sensor_status else 1
        collision_status = get_collision_status() if get_collision_status else 1

        still_alive = 0
        for c in cars:
            if c.is_alive():
                still_alive += 1
                # Wichtig: Dein Car.update erwartet screen, drawtracks, sensor_status, collision_status
                c.update(screen, state.drawtracks, sensor_status, collision_status)
        for c in cars:
            if c.is_alive():
                c.draw(screen)

        if still_alive == 0:
            log.info("Alle Fahrzeuge tot → Loop-Ende")
            break

        # -----------------------------------------------------
        # Steuerung anwenden (Python/C)
        # -----------------------------------------------------
        try:
            do_apply_control(state.mode_python, cars)
        except Exception:
            log.exception("apply_control() exception")

        # -----------------------------------------------------
        # Optional: zusätzliches Zeichnen (HUD etc.)
        # -----------------------------------------------------
        if on_tick is not None:
            try:
                on_tick(screen, state)
            except Exception:
                log.exception("on_tick() exception")

        # -----------------------------------------------------
        # Flip & Tick
        # -----------------------------------------------------
        pygame.display.flip()
        clock.tick(fps)
        tick_count += 1

        if max_ticks is not None and tick_count >= max_ticks:
            log.info("max_ticks=%d erreicht → Loop-Ende", max_ticks)
            break

    log.debug("Loop end")
