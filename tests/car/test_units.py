# tests/car/test_units.py
"""Unit-Tests für Einheitenumrechnung (Pixel ↔ Realwelt cm).

TESTBASIS (ISTQB):
- Anforderung: Bidirektionale Umrechnung Pixel ↔ cm mit Referenzbreite 1900cm
- Module: crazycar.car.units
- Funktionen: sim_to_real, real_to_sim

TESTVERFAHREN:
- Grenzwertanalyse: 0, WIDTH, negative Werte, sehr große Werte
- Bidirektionalität: Roundtrip px→cm→px und cm→px→cm  
- Linearität: Doppelte Eingabe → doppelte Ausgabe
"""
import math
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.units import sim_to_real, real_to_sim
from crazycar.car.constants import WIDTH

TOL = 1e-9
TRACK_WIDTH_CM = 1900.0  # Referenzwert


# ===============================================================================
# TESTGRUPPE 1: sim_to_real - Pixel → cm
# ===============================================================================

@pytest.mark.parametrize("pixels, expected_cm", [
    (0.0, 0.0),                      # Grenzwert: Zero
    (WIDTH, TRACK_WIDTH_CM),         # Grenzwert: Volle Breite
    (WIDTH / 2, TRACK_WIDTH_CM / 2), # Mitte
    (WIDTH / 4, TRACK_WIDTH_CM / 4), # Viertel
    (100.0, 100.0 * TRACK_WIDTH_CM / WIDTH),  # Beliebiger Wert
])
def test_sim_to_real_converts_proportionally(pixels, expected_cm):
    """Testbedingung: Pixel → cm mit fester Proportion WIDTH:1900cm.
    
    Erwartung: Lineare Skalierung beibehalten.
    """
    # ACT
    result = sim_to_real(pixels)
    
    # ASSERT
    assert math.isclose(result, expected_cm, rel_tol=1e-12)


def test_sim_to_real_returns_float():
    """Testbedingung: Ausgabetyp immer float.
    
    Erwartung: Konsistente Typsignatur.
    """
    # ACT
    result = sim_to_real(10)  # Integer-Eingabe
    
    # ASSERT
    assert isinstance(result, float)


# ===============================================================================
# TESTGRUPPE 2: real_to_sim - cm → Pixel
# ===============================================================================

@pytest.mark.parametrize("cm, expected_px", [
    (0.0, 0.0),                      # Grenzwert: Zero
    (TRACK_WIDTH_CM, WIDTH),         # Grenzwert: Volle Breite
    (950.0, WIDTH / 2),              # Mitte
    (475.0, WIDTH / 4),              # Viertel
    (100.0, 100.0 * WIDTH / TRACK_WIDTH_CM),  # Beliebiger Wert
])
def test_real_to_sim_converts_proportionally(cm, expected_px):
    """Testbedingung: cm → Pixel mit fester Proportion 1900cm:WIDTH.
    
    Erwartung: Lineare Skalierung beibehalten.
    """
    # ACT
    result = real_to_sim(cm)
    
    # ASSERT
    assert math.isclose(result, expected_px, rel_tol=1e-12)


def test_real_to_sim_returns_float():
    """Testbedingung: Ausgabetyp immer float.
    
    Erwartung: Konsistente Typsignatur.
    """
    # ACT
    result = real_to_sim(50)  # Integer-Eingabe
    
    # ASSERT
    assert isinstance(result, float)


# ===============================================================================
# TESTGRUPPE 3: Bidirektionalität (Roundtrip-Tests)
# ===============================================================================

@pytest.mark.parametrize("original_px", [0.0, 10.0, 100.0, 500.0, WIDTH, WIDTH * 2])
def test_roundtrip_pixel_to_cm_to_pixel(original_px):
    """Testbedingung: px → cm → px erhält Originalwert (Inverse-Funktionen).
    
    Erwartung: Keine numerischen Fehler bei Roundtrip.
    """
    # ACT
    cm = sim_to_real(original_px)
    back_px = real_to_sim(cm)
    
    # ASSERT
    assert math.isclose(back_px, original_px, rel_tol=1e-12)


@pytest.mark.parametrize("original_cm", [0.0, 10.0, 100.0, 950.0, 1900.0, 3800.0])
def test_roundtrip_cm_to_pixel_to_cm(original_cm):
    """Testbedingung: cm → px → cm erhält Originalwert (Inverse-Funktionen).
    
    Erwartung: Keine numerischen Fehler bei Roundtrip.
    """
    # ACT
    px = real_to_sim(original_cm)
    back_cm = sim_to_real(px)
    
    # ASSERT
    assert math.isclose(back_cm, original_cm, rel_tol=1e-12)


# ===============================================================================
# TESTGRUPPE 4: Linearitäts-Eigenschaften
# ===============================================================================

@pytest.mark.parametrize("factor", [2, 3, 10])
def test_sim_to_real_is_linear(factor):
    """Testbedingung: n-fache Pixel → n-fache cm (Linearität).
    
    Erwartung: sim_to_real(n*x) = n * sim_to_real(x).
    """
    # ARRANGE
    px1 = 50.0
    px_n = px1 * factor
    
    # ACT
    cm1 = sim_to_real(px1)
    cm_n = sim_to_real(px_n)
    
    # ASSERT
    assert math.isclose(cm_n, cm1 * factor, rel_tol=1e-12)


@pytest.mark.parametrize("factor", [2, 3, 10])
def test_real_to_sim_is_linear(factor):
    """Testbedingung: n-fache cm → n-fache Pixel (Linearität).
    
    Erwartung: real_to_sim(n*x) = n * real_to_sim(x).
    """
    # ARRANGE
    cm1 = 100.0
    cm_n = cm1 * factor
    
    # ACT
    px1 = real_to_sim(cm1)
    px_n = real_to_sim(cm_n)
    
    # ASSERT
    assert math.isclose(px_n, px1 * factor, rel_tol=1e-12)


# ===============================================================================
# TESTGRUPPE 5: Edge-Cases
# ===============================================================================

@pytest.mark.parametrize("value", [-100.0, -500.0])
def test_sim_to_real_handles_negative_values(value):
    """Testbedingung: Negative Pixel → negative cm (Richtungsvektoren).
    
    Erwartung: Proportionalität bleibt erhalten.
    """
    # ACT
    result = sim_to_real(value)
    
    # ASSERT
    assert result < 0
    assert math.isclose(result, value * TRACK_WIDTH_CM / WIDTH, abs_tol=TOL)


@pytest.mark.parametrize("value", [-500.0, -1000.0])
def test_real_to_sim_handles_negative_values(value):
    """Testbedingung: Negative cm → negative Pixel (Richtungsvektoren).
    
    Erwartung: Proportionalität bleibt erhalten.
    """
    # ACT
    result = real_to_sim(value)
    
    # ASSERT
    assert result < 0
    assert math.isclose(result, value * WIDTH / TRACK_WIDTH_CM, abs_tol=TOL)


def test_sim_to_real_very_large_value():
    """Testbedingung: Sehr großer Pixel-Wert (Stress-Test).
    
    Erwartung: Numerische Stabilität beibehalten.
    """
    # ARRANGE
    large_px = 1e6
    
    # ACT
    result = sim_to_real(large_px)
    
    # ASSERT
    expected = large_px * TRACK_WIDTH_CM / WIDTH
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_real_to_sim_very_small_value():
    """Testbedingung: Sehr kleiner cm-Wert (Präzisionstest).
    
    Erwartung: Floating-Point-Präzision erhalten.
    """
    # ARRANGE
    small_cm = 0.001
    
    # ACT
    result = real_to_sim(small_cm)
    
    # ASSERT
    expected = small_cm * WIDTH / TRACK_WIDTH_CM
    assert math.isclose(result, expected, rel_tol=1e-9)
