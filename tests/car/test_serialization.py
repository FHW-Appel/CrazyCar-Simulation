# tests/car/test_serialization.py
"""Unit-Tests für Fahrzeugzustands-Serialisierung.

TESTBASIS (ISTQB):
- Anforderung: Serialisierung von Fahrzeugzuständen für JSON-Export
- Module: crazycar.car.serialization
- Funktionen: _listify_point, _listify_radars, serialize_state, serialize_car, to_json

TESTVERFAHREN:
- Äquivalenzklassen: Verschiedene Eingabetypen (tuple/list, int/float, leer/gefüllt)
- Grenzwertanalyse: 0-Werte, negative Werte, große Listen
- Determinismus: Wiederholbare Serialisierung mit identischen Eingaben
- Roundtrip: serialize → to_json → json.loads bleibt inhaltlich konsistent
"""
import json
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.serialization import (
    _listify_point,
    _listify_radars,
    serialize_state,
    serialize_car,
    to_json
)


# ===============================================================================
# FIXTURES: Wiederverwendbare Test-Objekte
# ===============================================================================

@pytest.fixture
def minimal_car():
    """Car-Objekt mit nur Pflichtattributen (Normalfall)."""
    class CarStub:
        position = [100.0, 200.0]
        carangle = 45.0
        speed = 5.0
        speed_set = 10.0
        radars = []
        bit_volt_wert_list = []
        distance = 50.0
        time = 1.5
    return CarStub()


@pytest.fixture
def full_car():
    """Car-Objekt mit allen optionalen Attributen (Vollständigkeit)."""
    class CarStub:
        position = [100.0, 200.0]
        carangle = 90.0
        speed = 8.0
        speed_set = 10.0
        radars = [((150.0, 250.0), 30)]
        bit_volt_wert_list = [(1023, 4.95)]
        distance = 123.4
        time = 5.67
        power = 80.0
        radangle = 15.0
        fwert = 85.0
        swert = 12.0
    return CarStub()


# ===============================================================================
# TESTGRUPPE 1: _listify_point - Koordinaten-Konvertierung
# ===============================================================================
# Testbedingung: Point-Koordinaten (tuple/list, int/float) → float-Liste [x, y]
# Äquivalenzklassen: tuple, list mit int, list mit float, negative Werte

@pytest.mark.parametrize("point, expected", [
    ((10.5, 20.3), [10.5, 20.3]),           # Tuple mit floats
    ([100, 200], [100.0, 200.0]),            # List mit ints
    ([3.14, 2.71], [3.14, 2.71]),            # List mit floats (unverändert)
    ((-50.0, -100.5), [-50.0, -100.5]),      # Negative Werte
])
def test_listify_point_converts_to_float_list(point, expected):
    """Testbedingung: Verschiedene Point-Formate werden in float-Liste konvertiert.
    
    Erwartung: Immer [x, y] als float-Liste, unabhängig von Eingabetyp.
    """
    # ACT
    result = _listify_point(point)
    
    # ASSERT
    assert result == expected
    assert isinstance(result, list)
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)




# ===============================================================================
# TESTGRUPPE 2: _listify_radars - Radar-Daten-Konvertierung
# ===============================================================================
# Testbedingung: Radar-Liste [((x, y), dist), ...] → JSON-Format [[[x, y], dist], ...]
# Äquivalenzklassen: leer, einzeln, mehrfach, float-Distance → int

@pytest.mark.parametrize("radars, expected", [
    ([], []),                                                          # Leer
    ([((100.0, 200.0), 50)], [[[100.0, 200.0], 50]]),                # Einzeln
    ([((10.0, 20.0), 5), ((30.0, 40.0), 10), ((50.0, 60.0), 15)],   # Mehrfach
     [[[10.0, 20.0], 5], [[30.0, 40.0], 10], [[50.0, 60.0], 15]]),
    ([((100.0, 100.0), 42.7)], [[[100.0, 100.0], 42]]),              # Float → int
])
def test_listify_radars_converts_to_json_format(radars, expected):
    """Testbedingung: Radar-Tupel werden in JSON-kompatible Nested-Liste konvertiert.
    
    Erwartung: [[[x, y], dist], ...] mit Point als Liste, Distance als int.
    """
    # ACT
    result = _listify_radars(radars)
    
    # ASSERT
    assert result == expected
    if result:  # Nur prüfen bei nicht-leerer Liste
        assert isinstance(result[0][0], list)  # Point ist Liste
        assert isinstance(result[0][1], int)   # Distance ist int




# ===============================================================================
# TESTGRUPPE 3: serialize_state - Zustandsserialisierung
# ===============================================================================
# TESTBASIS: Zentrale Funktion zur Serialisierung aller Fahrzeugzustände
# Testbedingungen:
#   - Pflichtfelder immer vorhanden (position, carangle, speed, ...)
#   - Optionale Felder nur bei Übergabe (power, radangle, fwert, swert)
#   - f_scale skaliert Position korrekt
#   - Radare/Analog-Werte werden konvertiert

def test_serialize_state_minimal_required_fields():
    """Testbedingung: Nur Pflichtfelder übergeben (Normalfall).
    
    Erwartung: Dict enthält alle Pflichtfelder, keine optionalen Felder.
    """
    # ARRANGE & ACT
    result = serialize_state(
        position_px=(100.0, 200.0),
        carangle_deg=45.0,
        speed_px=5.0,
        speed_set=10.0,
        radars=[],
        bit_volt_wert_list=[],
        distance_px=50.0,
        time_s=1.5
    )
    
    # ASSERT: Pflichtfelder vorhanden
    assert isinstance(result, dict)
    assert result["position"] == [100.0, 200.0]
    assert result["carangle"] == 45.0
    assert result["speed"] == 5.0
    assert result["speed_set"] == 10.0
    assert result["radars"] == []
    assert result["analog_wert_list"] == []
    assert result["distance"] == 50.0
    assert result["time"] == 1.5
    
    # Optionale Felder fehlen
    assert "power" not in result
    assert "radangle" not in result


def test_serialize_state_with_all_optional_fields():
    """Testbedingung: Alle optionalen Felder übergeben (Vollständigkeit).
    
    Erwartung: Alle optionalen Felder erscheinen im Dict.
    """
    # ARRANGE & ACT
    result = serialize_state(
        position_px=(100.0, 200.0),
        carangle_deg=90.0,
        speed_px=8.0,
        speed_set=10.0,
        radars=[((150.0, 250.0), 30)],
        bit_volt_wert_list=[(1023, 4.95)],
        distance_px=123.4,
        time_s=5.67,
        power=80.0,
        radangle=15.0,
        fwert=85.0,
        swert=12.0
    )
    
    # ASSERT: Optionale Felder vorhanden
    assert result["power"] == 80.0
    assert result["radangle"] == 15.0
    assert result["fwert"] == 85.0
    assert result["swert"] == 12.0
    # Radare/Analog konvertiert
    assert result["radars"] == [[[150.0, 250.0], 30]]
    assert result["analog_wert_list"] == [[1023, 4.95]]


def test_serialize_state_with_f_scale():
    """Testbedingung: f_scale-Parameter skaliert Position (Sim→Real-Welt).
    
    Erwartung: position durch f_scale geteilt.
    """
    # ARRANGE & ACT
    result = serialize_state(
        position_px=(100.0, 200.0),
        carangle_deg=0.0,
        speed_px=0.0,
        speed_set=0.0,
        radars=[],
        bit_volt_wert_list=[],
        distance_px=0.0,
        time_s=0.0,
        f_scale=2.0
    )
    
    # ASSERT: Position durch 2.0 geteilt
    assert result["position"] == [50.0, 100.0]




# ===============================================================================
# TESTGRUPPE 4: serialize_car - Car-Objekt Serialisierung
# ===============================================================================
# TESTBASIS: Wrapper-Funktion, die Car-Attribute → serialize_state delegiert
# Testbedingungen: Pflichtattribute, optionale Attribute, f_scale-Parameter

def test_serialize_car_with_minimal_attributes(minimal_car):
    """Testbedingung: Car-Objekt mit nur Pflichtattributen (Normalfall).
    
    Erwartung: Dict enthält alle Pflichtfelder, keine optionalen.
    """
    # ACT
    result = serialize_car(minimal_car)
    
    # ASSERT
    assert result["position"] == [100.0, 200.0]
    assert result["carangle"] == 45.0
    assert result["speed"] == 5.0
    assert result["distance"] == 50.0
    assert "power" not in result
    assert "radangle" not in result


def test_serialize_car_with_optional_attributes(full_car):
    """Testbedingung: Car-Objekt mit allen optionalen Attributen (Vollständigkeit).
    
    Erwartung: Dict enthält optionale Felder (power, radangle, fwert, swert).
    """
    # ACT
    result = serialize_car(full_car)
    
    # ASSERT: Optionale Felder vorhanden
    assert result["power"] == 80.0
    assert result["radangle"] == 15.0
    assert result["fwert"] == 85.0
    assert result["swert"] == 12.0


def test_serialize_car_with_f_scale(minimal_car):
    """Testbedingung: f_scale-Parameter skaliert Position.
    
    Erwartung: Position durch f_scale geteilt.
    """
    # ARRANGE
    minimal_car.position = [200.0, 400.0]
    
    # ACT
    result = serialize_car(minimal_car, f_scale=4.0)
    
    # ASSERT
    assert result["position"] == [50.0, 100.0]  # /4.0




# ===============================================================================
# TESTGRUPPE 5: to_json - Dict → JSON-String Konvertierung
# ===============================================================================
# TESTBASIS: JSON-Serialisierung mit kompakter/formatierter Ausgabe
# Testbedingungen: Einfache Dicts, Nested Structures, indent-Parameter

def test_to_json_converts_dict_to_compact_string():
    """Testbedingung: Dict → JSON ohne indent (Normalfall).
    
    Erwartung: Kompakter JSON-String ohne Newlines.
    """
    # ARRANGE
    data = {"a": 1, "b": 2}
    
    # ACT
    result = to_json(data)
    
    # ASSERT
    assert isinstance(result, str)
    assert "\n" not in result  # Kompakt
    # Dict-Reihenfolge kann variieren
    assert '"a":1' in result and '"b":2' in result


def test_to_json_with_indent_formats_multiline():
    """Testbedingung: Dict → JSON mit indent=2 (lesbare Formatierung).
    
    Erwartung: Multi-line JSON mit Einrückung.
    """
    # ARRANGE
    data = {"key": "value", "number": 42}
    
    # ACT
    result = to_json(data, indent=2)
    
    # ASSERT
    assert "\n" in result       # Multi-line
    assert "  " in result       # Indentation
    assert '"key"' in result and '"value"' in result


def test_to_json_handles_nested_structures():
    """Testbedingung: Nested Dict mit Listen (typischer Serialisierungs-Output).
    
    Erwartung: JSON korrekt serialisiert, Roundtrip json.loads erhält Struktur.
    """
    # ARRANGE
    data = {
        "position": [100.0, 200.0],
        "radars": [[[10.0, 20.0], 5]],
        "analog": [[512, 2.5]]
    }
    
    # ACT
    result = to_json(data)
    
    # ASSERT: Roundtrip bleibt konsistent
    parsed = json.loads(result)
    assert parsed["position"] == [100.0, 200.0]
    assert parsed["radars"] == [[[10.0, 20.0], 5]]
    assert parsed["analog"] == [[512, 2.5]]


def test_to_json_preserves_unicode():
    r"""Testbedingung: Unicode-Zeichen (ensure_ascii=False).
    
    Erwartung: Nicht als \u escapet, lesbar bleibt.
    """
    # ARRANGE
    data = {"text": "Tür"}
    
    # ACT
    result = to_json(data)
    
    # ASSERT
    assert "Tür" in result  # Nicht escaped




# ===============================================================================
# TESTGRUPPE 6: Eigenschaften - Determinismus & Roundtrip
# ===============================================================================
# TESTBASIS: Sicherstellen, dass Serialisierung reproduzierbar und JSON-kompatibel ist
# Testverfahren: Determinismus (gleiche Eingaben → gleiche Ausgaben)
#                Roundtrip (serialize → to_json → json.loads bleibt konsistent)

def test_serialize_state_is_deterministic():
    """Testbedingung: Identische Eingaben → identische Ausgaben (Determinismus).
    
    Erwartung: Zweimaliger Aufruf mit gleichen Parametern liefert == Dicts.
    """
    # ARRANGE
    args = {
        "position_px": (100.0, 200.0),
        "carangle_deg": 45.0,
        "speed_px": 5.0,
        "speed_set": 10.0,
        "radars": [((150.0, 250.0), 30)],
        "bit_volt_wert_list": [(512, 2.5)],
        "distance_px": 123.4,
        "time_s": 5.67,
        "power": 80.0,
    }
    
    # ACT
    result1 = serialize_state(**args)
    result2 = serialize_state(**args)
    
    # ASSERT
    assert result1 == result2


def test_roundtrip_serialize_to_json_and_back():
    """Testbedingung: Roundtrip serialize_state → to_json → json.loads (Konsistenz).
    
    Erwartung: Zentrale Felder (position, radars, analog_wert_list) bleiben erhalten.
    """
    # ARRANGE
    state_dict = serialize_state(
        position_px=(100.0, 200.0),
        carangle_deg=45.0,
        speed_px=5.0,
        speed_set=10.0,
        radars=[((10.0, 20.0), 5), ((30.0, 40.0), 10)],
        bit_volt_wert_list=[(1023, 4.95)],
        distance_px=50.0,
        time_s=1.5
    )
    
    # ACT
    json_str = to_json(state_dict)
    parsed = json.loads(json_str)
    
    # ASSERT: Zentrale Felder inhaltlich erhalten
    assert parsed["position"] == [100.0, 200.0]
    assert parsed["carangle"] == 45.0
    assert parsed["radars"] == [[[10.0, 20.0], 5], [[30.0, 40.0], 10]]
    assert parsed["analog_wert_list"] == [[1023, 4.95]]
    assert parsed["distance"] == 50.0
    assert parsed["time"] == 1.5




# ===============================================================================
# TESTGRUPPE 7: Edge-Cases & Grenzwerte (Grenzwertanalyse - ISTQB)
# ===============================================================================
# Testbedingungen: 0-Werte (Minimum), negative Werte, große Listen (Stress-Test)

@pytest.mark.parametrize("position_px, carangle_deg, speed_px, expected_pos, expected_angle, expected_speed", [
    ((0.0, 0.0), 0.0, 0.0, [0.0, 0.0], 0.0, 0.0),              # Alle Nullen
    ((-10.0, -20.0), -45.0, -5.0, [-10.0, -20.0], -45.0, -5.0), # Negative Werte
])
def test_serialize_state_boundary_values(position_px, carangle_deg, speed_px, 
                                          expected_pos, expected_angle, expected_speed):
    """Testbedingung: Grenzwerte (0, negativ) korrekt serialisiert.
    
    Erwartung: Funktion akzeptiert Grenzwerte ohne Fehler, Werte unverändert.
    """
    # ACT
    result = serialize_state(
        position_px=position_px,
        carangle_deg=carangle_deg,
        speed_px=speed_px,
        speed_set=10.0,
        radars=[],
        bit_volt_wert_list=[],
        distance_px=0.0,
        time_s=0.0
    )
    
    # ASSERT
    assert result["position"] == expected_pos
    assert result["carangle"] == expected_angle
    assert result["speed"] == expected_speed


def test_serialize_state_large_radar_list():
    """Testbedingung: Große Radar-Liste (100 Einträge) - Stress-Test.
    
    Erwartung: Alle Radare korrekt konvertiert, kein Datenverlust.
    """
    # ARRANGE
    radars = [((i * 10.0, i * 20.0), i * 5) for i in range(100)]
    
    # ACT
    result = serialize_state(
        position_px=(0.0, 0.0),
        carangle_deg=0.0,
        speed_px=0.0,
        speed_set=0.0,
        radars=radars,
        bit_volt_wert_list=[],
        distance_px=0.0,
        time_s=0.0
    )
    
    # ASSERT
    assert len(result["radars"]) == 100
    assert result["radars"][50] == [[500.0, 1000.0], 250]  # Stichprobe
