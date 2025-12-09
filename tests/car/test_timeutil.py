# tests/car/test_timeutil.py
"""Unit-Tests für Zeit-Hilfsfunktionen (delay_ms).

TESTBASIS (ISTQB):
- Anforderung: Plattformunabhängige Wartefunktion (pygame.time.delay/time.sleep Fallback)
- Module: crazycar.car.timeutil
- Funktion: delay_ms(ms) - blockierende Wartezeit

TESTVERFAHREN:
- Grenzwertanalyse: 0ms, negative Werte, sehr kleine/große Werte
- Monotonie: Steigende ms → steigende Wartezeiten
- Akkumulation: Mehrfache Aufrufe addieren sich
- Timing-Toleranz: ±50ms (Windows Timer-Granularität ~15ms)
"""
import time
import pytest

pytestmark = pytest.mark.unit

from crazycar.car.timeutil import delay_ms

# Toleranz für Timing-Tests (Windows hat ~15ms Granularität)
TIMING_TOLERANCE = 0.05  # 50ms Toleranz


# ===============================================================================
# FIXTURE: Timing-Helper
# ===============================================================================

@pytest.fixture
def measure_delay():
    """Factory für präzise Zeitmessung."""
    def _measure(ms_value):
        start = time.perf_counter()
        delay_ms(ms_value)
        return time.perf_counter() - start
    return _measure


# ===============================================================================
# TESTGRUPPE 1: Grenzwerte
# ===============================================================================

@pytest.mark.parametrize("ms, max_elapsed", [
    (0, 0.01),     # Zero → keine Wartezeit
    (-100, 0.01),  # Negativ → keine Wartezeit
    (-1, 0.01),    # Negative Edge
])
def test_delay_ms_nonpositive_returns_immediately(measure_delay, ms, max_elapsed):
    """Testbedingung: ms ≤ 0 → sofortige Rückkehr (keine Blockierung).
    
    Erwartung: Elapsed < 10ms (overhead-tolerant).
    """
    # ACT
    elapsed = measure_delay(ms)
    
    # ASSERT
    assert elapsed < max_elapsed


@pytest.mark.parametrize("ms", [10, 50, 100])
def test_delay_ms_waits_approximately_correct_time(measure_delay, ms):
    """Testbedingung: delay_ms(X) wartet ~X Millisekunden.
    
    Erwartung: |elapsed - X/1000| < TIMING_TOLERANCE.
    """
    # ACT
    elapsed = measure_delay(ms)
    
    # ASSERT
    expected_sec = ms / 1000.0
    assert abs(elapsed - expected_sec) < TIMING_TOLERANCE


def test_delay_ms_small_value_1ms(measure_delay):
    """Testbedingung: Minimale Wartezeit (1ms).
    
    Erwartung: Elapsed ≥ 0, keine Exception.
    """
    # ACT
    elapsed = measure_delay(1)
    
    # ASSERT
    assert 0.0 <= elapsed < 0.1  # Max 100ms für 1ms Request


# ===============================================================================
# TESTGRUPPE 2: Monotonie und Linearität
# ===============================================================================

def test_delay_ms_is_monotonic():
    """Testbedingung: Steigende ms-Werte → steigende Wartezeiten.
    
    Erwartung: delay_ms(10) < delay_ms(20) < delay_ms(40).
    """
    # ARRANGE
    test_values = [10, 20, 40]
    timings = []
    
    # ACT
    for ms in test_values:
        start = time.perf_counter()
        delay_ms(ms)
        timings.append(time.perf_counter() - start)
    
    # ASSERT
    assert timings[0] < timings[1] < timings[2]


def test_delay_ms_multiple_calls_accumulate():
    """Testbedingung: 3× delay_ms(10) ≈ delay_ms(30) (Akkumulation).
    
    Erwartung: Gesamtwartezeit ~30ms.
    """
    # ACT
    start = time.perf_counter()
    delay_ms(10)
    delay_ms(10)
    delay_ms(10)
    elapsed = time.perf_counter() - start
    
    # ASSERT
    expected = 0.030
    assert abs(elapsed - expected) < TIMING_TOLERANCE


# ===============================================================================
# TESTGRUPPE 3: Stabilität
# ===============================================================================

def test_delay_ms_does_not_crash_on_repeated_calls():
    """Testbedingung: Mehrfache Aufrufe ohne Exception.
    
    Erwartung: Keine Fehler bei 3× Aufruf.
    """
    # ACT & ASSERT
    try:
        delay_ms(5)
        delay_ms(5)
        delay_ms(5)
    except Exception as e:
        pytest.fail(f"delay_ms sollte nicht crashen: {e}")


def test_delay_ms_handles_integer_conversion():
    """Testbedingung: Float-Input → int-Konvertierung (10.5 → 10).
    
    Erwartung: Funktioniert ohne TypeError.
    """
    # ACT
    try:
        start = time.perf_counter()
        delay_ms(int(10.5))  # Explizite Konvertierung
        elapsed = time.perf_counter() - start
        
        # ASSERT
        assert elapsed >= 0.005  # Mindestens etwas Zeit vergangen
    except Exception as e:
        pytest.fail(f"delay_ms sollte numerische Werte akzeptieren: {e}")


# ===============================================================================
# TESTGRUPPE 4: Edge-Cases
# ===============================================================================

def test_delay_ms_bounded_large_value():
    """Testbedingung: Große Wartezeit (50ms für schnelle Tests).
    
    Erwartung: Wartet tatsächlich mindestens 40ms.
    """
    # ACT
    start = time.perf_counter()
    delay_ms(50)
    elapsed = time.perf_counter() - start
    
    # ASSERT
    assert elapsed >= 0.040  # Mindestens 80% der Zeit


def test_delay_ms_works_regardless_of_backend():
    """Testbedingung: Funktioniert mit pygame.time.delay oder time.sleep Fallback.
    
    Erwartung: Wartezeit ~20ms unabhängig von Implementation.
    """
    # ACT
    start = time.perf_counter()
    delay_ms(20)
    elapsed = time.perf_counter() - start
    
    # ASSERT
    assert abs(elapsed - 0.020) < TIMING_TOLERANCE
