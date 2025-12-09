# tests/car/test_dynamics.py
"""Unit-Tests für Fahrzeugdynamik (Geschwindigkeits-Update).

TESTBASIS (ISTQB):
- Anforderung: Realistische Beschleunigung/Verzögerung mit Drag & Limits
- Module: crazycar.car.dynamics
- Funktion: step_speed (power, drag, max_speed → neue Geschwindigkeit)

TESTVERFAHREN:
- Äquivalenzklassen: power {0, positiv, negativ}, drag {0, >0}
- Grenzwertanalyse: v=0 (Minimum), v=max_speed (Maximum)
- Monotonie: Höhere power → höhere speed (bei gleichem Ausgangszustand)
"""
import math
import inspect
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.dynamics import step_speed


# ===============================================================================
# API-Feature-Flags & Adaptive Wrapper
# ===============================================================================

SIG = inspect.signature(step_speed)
HAS_DRAG = "drag" in SIG.parameters
HAS_MAX_SPEED = "max_speed" in SIG.parameters


def _call_step_speed(**kwargs):
    """Adaptiert Test-Keywords an aktuelle step_speed-Signatur (API-Kompatibilität)."""
    sig = inspect.signature(step_speed)
    params = sig.parameters
    call = {}

    # speed -> current_speed_px (Synonym)
    if "current_speed_px" in params and "speed" in kwargs:
        call["current_speed_px"] = kwargs["speed"]
    elif "current_speed_px" in kwargs:
        call["current_speed_px"] = kwargs["current_speed_px"]
    elif "speed" in kwargs:
        call["speed"] = kwargs["speed"]

    # Pflicht: power
    if "power" in kwargs:
        call["power"] = kwargs["power"]

    # radangle_deg (falls vorhanden)
    if "radangle_deg" in params:
        call["radangle_deg"] = kwargs.get("radangle_deg", 0.0)

    # dt (mit Default)
    if "dt" in params:
        call["dt"] = kwargs.get("dt", params["dt"].default)

    # Optional: drag, max_speed
    for opt in ["drag", "max_speed"]:
        if opt in params and opt in kwargs:
            call[opt] = kwargs[opt]

    return step_speed(**call)


# ===============================================================================
# TESTGRUPPE 1: Smoke-Tests
# ===============================================================================

def test_step_speed_returns_finite_number():
    """Testbedingung: Basis-Funktionalität ohne Exception.
    
    Erwartung: Numerischer Rückgabewert ohne NaN/Inf.
    """
    # ACT
    v1 = _call_step_speed(speed=0.0, power=0.5, dt=0.1)
    
    # ASSERT
    assert isinstance(v1, (int, float)) and math.isfinite(v1)


# ===============================================================================
# TESTGRUPPE 2: Monotonie-Eigenschaften
# ===============================================================================

@pytest.mark.parametrize("p_low, p_high", [(0.0, 0.5), (0.5, 1.0)])
def test_step_speed_monotone_in_power(p_low, p_high):
    """Testbedingung: Höhere power → nicht langsamere speed (Monotonie).
    
    Erwartung: v_high >= v_low bei identischen Startbedingungen.
    """
    # ACT
    v_low = _call_step_speed(speed=0.2, power=p_low, dt=0.1, drag=0.0, max_speed=99.0)
    v_high = _call_step_speed(speed=0.2, power=p_high, dt=0.1, drag=0.0, max_speed=99.0)
    
    # ASSERT
    assert v_high >= v_low


# ===============================================================================
# TESTGRUPPE 3: Drag-Dämpfung (optional, API-abhängig)
# ===============================================================================

@pytest.mark.skipif(not HAS_DRAG, reason="step_speed hat keinen 'drag'-Parameter")
@pytest.mark.parametrize("v0", [0.1, 1.0, 5.0])
def test_step_speed_decays_with_drag(v0):
    """Testbedingung: Positiver drag ohne power → Geschwindigkeitsabbau.
    
    Erwartung: v1 <= v0 (Dämpfung).
    """
    # ACT
    v1 = _call_step_speed(speed=v0, power=0.0, dt=0.1, drag=0.5, max_speed=99.0)
    
    # ASSERT
    assert v1 <= v0


# ===============================================================================
# TESTGRUPPE 4: Grenzwerte (max_speed, v≥0)
# ===============================================================================

@pytest.mark.skipif(not HAS_MAX_SPEED, reason="step_speed hat keinen 'max_speed'-Parameter")
def test_step_speed_bounded_by_zero_and_max_speed():
    """Testbedingung: Grenzwerte v∈[0, max_speed] eingehalten.
    
    Erwartung: Kein Überschreiten der Limits bei extremen power-Werten.
    """
    # ACT: Extremfälle
    v1 = _call_step_speed(speed=10.0, power=-100.0, dt=0.1, drag=0.0, max_speed=3.0)
    v2 = _call_step_speed(speed=0.0, power=+100.0, dt=0.1, drag=0.0, max_speed=3.0)
    
    # ASSERT
    assert 0.0 <= v1 <= 3.0
    assert 0.0 <= v2 <= 3.0


# ===============================================================================
# TESTGRUPPE 5: Verträge (xfail - zukünftige Validierung)
# ===============================================================================

@pytest.mark.xfail(reason="dt<=0 sollte ValueError werfen – TODO", strict=False)
@pytest.mark.parametrize("bad_dt", [0.0, -0.01])
def test_step_speed_invalid_dt_raises(bad_dt):
    """Testbedingung: Ungültiges dt <= 0 → ValueError.
    
    Erwartung: Validierung in Produktionscode (zukünftig).
    """
    with pytest.raises(ValueError):
        _call_step_speed(speed=0.0, power=0.1, dt=bad_dt, drag=0.0, max_speed=1.0)


def test_step_speed_accepts_keywords():
    """Testbedingung: Keyword-Argumente bevorzugt (Stabilität).
    
    Erwartung: Funktioniert mit benannten Parametern.
    """
    # ACT
    v = _call_step_speed(speed=0.0, power=0.1, dt=0.05, drag=0.0, max_speed=99.0)
    
    # ASSERT
    assert isinstance(v, (int, float)) and math.isfinite(v)
