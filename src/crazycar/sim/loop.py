"""Main Game Loop - Frame Loop (Event → Update → Draw).

This module contains the central game/simulation loop that orchestrates
all subsystems for each frame.

Core Function:
- run_loop(): Main frame loop coordinating events, updates, rendering

Responsibilities:
1. Event Processing: EventSource → normalized SimEvents
2. Mode Management: Pause, dialog, mode switching (ModeManager)
3. UI Rendering: HUD text, buttons, dialog overlays
4. Car Updates: Physics, sensors, collision per frame
5. Snapshot/Recovery: Trigger save/load operations
6. Exit Handling: Quit events and finalization

Classes:
- UICtx: UI context bundling rendering resources (screen, fonts, colors, rects)

Helper Functions:
- build_car_info_lines(): Format HUD telemetry text

Constants:
- HUD_FONT_SIZE: 19 (scaled font size)
- BUTTON_FONT_SIZE: 15 (button text size)
- STATUS_FONT_SIZE: 10 (status text size)
- UI_MARGIN_RATIO: 0.7 (right margin for HUD)
- UI_BOTTOM_OFFSET: 180 (bottom spacing for controls)

See Also:
- simulation.py: High-level entry point calling run_loop()
- state.py: SimConfig, SimRuntime data structures
- event_source.py: Event normalization
- modes.py: ModeManager for pause/dialog logic
"""

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

# UI Layout Constants
HUD_FONT_SIZE = 19  # Scaled font size for telemetry display
BUTTON_FONT_SIZE = 15  # Font size for UI buttons
STATUS_FONT_SIZE = 10  # Font size for status text
UI_MARGIN_RATIO = 0.7  # Right margin for HUD text (70% of width)
UI_BOTTOM_OFFSET = 180  # Bottom spacing for control buttons (pixels)
BUTTON_WIDTH = 215  # Standard button width (pixels)
BUTTON_HEIGHT = 45  # Standard button height (pixels)
BUTTON_SPACING = 30  # Vertical spacing between buttons (pixels)
DIALOG_WIDTH = 500  # Dialog box width (pixels)
DIALOG_HEIGHT = 200  # Dialog box height (pixels)
DIALOG_BUTTON_WIDTH = 100  # Dialog button width (pixels)
DIALOG_BUTTON_HEIGHT = 30  # Dialog button height (pixels)
DIALOG_BUTTON_PADDING = 30  # Padding around dialog buttons (pixels)
DIALOG_BUTTON_X_OFFSET = 100  # X offset for first dialog button
DIALOG_BUTTON_SPACING = 100  # Spacing between dialog buttons
UI_TEXT_PADDING = 5  # Text padding inside UI elements (pixels)
HUD_CROSSHAIR_THICKNESS = 1  # Crosshair line thickness
HUD_POSITION_OFFSET_X = 150  # Mouse position text X offset from right
HUD_POSITION_OFFSET_Y = 60  # Mouse position text Y offset from bottom
HUD_GENERATION_X_DIVISOR = 4  # X position divisor for generation text
HUD_GENERATION_Y_NUMERATOR = 450  # Y position numerator for generation text
HUD_GENERATION_Y_DIVISOR = 2  # Y position divisor for generation text
HUD_ALIVE_Y_NUMERATOR = 490  # Y position numerator for alive count text
HUD_ALIVE_Y_DIVISOR = 2  # Y position divisor for alive count text
HUD_DATA_X = 315  # X position for telemetry data (scaled by f)
HUD_DATA_Y = 285  # Y position for telemetry data (scaled by f)
HUD_DATA_LINE_SPACING = 20  # Line spacing for telemetry data (scaled by f)


def build_car_info_lines(c: Car, use_python_control: bool) -> List[str]:
    """Format HUD text lines for car telemetry display.
    
    Builds comprehensive status display including position, speed, sensors,
    and control parameters. Stable formatting without nested f-strings.
    
    Args:
        c: Car instance to display info for
        use_python_control: Whether Python or C controller is active
        
    Returns:
        List of formatted strings for on-screen display.
    """
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
        " Radars Contact Point: ",
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
    """UI context bundling all rendering resources for the main loop.
    
    Encapsulates pygame surfaces, fonts, colors, and UI element positions
    to avoid passing many individual parameters to run_loop().
    
    Attributes:
        screen: Main pygame display surface
        font_ft: FreeType font for high-quality text
        font_gen: Generic pygame font for fallback
        font_alive: Font for "alive" status indicator
        clock: Pygame clock for FPS limiting
        text1, text2: Button labels
        text_color, button_color: UI color scheme
        button_regelung1_rect, button_regelung2_rect: Controller selection buttons
        button_yes_rect, button_no_rect: Dialog confirmation buttons
    """
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

    # For draw_button (x,y,w,h)
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
    """Main simulation frame loop - Event processing, updates, rendering.
    
    Orchestrates the complete game loop cycle:
    1. Process events (keyboard, mouse, quit)
    2. Apply mode changes (pause, dialog, snapshots)
    3. Update car physics & sensors (if not paused)
    4. Render frame (map, cars, HUD, UI)
    5. Tick clock for FPS limiting
    
    Args:
        cfg: Simulation configuration (FPS, headless, etc.)
        rt: Runtime state (paused, quit_flag, etc.)
        es: Event source for normalized events
        modes: Mode manager for pause/dialog logic
        ui: UI context with fonts, colors, button rects
        ui_rects: UI rectangles for click detection
        map_service: Map service for background rendering
        cars: List of active car instances
        collision_button: Collision mode toggle widget
        sensor_button: Sensor enable/disable toggle widget
        finalize_exit: Exit callback function
        
    Note:
        Modifies car states (position, speed, sensors), updates runtime state
        (paused, counter), triggers snapshots/recovery, may call finalize_exit()
        on quit, and renders to screen each frame.
    """

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
                    log.info("Quit during pause → hard exit.")
                    finalize_exit(cfg.hard_exit)
                if ev.type == "ESC":
                    log.info("ESC during pause → hard exit.")
                    finalize_exit(cfg.hard_exit)

            actions = modes.apply(events, rt, ui_rects, cars)
            if actions.get("recover_snapshot"):
                cars = moment_recover(rt.file_text)

        # ----------------------------
        # Active events
        # ----------------------------
        events = es.poll()
        for ev in events:
            if ev.type == "QUIT":
                log.info("Quit event → hard exit.")
                finalize_exit(cfg.hard_exit)
            if ev.type == "ESC":
                if cars:
                    cars[0].alive = False
                log.info("ESC → hard exit requested.")
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
            log.info("Snapshot saved; pause activated.")
        if actions.get("recover_snapshot"):
            cars = moment_recover(rt.file_text)
            log.info("Snapshot restored: %s", rt.file_text)

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
            log.info("All vehicles dead → round ended.")
            break

        for c in cars:
            if c.is_alive():
                c.draw(ui.screen)

        # ----------------------------
        # Dialog & Buttons
        # ----------------------------
        if modes.show_dialog:
            # OLD (was previously in Interface): now via screen_service
                # Compute dialog/button positions dynamically from current screen size
                # so clicks (ui_rects) match the drawn dialog even after resize/DPI changes.
                draw_dialog(ui.screen)
                sw, sh = ui.screen.get_size()
                dialog_x = (sw - DIALOG_WIDTH) // 2
                dialog_y = (sh - DIALOG_HEIGHT) // 2
                button_dialog_x = dialog_x + DIALOG_BUTTON_X_OFFSET
                button_dialog_y = dialog_y + DIALOG_HEIGHT - DIALOG_BUTTON_HEIGHT - DIALOG_BUTTON_PADDING

                # Update UI rects (so ModeManager collision checks match what's drawn)
                ui_rects.button_yes_rect.x = button_dialog_x
                ui_rects.button_yes_rect.y = button_dialog_y
                ui_rects.button_yes_rect.w = DIALOG_BUTTON_WIDTH
                ui_rects.button_yes_rect.h = DIALOG_BUTTON_HEIGHT

                ui_rects.button_no_rect.x = button_dialog_x + DIALOG_BUTTON_WIDTH + DIALOG_BUTTON_SPACING
                ui_rects.button_no_rect.y = button_dialog_y
                ui_rects.button_no_rect.w = DIALOG_BUTTON_WIDTH
                ui_rects.button_no_rect.h = DIALOG_BUTTON_HEIGHT

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
            ui.positionx_btn, ui.positiony_btn + ui.button_height + BUTTON_SPACING,
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
        pygame.draw.line(ui.screen, (0, 255, 255), (mouse_pos[0], 0), (mouse_pos[0], HEIGHT), HUD_CROSSHAIR_THICKNESS)
        pygame.draw.line(ui.screen, (255, 100, 0), (0, mouse_pos[1]), (WIDTH, mouse_pos[1]), HUD_CROSSHAIR_THICKNESS)
        ui.font_ft.render_to(ui.screen, (WIDTH - HUD_POSITION_OFFSET_X, HEIGHT - HUD_POSITION_OFFSET_Y), f"Position: {mouse_pos}", (0, 0, 255))

        text = ui.font_gen.render("Generation: " + str(rt.current_generation), True, (0, 0, 0))
        ui.screen.blit(text, text.get_rect(center=(int(130 / HUD_GENERATION_X_DIVISOR * f), int(HUD_GENERATION_Y_NUMERATOR / HUD_GENERATION_Y_DIVISOR * f))))

        text = ui.font_alive.render("Still Alive: " + str(still_alive), True, (0, 0, 0))
        ui.screen.blit(text, text.get_rect(center=(int(130 / HUD_GENERATION_X_DIVISOR * f), int(HUD_ALIVE_Y_NUMERATOR / HUD_ALIVE_Y_DIVISOR * f))))

        # Daten-Text (HUD) – stabil formatiert
        if cars:
            lines = build_car_info_lines(cars[0], modes.regelung_py)
            for i, line in enumerate(lines):
                ui.font_ft.render_to(
                    ui.screen,
                    (int(HUD_DATA_X * f), int(HUD_DATA_Y * f + i * HUD_DATA_LINE_SPACING * f)),
                    line,
                    (255, 0, 100),
                )

        # UI-Buttons (Aufnahme/Recovery/Textbox)
        pygame.draw.rect(ui.screen, pygame.Color("red"), ui.aufnahmen_button)
        pygame.draw.rect(ui.screen, pygame.Color("blue"), ui.recover_button)
        pygame.draw.rect(ui.screen, pygame.Color("gray"), ui.text_box_rect)
        ui.font_ft.render_to(ui.screen, (ui.aufnahmen_button.x + UI_TEXT_PADDING, ui.aufnahmen_button.y + UI_TEXT_PADDING), "Aufnahmen", pygame.Color("white"))
        ui.font_ft.render_to(ui.screen, (ui.recover_button.x + UI_TEXT_PADDING, ui.recover_button.y + UI_TEXT_PADDING), "File_Recover", pygame.Color("white"))
        ui.font_ft.render_to(ui.screen, (ui.text_box_rect.x + UI_TEXT_PADDING, ui.text_box_rect.y + UI_TEXT_PADDING), rt.file_text, pygame.Color("black"))

        # Toggles rendern
        collision_button.draw(ui.screen)
        sensor_button.draw(ui.screen)

        # Flip & Tick
        pygame.display.flip()
        ui.clock.tick(cfg.fps)
