# crazycar/car/model.py
# Fahrzeugmodell und Hilfsfunktionen für CrazyCar-Simulation
import math
import os
import pygame
import numpy as np
from importlib import resources  # robustes Laden aus Paket-Assets

f = 1

# Race map
WIDTH = 1920 * f
HEIGHT = 1080 * f

def sim_to_real(simpx: float) -> float:
    """Pixel -> cm (Streckenbreite 1900cm ~ WIDTH Pixel)"""
    return (simpx * 1900) / WIDTH

def real_to_sim(realcm: float) -> float:
    """cm -> Pixel (Streckenbreite 1900cm ~ WIDTH Pixel)"""
    return realcm * WIDTH / 1900


# Fahrzeugabmessungen (real) und als Sim-Pixel
CAR_SIZE_Xcm = 40  # 40cm x 20cm
CAR_SIZE_Ycm = 20

CAR_SIZE_X = real_to_sim(CAR_SIZE_Xcm)  # ~32px
CAR_SIZE_Y = real_to_sim(CAR_SIZE_Ycm)  # ~16px
CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))  # für quadratische Sprite-Skalierung

CAR_SIZE_DiffY = real_to_sim(40 - 20)
CAR_Radstand = real_to_sim(25)
CAR_Spurweite = real_to_sim(10)

BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 255)  # Crash-Farbe (weiß)
OutBORDER_COLOR: tuple[int, int, int, int] = (0, 0, 0, 255)


def set_position(self, position):
    self.position = position


class Car:
    def __init__(self, position, carangle, power, speed_set, radars, bit_volt_wert_list, distance, time):
        # Car-Sprite laden (mit Alpha) und skalieren
        # Erwartet: car.png liegt in crazycar/assets/
        CAR_IMAGE_PATH = resources.files("crazycar.assets") / "car.png"
        img = pygame.image.load(str(CAR_IMAGE_PATH)).convert_alpha()
        self.sprite = pygame.transform.scale(img, (CAR_cover_size, CAR_cover_size))
        self.rotated_sprite = self.sprite

        self.position = position
        self.center = [self.position[0] + CAR_cover_size / 2, self.position[1] + CAR_cover_size / 2]
        self.corners = []
        self.left_rad = []
        self.right_rad = []

        self.fwert = power
        self.swert = 0
        self.sollspeed = self.soll_speed(power)
        self.speed = 0

        self.speed_set = speed_set
        self.power = power
        self.radangle = 0              # Lenkung (Fahrwerk)
        self.carangle = carangle       # Fahrzeugausrichtung (Grad)

        self.radars = radars
        self.radar_angle = 60
        self.radar_dist = []
        self.bit_volt_wert_list = bit_volt_wert_list
        self.drawing_radars = []

        self.alive = True
        self.speed_slowed = False
        self.angle_enable = True
        self.radars_enable = True
        self.drawradar_enable = True
        self.regelung_enable = True

        self.distance = distance
        self.anlog_dist = []
        self.time = time
        self.start_time = 0
        self.round_time = 0
        self.finished = False
        self.maxpower = 100

    def get_data_to_serialize(self):
        position_x = self.position[0] / f
        position_y = self.position[1] / f
        return {
            'position': [position_x, position_y],
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
        screen.blit(self.rotated_sprite, self.position)
        self.draw_radar(screen)

    def draw_radar(self, screen):
        if self.drawradar_enable:
            for radar in self.radars:
                position = radar[0]
                pygame.draw.line(screen, (0, 255, 0), self.center, position, 1)
                pygame.draw.circle(screen, (0, 255, 0), position, 5)

    def check_radar(self, degree, game_map):
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.carangle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.carangle + degree))) * length)

        # Vorwärts tasten bis Randfarbe oder max-Länge
        while not game_map.get_at((x, y)) == BORDER_COLOR and length < 130 * WIDTH / 1900:
            length += 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.carangle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.carangle + degree))) * length)

        dist = int(math.hypot(x - self.center[0], y - self.center[1]))
        self.radars.append([(x, y), dist])

    def get_radars_dist(self):
        self.radar_dist = [int(r[1]) for r in self.radars]
        return self.radar_dist

    def linearisierungDA(self):
        dist_list = self.get_radars_dist()
        A = 23962  # 2.5V -> 1024bit  /  1V -> 409.6bit
        B = -20
        AV = 58.5
        BV = -0.05
        bit_volt_wert_list = []
        for dist in dist_list:
            real_dist = sim_to_real(dist)
            if real_dist == 0:
                digital_bit, analog_volt = 0, 0
            else:
                digital_bit = int((A / real_dist) + B)
                analog_volt = (AV / real_dist) + BV
            bit_volt_wert_list.append((digital_bit, analog_volt))
        return bit_volt_wert_list

    def rebound_action(self, game_map, point0, nr):
        if nr in [1, 2]:
            x0, y0 = point0
            radius = 15

            for vi in range(0, 370, 10):
                angle = math.radians(vi)
                x1 = x0 + radius * math.cos(angle)
                y1 = y0 + radius * math.sin(angle)
                x2 = x0 + radius * math.cos(angle + math.radians(15))
                y2 = y0 + radius * math.sin(angle + math.radians(15))

                if game_map.get_at([int(x1), int(y1)]) == BORDER_COLOR and \
                   game_map.get_at([int(x2), int(y2)]) != BORDER_COLOR:
                    point1 = [int(x1), int(y1)]
                    break
            else:
                point1 = [int(x0), int(y0)]

            theta = np.radians(self.carangle)
            vi_vec = np.array([math.cos(theta), math.sin(theta)])
            vw_vec = np.array([point1[0] - point0[0], point1[1] - point0[1]])
            cosine = np.dot(vw_vec, vi_vec) / (np.linalg.norm(vw_vec) * np.linalg.norm(vi_vec))
            angle_theta = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

            if angle_theta > 90:
                angle_theta = 180 - angle_theta

            # Geschwindigkeitsdämpfung
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
            self.position[0] += k0 * math.cos(math.radians(360 - self.carangle)) * 8 * self.speed * np.sin(np.radians(angle_theta))
            self.position[1] += k0 * math.sin(math.radians(360 - self.carangle)) * 8 * self.speed * np.sin(np.radians(angle_theta))

            kt = -1 if nr == 1 else 1
            turn_angle = 7 * np.sin(np.radians(2 * angle_theta)) + 1
            self.carangle = (self.carangle + kt * turn_angle) % 360

        elif nr in [3, 4] and self.speed < 0:
            self.speed = 0

    def check_collision(self, game_map, collision_status: int):
        nr = 0
        for point in self.corners:
            nr += 1

            # Ziellinie (rot): Runde fertig
            if nr == 1 and game_map.get_at((int(point[0]), int(point[1]))) == (237, 28, 36, 255):
                if self.round_time == 0:
                    self.round_time = self.time
                self.finished = True
                print(self.round_time)
                with open('./log.csv', encoding='utf-8', mode='a+') as f:
                    f.write(str(self.round_time))
                    f.write('\n')

            # Kollision mit Rand?
            if game_map.get_at((int(point[0]), int(point[1]))) == BORDER_COLOR:
                status = collision_status
                if status == 0:       # Abprallen
                    self.rebound_action(game_map, point, nr)
                elif status == 1:     # Stop
                    self.speed = 0
                    self.regelung_enable = False
                elif status == 2:     # Entfernen
                    self.alive = False
                break

    def update(self, game_map, drawtracks: bool, sensor_status: int, collision_status: int):
        # Zeit/Distanz fortschreiben
        self.distance += self.speed
        self.time += 0.01

        position_tmp = self.position
        self.rotated_sprite = self.rotate_center(self.sprite, self.carangle)

        # Geradeaus oder Lenkung
        if self.radangle != 0:
            self.carangle = self.Lenkeinschlagsänderung()

        # Position anhand Geschwindigkeit
        position_tmp[0] += math.cos(math.radians(360 - self.carangle)) * self.speed
        position_tmp[1] += math.sin(math.radians(360 - self.carangle)) * self.speed

        # Ränder begrenzen
        position_tmp[0] = max(position_tmp[0], 10 * f)
        position_tmp[0] = min(position_tmp[0], WIDTH - 10 * f)
        position_tmp[1] = max(position_tmp[1], 10 * f)
        position_tmp[1] = min(position_tmp[1], HEIGHT - 10 * f)

        self.center = [int(position_tmp[0]) + CAR_cover_size / 2, int(position_tmp[1]) + CAR_cover_size / 2]
        set_position(self, position_tmp)

        # Ecken berechnen
        aus_pixel = 0 * f
        length = 0.5 * CAR_SIZE_X + aus_pixel
        width = 0.5 * CAR_SIZE_Y + aus_pixel
        diag = math.sqrt(length ** 2 + width ** 2)

        left_top = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 23))) * diag,
                    self.center[1] + math.sin(math.radians(360 - (self.carangle + 23))) * diag]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.carangle - 23))) * diag,
                     self.center[1] + math.sin(math.radians(360 - (self.carangle - 23))) * diag]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 157))) * diag,
                       self.center[1] + math.sin(math.radians(360 - (self.carangle + 157))) * diag]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 203))) * diag,
                        self.center[1] + math.sin(math.radians(360 - (self.carangle + 203))) * diag]
        self.corners = [left_top, right_top, left_bottom, right_bottom]

        self.left_rad = [self.center[0] + math.cos(math.radians(360 - (self.carangle + 23))) * (diag - 6),
                         self.center[1] + math.sin(math.radians(360 - (self.carangle + 23))) * (diag - 6)]
        self.right_rad = [self.center[0] + math.cos(math.radians(360 - (self.carangle - 23))) * (diag - 6),
                          self.center[1] + math.sin(math.radians(360 - (self.carangle - 23))) * (diag - 6)]

        # Kollision prüfen (jetzt, wo corners gesetzt sind)
        self.check_collision(game_map, collision_status)

        # Radare neu aufbauen
        self.radars.clear()

        # Track-Linien zeichnen?
        if drawtracks:
            self.draw_track(game_map)

        # Sensoren abhängig vom Status
        self.check_radars_enable(sensor_status)
        if self.radars_enable:
            for deg in range(-self.radar_angle, self.radar_angle + 1, self.radar_angle):
                self.check_radar(deg, game_map)
            self.radar_dist = self.get_radars_dist()
            self.bit_volt_wert_list = self.linearisierungDA()

    def Lenkeinschlagsänderung(self):
        k0 = -1 if self.radangle < 0 else 1
        angle_rad = math.radians(abs(self.radangle))
        car_radius = int(CAR_Radstand / math.tan(angle_rad) + CAR_Spurweite / 2)
        theta = math.degrees(self.speed / car_radius)
        self.carangle = (self.carangle + (k0 * theta if self.speed > 0 else -k0 * theta)) % 360
        return self.carangle

    def is_alive(self):
        return self.alive

    def get_reward(self):
        return self.distance / (CAR_SIZE_X / 2)

    def rotate_center(self, image, angle):
        rectangle = image.get_rect()
        rotated_image = pygame.transform.rotate(image, angle)
        rotated_image = rotated_image.convert_alpha()
        rotated_image.set_colorkey((255, 255, 255, 255))
        rotated_rectangle = rectangle.copy()
        rotated_rectangle.center = rotated_image.get_rect().center
        rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
        return rotated_image

    def check_radars_enable(self, sensor_status: int):
        if sensor_status == 0:
            self.radars_enable = True
            self.angle_enable = True
            self.drawradar_enable = True
        else:
            self.radars_enable = False
            self.angle_enable = False
            self.drawradar_enable = False

    def servo2IstWinkel(self, servo_wert):
        flag = servo_wert < 0
        if flag:
            servo_wert = -servo_wert
        winkel = 0 if servo_wert == 0 else 0.03 * servo_wert * servo_wert + 0.97 * servo_wert + 2.23
        return -winkel if flag else winkel

    def soll_speed(self, power):
        sollspeed = -0.0496 * (power ** 2) + 9.008 * power + 31.8089
        sollspeed /= 100
        return real_to_sim(sollspeed)  # noqa: keep original naming if needed

    def Geschwindigkeit(self, power):
        speed = sim_to_real(self.speed)
        turnback = False
        if power < 0:
            power = -power
            speed = -speed
            turnback = True

        if power == 0:
            speed = 0
        else:
            if self.radangle < 5:
                maxspeed = -0.0496 * (power ** 2) + 9.008 * power + 31.8089
                maxspeed /= 100
            else:
                maxspeed = -81562 * (power ** (-2.47)) + 215.5123
                maxspeed /= 100

            beschleunigung = -2.179 * speed + 0.155 * power * power + 7.015 * power
            beschleunigung /= 100

            if abs(speed + beschleunigung * 0.01) <= abs(maxspeed):
                speed += beschleunigung * 0.01

        sim_speed = real_to_sim(speed)
        return -sim_speed if turnback else sim_speed

    def getmotorleistung(self, fwert):
        if 18 > fwert > -18:
            self.power = 0
        elif 18 <= fwert <= self.maxpower:
            self.power = fwert
        elif -18 >= fwert >= (-1) * self.maxpower:
            self.ruckfahren(fwert)  # noqa: keep original naming if needed
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
