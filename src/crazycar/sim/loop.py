# =============================================================================
# crazycar/sim/loop.py  —  Hauptschleife (Frame-Loop)
# -----------------------------------------------------------------------------
# Aufgabe:
# - Enthält die zentrale Game-/Sim-Schleife: Events → Update → Draw → Tick.
# - Orchestriert EventSource, ModeManager, MapService, UI-Zeichnung und Toggles.
# - Führt Snapshot-/Recovery-Aktionen aus und behandelt Exit-Szenarien.
#
# Öffentliche API:
# - dataclass UICtx:
#       screen, font_ft, font_gen, font_alive, clock
#       text1, text2, text_color, button_color
#       button_regelung1_rect, button_regelung2_rect
#       button_yes_rect, button_no_rect
#       aufnahmen_button, recover_button, text_box_rect
#       positionx_btn, positiony_btn, button_width, button_height
# - run_loop(
#       cfg: SimConfig,
#       rt: SimRuntime,
#       es: EventSource,
#       modes: ModeManager,
#       ui: UICtx,
#       ui_rects: UIRects,
#       map_service: MapService,
#       cars: list[Car],
#       collision_button: ToggleButton,
#       sensor_button: ToggleButton,
#       finalize_exit: Callable[[bool], None]
#   ) -> None
#
# Hinweise:
# - Zeichnen des HUD/Textes erfolgt mit ui.font_*; Buttons/Dialog via screen_service.
# - FPS-Begrenzung über cfg.fps (ui.clock.tick(cfg.fps)).
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Callable, Tuple
import logging
import pygame

from ..car.model import Car, WIDTH, HEIGHT, f, sim_to_real
from ..control.interface import Interface
from .state import SimConfig, SimRuntime
from .event_source import EventSource
from .modes import ModeManager, UIRects
from .map_service import MapService
from .screen_service import draw_button, draw_dialog
from .snapshot_service import moment_aufnahmen, moment_recover

log = logging.getLogger("crazycar.sim.loop")


def build_car_info_lines(c: Car, use_python_control: bool) -> List[str]:
    """Formatiert die HUD-Zeilen stabil ohne verschachtelte f-Strings."""
    regelung = " Python " if use_python_control else " C "
    lines: List[str] = [
        f"Regelung : {regelung}",
        "   ",
        " Center Position: " + ", ".join(f"{pos / f:.0f}" for pos in c.center),
        f"Angle: {c.carangle:.2f} ",
        f"Speed: {c.speed:.2f}( px/10ms)    {sim_to_real(c.speed):.2f}( cm/10ms) ",
        f"Speed Set: {c.speed_set}",
        f"power: {c.power:.1f}",
        f"rad_angel: {c.radangle:.2f}",
        "",
        " Radars Beruehrungspunkt: ",
        "    " + ", ".join(f"{rad[0]}" for rad in c.radars),
        "Radars dist(px): " + ", ".join(f"{rad[1]}px" for rad in c.radars),
        "Radars realdist(cm): " + ", ".join(f"{sim_to_real(rad[1]):.2f}cm" for rad in c.radars),
        "Analog Wert(Volt) List: " + ", ".join(f"{wertV[1]:.2f}V" for wertV in c.bit_volt_wert_list),
        "Digital Wert(bit) List: " + ", ".join(f"{wertbit[0]:.0f}" for wertbit in c.bit_volt_wert_list),
        "",
        f"Distance: {c.distance:.1f} px   {sim_to_real(c.distance):.1f}cm",
        f"Time: {c.time:.2f} s  ",
        f"Rundenzeit: {c.round_time:.2f}",
    ]
    return lines


@dataclass
class UICtx:
    # Surfaces/Fonts
    screen: pygame.Surface
    font_ft: "pygame.freetype.Font"
    font_gen: "pygame.font.Font"
    font_alive: "pygame.font.Font"
    clock: pygame.time.Clock

    # Labels/Colors
    text1: str
    text2: str
    text_color: Tuple[int, int, int]
    button_color: Tuple[int, int, int]

    # UI Rects
    button_regelung1_rect: pygame.Rect
    button_regelung2_rect: pygame.Rect
    button_yes_rect: pygame.Rect
    button_no_rect: pygame.Rect
    aufnahmen_button: pygame.Rect
    recover_button: pygame.Rect
    text_box_rect: pygame.Rect

    # Für draw_button (x,y,w,h)
    positionx_btn: int
    positiony_btn: int
    button_width: int
    button_height: int


def run_loop(
    cfg: SimConfig,
    rt: SimRuntime,
    es: EventSource,
    modes: ModeManager,
    ui: UICtx,
    ui_rects: UIRects,
    map_service: MapService,
    cars: List[Car],
    collision_button,
    sensor_button,
    finalize_exit: Callable[[bool], None],
) -> None:

    running = True
    while running:
        # ----------------------------
        # Resize
        # ----------------------------
        for ev in es.poll_resize():
            size = ev.payload["size"]
            rt.window_size = size
            ui.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            map_service.resize(size)
            log.debug("Resize-Event: window_size=%s", size)

        # ----------------------------
        # Pause-Loop
        # ----------------------------
        while rt.paused:
            events = es.poll()
            for ev in events:
                if ev.type == "QUIT":
                    log.info("Quit während Pause → harter Exit.")
                    finalize_exit(cfg.hard_exit)
                if ev.type == "ESC":
                    log.info("ESC während Pause → harter Exit.")
                    finalize_exit(cfg.hard_exit)

            actions = modes.apply(events, rt, ui_rects, cars)
            if actions.get("recover_snapshot"):
                cars = moment_recover(rt.file_text)

        # ----------------------------
        # Aktive Events
        # ----------------------------
        events = es.poll()
        for ev in events:
            if ev.type == "QUIT":
                log.info("Quit-Event → harter Exit.")
                finalize_exit(cfg.hard_exit)
            if ev.type == "ESC":
                if cars:
                    cars[0].alive = False
                log.info("ESC → harter Exit angefordert.")
                finalize_exit(cfg.hard_exit)

        for ev in events:
            if ev.type == "TOGGLE_TRACKS":
                rt.drawtracks = not rt.drawtracks
                log.debug("DrawTracks toggled → %s", rt.drawtracks)
            elif ev.type == "KEY_CHAR":
                rt.file_text += ev.payload["char"]
            elif ev.type == "BACKSPACE":
                rt.file_text = rt.file_text[:-1]

        actions = modes.apply(events, rt, ui_rects, cars)
        if actions.get("take_snapshot"):
            moment_aufnahmen(cars)
            log.info("Momentaufnahme gespeichert; Pause aktiviert.")
        if actions.get("recover_snapshot"):
            cars = moment_recover(rt.file_text)
            log.info("Momentaufnahme wiederhergestellt: %s", rt.file_text)

        # Toggle-Buttons brauchen raw Events
        for raw in es.last_raw():
            collision_button.handle_event(raw, 3)
            sensor_button.handle_event(raw, 2)

        # ----------------------------
        # Hintergrund
        # ----------------------------
        map_service.blit(ui.screen)

        # ----------------------------
        # Update & Draw Cars
        # ----------------------------
        still_alive = 0
        sensor_status = sensor_button.get_status()
        collision_status = collision_button.get_status()

        for c in cars:
            if c.is_alive():
                still_alive += 1
                c.update(ui.screen, rt.drawtracks, sensor_status, collision_status)

        if still_alive == 0:
            log.info("Alle Fahrzeuge tot → Runde beendet.")
            break

        for c in cars:
            if c.is_alive():
                c.draw(ui.screen)

        # ----------------------------
        # Dialog & Buttons
        # ----------------------------
        if modes.show_dialog:
            # ALT (war zuvor in Interface): jetzt via screen_service
                # Compute dialog/button positions dynamically from current screen size
                # so clicks (ui_rects) match the drawn dialog even after resize/DPI changes.
                draw_dialog(ui.screen)
                sw, sh = ui.screen.get_size()
                dialog_w, dialog_h = 500, 200
                dialog_x = (sw - dialog_w) // 2
                dialog_y = (sh - dialog_h) // 2
                button_dialog_width = 100
                button_dialog_height = 30
                button_padding = 30
                button_dialog_x = dialog_x + 100
                button_dialog_y = dialog_y + dialog_h - button_dialog_height - button_padding

                # Update UI rects (so ModeManager collision checks match what's drawn)
                ui_rects.button_yes_rect.x = button_dialog_x
                ui_rects.button_yes_rect.y = button_dialog_y
                ui_rects.button_yes_rect.w = button_dialog_width
                ui_rects.button_yes_rect.h = button_dialog_height

                ui_rects.button_no_rect.x = button_dialog_x + button_dialog_width + 100
                ui_rects.button_no_rect.y = button_dialog_y
                ui_rects.button_no_rect.w = button_dialog_width
                ui_rects.button_no_rect.h = button_dialog_height

                draw_button(
                    ui.screen, "Yes", (0, 0, 0), (0, 255, 0),
                    ui_rects.button_yes_rect.x, ui_rects.button_yes_rect.y, ui_rects.button_yes_rect.w, ui_rects.button_yes_rect.h, ui_rects.button_yes_rect
                )
                draw_button(
                    ui.screen, "No", (0, 0, 0), (255, 0, 0),
                    ui_rects.button_no_rect.x, ui_rects.button_no_rect.y, ui_rects.button_no_rect.w, ui_rects.button_no_rect.h, ui_rects.button_no_rect
                )

        # Haupt-Buttons
        draw_button(
            ui.screen, ui.text1, ui.text_color, ui.button_color,
            ui.positionx_btn, ui.positiony_btn,
            ui.button_width, ui.button_height, ui.button_regelung1_rect
        )
        draw_button(
            ui.screen, ui.text2, ui.text_color, ui.button_color,
            ui.positionx_btn, ui.positiony_btn + ui.button_height + 30,
            ui.button_width, ui.button_height, ui.button_regelung2_rect
        )

        # ----------------------------
        # Regelung
        # ----------------------------
        if modes.regelung_py:
            Interface.regelungtechnik_python(cars)
        else:
            Interface.regelungtechnik_c(cars)

        # ----------------------------
        # HUD / Guides
        # ----------------------------
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.line(ui.screen, (0, 255, 255), (mouse_pos[0], 0), (mouse_pos[0], HEIGHT), 1)
        pygame.draw.line(ui.screen, (255, 100, 0), (0, mouse_pos[1]), (WIDTH, mouse_pos[1]), 1)
        ui.font_ft.render_to(ui.screen, (WIDTH - 150, HEIGHT - 60), f"Position: {mouse_pos}", (0, 0, 255))

        text = ui.font_gen.render("Generation: " + str(rt.current_generation), True, (0, 0, 0))
        ui.screen.blit(text, text.get_rect(center=(int(130 / 4 * f), int(450 / 2 * f))))

        text = ui.font_alive.render("Still Alive: " + str(still_alive), True, (0, 0, 0))
        ui.screen.blit(text, text.get_rect(center=(int(130 / 4 * f), int(490 / 2 * f))))

        # Daten-Text (HUD) – stabil formatiert
        if cars:
            lines = build_car_info_lines(cars[0], modes.regelung_py)
            for i, line in enumerate(lines):
                ui.font_ft.render_to(
                    ui.screen,
                    (int(315 * f), int(285 * f + i * 20 * f)),
                    line,
                    (255, 0, 100),
                )

        # UI-Buttons (Aufnahme/Recovery/Textbox)
        pygame.draw.rect(ui.screen, pygame.Color("red"), ui.aufnahmen_button)
        pygame.draw.rect(ui.screen, pygame.Color("blue"), ui.recover_button)
        pygame.draw.rect(ui.screen, pygame.Color("gray"), ui.text_box_rect)
        ui.font_ft.render_to(ui.screen, (ui.aufnahmen_button.x + 5, ui.aufnahmen_button.y + 5), "Aufnahmen", pygame.Color("white"))
        ui.font_ft.render_to(ui.screen, (ui.recover_button.x + 5, ui.recover_button.y + 5), "File_Recover", pygame.Color("white"))
        ui.font_ft.render_to(ui.screen, (ui.text_box_rect.x + 5, ui.text_box_rect.y + 5), rt.file_text, pygame.Color("black"))

        # Toggles rendern
        collision_button.draw(ui.screen)
        sensor_button.draw(ui.screen)

        # Flip & Tick
        pygame.display.flip()
        ui.clock.tick(cfg.fps)
