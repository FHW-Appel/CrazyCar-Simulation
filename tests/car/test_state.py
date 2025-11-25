# tests/car/test_state.py
"""Unit-Tests für CarState Datenklasse (Fahrzeugzustand).

TESTBASIS (ISTQB):
- Anforderung: Immutable dataclass für Fahrzeugzustand (Position, Winkel, Geschwindigkeit, Sensoren)
- Module: crazycar.car.state
- Klasse: CarState (Python dataclass)

TESTVERFAHREN:
- Zustandsübergangstest: Creation → Modification → Isolation
- Äquivalenzklassen: Pflichtfelder, optionale Felder mit Defaults
- Grenzwertanalyse: Negative Werte, Zero-Werte, leere Listen
- Mutable State: Listen (radars, corners) isoliert zwischen Instanzen
"""
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.state import CarState


# ===============================================================================
# FIXTURES: CarState-Vorlagen
# ===============================================================================

@pytest.fixture
def minimal_state():
    """Minimale CarState mit Pflichtfeldern."""
    return CarState(
        position=[0.0, 0.0],
        carangle=0.0,
        speed=0.0,
        power=0.0,
        radangle=0.0,
        time=0.0,
        distance=0.0
    )


@pytest.fixture
def full_state():
    """Vollständiger CarState mit typischen Werten."""
    return CarState(
        position=[100.0, 200.0],
        carangle=45.0,
        speed=5.0,
        power=50.0,
        radangle=10.0,
        time=2.5,
        distance=150.0,
        center=[100.0, 200.0],
        corners=[(90.0, 190.0), (110.0, 190.0), (110.0, 210.0), (90.0, 210.0)],
        left_rad=15.0,
        right_rad=-15.0,
        alive=True,
        finished=False,
        round_time=60.0,
        regelung_enable=True,
        radar_angle=60,
        radars=[((150.0, 250.0), 75), ((120.0, 220.0), 80)],
        radar_dist=[75.0, 80.0],
        bit_volt_wert_list=[10, 15, 20]
    )


# ===============================================================================
# TESTGRUPPE 1: Initialisierung - Pflichtfelder
# ===============================================================================

@pytest.mark.parametrize("pos, angle, spd, pwr, rad, t, dist", [
    ([100.0, 200.0], 45.0, 5.0, 50.0, 10.0, 0.0, 0.0),      # Normale Werte
    ([0.0, 0.0], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),             # Zero
    ([-10.0, -20.0], -45.0, -5.0, -30.0, -15.0, 1.0, 50.0), # Negative
])
def test_carstate_creation_with_required_fields(pos, angle, spd, pwr, rad, t, dist):
    """Testbedingung: Pflichtfelder → CarState erstellt.
    
    Erwartung: Alle Felder korrekt gesetzt.
    """
    # ACT
    state = CarState(
        position=pos,
        carangle=angle,
        speed=spd,
        power=pwr,
        radangle=rad,
        time=t,
        distance=dist
    )
    
    # ASSERT
    assert state.position == pos
    assert state.carangle == angle
    assert state.speed == spd
    assert state.power == pwr
    assert state.radangle == rad
    assert state.time == t
    assert state.distance == dist


# ===============================================================================
# TESTGRUPPE 2: Default-Werte für optionale Felder
# ===============================================================================

def test_carstate_defaults_for_optional_fields(minimal_state):
    """Testbedingung: Nur Pflichtfelder → Defaults gesetzt.
    
    Erwartung: center=[0,0], corners=[], alive=True, finished=False, etc.
    """
    # ASSERT
    assert minimal_state.center == [0.0, 0.0]
    assert minimal_state.corners == []
    assert minimal_state.left_rad is None
    assert minimal_state.right_rad is None
    assert minimal_state.alive is True
    assert minimal_state.finished is False
    assert minimal_state.round_time == 0.0
    assert minimal_state.regelung_enable is True
    assert minimal_state.radar_angle == 60
    assert minimal_state.radars == []
    assert minimal_state.radar_dist == []
    assert minimal_state.bit_volt_wert_list == []


@pytest.mark.parametrize("field_name, expected_type", [
    ("alive", bool),
    ("finished", bool),
    ("regelung_enable", bool),
    ("radars", list),
    ("radar_dist", list),
    ("corners", list),
])
def test_carstate_default_field_types(minimal_state, field_name, expected_type):
    """Testbedingung: Default-Felder haben erwartete Typen.
    
    Erwartung: Boolean-Flags sind bool, Listen sind list.
    """
    # ACT
    value = getattr(minimal_state, field_name)
    
    # ASSERT
    assert isinstance(value, expected_type)


# ===============================================================================
# TESTGRUPPE 3: Modifikation - Mutable Lists
# ===============================================================================

def test_carstate_position_is_mutable_list(minimal_state):
    """Testbedingung: position-Liste kann modifiziert werden.
    
    Erwartung: In-Place-Mutation funktioniert.
    """
    # ARRANGE
    original_y = minimal_state.position[1]
    
    # ACT
    minimal_state.position[0] = 30.0
    
    # ASSERT
    assert minimal_state.position == [30.0, original_y]


def test_carstate_can_add_radars(minimal_state):
    """Testbedingung: Radare hinzufügen via append().
    
    Erwartung: Liste erweitert sich.
    """
    # ACT
    minimal_state.radars.append(((100.0, 200.0), 50))
    minimal_state.radars.append(((150.0, 250.0), 60))
    
    # ASSERT
    assert len(minimal_state.radars) == 2
    assert minimal_state.radars[0] == ((100.0, 200.0), 50)


def test_carstate_can_update_alive_flag(minimal_state):
    """Testbedingung: alive-Flag ändern.
    
    Erwartung: Boolean-Zuweisung funktioniert.
    """
    # ARRANGE
    assert minimal_state.alive is True
    
    # ACT
    minimal_state.alive = False
    
    # ASSERT
    assert minimal_state.alive is False


def test_carstate_can_set_corners(minimal_state):
    """Testbedingung: corners-Liste komplett setzen.
    
    Erwartung: Liste überschrieben.
    """
    # ACT
    minimal_state.corners = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]
    
    # ASSERT
    assert len(minimal_state.corners) == 4
    assert minimal_state.corners[0] == (10.0, 10.0)


# ===============================================================================
# TESTGRUPPE 4: Unabhängigkeit von Instanzen
# ===============================================================================

def test_carstate_multiple_instances_independent():
    """Testbedingung: 2 CarState-Objekte sind isoliert.
    
    Erwartung: Änderung in state1 beeinflusst state2 nicht.
    """
    # ARRANGE
    state1 = CarState(
        position=[10.0, 20.0], carangle=45.0, speed=5.0,
        power=50.0, radangle=10.0, time=0.0, distance=0.0
    )
    state2 = CarState(
        position=[100.0, 200.0], carangle=90.0, speed=3.0,
        power=30.0, radangle=-5.0, time=1.0, distance=50.0
    )
    
    # ACT
    state1.speed = 8.0
    state1.alive = False
    
    # ASSERT
    assert state2.speed == 3.0
    assert state2.alive is True


def test_carstate_default_lists_not_shared():
    """Testbedingung: Default-Listen (radars) nicht zwischen Instanzen geteilt.
    
    Erwartung: Jede Instanz hat eigene Listen-Objekte.
    """
    # ARRANGE
    state1 = CarState(
        position=[0.0, 0.0], carangle=0.0, speed=0.0,
        power=0.0, radangle=0.0, time=0.0, distance=0.0
    )
    state2 = CarState(
        position=[0.0, 0.0], carangle=0.0, speed=0.0,
        power=0.0, radangle=0.0, time=0.0, distance=0.0
    )
    
    # ACT
    state1.radars.append(((10.0, 10.0), 5))
    
    # ASSERT
    assert len(state1.radars) == 1
    assert len(state2.radars) == 0


# ===============================================================================
# TESTGRUPPE 5: Edge-Cases - Negative/Zero Werte
# ===============================================================================

@pytest.mark.parametrize("speed, power, distance", [
    (-5.0, -30.0, -50.0),  # Alle negativ
    (0.0, 0.0, 0.0),       # Alle zero
])
def test_carstate_accepts_edge_values(speed, power, distance):
    """Testbedingung: Negative und Zero-Werte erlaubt.
    
    Erwartung: Keine Validierung, alle Werte akzeptiert.
    """
    # ACT
    state = CarState(
        position=[0.0, 0.0],
        carangle=0.0,
        speed=speed,
        power=power,
        radangle=0.0,
        time=0.0,
        distance=distance
    )
    
    # ASSERT
    assert state.speed == speed
    assert state.power == power
    assert state.distance == distance


def test_carstate_negative_position_coordinates():
    """Testbedingung: Negative Position (außerhalb Spielfeld).
    
    Erwartung: Position akzeptiert ohne Constraints.
    """
    # ACT
    state = CarState(
        position=[-100.0, -200.0],
        carangle=0.0, speed=0.0, power=0.0,
        radangle=0.0, time=0.0, distance=0.0
    )
    
    # ASSERT
    assert state.position == [-100.0, -200.0]
