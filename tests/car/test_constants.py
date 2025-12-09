# tests/car/test_constants.py
"""Unit-Tests für Fahrzeugkonstanten (Pixel-Konvertierung).

TESTBASIS (ISTQB):
- Anforderung: Umrechnung Realmaße (cm) → Simulationspixel
- Module: crazycar.car.constants
- Funktion: init_pixels (konvertiert CAR_SIZE_X/Y, Radstand, Spurweite)

TESTVERFAHREN:
- Äquivalenzklassen: Normale Konvertierung, Exception-Fallback
- Grenzwertanalyse: Verschiedene Skalierungsfaktoren (0.8, 1.0, 100.0)
- Fallback-Tests: Exception → FALLBACK_* Werte
"""
import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock
from crazycar.car import constants

# Backup für Cleanup
_ORIGINAL_VALUES = {
    "CAR_SIZE_X": constants.CAR_SIZE_X,
    "CAR_SIZE_Y": constants.CAR_SIZE_Y,
    "CAR_cover_size": constants.CAR_cover_size,
    "CAR_Radstand": constants.CAR_Radstand,
    "CAR_Spurweite": constants.CAR_Spurweite,
}


# ===============================================================================
# FIXTURES
# ===============================================================================

@pytest.fixture(autouse=True)
def reset_constants():
    """Reset globale Variablen nach jedem Test (Isolation)."""
    yield
    # Restore
    constants.CAR_SIZE_X = _ORIGINAL_VALUES["CAR_SIZE_X"]
    constants.CAR_SIZE_Y = _ORIGINAL_VALUES["CAR_SIZE_Y"]
    constants.CAR_cover_size = _ORIGINAL_VALUES["CAR_cover_size"]
    constants.CAR_Radstand = _ORIGINAL_VALUES["CAR_Radstand"]
    constants.CAR_Spurweite = _ORIGINAL_VALUES["CAR_Spurweite"]


@pytest.fixture
def mock_converter():
    """Factory für einfache Konverter-Funktionen."""
    def _factory(scale=0.8):
        return lambda cm: cm * scale
    return _factory


# ===============================================================================
# TESTGRUPPE 1: init_pixels - Normale Konvertierung
# ===============================================================================

def test_init_pixels_converts_car_dimensions(mock_converter):
    """Testbedingung: real_to_sim skaliert Fahrzeugabmessungen.
    
    Erwartung: CAR_SIZE_X/Y entsprechen skalierten Werten.
    """
    # ARRANGE
    converter = mock_converter(scale=0.8)  # 40cm → 32px, 20cm → 16px
    
    # ACT
    constants.init_pixels(converter)
    
    # ASSERT
    assert constants.CAR_SIZE_X == pytest.approx(32.0, abs=0.1)
    assert constants.CAR_SIZE_Y == pytest.approx(16.0, abs=0.1)


def test_init_pixels_sets_cover_size_to_max(mock_converter):
    """Testbedingung: CAR_cover_size = max(CAR_SIZE_X, CAR_SIZE_Y).
    
    Erwartung: Größere Dimension bestimmt cover_size.
    """
    # ARRANGE
    converter = mock_converter(scale=0.8)
    
    # ACT
    constants.init_pixels(converter)
    
    # ASSERT
    assert constants.CAR_cover_size == 32  # max(32, 16)


@pytest.mark.parametrize("scale, expected_x, expected_y", [
    (0.8, 32.0, 16.0),   # Standard-Skalierung
    (1.0, 40.0, 20.0),   # 1:1
    (2.0, 80.0, 40.0),   # Doppelt
])
def test_init_pixels_different_scales(scale, expected_x, expected_y):
    """Testbedingung: Verschiedene Skalierungen → proportionale Werte.
    
    Erwartung: Lineare Skalierung beibehalten.
    """
    # ARRANGE & ACT
    constants.init_pixels(lambda cm: cm * scale)
    
    # ASSERT
    assert constants.CAR_SIZE_X == pytest.approx(expected_x, abs=0.1)
    assert constants.CAR_SIZE_Y == pytest.approx(expected_y, abs=0.1)


def test_init_pixels_converts_radstand_and_spurweite(mock_converter):
    """Testbedingung: Radstand & Spurweite werden konvertiert.
    
    Erwartung: Skalierte Werte für Geometrie-Berechnungen.
    """
    # ARRANGE
    converter = mock_converter(scale=0.8)
    
    # ACT
    constants.init_pixels(converter)
    
    # ASSERT: _RADSTAND_CM=25, _SPURWEITE_CM=10
    assert constants.CAR_Radstand == pytest.approx(20.0, abs=0.1)  # 25*0.8
    assert constants.CAR_Spurweite == pytest.approx(8.0, abs=0.1)  # 10*0.8


# ===============================================================================
# TESTGRUPPE 2: Exception-Fallback
# ===============================================================================

def test_init_pixels_exception_uses_fallback_values():
    """Testbedingung: Converter-Exception → FALLBACK_* Werte.
    
    Erwartung: Robustheit gegen fehlerhafte Konvertierung.
    """
    # ARRANGE
    def failing_converter(cm):
        raise ValueError("Test error")
    
    # ACT
    constants.init_pixels(failing_converter)
    
    # ASSERT: Fallback-Werte aus Code
    assert constants.CAR_SIZE_X == 32.0
    assert constants.CAR_SIZE_Y == 16.0
    assert constants.CAR_cover_size == 32
    assert constants.CAR_Radstand == 25.0
    assert constants.CAR_Spurweite == 10.0


def test_init_pixels_exception_logged(caplog):
    """Testbedingung: Exception → Log-Eintrag ERROR.
    
    Erwartung: Diagnose-Information für Entwickler.
    """
    # ARRANGE
    def failing_converter(cm):
        raise RuntimeError("Conversion failed")
    
    # ACT
    with caplog.at_level("ERROR"):
        constants.init_pixels(failing_converter)
    
    # ASSERT
    assert any("init_pixels: Fehler beim Umrechnen" in rec.message 
               for rec in caplog.records)


def test_init_pixels_exception_continues_execution():
    """Testbedingung: Exception catchen → kein Crash.
    
    Erwartung: Anwendung bleibt lauffähig.
    """
    # ARRANGE
    def failing_converter(cm):
        raise Exception("Test exception")
    
    # ACT / ASSERT: Sollte nicht crashen
    try:
        constants.init_pixels(failing_converter)
    except Exception as e:
        pytest.fail(f"init_pixels sollte Exception catchen: {e}")


# ===============================================================================
# TESTGRUPPE 3: Konstanten-Werte (Smoke-Tests)
# ===============================================================================

@pytest.mark.parametrize("constant, expected", [
    ("WIDTH", int(1920 * 0.8)),
    ("HEIGHT", int(1080 * 0.8)),
    ("BORDER_COLOR", (255, 255, 255, 255)),
    ("FINISH_LINE_COLOR", (237, 28, 36, 255)),
    ("RADAR_SWEEP_DEG", 60),
])
def test_constants_module_values(constant, expected):
    """Testbedingung: Modul-Konstanten haben erwartete Werte.
    
    Erwartung: Statische Konfiguration korrekt.
    """
    # ACT
    actual = getattr(constants, constant)
    
    # ASSERT
    assert actual == expected


def test_constants_max_radar_len_ratio():
    """Testbedingung: MAX_RADAR_LEN_RATIO = 130/1900.
    
    Erwartung: Radar-Reichweite proportional zur Streckenbreite.
    """
    # ACT / ASSERT
    assert constants.MAX_RADAR_LEN_RATIO == pytest.approx(130.0 / 1900.0, abs=0.0001)


# ===============================================================================
# TESTGRUPPE 4: Edge-Cases
# ===============================================================================

def test_init_pixels_called_multiple_times(mock_converter):
    """Testbedingung: Mehrfache Aufrufe → Werte überschreiben.
    
    Erwartung: Letzte Konvertierung gilt.
    """
    # ARRANGE
    first = mock_converter(scale=1.0)
    second = mock_converter(scale=2.0)
    
    # ACT
    constants.init_pixels(first)
    first_x = constants.CAR_SIZE_X
    constants.init_pixels(second)
    second_x = constants.CAR_SIZE_X
    
    # ASSERT
    assert second_x == pytest.approx(first_x * 2.0, abs=0.1)


def test_init_pixels_cover_size_is_int(mock_converter):
    """Testbedingung: CAR_cover_size immer int (Pixel).
    
    Erwartung: Typsicherheit für Rendering-Code.
    """
    # ARRANGE
    converter = mock_converter(scale=0.75)  # Ergibt floats
    
    # ACT
    constants.init_pixels(converter)
    
    # ASSERT
    assert isinstance(constants.CAR_cover_size, int)


def test_real_car_dimensions_are_positive():
    """Testbedingung: Real-Welt-Maße > 0 (Plausibilität).
    
    Erwartung: Keine negativen/null Dimensionen.
    """
    # ACT / ASSERT
    assert constants._CAR_X_CM > 0
    assert constants._CAR_Y_CM > 0
    assert constants._RADSTAND_CM > 0
    assert constants._SPURWEITE_CM > 0
