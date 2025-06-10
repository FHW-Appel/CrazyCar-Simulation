import math
import random
import sys
import os
import time
from typing import Tuple
import datetime
import neat
import numpy as np
import pygame
import pickle
import pygame.freetype
import cffi
import math
from PIL import Image
from car import Car
import car
from interface import Interface


from toggle_button import ToggleButton
from scipy.optimize import minimize

f = car.f

WIDTH = 1920 * f  #
HEIGHT = 1080 * f
window_size = (WIDTH, HEIGHT)

time_flip = 0.01  # 10ms

# CAR_SIZE_X = 23.75 * 2 * f
# CAR_SIZE_Y = 10 * 2 * f

BORDER_COLOR = (255, 255, 255)  # Color To Crash on Hit

current_generation = 0  # Generation counter
drawtracks = False
paused = False
file_text = ""

# Initialize PyGame And The Display
pygame.init()
screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)  # , pygame.FULLSCREEN

# BUTTON setting
positionx = WIDTH * 0.7 * f
positiony = HEIGHT - 180 * f

# font setting
font = pygame.freetype.SysFont("Arial", 19*f)
clock = pygame.time.Clock()
generation_font = pygame.font.SysFont("Arial", 15)
alive_font = pygame.font.SysFont("Arial", 10)

text_box_rect = pygame.Rect(positionx * 0.73, positiony + 40, 200, 30)
aufnahmen_button = pygame.Rect(positionx, positiony, 100, 30)
recover_button = pygame.Rect(positionx, positiony + 40, 100, 30)
collision_button = ToggleButton(positionx * 1.2, positiony,
                              'Collision-Model: Rebound', 'Collision-Model: Stop', 'Collision-Model: Remove')
sensor_button = ToggleButton(collision_button.rect.x, positiony + collision_button.rect.height + 5
                             , "Sensor Enabled", "Sensor Unable", "")
button_width = 215
button_height = 45
button_color = (0, 255, 0)
positionx = 1700 * f
positiony = 530 * f
button_regelung1_rect = pygame.Rect(positionx, positiony, button_width, button_height)
button_regelung2_rect = pygame.Rect(positionx, positiony + button_height + 30, button_width, button_height)
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
button_no_rect = pygame.Rect(button_dialog_x + button_dialog_width + 100, button_dialog_y, button_dialog_width,
                             button_dialog_height)
collision_button.draw(screen)
sensor_button.draw(screen)
# switch_regelungbutton.draw(screen)
text1 = "c_regelung"
text_color = (0, 0, 0)
text2 = "python_regelung"

regelung_py = True
time_printed = False




def run_simulation(genomes, config):
    # Empty Collections For Nets and Cars
    map_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "Racemap.png")

    nets = []
    cars = []
    global drawtracks
    global regelung_py
    global time_printed

    show_dialog = False
    button_py = False
    button_c = False


    # regelung_py = True
    # For All Genomes Passed Create A New Neural Network
    for i, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

        # _init__(self, position, carangle, power, speed_set, radars,  bit_volt_wert_list, distance, time)
        # position anfang: Racemap[280 * f, 758 * f]  Rmap:[900 * f, 937 * f]]    [790 * f, 825 * f]  [210 * f, 250 * f], [632 * f, 682 * f]310°[900 * f, 937 * f][1150 * f, 775 * f]
    new_car = Car([280 * f, 758 * f], 0, 20 ,False, [], [], 0, 0)
    cars.append(new_car)

    # Clock Settings
    # Font Settings & Loading Map

    game_map = pygame.image.load(map_path).convert()# Convert Speeds Up A Lot
    game_map = pygame.transform.scale(game_map, window_size)

    global current_generation, paused, file_text
    current_generation += 1

    # Simple Counter To Roughly Limit Time (Not Good Practice)
    counter = 0

    while True:

        while paused:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # recover sys
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
                        cars[0].alive = False
                        paused = False
                        show_dialog = False
        # system action
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                # space ==pause
                if event.key == pygame.K_SPACE:
                    paused = True
                    # t == draw tracks
                elif event.key == pygame.K_t:
                    drawtracks = not drawtracks
                    #  Textbox input
                elif event.key == pygame.K_ESCAPE:
                    cars[0].alive = False
                    pygame.quit()
                    sys.exit(0)



                elif event.unicode.isalnum():
                    file_text += event.unicode
                elif event.key == pygame.K_BACKSPACE:
                    file_text = file_text[:-1]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # BUTTON_Aufnahmen
                if aufnahmen_button.collidepoint(event.pos):
                    moment_aufnahmen(cars)
                    paused = True
                    # pygame.time.wait(500)  # warten 3 sekunden
                # RECOVER button
                if button_regelung1_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_py = True
                if button_regelung2_rect.collidepoint(event.pos):
                    show_dialog = True
                    paused = True
                    button_c = True
                if recover_button.collidepoint(event.pos):
                    print(f"file recovered: {file_text}")
                    cars = moment_recover(file_text)

            collision_button.handle_event(event, 3)
            sensor_button.handle_event(event, 2)
        screen.blit(game_map, (0, 0))

        # Check If Car Is Still Alive
        still_alive = 0
        # Increase Fitness If Yes And Break Loop If Not
        for i, car in enumerate(cars):
            if car.is_alive():
                still_alive += 1
                car.update(game_map)
                #   genomes[i][1].fitness += car.get_reward()

        if still_alive == 0:
            break
        for car in cars:
            if car.is_alive():
                car.draw(screen)
        if show_dialog:
            Interface.draw_dialog(screen)
            Interface.draw_button(screen, "Yes", (0, 0, 0), (0, 255, 0), button_dialog_x, button_dialog_y,
                                  button_dialog_width, button_dialog_height, button_yes_rect)
            Interface.draw_button(screen, "No", (0, 0, 0), (255, 0, 0), button_dialog_x + button_dialog_width + 100,
                                  button_dialog_y, button_dialog_width, button_dialog_height, button_no_rect)

        Interface.draw_button(screen, text1, text_color, button_color, positionx, positiony, button_width,
                              button_height, button_regelung1_rect)
        Interface.draw_button(screen, text2, text_color, button_color, positionx, positiony + button_height + 30,
                              button_width,
                              button_height, button_regelung2_rect)
        # Draw Map And All Cars That Are Alive
        if  regelung_py:
            Interface.regelungtechnik_python(cars)
        else:
            Interface.regelungtechnik_c(cars)


        # ************************************************************************************

        # Once sumtime  Zeitcount
        counter += 1
        if counter == 100 * 500:  # Stop After 100FPS * S
            break

        # mouse position
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.line(screen, (0, 255, 255), (mouse_pos[0], 0), (mouse_pos[0], HEIGHT), 1)
        pygame.draw.line(screen, (255, 100, 0), (0, mouse_pos[1]), (WIDTH, mouse_pos[1]), 1)
        font.render_to(screen, (WIDTH - 150, HEIGHT - 60), "Position: {}".format(mouse_pos), (0, 0, 255))

        # screen.blit(mouse_text, mouse_text.get  (WIDTH, HEIGHT-10))

        # Display Info------------------------------------------------------------------------------------
        text = generation_font.render("Generation: " + str(current_generation), True, (0, 0, 0))
        text_rect = text.get_rect(center=(130 / 4 * f, 450 / 2 * f))

        screen.blit(text, text_rect)
        text = alive_font.render("Still Alive: " + str(still_alive), True, (0, 0, 0))
        text_rect = text.get_rect(center=(130 / 4 * f, 490 / 2 * f))
        screen.blit(text, text_rect)

        # Car info_Text
        car_info_lines = data_text(cars)
        for i, line in enumerate(car_info_lines):
            font.render_to(screen, (315 * f, 285 * f + i * 20*f), line, (255, 0, 100))
        # Interface.draw_dialog(screen)

        pygame.draw.rect(screen, pygame.Color('red'), aufnahmen_button)
        pygame.draw.rect(screen, pygame.Color('blue'), recover_button)
        pygame.draw.rect(screen, pygame.Color('gray'), text_box_rect)
        font.render_to(screen, (aufnahmen_button.x + 5, aufnahmen_button.y + 5), "Aufnahmen", pygame.Color('white'))
        font.render_to(screen, (recover_button.x + 5, recover_button.y + 5), "File_Recover", pygame.Color('white'))
        # screen.blit(recover_button_text, (recover_button.x + 5, recover_button.y + 5))
        font.render_to(screen, (text_box_rect.x + 5, text_box_rect.y + 5), file_text, pygame.Color('black'))
        # screen.blit(text_surface, (text_box_rect.x + 5, text_box_rect.y + 5))

        collision_button.draw(screen)
        sensor_button.draw(screen)

        pygame.display.flip()
        clock.tick(1 / time_flip)  # 100 FPS 10ms


def testregelung(c,time_printed):

    time = c.get_round_time()
    if not time_printed:
        print(time)
        return time

def moment_aufnahmen(cars):
    count = 1
    date = str(datetime.datetime.now().strftime("%d%M%S"))
    doc_text = "Momentaufnahme_%d_%s.pkl" % (count, date)
    # file Address
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MomentAufnahme', doc_text)
    # datas
    data_to_serialize = []
    for acar in cars:
        data_to_serialize.append(acar.get_data_to_serialize())

    # Surface object transport into datalist
    with open(file_path, 'wb') as auf:
        pickle.dump(data_to_serialize, auf)

    count += 1


def moment_recover(file_text_date):
    recover_cars = []
    count = 1
    date = "p1"
    if file_text != "":
        date = file_text_date

    file_path = os.path.abspath(f"MomentAufnahme/Momentaufnahme_{count}_{date}.pkl")
    with open(file_path, 'rb') as ein:
        deserialized_data = pickle.load(ein)
        print(deserialized_data)

    for data in deserialized_data:
        position_x = data['position'][0] * f
        position_y = data['position'][1] * f
        recover_cars.append(
            Car( [position_x, position_y],
                data['carangle'],
                data['speed'],
                data['speed_set'],
                data['radars'],
                data['analog_wert_list'],
                data['distance'],
                data['time']))


    return recover_cars


def sim_to_real(simpx):
    realcm = (simpx * 1900) / WIDTH
    return realcm


def real_to_sim(realcm):
    simpx = realcm * WIDTH / 1900
    return simpx


# return text Atrribute
def data_text(cars):
    if regelung_py:
        regelung = " Python "
    else:
        regelung = " C "
    for car in cars:
        car_info = \
            f"Regelung : {regelung}\n   \n " + \
            f"Center Position: " + \
            ", ".join([f"{pos / f:.0f}" for pos in car.center]) \
            + "\n" \
 \
              f"Angle: {car.carangle:.2f} \n" \
              f"Speed: {car.speed:.2f}( px/10ms)    {sim_to_real(car.speed):.2f}( cm/10ms) \n" \
              f"Speed Set: {car.speed_set}\n    " + \
            f"power: {car.power:.1f}\n    " + \
            f"rad_angel: {car.radangle:.2f}\n    " + \
            "\n " +  \
 \
            f"Radars Beruehrungspunkt: \n " + \
            "    " + ", ".join([f"{rad[0]}" for i, rad in enumerate(car.radars)]) \
            + "\n" \
 \
              f"Radars dist(px): " + ", " \
                .join([f"{rad[1]}px" for i, rad in enumerate(car.radars)]) \
            + "\n" \
 \
              f"Radars realdist(cm): " + ", " \
                .join([f"{sim_to_real(rad[1]):.2f}cm" for i, rad in enumerate(car.radars)]) \
            + "\n" \
 \
              f"Analog Wert(Volt) List: " + ", ".join(
                [f"{wertV[1]:.2f}V" for i, wertV in enumerate(car.bit_volt_wert_list)]) \
            + "\n" \
 \
              f"Digital Wert(bit) List: " + ", ".join(
                [f"{wertbit[0]:.0f}" for i, wertbit in enumerate(car.bit_volt_wert_list)]) \
            + "\n\n" \
              f"Distance: {car.distance:.1f} px   {sim_to_real(car.distance):.1f}cm\n" \
              f"Time: {car.time:.2f} s  \nRundenzeit: {car.round_time:.2f}"
        info_lines = car_info.splitlines()

        return info_lines
