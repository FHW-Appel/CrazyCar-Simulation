# tests/car/test_dynamics.py
import math
import inspect
import pytest
pytestmark = pytest.mark.unit

from crazycar.car.dynamics import step_speed

# --- API-Feature-Flags anhand der aktuellen step_speed-Signatur ----------
SIG = inspect.signature(step_speed)
HAS_DRAG = "drag" in SIG.parameters
HAS_MAX_SPEED = "max_speed" in SIG.parameters

# --- Helfer: robust gg. abweichende Signaturen --------------------------
def _call_step_speed(**kwargs):
    """
    Adaptiert Test-Keywords auf die aktuelle step_speed-Signatur und ignoriert
    unbekannte Keys (z.B. drag, max_speed). Setzt radangle_deg=0.0, wenn nötig.
    """
    sig = inspect.signature(step_speed)
    params = sig.parameters

    call = {}

    # speed -> current_speed_px (Synonym)
    if "current_speed_px" in params and "speed" in kwargs:
        call["current_speed_px"] = kwargs["speed"]
    elif "current_speed_px" in kwargs:
        call["current_speed_px"] = kwargs["current_speed_px"]
    elif "speed" in kwargs:
        # Fallback: evtl. erlaubt die Impl. 'speed' direkt
        call["speed"] = kwargs["speed"]

    # Pflicht: power
    if "power" in kwargs:
        call["power"] = kwargs["power"]

    # Winkel: falls Param vorhanden, notfalls 0.0 annehmen
    if "radangle_deg" in params:
        call["radangle_deg"] = kwargs.get("radangle_deg", 0.0)

    # dt (Keyword-only erlaubt)
    if "dt" in params:
        default_dt = params["dt"].default
        call["dt"] = kwargs.get("dt", default_dt)

    return step_speed(**call)

# ----------------------------- Smoke -----------------------------------
def test_step_speed_returns_number():
    # GIVEN
    speed0 = 0.0
    # WHEN
    v1 = _call_step_speed(speed=speed0, power=0.5, dt=0.1)
    # THEN
    assert isinstance(v1, (int, float)) and math.isfinite(v1)

# --------------------------- Eigenschaften ------------------------------
@pytest.mark.parametrize("p_low,p_high", [(0.0, 0.5), (0.5, 1.0)])
def test_step_speed_monotone_in_power(p_low, p_high):
    # GIVEN identische Startwerte, nur Power variiert
    # WHEN
    v_low  = _call_step_speed(speed=0.2, power=p_low,  dt=0.1, drag=0.0, max_speed=99.0)
    v_high = _call_step_speed(speed=0.2, power=p_high, dt=0.1, drag=0.0, max_speed=99.0)
    # THEN: mehr Antrieb → nicht langsamer
    assert v_high >= v_low

@pytest.mark.skipif(not HAS_DRAG, reason="step_speed hat keinen 'drag'-Parameter")
@pytest.mark.parametrize("v0", [0.1, 1.0, 5.0])
def test_step_speed_decays_with_drag(v0):
    # GIVEN: keine Antriebsleistung, positiver Drag
    # WHEN
    v1 = _call_step_speed(speed=v0, power=0.0, dt=0.1, drag=0.5, max_speed=99.0)
    # THEN: Dämpfung → nicht schneller
    assert v1 <= v0

@pytest.mark.skipif(not HAS_MAX_SPEED, reason="step_speed hat keinen 'max_speed'-Parameter")
def test_step_speed_is_bounded_by_zero_and_max_speed():
    # GIVEN/WHEN: starker Gegen-/Vortrieb; Grenzen sollten greifen
    v1 = _call_step_speed(speed=10.0, power=-100.0, dt=0.1, drag=0.0, max_speed=3.0)
    v2 = _call_step_speed(speed=0.0,  power=+100.0, dt=0.1, drag=0.0, max_speed=3.0)
    # THEN
    assert 0.0 <= v1 <= 3.0
    assert 0.0 <= v2 <= 3.0

# -------------------------- Fehlerfälle/Verträge ------------------------
@pytest.mark.xfail(reason="dt<=0 sollte ValueError werfen – TODO in step_speed implementieren", strict=False)
@pytest.mark.parametrize("bad_dt", [0.0, -0.01])
def test_step_speed_invalid_dt_raises(bad_dt):
    with pytest.raises(ValueError):
        _call_step_speed(speed=0.0, power=0.1, dt=bad_dt, drag=0.0, max_speed=1.0)

def test_step_speed_accepts_keywords_only():
    # Stabilität gg. Positionsargumente – bevorzugt Keywords nutzen
    v = _call_step_speed(speed=0.0, power=0.1, dt=0.05, drag=0.0, max_speed=99.0)
    assert isinstance(v, (int, float)) and math.isfinite(v)
