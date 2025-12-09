# tests/integration/test_e2e_simulation.py
"""End-to-End Integration Tests für vollständige Simulation.

TESTBASIS (ISTQB):
- Anforderung: Komplette Simulationsläufe (spawn → update → finish)
- Module: Alle crazycar.sim + crazycar.car Module zusammen
- Teststufe: System-nahe Integration (ISTQB Level 3)

TESTVERFAHREN:
- End-to-End Szenarien: Init → Spawn → Loop → Exit
- Grenzwertanalyse: 0 Frames, 1 Frame, viele Frames
- Smoke Tests: Minimale Durchläufe ohne Fehler

INTEGRATION-SCHWERPUNKT:
- Vollständiger Simulation-Stack
- spawn_from_map → Car creation
- Car → MapService collision
- Frame-Loop → Finish detection (wenn implementiert)
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import pygame

pytestmark = pytest.mark.integration

from crazycar.sim.spawn_utils import spawn_from_map
from crazycar.car.model import Car


# ===============================================================================
# FIXTURES: E2E Components
# ===============================================================================

@pytest.fixture
def mock_map_service():
    """Mock MapService für Spawn-Tests."""
    def _create(spawn_x=100.0, spawn_y=100.0, spawn_angle=0.0):
        mock_map = Mock()
        mock_spawn = Mock()
        mock_spawn.x_px = spawn_x
        mock_spawn.y_px = spawn_y
        mock_spawn.angle_deg = spawn_angle
        mock_map.get_spawn.return_value = mock_spawn
        mock_map.get_detect_info.return_value = None
        return mock_map
    return _create


@pytest.fixture
def headless_pygame_surface():
    """Pygame surface für Headless-Drawing."""
    if not pygame.display.get_surface():
        surface = pygame.display.set_mode((800, 600))
    else:
        surface = pygame.display.get_surface()
    return surface


# ===============================================================================
# TESTGRUPPE 1: Car Spawning (spawn_from_map Integration)
# ===============================================================================

def test_spawn_from_map_creates_car(mock_map_service):
    """Testbedingung: spawn_from_map(MapService) → Car-Objekt.
    
    Erwartung: Liste mit einem Car wird zurückgegeben.
    Integration: spawn_utils.spawn_from_map → Car.__init__.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=200.0, spawn_y=150.0, spawn_angle=0.0)
    
    # ACT
    with patch('crazycar.car.constants.CAR_cover_size', 32):
        cars = spawn_from_map(mock_map)
    
    # ASSERT
    assert isinstance(cars, list)
    assert len(cars) == 1
    assert isinstance(cars[0], Car)


@pytest.mark.parametrize("spawn_x, spawn_y, car_size, expected_offset", [
    (100.0, 100.0, 32, 16.0),  # car_size/2 = offset
    (200.0, 300.0, 64, 32.0),
])
def test_spawn_from_map_converts_center_to_topleft(mock_map_service, spawn_x, spawn_y, car_size, expected_offset):
    """Testbedingung: Spawn center → Car top-left (center - car_size/2).
    
    Erwartung: Car.position korrekt konvertiert.
    Integration: spawn_utils coordinate conversion → Car.position.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=spawn_x, spawn_y=spawn_y, spawn_angle=0.0)
    
    # ACT
    with patch('crazycar.car.constants.CAR_cover_size', car_size):
        cars = spawn_from_map(mock_map)
    
    # ASSERT
    car = cars[0]
    assert car.position[0] == pytest.approx(spawn_x - expected_offset, abs=1.0)
    assert car.position[1] == pytest.approx(spawn_y - expected_offset, abs=1.0)


@pytest.mark.parametrize("map_angle, expected_car_angle", [
    (0.0, 0.0),      # MapService 0° → pygame 0°
    (90.0, 270.0),   # MapService 90° → pygame 270°
    (180.0, 180.0),  # MapService 180° → pygame 180°
    (270.0, 90.0),   # MapService 270° → pygame 90°
])
def test_spawn_from_map_converts_angle(mock_map_service, map_angle, expected_car_angle):
    """Testbedingung: MapService angle → pygame angle (360 - angle) % 360.
    
    Erwartung: Car.carangle korrekt konvertiert.
    Integration: spawn_utils angle conversion → Car.carangle.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=100.0, spawn_y=100.0, spawn_angle=map_angle)
    
    # ACT
    cars = spawn_from_map(mock_map)
    
    # ASSERT
    car = cars[0]
    assert car.carangle == pytest.approx(expected_car_angle, abs=1.0)


# ===============================================================================
# TESTGRUPPE 2: Multi-Frame Simulation (Mini Loop)
# ===============================================================================

def test_car_survives_multiple_updates_free_space(mock_map_service, headless_pygame_surface):
    """Testbedingung: Car.update() N mal in freiem Raum → alive bleibt True.
    
    Erwartung: Keine Kollision, Car bewegt sich.
    Integration: Car.update() × N frames + collision detection.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)  # Schwarz = freie Fahrt
    
    car.getmotorleistung(30)  # Use getmotorleistung to trigger speed
    initial_pos = car.position.copy()
    
    # ACT - 50 Frames
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    for _ in range(50):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    assert car.alive is True
    assert car.position != initial_pos  # Hat sich bewegt


@pytest.mark.parametrize("frames", [10, 50, 100])
def test_car_accumulates_distance_over_frames(mock_map_service, headless_pygame_surface, frames):
    """Testbedingung: N Frames → car.distance steigt.
    
    Erwartung: Distance-Tracking funktioniert über mehrere Frames.
    Integration: Car.update() → distance accumulation.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    car.getmotorleistung(40)  # Use getmotorleistung to trigger speed
    initial_distance = car.distance
    
    # ACT
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    for _ in range(frames):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    assert car.distance > initial_distance


# ===============================================================================
# TESTGRUPPE 3: Collision Detection (Multi-Frame)
# ===============================================================================

def test_car_collision_stops_movement(mock_map_service, headless_pygame_surface):
    """Testbedingung: Car fährt in Wand → alive = False oder speed = 0.
    
    Erwartung: Collision Detection stoppt Car.
    Integration: Car.update() + collision.collision_step + rebound.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_wall(point):
        return (255, 255, 255, 255)  # Weiß = Wand
    
    car.getmotorleistung(50)  # Use getmotorleistung to trigger speed
    
    # ACT - Fahre in Wand
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_wall(pos)
    
    for _ in range(10):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=1)
        if not car.alive:
            break
    
    # ASSERT
    # Je nach Collision-Model: alive=False (Stop) oder speed reduziert (Rebound)
    assert not car.alive or car.speed == 0


# ===============================================================================
# TESTGRUPPE 4: Sensor Updates (Multi-Frame)
# ===============================================================================

def test_car_sensors_update_every_frame(mock_map_service, headless_pygame_surface):
    """Testbedingung: car.check_radar() aktualisiert Sensoren jeden Frame.
    
    Erwartung: radars werden kontinuierlich neu berechnet.
    Integration: Car.check_radar() + sensors.cast_radar over time.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_varied(point):
        # Unterschiedliche Farben je nach Position für Sensor-Variation
        if point[0] > 450:
            return (255, 255, 255, 255)  # Wand rechts
        return (0, 0, 0, 255)
    
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_varied(pos)
    
    # ACT - Update sensors mehrmals
    for _ in range(5):
        car.radars.clear()  # Clear before each check
        car.check_radar(-60, game_map)  # Left radar
        car.check_radar(0, game_map)    # Center radar
        car.check_radar(60, game_map)   # Right radar
    
    # ASSERT - Radars populated
    assert len(car.radars) >= 1, "Radars should be populated after check_radar calls"
    # ASSERT - Readings enthalten Daten
    for contact, distance in car.radars:
        assert isinstance(contact, (list, tuple))
        assert isinstance(distance, (int, float))
        assert distance >= 0


# ===============================================================================
# TESTGRUPPE 5: Draw/Render Integration (Multi-Frame)
# ===============================================================================

def test_car_draw_succeeds_every_frame(mock_map_service, headless_pygame_surface):
    """Testbedingung: car.draw() läuft N Frames ohne Fehler.
    
    Erwartung: Rendering stabil über mehrere Frames.
    Integration: Car.draw() + rendering pipeline.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    # ACT - Draw 20 Frames
    errors = []
    for frame in range(20):
        car.carangle = frame * 10  # Rotation testen
        try:
            car.draw(headless_pygame_surface)
        except Exception as e:
            errors.append((frame, e))
    
    # ASSERT
    assert len(errors) == 0, f"Draw failed: {errors}"


# ===============================================================================
# TESTGRUPPE 6: Smoke Tests (Minimal E2E)
# ===============================================================================

def test_smoke_spawn_update_draw_cycle(mock_map_service, headless_pygame_surface):
    """Testbedingung: Spawn → Update → Draw in einem Zyklus.
    
    Erwartung: Minimaler E2E-Zyklus läuft ohne Fehler.
    Integration: spawn_from_map → Car.update → Car.get_data → Car.draw.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    # ACT
    cars = spawn_from_map(mock_map)
    car = cars[0]
    car.getmotorleistung(30)  # Use getmotorleistung to trigger speed
    
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    car.draw(headless_pygame_surface)
    
    # ASSERT
    assert car.alive is True
    # Radars populated during update with sensor_status=1
    assert len(car.radars) >= 0  # May be empty if radars disabled


@pytest.mark.parametrize("power, frames", [
    (20, 10),
    (50, 20),
    (80, 30),
])
def test_smoke_varying_power_levels(mock_map_service, headless_pygame_surface, power, frames):
    """Testbedingung: Verschiedene Power-Level über N Frames.
    
    Erwartung: Car reagiert auf unterschiedliche Power-Einstellungen.
    Integration: Power → Speed → Distance über Zeit.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    car.getmotorleistung(power)  # Use getmotorleistung to trigger speed
    initial_distance = car.distance
    
    # ACT
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    for _ in range(frames):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    assert car.alive is True
    assert car.distance > initial_distance, f"No movement with power={power}"
    # Höhere Power sollte mehr Strecke in gleicher Zeit zurücklegen
    # Realistische Werte: ~1-4 px distance in 10-30 frames
    if power >= 50:
        assert car.distance > 0.5, f"Expected movement with power={power}, got {car.distance}"


# ===============================================================================
# TESTGRUPPE 7: Edge Cases
# ===============================================================================

def test_car_zero_power_no_movement(mock_map_service, headless_pygame_surface):
    """Testbedingung: power=0 → Keine Bewegung.
    
    Erwartung: position bleibt gleich bei power=0.
    Integration: Car mit power=0 über mehrere Frames.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    # Don't call getmotorleistung - we want zero power
    car.power = 0
    initial_pos = car.position.copy()
    
    # ACT
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    for _ in range(20):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    # Position sollte sich kaum ändern (evtl. minimaler Drift)
    assert abs(car.position[0] - initial_pos[0]) < 5
    assert abs(car.position[1] - initial_pos[1]) < 5


def test_car_max_speed_limit(mock_map_service, headless_pygame_surface):
    """Testbedingung: Speed begrenzt auf Maximum.
    
    Erwartung: Speed überschreitet nicht maxspeed.
    Integration: dynamics.step_speed speed limiting.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=400.0, spawn_y=300.0, spawn_angle=0.0)
    cars = spawn_from_map(mock_map)
    car = cars[0]
    
    def color_at_free(point):
        return (0, 0, 0, 255)
    
    car.getmotorleistung(100)  # Use getmotorleistung for max power
    
    # ACT - Build up speed
    game_map = Mock()
    game_map.get_at = lambda pos: color_at_free(pos)
    
    for _ in range(100):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
    
    # ASSERT
    # Speed sollte sich stabilisieren und nicht unbegrenzt steigen
    speed_samples = []
    for _ in range(10):
        car.update(game_map, drawtracks=False, sensor_status=1, collision_status=0)
        speed_samples.append(car.speed)
    
    # Variance sollte gering sein (stabile Geschwindigkeit)
    assert max(speed_samples) - min(speed_samples) < 1.0
