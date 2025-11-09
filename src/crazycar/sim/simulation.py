# =============================================================================
# crazycar/sim/simulation.py  —  Fassade / Sammelzugang
# -----------------------------------------------------------------------------
# Aufgabe:
# - Startpunkt für einen einzelnen Simulationslauf (NEAT-Callback).
# - Initialisiert Konfiguration/Runtime (state.py) und Pygame-Fenster (lazy).
# - Erzeugt UI-Geometrie (Buttons/Dialog/Toggles) und Service-Objekte.
# - Spawnt Fahrzeuge & NEAT-Netze.
# - Delegiert die eigentliche Hauptschleife an loop.run_loop(...).
#
# Öffentliche API (dieses Moduls):
# - run_simulation(genomes, config): Startet genau einen Simulationslauf.
# - run_direct(duration_s: float | None = None): Startet einen Lauf OHNE NEAT
#   (wird z. B. im DLL-Only-Modus vom Optimizer-Adapter aufgerufen).
#
# Wichtige Helfer:
# - _finalize_exit(hard_kill: bool): Garantierter/Weicher Prozess-Exit.
# - _get_or_create_screen(size): Re-uses/erstellt Pygame-Window (verhindert Doppel-Fenster).
#
# Abhängigkeiten:
# - state.SimConfig, state.SimRuntime, state.build_default_config, state.seed_all
# - event_source.EventSource (normierte Events; Headless-fähig)
# - modes.ModeManager, modes.UIRects (Pausen-/Moduslogik, Dialogsteuerung)
# - map_service.MapService (Laden/Resize/Blit der Karte)
# - loop.run_loop, loop.UICtx (zentraler Frame-Loop + UI-Kontext)
# - toggle_button.ToggleButton (UI-Widget)
#
# Tests:
# - Unit: ModeManager, EventSource-Parsing, MapService-Resize, UICtx-Factories (reine Python-Tests).
# - Integration: loop.run_loop mit SDL_VIDEODRIVER=dummy (Headless), feste Seeds.
# - E2E/Smoke: kurzer Sim-Lauf, Artefakte (z. B. CSV/Screenshots) via snapshot_service verifizieren.
# =============================================================================

from __future__ import annotations
import sys
import os
import logging
from typing import List, Tuple

import neat
import pygame
import pygame.freetype

from ..car.model import Car, WIDTH, HEIGHT, f           # sim_to_real wird hier nicht benötigt
from .toggle_button import ToggleButton

# Zentrale Zustände/Konfiguration
from .state import SimConfig, SimRuntime, build_default_config, seed_all
# Event-Pipeline (pygame/Headless)
from .event_source import EventSource
# Modus-/Pausenlogik
from .modes import ModeManager, UIRects
# Map-Service (Hintergrundkarte)
from .map_service import MapService
# Loop (Hauptschleife) + UI-Kontext
from .loop import run_loop, UICtx

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.sim] %(message)s",
    )
log = logging.getLogger("crazycar.sim")


def _finalize_exit(hard_kill: bool) -> None:
    """
    Zentraler Exit-Helfer:
    - pygame.quit()
    - Entweder sys.exit(0) (standard; nicht abfangbar) ODER SystemExit(0) (weich, abfangbar).
    Steuerung über cfg.hard_exit.
    """
    log.info("Harter Exit → pygame.quit() + %s",
             "sys.exit(0)" if hard_kill else "SystemExit(0)")
    try:
        pygame.quit()
    finally:
        if hard_kill:
            sys.exit(0)
        else:
            raise SystemExit(0)


def _get_or_create_screen(size: Tuple[int, int]) -> pygame.Surface:
    """
    Nimmt ein existierendes Fenster (falls z. B. der Optimizer eins geöffnet hat),
    oder erzeugt eines. So vermeiden wir Doppel-Fenster. Kümmert sich auch um Resize.
    """
    scr = pygame.display.get_surface()
    if scr is None:
        log.debug("Kein aktives Display gefunden → set_mode(%s) wird erstellt.", size)
        scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    else:
        if scr.get_size() != size:
            log.debug("Displaygröße %s → Resize auf %s", scr.get_size(), size)
            scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    return scr


def run_simulation(genomes, config):
    """
    NEAT-Callback: führt EINEN Simulationslauf aus.
    Verantwortlichkeiten hier:
      - Config/Runtime initialisieren (inkl. Seeds für Reproduzierbarkeit)
      - Pygame/Window lazy erzeugen
      - UI-Elemente/Rects/Toggles definieren
      - Services/Manager instanziieren (EventSource, ModeManager, MapService)
      - Cars spawnen, Netze erzeugen
      - an loop.run_loop(...) delegieren
    """

    # --- Config/Runtime ---
    cfg: SimConfig = build_default_config()
    seed_all(cfg.seed)               # deterministische RNGs
    rt = SimRuntime()
    rt.start(cfg)                    # setzt window_size, counter etc.

    # --- Pygame init & Window (lazy) ---
    if not pygame.get_init():
        log.debug("pygame.init() (lazy)")
        pygame.init()

    window_size = rt.window_size
    screen = _get_or_create_screen(window_size)
    pygame.display.set_caption("CrazyCar Simulation")

    # --- UI-Setup (Fonts/Clock) ---
    font_ft = pygame.freetype.SysFont("Arial", int(19 * f))  # FreeType für HUD-Text
    font_gen = pygame.font.SysFont("Arial", 15)
    font_alive = pygame.font.SysFont("Arial", 10)
    clock = pygame.time.Clock()

    # --- UI-Elemente/Buttons/Toggles (Geometrie wie im Bestand) ---
    positionx = WIDTH * 0.7 * f
    positiony = HEIGHT - 180 * f

    text_box_rect = pygame.Rect(int(positionx * 0.73), int(positiony + 40), 200, 30)
    aufnahmen_button = pygame.Rect(int(positionx), int(positiony), 100, 30)
    recover_button = pygame.Rect(int(positionx), int(positiony + 40), 100, 30)

    collision_button = ToggleButton(
        int(positionx * 1.2),
        int(positiony),
        "Collision-Model: Rebound",
        "Collision-Model: Stop",
        "Collision-Model: Remove",
    )
    sensor_button = ToggleButton(
        collision_button.rect.x,
        int(positiony + collision_button.rect.height + 5),
        "Sensor Enabled",
        "Sensor Unable",
        "",
    )

    button_width = 215
    button_height = 45
    button_color = (0, 255, 0)
    positionx_btn = int(1700 * f)
    positiony_btn = int(530 * f)
    button_regelung1_rect = pygame.Rect(positionx_btn, positiony_btn, button_width, button_height)
    button_regelung2_rect = pygame.Rect(positionx_btn, positiony_btn + button_height + 30, button_width, button_height)

    dialog_width = 500
    dialog_height = 200
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = (HEIGHT - dialog_height) // 2
    button_dialog_width = 100
    button_dialog_height = 30
    button_padding = 30
    button_dialog_x = dialog_x + 100
    button_dialog_y = dialog_y + dialog_height - button_dialog_height - button_padding
    button_yes_rect = pygame.Rect(button_dialog_x, button_dialog_y, button_dialog_width, button_dialog_height)
    button_no_rect = pygame.Rect(
        button_dialog_x + button_dialog_width + 100, button_dialog_y, button_dialog_width, button_dialog_height
    )

    # UI-Rects-Bundle für ModeManager (kapselt Klickflächen für Dialog/Moduswahl/Snapshots)
    ui_rects = UIRects(
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
    )

    # Initial-Toggles (dürfen jetzt gezeichnet werden, screen existiert)
    collision_button.draw(screen)
    sensor_button.draw(screen)

    # Labels der Modus-Schaltflächen (Bestand)
    text1 = "c_regelung"
    text2 = "python_regelung"
    text_color = (0, 0, 0)

    # --- Map-Service (lädt „Racemap.png“, skaliert/resize, blit) ---
    map_service = MapService(window_size, asset_name="Racemap.png")

    # --- NEAT-Netze (Bestand) ---
    nets = []
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

    # --- Fahrzeuge (Bestand / Spawnpunkt) ---
    cars: List[Car] = [Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)]
    log.info("Sim-Start: cars=%d size=%sx%s", len(cars), *window_size)

    rt.current_generation += 1

    # --- Manager (Events/Modus) ---
    es = EventSource(headless=cfg.headless)    # liefert normalisierte Events + Raw-Events (für Widgets)
    # Allow persistent override via marker file or env var so a restart can honor user's choice.
    start_python = None
    try:
        path = os.path.join(os.getcwd(), ".crazycar_start_mode")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as _f:
                    val = _f.read().strip()
                # consume the file so it's one-shot
                try:
                    os.remove(path)
                except Exception:
                    pass
                start_python = (val == "1")
                log.debug("Found start-mode marker file %s -> start_python=%s", path, start_python)
            except Exception as e:
                log.debug("Could not read start-mode file %s: %r", path, e)
    except Exception:
        # fall through to env var default
        start_python = None

    if start_python is None:
        start_python = os.getenv("CRAZYCAR_START_PYTHON", "1") == "1"
    modes = ModeManager(start_python=start_python)     # verwaltet Pause/Dialog + PY/C-Regelung

    # --- UI-Kontext für den Loop (zentralisiert alles, was der Loop zum Zeichnen braucht) ---
    ui = UICtx(
        screen=screen,
        font_ft=font_ft,
        font_gen=font_gen,
        font_alive=font_alive,
        clock=clock,
        text1=text1,
        text2=text2,
        text_color=text_color,
        button_color=button_color,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        text_box_rect=text_box_rect,
        positionx_btn=positionx_btn,
        positiony_btn=positiony_btn,
        button_width=button_width,
        button_height=button_height,
    )

    # --- Hauptschleife (delegiert) ---
    # Der Loop kümmert sich um:
    #   - Resize-Events (via EventSource.poll_resize → MapService.resize + set_mode-Refresh)
    #   - aktive/pausierte Eingaben (Modes.apply), Snapshots/Recovery
    #   - Zeichnen: Map, Cars, Dialog/Buttons, HUD, Toggles
    #   - Exit (QUIT/ESC) via finalize_exit
    run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=_finalize_exit,
    )

    # KEIN auto-quit hier: der Aufrufer darf das Fenster ggf. weiterverwenden.
    return


# -----------------------------------------------------------------------------
# Direktmodus für DLL-Only (ohne NEAT)
# Wird vom Optimizer-Adapter aufgerufen, wenn CRAZYCAR_ONLY_DLL aktiv ist
# und er eine NEAT-freie Einstiegsmethode benötigt.
# -----------------------------------------------------------------------------
def run_direct(duration_s: float | None = None) -> None:
    """
    Startet die Simulation ohne NEAT.
    - Verwendet dieselbe UI-/Service-Initialisierung wie run_simulation(),
      nur ohne genomes/config/NEAT-Netze.
    - Standardmäßig ist die **C-Regelung (DLL)** aktiv (start_python=False).
    - Beendet sauber per ESC/X. Optional kann die Laufzeit mit duration_s
      begrenzt werden (sofern run_loop keine eigene Dauer unterstützt).

    Args:
        duration_s: Optionale maximale Laufzeit in Sekunden (soft).
    """
    import time as _t

    # --- Config/Runtime ---
    cfg: SimConfig = build_default_config()
    seed_all(cfg.seed)               # deterministische RNGs
    rt = SimRuntime()
    rt.start(cfg)                    # setzt window_size, counter etc.

    # --- Pygame init & Window (lazy) ---
    if not pygame.get_init():
        log.debug("pygame.init() (lazy, DLL-Only)")
        pygame.init()

    window_size = rt.window_size
    screen = _get_or_create_screen(window_size)
    pygame.display.set_caption("CrazyCar – DLL-Only")

    # --- UI-Setup (Fonts/Clock) ---
    font_ft = pygame.freetype.SysFont("Arial", int(19 * f))
    font_gen = pygame.font.SysFont("Arial", 15)
    font_alive = pygame.font.SysFont("Arial", 10)
    clock = pygame.time.Clock()

    # --- UI-Elemente/Buttons/Toggles (wie Bestand) ---
    positionx = WIDTH * 0.7 * f
    positiony = HEIGHT - 180 * f

    text_box_rect = pygame.Rect(int(positionx * 0.73), int(positiony + 40), 200, 30)
    aufnahmen_button = pygame.Rect(int(positionx), int(positiony), 100, 30)
    recover_button = pygame.Rect(int(positionx), int(positiony + 40), 100, 30)

    collision_button = ToggleButton(
        int(positionx * 1.2),
        int(positiony),
        "Collision-Model: Rebound",
        "Collision-Model: Stop",
        "Collision-Model: Remove",
    )
    sensor_button = ToggleButton(
        collision_button.rect.x,
        int(positiony + collision_button.rect.height + 5),
        "Sensor Enabled",
        "Sensor Unable",
        "",
    )

    button_width = 215
    button_height = 45
    button_color = (0, 255, 0)
    positionx_btn = int(1700 * f)
    positiony_btn = int(530 * f)
    button_regelung1_rect = pygame.Rect(positionx_btn, positiony_btn, button_width, button_height)
    button_regelung2_rect = pygame.Rect(positionx_btn, positiony_btn + button_height + 30, button_width, button_height)

    dialog_width = 500
    dialog_height = 200
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = (HEIGHT - dialog_height) // 2
    button_dialog_width = 100
    button_dialog_height = 30
    button_padding = 30
    button_dialog_x = dialog_x + 100
    button_dialog_y = dialog_y + dialog_height - button_dialog_height - button_padding
    button_yes_rect = pygame.Rect(button_dialog_x, button_dialog_y, button_dialog_width, button_dialog_height)
    button_no_rect = pygame.Rect(
        button_dialog_x + button_dialog_width + 100, button_dialog_y, button_dialog_width, button_dialog_height
    )

    # UI-Rects-Bundle für ModeManager (kapselt Klickflächen für Dialog/Moduswahl/Snapshots)
    ui_rects = UIRects(
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
    )

    # Initial-Toggles (dürfen jetzt gezeichnet werden, screen existiert)
    collision_button.draw(screen)
    sensor_button.draw(screen)

    # Labels der Modus-Schaltflächen (wie Bestand)
    text1 = "c_regelung"
    text2 = "python_regelung"
    text_color = (0, 0, 0)

    # --- Map-Service (lädt „Racemap.png“, skaliert/resize, blit) ---
    map_service = MapService(window_size, asset_name="Racemap.png")

    # --- Fahrzeuge (Bestand / Spawnpunkt) ---
    cars: List[Car] = [Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)]
    log.info("Direct-Run (DLL-Only): cars=%d size=%sx%s", len(cars), *window_size)

    rt.current_generation += 1  # kosmetisch für HUD/Counter

    # --- Manager (Events/Modus) ---
    es = EventSource(headless=cfg.headless)

    # Wichtig: standardmäßig **C-Regelung** aktivieren (DLL-Logik bevorzugen)
    # Allow override by marker file or env var so a restart can start in Python mode if requested.
    start_python = None
    try:
        path = os.path.join(os.getcwd(), ".crazycar_start_mode")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as _f:
                    val = _f.read().strip()
                try:
                    os.remove(path)
                except Exception:
                    pass
                start_python = (val == "1")
                log.debug("Found start-mode marker file %s -> start_python=%s", path, start_python)
            except Exception as e:
                log.debug("Could not read start-mode file %s: %r", path, e)
    except Exception:
        start_python = None

    if start_python is None:
        start_python = os.getenv("CRAZYCAR_START_PYTHON", "0") == "1"
    modes = ModeManager(start_python=start_python)

    # --- UI-Kontext für den Loop (zentralisiert alles, was der Loop zum Zeichnen braucht) ---
    ui = UICtx(
        screen=screen,
        font_ft=font_ft,
        font_gen=font_gen,
        font_alive=font_alive,
        clock=clock,
        text1=text1,
        text2=text2,
        text_color=text_color,
        button_color=button_color,
        button_regelung1_rect=button_regelung1_rect,
        button_regelung2_rect=button_regelung2_rect,
        button_yes_rect=button_yes_rect,
        button_no_rect=button_no_rect,
        aufnahmen_button=aufnahmen_button,
        recover_button=recover_button,
        text_box_rect=text_box_rect,
        positionx_btn=positionx_btn,
        positiony_btn=positiony_btn,
        button_width=button_width,
        button_height=button_height,
    )

    # --- Hauptschleife ---
    # Hinweis: Falls deine run_loop bereits eine "duration" unterstützt, kannst du
    # den Parameter unten ergänzen (auskommentierte Zeile). Ansonsten sorgt
    # duration_s nur als Soft-Grenze für einen nachgelagerten Soft-Exit.
    start_t = _t.time()
    run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=_finalize_exit,
        # duration=duration_s,  # nur aktivieren, falls run_loop(duration=...) existiert
    )

    # Fallback-Soft-Exit, wenn run_loop keine Dauer kennt:
    if duration_s is not None and (_t.time() - start_t) >= duration_s:
        try:
            _finalize_exit(hard_kill=False)
        except SystemExit:
            pass

    # KEIN auto-quit hier: der Aufrufer darf das Fenster ggf. weiterverwenden.
    return
