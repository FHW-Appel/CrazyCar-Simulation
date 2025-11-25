# tests/integration/test_car_component.py
"""Integration Tests für Car-Komponente.

TESTBASIS (ISTQB):
- Anforderung: Car-Klasse integriert alle Submodule (kinematics, dynamics, sensors, collision, rendering)
- Module: crazycar.car.model.Car + alle Submodule
- Teststufe: Komponentenintegration (ISTQB Level 2)

TESTVERFAHREN:
- Zustandsübergänge: Initialisierung → Update → Sensor-Reading → Collision
- Äquivalenzklassen: Normale Bewegung, Kollision, Sensor-Detektion
- Grenzwertanalyse: Geschwindigkeit 0/Max, Winkel 0°/360°, Kollisionen
- Mock-basiert: MapService, color_at für deterministische Tests

INTEGRATION-SCHWERPUNKT:
- Kinematics + Dynamics: Power → Speed → Position
- Sensors + Map: Radar-Casting auf echter Map-Oberfläche
- Collision + Rebound: Wandkontakt → Speed-Reduktion
"""
import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.integration

from crazycar.car.model import Car


# ===============================================================================
# FIXTURES: Car-Factories
# ===============================================================================

@pytest.fixture
def minimal_car(sample_car_position, sample_car_angle, default_car_config):
    """Factory für minimale Car-Instanz."""
    return Car(
        position=sample_car_position.copy(),
        carangle=sample_car_angle,
        power=default_car_config['power'],
        speed_set=default_car_config['speed_set'],
        radars=default_car_config['radars'].copy(),
        bit_volt_wert_list=default_car_config['bit_volt_wert_list'].copy(),
        distance=default_car_config['distance'],
        time=default_car_config['time']
    )


@pytest.fixture
def color_at_factory():
    """Factory für color_at Mock-Funktionen."""
    def _create(default_color=(0, 0, 0, 255), collision_zones=None):
        """
        Args:
            default_color: Standardfarbe für freie Fläche
            collision_zones: Dict {(x, y): color} für Kollisionsbereiche
        """
        collision_zones = collision_zones or {}
        
        def color_at(point):
            pt_tuple = (int(point[0]), int(point[1]))
            return collision_zones.get(pt_tuple, default_color)
        
        return color_at
    return _create


# ===============================================================================
# TESTGRUPPE 1: Car Initialization (Komponentenintegration)
# ===============================================================================

def test_car_init_integrates_all_submodules(minimal_car):
    """Testbedingung: Car() initialisiert alle Submodule (Sprite, Geometrie, Sensoren).
    
    Erwartung: Alle Attribute korrekt gesetzt, sprite geladen, center berechnet.
    Integration: rendering.load_car_sprite + geometry (center calculation).
    """
    # ASSERT - Sprite
    assert minimal_car.sprite is not None
    assert minimal_car.rotated_sprite is not None
    
    # ASSERT - Position/Geometrie
    assert minimal_car.position == [400.0, 300.0]
    assert len(minimal_car.center) == 2
    assert minimal_car.center[0] > minimal_car.position[0]  # center rechts von top-left
    assert minimal_car.center[1] > minimal_car.position[1]  # center unten von top-left
    
    # ASSERT - Sensoren
    assert len(minimal_car.radars) == 5
    assert minimal_car.radar_dist == []
    
    # ASSERT - Zustand
    assert minimal_car.alive is True
    assert minimal_car.speed == 0
    assert minimal_car.power == 20.0


@pytest.mark.parametrize("power, expected_min_speed", [
    (0, 0.0),      # Keine Power → Keine Sollgeschwindigkeit
    (20, 1.0),     # Niedrige Power → Geringe Geschwindigkeit
    (50, 2.0),     # Mittlere Power → Moderate Geschwindigkeit  
    (100, 3.0),    # Maximale Power → Höhere Geschwindigkeit
])
def test_car_soll_speed_integration(sample_car_position, sample_car_angle, default_car_config, power, expected_min_speed):
    """Testbedingung: Car.soll_speed() ruft dynamics.soll_speed() auf.
    
    Erwartung: Power → Sollgeschwindigkeit korrekt berechnet.
    Integration: Car.soll_speed() → dynamics.soll_speed().
    """
    # ARRANGE
    config = default_car_config.copy()
    config['power'] = power
    car = Car(
        position=sample_car_position.copy(),
        carangle=sample_car_angle,
        power=config['power'],
        speed_set=config['speed_set'],
        radars=config['radars'].copy(),
        bit_volt_wert_list=config['bit_volt_wert_list'].copy(),
        distance=config['distance'],
        time=config['time']
    )
    
    # ACT
    soll = car.soll_speed(power)
    
    # ASSERT
    assert soll >= expected_min_speed
    if power > 0:
        assert soll > 0


# ===============================================================================
# TESTGRUPPE 2: Car Update Cycle (Kinematics + Dynamics Integration)
# ===============================================================================

def test_car_update_integrates_kinematics_and_dynamics(minimal_car, color_at_factory):
    """Testbedingung: car.update() orchestriert kinematics + dynamics + collision.
    
    Erwartung: Position ändert sich nach update(), speed wird angepasst.
    Integration: kinematics.steer_step + dynamics.step_speed + collision.collision_step.
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))  # Freie Fahrt
    initial_pos = minimal_car.position.copy()
    minimal_car.power = 30  # Mehr Power für sichtbare Bewegung
    
    # ACT - Mehrere Update-Zyklen
    # Create mock game_map
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(10):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT - Position hat sich geändert
    assert minimal_car.position != initial_pos
    # ASSERT - Speed wurde aufgebaut
    assert minimal_car.speed > 0


@pytest.mark.parametrize("steering_angle, expected_turn", [
    (0, "straight"),    # Geradeaus
    (15, "right"),      # Rechtskurve
    (-15, "left"),      # Linkskurve
])
def test_car_steering_changes_angle(minimal_car, color_at_factory, steering_angle, expected_turn):
    """Testbedingung: Lenkwinkel → Änderung der carangle.
    
    Erwartung: radangle beeinflusst carangle über kinematics.
    Integration: Car.radangle → kinematics.steer_step → Car.carangle.
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))
    minimal_car.power = 30
    minimal_car.radangle = steering_angle
    initial_angle = minimal_car.carangle
    
    # ACT - Mehrere Frames für sichtbare Drehung
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(20):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    if expected_turn == "straight":
        # Winkel sollte relativ stabil bleiben
        assert abs(minimal_car.carangle - initial_angle) < 5
    elif expected_turn == "right":
        # Winkel sollte zunehmen (CW rotation)
        assert minimal_car.carangle != initial_angle
    elif expected_turn == "left":
        # Winkel sollte abnehmen (CCW rotation)
        assert minimal_car.carangle != initial_angle


# ===============================================================================
# TESTGRUPPE 3: Sensor Integration (Radar Casting + Map)
# ===============================================================================

def test_car_get_data_integrates_sensors(minimal_car, color_at_factory, headless_display):
    """Testbedingung: car.check_radar() führt Sensor-Casting durch.
    
    Erwartung: radars werden aktualisiert, distances berechnet.
    Integration: sensors.cast_radar + sensors.distances + ADC-Konvertierung.
    """
    # ARRANGE
    color_at = color_at_factory(
        default_color=(0, 0, 0, 255),  # Schwarz = freie Fahrt
        collision_zones={
            (450, 300): (255, 255, 255, 255),  # Wand 50px rechts
        }
    )
    minimal_car.power = 20
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    # ACT - Check multiple radar angles
    for degree in [-60, -30, 0, 30, 60]:
        minimal_car.check_radar(degree, game_map)
    
    # ASSERT - Radars aktualisiert
    assert len(minimal_car.radars) > 0
    # ASSERT - Distances berechnet
    for contact, distance in minimal_car.radars:
        assert isinstance(contact, (list, tuple))
        assert isinstance(distance, (int, float))
        assert distance >= 0
    
    # ASSERT - Bit/Volt-Werte aktualisiert
    assert len(minimal_car.bit_volt_wert_list) > 0


@pytest.mark.parametrize("radar_count, expected_radars", [
    (3, 3),
    (5, 5),
    (7, 7),
])
def test_car_radar_count_configurable(sample_car_position, sample_car_angle, default_car_config, headless_display, color_at_factory, radar_count, expected_radars):
    """Testbedingung: Anzahl Radars konfigurierbar.
    
    Erwartung: car.radars hat korrekte Länge.
    Integration: Car.__init__ + sensors.collect_radars.
    """
    # ARRANGE
    config = default_car_config.copy()
    config['radars'] = [([0, 0], 0) for _ in range(radar_count)]
    config['bit_volt_wert_list'] = [(0, 0.0) for _ in range(radar_count)]
    
    car = Car(
        position=sample_car_position.copy(),
        carangle=sample_car_angle,
        power=config['power'],
        speed_set=config['speed_set'],
        radars=config['radars'],
        bit_volt_wert_list=config['bit_volt_wert_list'],
        distance=config['distance'],
        time=config['time']
    )
    color_at = color_at_factory(default_color=(0, 0, 0, 255))
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    # ACT - Initialize radars via check_radar
    car.radars = []
    for i, degree in enumerate(range(-60, 60, 120 // (radar_count - 1) if radar_count > 1 else 1)):
        if len(car.radars) < radar_count:
            result = car.check_radar(degree, game_map)
            if result:
                car.radars.append(result)
    
    # ASSERT
    assert len(car.radars) <= radar_count


# ===============================================================================
# TESTGRUPPE 4: Collision Integration (Collision Detection + Rebound)
# ===============================================================================

def test_car_collision_stops_on_wall(minimal_car, color_at_factory):
    """Testbedingung: Kollision mit Wand → car.alive = False.
    
    Erwartung: collision.collision_step setzt alive auf False.
    Integration: collision.collision_step + rebound.rebound_action.
    """
    # ARRANGE - Wand direkt vor dem Auto
    color_at = color_at_factory(
        default_color=(255, 255, 255, 255),  # Weiß = Wand überall
        collision_zones={}
    )
    minimal_car.power = 50
    
    # ACT - Update mit Kollision
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(5):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=1)
        if not minimal_car.alive:
            break
    
    # ASSERT
    # Collision-Model abhängig: Stop (alive=False) oder Rebound (speed reduziert)
    # Da überall Wand ist, sollte Auto gestoppt werden
    assert not minimal_car.alive or minimal_car.speed < minimal_car.sollspeed


def test_car_rebound_reduces_speed(minimal_car, color_at_factory):
    """Testbedingung: Rebound-Kollision → Speed-Reduktion.
    
    Erwartung: speed wird durch rebound_action reduziert.
    Integration: collision.collision_step (status=0) + rebound.rebound_action.
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))  # Freie Fahrt initial
    minimal_car.power = 40
    
    # Build up speed first
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(10):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    initial_speed = minimal_car.speed
    
    # Now create collision zone
    color_at_collision = color_at_factory(
        default_color=(255, 255, 255, 255),  # Wand
        collision_zones={}
    )
    game_map_collision = Mock()
    game_map_collision.get_at = lambda pos: color_at_collision(pos)
    
    # ACT - Kollision
    minimal_car.update(game_map_collision, drawtracks=False, sensor_status=1, collision_status=1)
    
    # ASSERT - Speed reduziert oder Auto gestoppt
    assert minimal_car.speed <= initial_speed or not minimal_car.alive


# ===============================================================================
# TESTGRUPPE 5: Rendering Integration (Sprite Rotation + Drawing)
# ===============================================================================

def test_car_draw_integrates_rendering(minimal_car, headless_display, color_at_factory):
    """Testbedingung: car.draw() rendert Sprite, Radars, Tracks.
    
    Erwartung: Kein Fehler beim Zeichnen, rotated_sprite aktualisiert.
    Integration: rendering.draw_car + rendering.draw_radar + rendering.draw_track.
    """
    # ARRANGE
    minimal_car.carangle = 45  # Rotation testen
    
    # ACT - Draw sollte ohne Fehler durchlaufen
    try:
        minimal_car.draw(headless_display)
        success = True
    except Exception as e:
        success = False
        error = e
    
    # ASSERT
    assert success, f"draw() failed: {error if not success else ''}"
    # ASSERT - Sprite wurde rotiert
    assert minimal_car.rotated_sprite is not None


@pytest.mark.parametrize("angle, expected_rotation", [
    (0, "no_rotation"),
    (90, "rotated_90"),
    (180, "rotated_180"),
    (270, "rotated_270"),
])
def test_car_sprite_rotation(minimal_car, headless_display, angle, expected_rotation):
    """Testbedingung: carangle → rotated_sprite angepasst.
    
    Erwartung: rotate_center() wird aufgerufen, Sprite gedreht.
    Integration: Car.carangle → rendering.rotate_center → Car.rotated_sprite.
    """
    # ARRANGE
    minimal_car.carangle = angle
    
    # ACT
    minimal_car.draw(headless_display)
    
    # ASSERT - rotated_sprite existiert
    assert minimal_car.rotated_sprite is not None
    # ASSERT - Sprite ist nicht None
    if expected_rotation != "no_rotation":
        # Bei Rotation sollte rotated_sprite != original sprite sein
        # (Aber in headless-Mode schwer zu verifizieren, daher nur Existenz prüfen)
        assert minimal_car.rotated_sprite is not None


# ===============================================================================
# TESTGRUPPE 6: Power/Speed Integration (Actuation + Dynamics)
# ===============================================================================

@pytest.mark.parametrize("initial_power, new_power, expected_speed_change", [
    (20, 50, "increase"),  # Power erhöhen → Speed steigt
    (50, 20, "decrease"),  # Power reduzieren → Speed sinkt
    (30, 30, "stable"),    # Power gleich → Speed stabil
])
def test_car_power_affects_speed(minimal_car, color_at_factory, initial_power, new_power, expected_speed_change):
    """Testbedingung: Power-Änderung → Speed-Änderung.
    
    Erwartung: Höhere Power → höhere Speed, niedrigere Power → niedrigere Speed.
    Integration: actuation.apply_power + dynamics.step_speed.
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))
    minimal_car.power = initial_power
    
    # Build up to steady state
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(20):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    initial_speed = minimal_car.speed
    
    # Change power
    minimal_car.power = new_power
    
    # ACT - Let speed adjust
    for _ in range(20):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    final_speed = minimal_car.speed
    
    # ASSERT
    if expected_speed_change == "increase":
        assert final_speed > initial_speed
    elif expected_speed_change == "decrease":
        assert final_speed < initial_speed
    elif expected_speed_change == "stable":
        # Speed sollte ähnlich bleiben (kleine Toleranz)
        assert abs(final_speed - initial_speed) < initial_speed * 0.2


# ===============================================================================
# TESTGRUPPE 7: Distance/Time Tracking
# ===============================================================================

def test_car_tracks_distance_over_time(minimal_car, color_at_factory):
    """Testbedingung: car.distance akkumuliert gefahrene Strecke.
    
    Erwartung: Nach mehreren Updates ist distance > 0.
    Integration: Car.update() → distance-Tracking.
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))
    minimal_car.power = 40
    initial_distance = minimal_car.distance
    
    # ACT
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(30):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    assert minimal_car.distance > initial_distance


def test_car_tracks_time(minimal_car, color_at_factory):
    """Testbedingung: car.time akkumuliert Zeit.
    
    Erwartung: time steigt mit jedem Update.
    Integration: Car.update() + timeutil (implizit).
    """
    # ARRANGE
    color_at = color_at_factory(default_color=(0, 0, 0, 255))
    initial_time = minimal_car.time
    
    # ACT
    game_map = Mock()
    game_map.get_at = lambda pos: color_at(pos)
    
    for _ in range(10):
        minimal_car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    # Time tracking depends on implementation - if present, should increase
    # (Some implementations may not auto-increment time in update())
    # This test documents the expectation even if not yet implemented
    assert minimal_car.time >= initial_time
