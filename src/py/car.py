import math
import sys

import pygame
from scipy.optimize import minimize

import car
import simulation
import numpy as np
import os
import signal

f = 1
# race map
WIDTH = 1920 * f
HEIGHT = 1080 * f


# window_size = (WIDTH, HEIGHT)


def sim_to_real(simpx):
    realcm = (simpx * 1900) / WIDTH  # realmap: 1900cm(17m+1m+1m)<=> WIDTH(1920 * f)pixel
    return realcm


def real_to_sim(realcm):
    simpx = realcm * WIDTH / 1900
    return simpx


CAR_SIZE_Xcm = 40  # Car real size 40cm *20cm
CAR_SIZE_Ycm = 20

CAR_SIZE_X = real_to_sim(CAR_SIZE_Xcm)  # 23.75*2 * f  32.3px
CAR_SIZE_Y = real_to_sim(CAR_SIZE_Ycm)  # 20cm == 16.17px

CAR_cover_size = max(CAR_SIZE_X, CAR_SIZE_Y)

CAR_SIZE_DiffY = real_to_sim(40 - 20)
CAR_Radstand = real_to_sim(25)
CAR_Spurweite = real_to_sim(10)

BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 255)  # Color To Crash on Hit
OutBORDER_COLOR: tuple[int, int, int, int] = (0, 0, 0, 255)


def set_position(self, position):
    self.position = position


class Car:

    def __init__(self, position, carangle, power, speed_set, radars, bit_volt_wert_list, distance, time):
        # Load Car Sprite and Rotate
        CAR_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "car.png")
        self.sprite = pygame.image.load(CAR_IMAGE_PATH).convert()
        self.sprite = pygame.transform.scale(self.sprite, (CAR_cover_size, CAR_cover_size))
        self.rotated_sprite = self.sprite

        # self.position = [690, 740] # Starting Position
        # self.position = [800 * f, 825 * f]  # Starting Position
        # self.position = [840 * f, 930 * f]
        self.position = position
        self.center = [self.position[0] + CAR_cover_size / 2, self.position[1] + CAR_cover_size / 2]  # Calculate Center
        self.corners = []
        self.left_rad = []
        self.right_rad = []
        self.fwert = power
        self.swert = 0
        self.sollspeed = self.soll_speed(power)

        self.speed = 0  # anfang soll_speed

        self.speed_set = speed_set  # Flag For Default Speed Later on

        self.power = power
        self.radangle = 0  # Radlenkung für Fahrwerke
        self.carangle = carangle  # Gesamtausrichtung des Wagens in der simulierten Umgebung

        self.radars = radars  # List For Sensors / Radars
        # self.radarR = self.radars[0:1]
        # self.radarM = self.radars[2:3]
        # self.radarL = self.radars[4:5]
        self.radar_angle = 60
        self.radar_dist = []
        self.bit_volt_wert_list = bit_volt_wert_list  # ADC  [(bit, volt),(,)...]
        self.drawing_radars = []  # Radars To Be Drawn

        self.alive = True  # Boolean To Check If Car is Crashed
        self.speed_slowed = False
        self.angle_enable = True
        self.radars_enable = True
        self.drawradar_enable = True
        self.regelung_enable = True

        self.distance = distance  # Distance Driven
        self.anlog_dist = []
        self.time = time  # Time Passed
        self.start_time = 0
        self.round_time = 0
        self.finished = False
        self.maxpower = 100

    def get_data_to_serialize(self):
        position_x = self.position[0] / f
        position_y = self.position[1] / f
        return {
            'position': [position_x,position_y],
            'carangle': self.carangle,
            'speed': self.speed,
            'speed_set': self.speed_set,
            'radars': self.radars,
            'analog_wert_list': self.bit_volt_wert_list,

            'distance': self.distance,
            'time': self.time,
        }

    def draw_track(self, screen):
        pygame.draw.circle(screen, (180, 180, 0), self.left_rad, 1)
        pygame.draw.circle(screen, (180, 0, 180), self.right_rad, 1)

        pygame.draw.circle(screen, (0, 180, 180), self.corners[2], 1)
        pygame.draw.circle(screen, (180, 180, 180), self.corners[3], 1)

    def draw(self, screen):
        screen.blit(self.rotated_sprite, self.position)  # Draw Sprite
        self.draw_radar(screen)  # OPTIONAL FOR SENSORS

    def draw_radar(self, screen):
        # Optionally Draw All Sensors / Radars
        if self.drawradar_enable:
            for radar in self.radars:
                position = radar[0]
                pygame.draw.line(screen, (0, 255, 0), self.center, position, 1)
                pygame.draw.circle(screen, (0, 255, 0), position, 5)
        else:
            return

    def check_radar(self, degree, game_map):  # , midlength):
        # midradar = False
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.carangle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.carangle + degree))) * length)

        # While We Don't Hit BORDER_COLOR AND length < 300 (just a max) -> go further and further
        while not game_map.get_at((x, y)) == BORDER_COLOR and length < 130 * WIDTH / 1900:
            length = length + 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.carangle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.carangle + degree))) * length)

        # Calculate Distance To Border And Append To Radars List
        dist = int(math.sqrt(math.pow(x - self.center[0], 2) + math.pow(y - self.center[1], 2)))
        self.radars.append([(x, y), dist])

    def get_radars_dist(self):
        # Get Distances To Border Recht Mittel Links
        radars = self.radars
        self.radar_dist = []
        for i, radar in enumerate(radars):
            self.radar_dist.append(int(radar[1]))

        return self.radar_dist

    def linearisierungDA(self):
        dist_list = self.get_radars_dist()
        A = 23962  # pro 2.5v == 1024bit <-->1v == 409.6bit
        B = -20
        AV = 58.5  # Wert in Volt
        BV = -0.05
        bit_volt_wert_list = []
        for dist in dist_list:
            #    dist to real_dist(cm)
            real_dist = sim_to_real(dist)
            if real_dist == 0:
                digital_bit, analog_volt = 0, 0
            else:
                digital_bit = int((A / real_dist) + B)
                analog_volt = (AV / real_dist) + BV
            bit_volt_wert_list.append((digital_bit, analog_volt))
        return bit_volt_wert_list

    def rebound_action(self, game_map, point0, nr):
        # self.speed = 1
        # pygame.draw.circle(game_map, (100, 0, 255), point0, 1)
        if nr in [1, 2]:
            x0 = point0[0]
            y0 = point0[1]
            # point1 = [0, y0]

            radius = 15
            # Die andere Kollisionspunkte zwischen der Rennstrecke und den Wänden werden durch Farbunterschiede identifiziert.
            for vi in range(0, 370, 10):
                angle = math.radians(vi)
                x1 = x0 + radius * math.cos(angle)
                y1 = y0 + radius * math.sin(angle)
                x2 = x0 + radius * math.cos(angle + math.radians(15))
                y2 = y0 + radius * math.sin(angle + math.radians(15))

                point1 = [int(x1), int(y1)]

                if game_map.get_at([int(x1), int(y1)]) == BORDER_COLOR and \
                        game_map.get_at([int(x2), int(y2)]) != BORDER_COLOR:
                    point1 = [int(x1), int(y1)]

                    # Berechnen Sie die Steigung zwischen den beiden Punkten, die Steigung der Kollision
                    # m = (point1[1] - point0[1]) / (point1[0] - point0[0])
                    # pygame.draw.line(game_map, (100, 180, 180), (0, point1[1] - m * point1[0]),
                    #                  (WIDTH, point0[1] + m * (WIDTH - point0[0])), 3)
                    break
            # pygame.draw.circle(game_map, (100, 100, 100), (x1, y1), 1)

            # Berechnung der Vektoren für den Einfallswinkel und die reflektierten Flächen
            theta = np.radians(self.carangle)
            vi = np.array([math.cos(theta), math.sin(theta)])
            vw = np.array([point1[0] - point0[0], point1[1] - point0[1]])  # np.array(point1) - np.array(point)
            cosine = np.dot(vw, vi) / (np.linalg.norm(vw) * np.linalg.norm(vi))
            angle_theta = np.degrees(np.arccos(cosine))

            if angle_theta > 90:
                angle_theta = 180 - angle_theta

            # slower speed
            if angle_theta == 0:
                self.speed = self.speed * 1
            elif angle_theta < 30:
                self.speed = self.speed * 0.8
            elif angle_theta < 60:
                self.speed = self.speed * 0.5
            else:
                self.speed = self.speed * 0.2
            self.speed_slowed = True

            k0 = -1.7
            self.position[0] += k0 * math.cos(math.radians(360 - self.carangle)) * 8 * self.speed * np.sin(
                np.radians(angle_theta))
            self.position[1] += k0 * math.sin(math.radians(360 - self.carangle)) * 8 * self.speed * np.sin(
                np.radians(angle_theta))
            # change angle
            if nr == 1:  # left top
                kt = -1
            else:  # right top
                kt = 1
            # Einstellen des Lenkwinkels auf 8 Grad multipliziert mit dem Koeffizienten.
            turn_angle = 7 * np.sin(np.radians(2 * angle_theta)) +1 # np.sin(np.radians(2*(360-angle_theta)))+0.1
            self.carangle += kt * turn_angle
            self.carangle = (self.carangle % 360 + 360) % 360  # limit carangle 0~360

        elif nr in [3, 4] and self.speed < 0:
            self.speed = 0

    def check_collision(self, game_map):
        # self.alive = True
        nr = 0

        for point in self.corners:
            # If Any Corner Touches Border Color -> Crash
            # Assumes Rectangle
            nr = nr + 1

            # (237, 28, 36, 255)
            if nr == 1 and game_map.get_at((int(point[0]), int(point[1]))) == (237, 28, 36, 255):
                if self.round_time == 0:
                    self.round_time = self.time

                self.finished = True
                # self.speed, self.power = 0, 0
                # self.regelung_enable = False

                print(self.round_time)

                with open('./log.csv', encoding='utf-8', mode='a+') as f:
                    f.write(str(self.round_time))
                    f.write('\n')

                # os.kill(os.getpid(), signal.SIGILL)

            if game_map.get_at((int(point[0]), int(point[1]))) == BORDER_COLOR:
                # check status
                status = simulation.collision_button.get_status()
                if status == 0:
                    self.rebound_action(game_map, point, nr)

                elif status == 1:
                    self.speed = 0
                    self.regelung_enable = False

                elif status == 2:
                    self.alive = False
                break

    def update(self, game_map):
        # Set The Speed To 20 For The First Time
        # Only When Having 4 Output Nodes With Speed Up and Down

        # Increase Distance and Time
        self.distance += self.speed
        self.time += 0.01

        position_tmp = self.position

        self.rotated_sprite = self.rotate_center(self.sprite, self.carangle)

        # geradaus oder lenkung

        if self.radangle != 0:
            self.carangle = self.Lenkeinschlagsänderung()

        position_tmp[0] += math.cos(math.radians(360 - self.carangle)) * self.speed
        position_tmp[1] += math.sin(math.radians(360 - self.carangle)) * self.speed
        # Get Rotated Sprite And Move Into The Right X-Direction   Same For Y-Position
        # Don't Let The Car Go Closer Than 10px To The Edge
        position_tmp[0] = max(position_tmp[0], 10 * f)
        position_tmp[0] = min(position_tmp[0], WIDTH - 10 * f)
        # Calculate New Center
        position_tmp[1] = max(position_tmp[1], 10 * f)
        position_tmp[1] = min(position_tmp[1], WIDTH - 10 * f)

        self.center = [int(position_tmp[0]) + CAR_cover_size / 2, int(position_tmp[1]) + CAR_cover_size / 2]

        set_position(self, position_tmp)

        # Calculate Four Corners
        # Length Is Half The Side
        aus_pixel = 0 * f
        length = 0.5 * CAR_SIZE_X + aus_pixel
        width = 0.5 * CAR_SIZE_Y + aus_pixel
        d = math.sqrt(length ** 2 + width ** 2)
        left_top = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 23))) * d,
                    self.center[1] + math.sin(math.radians(360 - (self.carangle + 23))) * d]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.carangle - 23))) * d,
                     self.center[1] + math.sin(math.radians(360 - (self.carangle - 23))) * d]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 157))) * d,
                       self.center[1] + math.sin(math.radians(360 - (self.carangle + 157))) * d]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 203))) * d,
                        self.center[1] + math.sin(math.radians(360 - (self.carangle + 203))) * d]
        self.corners = [left_top, right_top, left_bottom, right_bottom]

        self.left_rad = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 23))) * (d - 6),
                         self.center[1] + math.sin(math.radians(360 - (self.carangle + 23))) * (d - 6)]
        self.right_rad = [self.center[0] + math.cos(math.radians(360 - (self.carangle - 23))) * (d - 6),
                          self.center[1] + math.sin(math.radians(360 - (self.carangle - 23))) * (d - 6)]

        # Check Collisions And Clear Radars
        self.check_collision(game_map)
        self.radars.clear()
        # Draw tracks
        if simulation.drawtracks:
            self.draw_track(game_map)
        # From -90 To 120 With Step-Size 45 Check Radar
        self.check_radars_enable()
        if self.radars_enable:
            for d in range(-self.radar_angle, self.radar_angle + 1, self.radar_angle):
                self.check_radar(d, game_map)

            self.radar_dist = self.get_radars_dist()
            self.bit_volt_wert_list = self.linearisierungDA()

    def Lenkeinschlagsänderung(self):
        k0 = 1
        if self.radangle < 0:  # rechts
            k0 = -1

        angle_rad = math.radians(abs(self.radangle))
        car_radius = int(CAR_Radstand / math.tan(angle_rad) + CAR_Spurweite / 2)  # CAR_Radstand
        theta = math.degrees(self.speed / car_radius)

        if self.speed > 0:
            self.carangle += k0 * theta
        else:
            self.carangle -= k0 * theta

        while self.carangle < 0:
            self.carangle += 360
        while self.carangle >= 360:
            self.carangle -= 360
        # self.carangle= 2*math.atan(math.tan(angle_rad)*CAR_Radstand)
        return self.carangle

    def is_alive(self):
        # Basic Alive Function
        return self.alive

    def get_reward(self):
        # Calculate Reward (Maybe Change?)
        # return self.distance / 50.0
        return self.distance / (CAR_SIZE_X / 2)

    def rotate_center(self, image, angle):
        # Rotate The Rectangle
        rectangle = image.get_rect()
        rotated_image = pygame.transform.rotate(image, angle)
        rotated_image = rotated_image.convert_alpha()  # surface alpha path
        rotated_image.set_colorkey((255, 255, 255, 255))  # transport color set
        rotated_rectangle = rectangle.copy()
        rotated_rectangle.center = rotated_image.get_rect().center
        rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
        return rotated_image

    def check_radars_enable(self):
        if simulation.sensor_button.get_status() == 0:
            self.radars_enable = self.angle_enable = self.drawradar_enable = True
        else:
            self.radars_enable = False
            self.angle_enable, self.drawradar_enable = False, False

    def servo2IstWinkel(self, servo_wert):
        flag = False
        if servo_wert < 0:
            servo_wert = (-1) * servo_wert
            flag = True

        if servo_wert == 0:
            winkel = 0
        else:
            winkel = 0.03 * servo_wert * servo_wert + 0.97 * servo_wert + 2.23

        if flag:
            return (-1) * winkel
        else:
            return winkel

    def soll_speed(self, power):
        sollspeed = -0.0496 * (power ** 2) + 9.008 * power + 31.8089  # max(0 , self.speed + beschleunigungänderung)
        sollspeed /= 100
        sim_sollspeed = real_to_sim(sollspeed)
        return sim_sollspeed

    def Geschwindigkeit(self, power):
        speed = sim_to_real(self.speed)
        turnback = False
        if power < 0:
            power = (-1) * power
            speed = (-1) * speed
            turnback = True

        if power == 0:
            speed = 0
        else:
            if self.radangle < 5:
                maxspeed = -0.0496 * (
                        power ** 2) + 9.008 * power + 31.8089  # max(0 , self.speed + beschleunigungänderung)
                maxspeed /= 100
            else:
                maxspeed = -81562 * (power ** (-2.47)) + 215.5123
                maxspeed /= 100

            beschleunigung = -2.179 * speed + 0.155 * power * power + 7.015 * power  # fahr von 18 bis 50
            beschleunigung /= 100

            if abs(speed + beschleunigung * 0.01) <= abs(maxspeed):
                speed += beschleunigung * 0.01

        sim_speed = real_to_sim(speed)

        if turnback:
            return (-1) * sim_speed
        else:
            return sim_speed

    def getmotorleistung(self, fwert):

        if 18 > fwert > -18:
            self.power = 0
        elif 18 <= fwert <= self.maxpower:
            self.power = fwert
        elif -18 >= fwert >= (-1) * self.maxpower:
            self.ruckfahren(fwert)
        else:
            pass

    def ruckfahren(self, fwert):
        if self.power > 0:
            self.power = -30
            self.speed = self.Geschwindigkeit(self.power)
            self.delay_ms(10)
            self.power = 0
            self.speed = self.Geschwindigkeit(self.power)
            self.delay_ms(10)
        self.power = fwert

    def delay_ms(self, milliseconds):
        clock = pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < milliseconds:
            clock.tick(100)

    def getwinkel(self, swert):
        if swert == 0:
            return 0

        elif swert >= 10:
            return 10
        elif swert <= -10:
            return -10
        else:
            return swert

    def get_round_time(self):
        return self.round_time

    def get_finished(self):
        return self.finished
