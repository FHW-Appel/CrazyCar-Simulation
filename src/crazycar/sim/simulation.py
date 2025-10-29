# crazycar/sim/simulation.py
# Hinweis:
# - Pygame wird NICHT mehr auf Modulebene initialisiert → verhindert Doppel-Fenster.
# - Alles UI-Setup passiert lazy in run_simulation().
# - Entfernte/verschobene Stellen sind unten EXPLIZIT auskommentiert.
# - NEU: harter Exit (_finalize_exit) → ESC/QUIT schließt wirklich die ganze App (auch im Pause-Dialog).

from __future__ import annotations
import sys
import os
import time
import datetime
import logging
from typing import List

import neat
import pygame
import pygame.freetype
import pickle

from ..car.model import Car, WIDTH, HEIGHT, f, sim_to_real
from ..control.interface import Interface
from ..car.serialization import serialize_car
from .toggle_button import ToggleButton

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Per ENV an/aus:
#   CRAZYCAR_DEBUG=1  -> DEBUG-Logs
#   sonst             -> INFO
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.sim] %(message)s",
    )
log = logging.getLogger("crazycar.sim")

# --- Globale Sim-Parameter ---
window_size = (WIDTH, HEIGHT)
time_flip = 0.01  # 10ms pro Frame

BORDER_COLOR = (255, 255, 255)  # Color To Crash on Hit

current_generation = 0
drawtracks = False
paused = False
file_text = ""

# NEU: Env-Schalter für „wirklich hart“ beenden
_HARD_KILL = os.getenv("CRAZYCAR_HARD_EXIT", "1") == "1"

def _finalize_exit() -> None:
    """
    Zentraler Exit-Helfer:
    - pygame.quit()
    - Entweder sys.exit(0) (standard; nicht abfangbar) ODER SystemExit (per Env).
    """
    log.info("Harter Exit → pygame.quit() + %s",
             "sys.exit(0)" if _HARD_KILL else "SystemExit(0)")
    try:
        pygame.quit()
    finally:
        if _HARD_KILL:
            sys.exit(0)        # garantiertes Ende des Prozesses
        else:
            raise SystemExit(0) # weiches Ende (kann abgefangen werden)

# -----------------------------------------------------------------------------
# WICHTIG: KEINE PYGAME-FENSTER-ERZEUGUNG AUF MODULEBENE
# -----------------------------------------------------------------------------
# Früher (entfernt):
# pygame.init()
# screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
# font = pygame.freetype.SysFont("Arial", int(19 * f))
# clock = pygame.time.Clock()
# generation_font = pygame.font.SysFont("Arial", 15)
# alive_font = pygame.font.SysFont("Arial", 10)
#
# Begründung:
# - Das führte zu einem zweiten (leeren) Fenster, wenn woanders ebenfalls set_mode() aufgerufen wurde.
# - Jetzt: alles davon erst in run_simulation().

def _get_or_create_screen(size) -> pygame.Surface:
    """
    Nimmt ein existierendes Fenster (falls z. B. der Optimizer eins geöffnet hat),
    oder erzeugt eines. So vermeiden wir Doppel-Fenster.
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
    """NEAT Callback: führt 1 Simulationslauf aus (ein Fenster, kein Doppelstart)."""
    global drawtracks, current_generation, paused, file_text, window_size

    # --- Pygame init & Window (lazy) ---
    if not pygame.get_init():
        log.debug("pygame.init() (lazy)")
        pygame.init()
    screen = _get_or_create_screen(window_size)
    pygame.display.set_caption("CrazyCar Simulation")

    # --- UI-Setup (erst NACH init / screen!) ---
    # (Das war früher oben auf Modulebene – JETZT HIER.)
    font = pygame.freetype.SysFont("Arial", int(19 * f))
    clock = pygame.time.Clock()
    generation_font = pygame.font.SysFont("Arial", 15)
    alive_font = pygame.font.SysFont("Arial", 10)

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

    # Initialzeichnung der Toggles (jetzt okay, screen existiert)
    collision_button.draw(screen)
    sensor_button.draw(screen)

    text1 = "c_regelung"
    text2 = "python_regelung"
    text_color = (0, 0, 0)

    # Früher global initialisiert; hier bewusst pro-Lauf gesetzt.
    regelung_py = True
    time_printed = False

    # --- Map laden ---
    map_path = os.path.join(os.path.dirname(__file__), "..", "assets", "Racemap.png")
    map_path = os.path.normpath(map_path)
    log.debug("Lade Map: %s", map_path)
    game_map_raw = pygame.image.load(map_path).convert()
    game_map = pygame.transform.scale(game_map_raw, window_size)

    # --- Netze aufbauen (NEAT) ---
    nets = []
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

    # Ein Fahrzeug spawnen
    cars: List[Car] = [Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)]
    log.info("Sim-Start: cars=%d size=%sx%s", len(cars), *window_size)

    current_generation += 1
    counter = 0
    show_dialog = False
    button_py = False
    button_c = False

    running = True
    while running:
        # ---------------------------------------------------------
        # Resize-Events (neu: wir unterstützen RESIZABLE sauber)
        # ---------------------------------------------------------
        for event in pygame.event.get(pygame.VIDEORESIZE):
            window_size = event.size
            screen = _get_or_create_screen(window_size)
            game_map = pygame.transform.scale(game_map_raw, window_size)
            log.debug("Resize-Event: window_size=%s", window_size)

        # ---------------------------------------------------------
        # Pause-Schleife
        # ---------------------------------------------------------
        while paused:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    log.info("Quit während Pause → harter Exit.")
                    _finalize_exit()  # sofortiger, garantierter Prozess-Exit
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        paused = False
                        log.debug("Pause beendet (SPACE).")
                    elif event.key == pygame.K_ESCAPE:
                        log.info("ESC während Pause → harter Exit.")
                        _finalize_exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if aufnahmen_button.collidepoint(event.pos):
                        paused = False
                        log.debug("Pause beendet (Aufnahmen-Button).")
                    if button_no_rect.collidepoint(event.pos):
                        if button_py:
                            regelung_py = True
                            button_py = False
                        if button_c:
                            regelung_py = False
                            button_c = False
                        paused = False
                        show_dialog = False
                        log.debug("Dialog: NO → Modus bleibt: %s", "PY" if regelung_py else "C")
                    if button_yes_rect.collidepoint(event.pos):
                        if button_py:
                            regelung_py = False
                            button_py = False
                        if button_c:
                            regelung_py = True
                            button_c = False
                        if cars:
                            cars[0].alive = False
                        paused = False
                        show_dialog = False
                        log.debug("Dialog: YES → Modus wechselt auf: %s", "PY" if regelung_py else "C")

        # ---------------------------------------------------------
        # Events
        # ---------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Optional: wie ESC behandeln (harter Exit)
                log.info("Quit-Event → harter Exit.")
                _finalize_exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = True
                    log.debug("Pause aktiviert (SPACE).")
                elif event.key == pygame.K_t:
                    drawtracks = not drawtracks
                    log.debug("DrawTracks toggled → %s", drawtracks)
                elif event.key == pygame.K_ESCAPE:
                    # NEU: harter Exit (nicht nur Loop verlassen)
                    if cars:
                        cars[0].alive = False
                    log.info("ESC → harter Exit angefordert.")
                    _finalize_exit()
                elif event.unicode.isalnum():
                    file_text += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    file_text = file_text[:-1]
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if aufnahmen_button.collidepoint(event.pos):
                    moment_aufnahmen(cars)
                    paused = True
                    log.info("Momentaufnahme gespeichert; Pause aktiviert.")
                if button_regelung1_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_py = True
                    log.debug("Dialog geöffnet: Ziel 'python_regelung'")
                if button_regelung2_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_c = True
                    log.debug("Dialog geöffnet: Ziel 'c_regelung'")
                if recover_button.collidepoint(event.pos):
                    cars = moment_recover(file_text)
                    log.info("Momentaufnahme wiederhergestellt: %s", file_text)

            # Toggle-Buttons verarbeiten
            collision_button.handle_event(event, 3)
            sensor_button.handle_event(event, 2)

        # ---------------------------------------------------------
        # Hintergrund zeichnen
        # ---------------------------------------------------------
        screen.blit(game_map, (0, 0))

        # ---------------------------------------------------------
        # Update aller Cars
        # ---------------------------------------------------------
        still_alive = 0
        sensor_status = sensor_button.get_status()
        collision_status = collision_button.get_status()

        for i, c in enumerate(cars):
            if c.is_alive():
                still_alive += 1
                # Früher: c.update(game_map, drawtracks, sensor_status, collision_status)
                # Jetzt übergeben wir 'screen' (Map liegt bereits auf screen):
                c.update(screen, drawtracks, sensor_status, collision_status)

        if still_alive == 0:
            log.info("Alle Fahrzeuge tot → Runde beendet.")
            break

        # ---------------------------------------------------------
        # Draw aller Cars
        # ---------------------------------------------------------
        for c in cars:
            if c.is_alive():
                c.draw(screen)

        # ---------------------------------------------------------
        # Dialog & Buttons
        # ---------------------------------------------------------
        if show_dialog:
            Interface.draw_dialog(screen)
            Interface.draw_button(
                screen, "Yes", (0, 0, 0), (0, 255, 0),
                button_dialog_x, button_dialog_y, button_dialog_width, button_dialog_height, button_yes_rect
            )
            Interface.draw_button(
                screen, "No", (0, 0, 0), (255, 0, 0),
                button_dialog_x + button_dialog_width + 100, button_dialog_y,
                button_dialog_width, button_dialog_height, button_no_rect
            )

        Interface.draw_button(
            screen, text1, text_color, button_color, positionx_btn, positiony_btn,
            button_width, button_height, button_regelung1_rect
        )
        Interface.draw_button(
            screen, text2, text_color, button_color, positionx_btn, positiony_btn + button_height + 30,
            button_width, button_height, button_regelung2_rect
        )

        # ---------------------------------------------------------
        # Regelung (PY/C)
        # ---------------------------------------------------------
        if regelung_py:
            Interface.regelungtechnik_python(cars)
        else:
            Interface.regelungtechnik_c(cars)

        # ---------------------------------------------------------
        # Zeitlimit (optional)
        # ---------------------------------------------------------
        counter += 1
        if counter == 100 * 500:
            log.info("Zeitlimit erreicht → Runde beendet.")
            break

        # ---------------------------------------------------------
        # Maus-Guides & HUD
        # ---------------------------------------------------------
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.line(screen, (0, 255, 255), (mouse_pos[0], 0), (mouse_pos[0], HEIGHT), 1)
        pygame.draw.line(screen, (255, 100, 0), (0, mouse_pos[1]), (WIDTH, mouse_pos[1]), 1)
        font.render_to(screen, (WIDTH - 150, HEIGHT - 60), f"Position: {mouse_pos}", (0, 0, 255))

        # HINWEIS: generation_font / alive_font wurden bereits oben erzeugt.
        # Früher standen hier erneute Zuweisungen – die sind unnötig und auskommentiert.
        # generation_font = pygame.font.SysFont("Arial", 15)
        # alive_font = pygame.font.SysFont("Arial", 10)

        text = generation_font.render("Generation: " + str(current_generation), True, (0, 0, 0))
        text_rect = text.get_rect(center=(int(130 / 4 * f), int(450 / 2 * f)))
        screen.blit(text, text_rect)

        text = alive_font.render("Still Alive: " + str(still_alive), True, (0, 0, 0))
        text_rect = text.get_rect(center=(int(130 / 4 * f), int(490 / 2 * f)))
        screen.blit(text, text_rect)

        for i, line in enumerate(data_text(cars)):
            font.render_to(screen, (int(315 * f), int(285 * f + i * 20 * f)), line, (255, 0, 100))

        # UI-Buttons (Aufnahme/Recovery/Textbox)
        pygame.draw.rect(screen, pygame.Color("red"), aufnahmen_button)
        pygame.draw.rect(screen, pygame.Color("blue"), recover_button)
        pygame.draw.rect(screen, pygame.Color("gray"), text_box_rect)
        font.render_to(screen, (aufnahmen_button.x + 5, aufnahmen_button.y + 5), "Aufnahmen", pygame.Color("white"))
        font.render_to(screen, (recover_button.x + 5, recover_button.y + 5), "File_Recover", pygame.Color("white"))
        font.render_to(screen, (text_box_rect.x + 5, text_box_rect.y + 5), file_text, pygame.Color("black"))

        # Toggles rendern
        collision_button.draw(screen)
        sensor_button.draw(screen)

        # Flip & Tick
        pygame.display.flip()
        clock.tick(1 / time_flip)  # 100 FPS

    # Sauberes Ende:
    # KEIN auto-quit hier, der Aufrufer (z. B. Optimizer) darf das Fenster ggf. weiterverwenden.
    # Der harte Exit wird bereits im Event-Handling durchgeführt.
    return


# -----------------------------------------------------------------------------
# Info-Text für die HUD-Ausgabe (liefert IMMER eine Liste)
# -----------------------------------------------------------------------------
def data_text(cars) -> List[str]:
    if not cars:
        return []
    # Hinweis: Anzeige des Modus hier statisch; wenn du den echten Modus willst,
    # gib ihn als Parameter rein oder nutze eine globale/closure.
    regelung = " Python "  # if True else " C "
    c = cars[0]
    car_info = (
        f"Regelung : {regelung}\n   \n "
        f"Center Position: " + ", ".join([f"{pos / f:.0f}" for pos in c.center]) + "\n"
        f"Angle: {c.carangle:.2f} \n"
        f"Speed: {c.speed:.2f}( px/10ms)    {sim_to_real(c.speed):.2f}( cm/10ms) \n"
        f"Speed Set: {c.speed_set}\n    "
        f"power: {c.power:.1f}\n    "
        f"rad_angel: {c.radangle:.2f}\n    "
        "\n "
        f"Radars Beruehrungspunkt: \n "
        "    " + ", ".join([f"{rad[0]}" for rad in c.radars]) + "\n"
        f"Radars dist(px): " + ", ".join([f"{rad[1]}px" for rad in c.radars]) + "\n"
        f"Radars realdist(cm): " + ", ".join([f"{sim_to_real(rad[1]):.2f}cm" for rad in c.radars]) + "\n"
        f"Analog Wert(Volt) List: "
        + ", ".join([f"{wertV[1]:.2f}V" for wertV in c.bit_volt_wert_list])
        + "\n"
        f"Digital Wert(bit) List: "
        + ", ".join([f"{wertbit[0]:.0f}" for wertbit in c.bit_volt_wert_list])
        + "\n\n"
        f"Distance: {c.distance:.1f} px   {sim_to_real(c.distance):.1f}cm\n"
        f"Time: {c.time:.2f} s  \nRundenzeit: {c.round_time:.2f}"
    )
    return car_info.splitlines()


# -----------------------------------------------------------------------------
# Snapshots: Speichern & Laden
# -----------------------------------------------------------------------------
def moment_aufnahmen(cars):
    count = 1
    date = datetime.datetime.now().strftime("%d%M%S")
    doc_text = f"Momentaufnahme_{count}_{date}.pkl"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "MomentAufnahme", doc_text)

    # Serializer nutzen (Position wird – wie früher – mit f skaliert gespeichert)
    data_to_serialize = [serialize_car(acar, f_scale=f) for acar in cars]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as auf:
        pickle.dump(data_to_serialize, auf)
    log.info("Momentaufnahme geschrieben: %s", file_path)


def moment_recover(file_text_date):
    recover_cars: List[Car] = []
    count = 1
    date = "p1"
    if file_text_date:
        date = file_text_date

    base_dir = os.path.dirname(os.path.abspath(__file__))
    doc_text = f"Momentaufnahme_{count}_{date}.pkl"
    file_path = os.path.join(base_dir, "MomentAufnahme", doc_text)

    with open(file_path, "rb") as ein:
        deserialized_data = pickle.load(ein)

    for data in deserialized_data:
        position_x = data["position"][0] * f
        position_y = data["position"][1] * f
        recover_cars.append(
            Car(
                [position_x, position_y],
                data["carangle"],
                data["speed"],            # historisch: 3. Arg ist "power" im Ctor
                data["speed_set"],
                data["radars"],
                data["analog_wert_list"],
                data["distance"],
                data["time"],
            )
        )

    log.info("Momentaufnahme geladen: %s  (cars=%d)", file_path, len(recover_cars))
    return recover_cars
