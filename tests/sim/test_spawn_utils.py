# tests/sim/test_spawn_utils.py
"""Unit-Tests für spawn_from_map() (Car-Initialisierung).

TESTBASIS (ISTQB):
- Anforderung: Auto-Spawn aus MapService-Daten (Position, Winkel)
- Module: crazycar.sim.spawn_utils
- Funktion: spawn_from_map(map_service) → List[Car]
- Konvertierungen: Center→TopLeft, MapAngle→pygameAngle

TESTVERFAHREN:
- Äquivalenzklassen: Mit detect_info, ohne detect_info
- Koordinaten-Transformation: center - CAR_cover_size/2 = top_left
- Winkel-Konvertierung: (360 - map_angle) % 360 = pygame_angle
- Mock-basiert: MapService.get_spawn(), get_detect_info()
"""
import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock, patch
from crazycar.sim.spawn_utils import spawn_from_map


# ===============================================================================
# FIXTURES: Mock-Factories
# ===============================================================================

@pytest.fixture
def mock_map_service():
    """Factory für MapService-Mock."""
    def _create(spawn_x=100.0, spawn_y=200.0, spawn_angle=0.0, detect_info=None):
        mock_map = Mock()
        mock_spawn = Mock()
        mock_spawn.x_px = spawn_x
        mock_spawn.y_px = spawn_y
        mock_spawn.angle_deg = spawn_angle
        mock_map.get_spawn.return_value = mock_spawn
        mock_map.get_detect_info.return_value = detect_info
        return mock_map
    return _create


# ===============================================================================
# TESTGRUPPE 1: Koordinaten-Konvertierung (Center → Top-Left)
# ===============================================================================


@pytest.mark.parametrize("spawn_x, spawn_y, car_size, expected_x, expected_y", [
    (100.0, 200.0, 32, 84.0, 184.0),  # 100-16, 200-16
    (64.0, 128.0, 32, 48.0, 112.0),   # 64-16, 128-16
    (200.0, 300.0, 64, 168.0, 268.0), # 200-32, 300-32
])
def test_spawn_from_map_converts_center_to_top_left(mock_map_service, spawn_x, spawn_y, car_size, expected_x, expected_y):
    """Testbedingung: Spawn center → Car top-left via CAR_cover_size/2 offset.
    
    Erwartung: pos = (spawn_x - car_size/2, spawn_y - car_size/2).
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=spawn_x, spawn_y=spawn_y)
    
    # ACT
    with patch('crazycar.car.constants.CAR_cover_size', car_size):
        cars = spawn_from_map(mock_map)
    
    # ASSERT
    car = cars[0]
    assert car.position[0] == pytest.approx(expected_x, abs=1.0)
    assert car.position[1] == pytest.approx(expected_y, abs=1.0)


# ===============================================================================
# TESTGRUPPE 2: Winkel-Konvertierung (MapService → pygame)
# ===============================================================================

def test_spawn_from_map_converts_angle_no_detect_info():
    """GIVEN: Keine detect_info, WHEN: spawn_from_map(), THEN: angle aus spawn.angle_deg."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 90.0  # MapService-Konvention
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    car = cars[0]
    # Conversion: (360 - 90) % 360 = 270
    assert car.carangle == pytest.approx(270.0, abs=1.0)


def test_spawn_from_map_uses_detect_info_angle():
    """GIVEN: detect_info mit angle_deg, WHEN: spawn_from_map(), THEN: Bevorzugt."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0  # Wird ignoriert
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = {
        "n": 10,  # Genug Pixel für valide Detection
        "cx": 200.0,
        "cy": 100.0,
        "angle_deg": 45.0
    }
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    car = cars[0]
    # Angle aus cx/cy: atan2(100-100, 200-100) = atan2(0, 100) = 0° → pygame=0°
    assert car.carangle == pytest.approx(0.0, abs=5.0)


def test_spawn_from_map_computes_angle_from_line_center():
    """GIVEN: detect_info cx/cy rechts vom Spawn, WHEN: spawn_from_map(), THEN: angle=0° (rechts)."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = {
        "n": 50,
        "cx": 200.0,  # Rechts von spawn
        "cy": 100.0,  # Gleiche Y
        "angle_deg": 0.0
    }
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    car = cars[0]
    # dx=100, dy=0 → atan2(0,100)=0 → pygame: 360-0=0° (nach rechts)
    assert car.carangle == pytest.approx(0.0, abs=2.0)


def test_spawn_from_map_angle_down_when_line_below():
    """GIVEN: detect_info cy unterhalb spawn, WHEN: spawn_from_map(), THEN: angle≈90° (unten)."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = {
        "n": 50,
        "cx": 100.0,  # Gleiche X
        "cy": 200.0,  # Unten
        "angle_deg": 0.0
    }
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    car = cars[0]
    # dx=0, dy=100 → atan2(100, 0)=90° → pygame: (360-90)%360=270°
    # Pygame: 0°=rechts, 90°=oben (wegen Invertierung), 180°=links, 270°=unten
    assert car.carangle == pytest.approx(270.0, abs=5.0)



@pytest.mark.parametrize("detect_info, spawn_angle, expected_angle", [
    (None, 180.0, 180.0),  # detect_info=None → spawn.angle_deg
    ({"n": 0, "cx": 0, "cy": 0, "angle_deg": 0}, 45.0, 315.0),  # n=0 → Fallback
])
def test_spawn_from_map_detect_info_fallback(mock_map_service, detect_info, spawn_angle, expected_angle):
    """Testbedingung: detect_info=None oder n=0 → Fallback zu spawn.angle_deg.
    
    Erwartung: spawn_angle wird verwendet und konvertiert.
    """
    # ARRANGE
    mock_map = mock_map_service(spawn_x=100.0, spawn_y=100.0, spawn_angle=spawn_angle)
    mock_map.get_detect_info.return_value = detect_info
    
    # ACT
    cars = spawn_from_map(mock_map)
    
    # ASSERT
    car = cars[0]
    assert car.carangle == pytest.approx(expected_angle, abs=1.0)


def test_spawn_from_map_detect_info_exception_fallback():
    """GIVEN: get_detect_info() wirft Exception, WHEN: spawn_from_map(), THEN: spawn.angle_deg."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 270.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.side_effect = Exception("Test error")
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    car = cars[0]
    # (360 - 270) % 360 = 90°
    assert car.carangle == pytest.approx(90.0, abs=1.0)


# ------------------- Car-Objekt-Eigenschaften -------------------

def test_spawn_from_map_returns_list_with_one_car():
    """GIVEN: spawn_from_map(), WHEN: aufgerufen, THEN: Liste mit 1 Car."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    # THEN
    assert isinstance(cars, list)
    assert len(cars) == 1


def test_spawn_from_map_car_has_correct_attributes():
    """GIVEN: spawn_from_map(), WHEN: Car erstellt, THEN: Attribute korrekt."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 150.0
    mock_spawn.y_px = 250.0
    mock_spawn.angle_deg = 30.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN
    assert hasattr(car, 'position')
    assert hasattr(car, 'carangle')
    assert isinstance(car.position, list)
    assert len(car.position) == 2


def test_spawn_from_map_car_power_set_to_20():
    """GIVEN: spawn_from_map(), WHEN: Car erstellt, THEN: power=20."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN
    assert car.power == 20


def test_spawn_from_map_car_radars_empty():
    """GIVEN: spawn_from_map(), WHEN: Car erstellt, THEN: radars=[]."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN
    assert car.radars == []


# ------------------- Edge-Cases -------------------

def test_spawn_from_map_negative_coordinates():
    """GIVEN: Spawn mit negativen Koordinaten, WHEN: spawn_from_map(), THEN: Funktioniert."""
    # GIVEN
    from unittest.mock import patch
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = -50.0
    mock_spawn.y_px = -100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    with patch('crazycar.car.constants.CAR_cover_size', 32):
        cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN: -50-16=-66, -100-16=-116
    assert car.position[0] == pytest.approx(-66.0, abs=1.0)
    assert car.position[1] == pytest.approx(-116.0, abs=1.0)


def test_spawn_from_map_angle_360_normalizes():
    """GIVEN: angle_deg=360, WHEN: spawn_from_map(), THEN: Normalisiert zu 0°."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 360.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = None
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN: (360 - 360) % 360 = 0
    assert car.carangle == pytest.approx(0.0, abs=1.0)


def test_spawn_from_map_detect_info_large_n():
    """GIVEN: detect_info n=1000, WHEN: spawn_from_map(), THEN: Verwendet cx/cy."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 0.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = {
        "n": 1000,
        "cx": 300.0,
        "cy": 100.0,
        "angle_deg": 0.0
    }
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN: dx=200, dy=0 → atan2(0, 200)=0 → pygame: 0°
    assert car.carangle == pytest.approx(0.0, abs=2.0)


def test_spawn_from_map_detect_info_missing_keys():
    """GIVEN: detect_info ohne cx/cy, WHEN: spawn_from_map(), THEN: Nutzt Default 0.0."""
    # GIVEN
    mock_map = Mock()
    mock_spawn = Mock()
    mock_spawn.x_px = 100.0
    mock_spawn.y_px = 100.0
    mock_spawn.angle_deg = 120.0
    mock_map.get_spawn.return_value = mock_spawn
    mock_map.get_detect_info.return_value = {
        "n": 10
        # cx/cy fehlen → get('cx', 0.0), get('cy', 0.0)
    }
    
    # WHEN
    cars = spawn_from_map(mock_map)
    car = cars[0]
    # THEN: cx=0.0, cy=0.0 → dx=-100, dy=-100
    # atan2(-100, -100) = -135° → (360 - (-135)) % 360 = 135°
    assert car.carangle == pytest.approx(135.0, abs=5.0)
