import sys
import os
import time
import datetime
from typing import List

import neat
import pygame
import pygame.freetype
import pickle

from car import Car, WIDTH, HEIGHT, f, sim_to_real
from interface import Interface
from toggle_button import ToggleButton

# --- Globale Sim-Parameter ---
window_size = (WIDTH, HEIGHT)
time_flip = 0.01  # 10ms pro Frame

BORDER_COLOR = (255, 255, 255)  # Color To Crash on Hit

current_generation = 0  # Generation counter
drawtracks = False
paused = False
file_text = ""

# --- Pygame init & Window ---
pygame.init()
screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)

# --- UI-Setup ---
positionx = WIDTH * 0.7 * f
positiony = HEIGHT - 180 * f

font = pygame.freetype.SysFont("Arial", int(19 * f))
clock = pygame.time.Clock()
generation_font = pygame.font.SysFont("Arial", 15)
alive_font = pygame.font.SysFont("Arial", 10)

text_box_rect = pygame.Rect(positionx * 0.73, positiony + 40, 200, 30)
aufnahmen_button = pygame.Rect(positionx, positiony, 100, 30)
recover_button = pygame.Rect(positionx, positiony + 40, 100, 30)

collision_button = ToggleButton(
    positionx * 1.2,
    positiony,
    "Collision-Model: Rebound",
    "Collision-Model: Stop",
    "Collision-Model: Remove",
)
sensor_button = ToggleButton(
    collision_button.rect.x,
    positiony + collision_button.rect.height + 5,
    "Sensor Enabled",
    "Sensor Unable",
    "",
)

button_width = 215
button_height = 45
button_color = (0, 255, 0)
positionx_btn = 1700 * f
positiony_btn = 530 * f
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

# Initialzeichung der Toggles
collision_button.draw(screen)
sensor_button.draw(screen)

text1 = "c_regelung"
text2 = "python_regelung"
text_color = (0, 0, 0)

regelung_py = True
time_printed = False


def run_simulation(genomes, config):
    """NEAT Callback: führt 1 Simulationslauf aus."""
    map_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "Racemap.png")

    nets = []
    cars: List[Car] = []

    global drawtracks, regelung_py, time_printed, current_generation, paused, file_text

    show_dialog = False
    button_py = False
    button_c = False

    # Netze aufbauen (für spätere Nutzung – aktuell nicht genutzt)
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

    # Ein Fahrzeug spawnen (Startposition ggf. anpassen)
    new_car = Car([280 * f, 758 * f], 0, 20, False, [], [], 0, 0)
    cars.append(new_car)

    # Map laden
    game_map = pygame.image.load(map_path).convert()
    game_map = pygame.transform.scale(game_map, window_size)

    current_generation += 1
    counter = 0

    while True:
        # --- Pause-Bildschirm ---
        while paused:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    paused = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if aufnahmen_button.collidepoint(event.pos):
                        paused = False
                    if button_no_rect.collidepoint(event.pos):
                        if button_py:
                            regelung_py = True
                            button_py = False
                        if button_c:
                            regelung_py = False
                            button_c = False
                        paused = False
                        show_dialog = False
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

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = True
                elif event.key == pygame.K_t:
                    drawtracks = not drawtracks
                elif event.key == pygame.K_ESCAPE:
                    if cars:
                        cars[0].alive = False
                    pygame.quit()
                    sys.exit(0)
                elif event.unicode.isalnum():
                    file_text += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    file_text = file_text[:-1]
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if aufnahmen_button.collidepoint(event.pos):
                    moment_aufnahmen(cars)
                    paused = True
                if button_regelung1_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_py = True
                if button_regelung2_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_c = True
                if recover_button.collidepoint(event.pos):
                    cars = moment_recover(file_text)

            collision_button.handle_event(event, 3)
            sensor_button.handle_event(event, 2)

        # --- Zeichenfläche ---
        screen.blit(game_map, (0, 0))

        # --- Update aller Cars ---
        still_alive = 0
        sensor_status = sensor_button.get_status()
        collision_status = collision_button.get_status()

        for i, c in enumerate(cars):
            if c.is_alive():
                still_alive += 1
                # NEU: update-Signatur übergeben (drawtracks, sensor_status, collision_status)
                c.update(game_map, drawtracks, sensor_status, collision_status)
                # genomes[i][1].fitness += c.get_reward()  # ggf. wieder aktivieren

        if still_alive == 0:
            break

        # --- Draw aller Cars ---
        for c in cars:
            if c.is_alive():
                c.draw(screen)

        # --- Dialog & Buttons ---
        if show_dialog:
            Interface.draw_dialog(screen)
            Interface.draw_button(screen, "Yes", (0, 0, 0), (0, 255, 0), button_dialog_x, button_dialog_y,
                                  button_dialog_width, button_dialog_height, button_yes_rect)
            Interface.draw_button(screen, "No", (0, 0, 0), (255, 0, 0), button_dialog_x + button_dialog_width + 100,
                                  button_dialog_y, button_dialog_width, button_dialog_height, button_no_rect)

        Interface.draw_button(screen, text1, text_color, button_color, positionx_btn, positiony_btn,
                              button_width, button_height, button_regelung1_rect)
        Interface.draw_button(screen, text2, text_color, button_color, positionx_btn, positiony_btn + button_height + 30,
                              button_width, button_height, button_regelung2_rect)

        # --- Regelung (C oder Python) ---
        if regelung_py:
            Interface.regelungtechnik_python(cars)
        else:
            Interface.regelungtechnik_c(cars)

        # --- Zeitlimit (optional) ---
        counter += 1
        if counter == 100 * 500:  # Stop After 100FPS * S
            break

        # --- Maus-Guides ---
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.line(screen, (0, 255, 255), (mouse_pos[0], 0), (mouse_pos[0], HEIGHT), 1)
        pygame.draw.line(screen, (255, 100, 0), (0, mouse_pos[1]), (WIDTH, mouse_pos[1]), 1)
        font.render_to(screen, (WIDTH - 150, HEIGHT - 60), f"Position: {mouse_pos}", (0, 0, 255))

        # --- Infos/Labels ---
        text = generation_font.render("Generation: " + str(current_generation), True, (0, 0, 0))
        text_rect = text.get_rect(center=(int(130 / 4 * f), int(450 / 2 * f)))
        screen.blit(text, text_rect)

        text = alive_font.render("Still Alive: " + str(still_alive), True, (0, 0, 0))
        text_rect = text.get_rect(center=(int(130 / 4 * f), int(490 / 2 * f)))
        screen.blit(text, text_rect)

        # Car Info Text (immer Liste zurückgeben => kein enumerate(None))
        car_info_lines = data_text(cars)
        for i, line in enumerate(car_info_lines):
            font.render_to(screen, (int(315 * f), int(285 * f + i * 20 * f)), line, (255, 0, 100))

        # --- UI-Buttons ---
        pygame.draw.rect(screen, pygame.Color("red"), aufnahmen_button)
        pygame.draw.rect(screen, pygame.Color("blue"), recover_button)
        pygame.draw.rect(screen, pygame.Color("gray"), text_box_rect)
        font.render_to(screen, (aufnahmen_button.x + 5, aufnahmen_button.y + 5), "Aufnahmen", pygame.Color("white"))
        font.render_to(screen, (recover_button.x + 5, recover_button.y + 5), "File_Recover", pygame.Color("white"))
        font.render_to(screen, (text_box_rect.x + 5, text_box_rect.y + 5), file_text, pygame.Color("black"))

        collision_button.draw(screen)
        sensor_button.draw(screen)

        pygame.display.flip()
        clock.tick(1 / time_flip)  # 100 FPS


def testregelung(c, time_printed):
    t = c.get_round_time()
    if not time_printed:
        print(t)
        return t


def moment_aufnahmen(cars):
    count = 1
    date = datetime.datetime.now().strftime("%d%M%S")
    doc_text = f"Momentaufnahme_{count}_{date}.pkl"
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MomentAufnahme", doc_text)

    data_to_serialize = [acar.get_data_to_serialize() for acar in cars]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as auf:
        pickle.dump(data_to_serialize, auf)


def moment_recover(file_text_date):
    recover_cars: List[Car] = []
    count = 1
    date = "p1"
    if file_text:
        date = file_text_date

    file_path = os.path.abspath(f"MomentAufnahme/Momentaufnahme_{count}_{date}.pkl")
    with open(file_path, "rb") as ein:
        deserialized_data = pickle.load(ein)

    for data in deserialized_data:
        position_x = data["position"][0] * f
        position_y = data["position"][1] * f
        recover_cars.append(
            Car(
                [position_x, position_y],
                data["carangle"],
                data["speed"],
                data["speed_set"],
                data["radars"],
                data["analog_wert_list"],
                data["distance"],
                data["time"],
            )
        )

    return recover_cars


# --- Info-Text für die HUD-Ausgabe (liefert IMMER eine Liste) ---
def data_text(cars) -> List[str]:
    if not cars:
        return []
    regelung = " Python " if regelung_py else " C "
    c = cars[0]  # HUD zeigt 1. Car
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
