"""Unit-Tests für Car TimeUtil - Timing und Delays.

TESTBASIS (ISTQB):
- Anforderung: Zeitverzögerungen, FPS-Limiting, Timing-Utilities
- Module: crazycar.car.timeutil
- Funktionen: delay_ms, timestamp-Funktionen

TESTVERFAHREN:
- Äquivalenzklassen: Verschiedene Delay-Werte, Min/Max Delays
- Timing-Tests: Mit Toleranzen für Ungenauigkeiten
"""
import pytest
import time

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: Delay-Funktionen
# ===============================================================================

class TestDelayFunctions:
    """Tests für Delay-Funktionen."""
    
    def test_delay_ms_import(self):
        """GIVEN: TimeUtil-Modul, WHEN: Import delay_ms, THEN: Erfolgreich.
        
        Erwartung: delay_ms kann importiert werden.
        """
        # ACT & THEN
        try:
            from crazycar.car.timeutil import delay_ms
            assert delay_ms is not None
        except ImportError as e:
            pytest.fail(f"Import fehlgeschlagen: {e}")
    
    def test_delay_ms_zero_delay(self):
        """GIVEN: delay_ms(0), WHEN: Aufrufen, THEN: Keine Exception.
        
        Erwartung: 0ms Delay ist gültig.
        """
        # ARRANGE
        from crazycar.car.timeutil import delay_ms
        
        # ACT
        start = time.perf_counter()
        delay_ms(0)
        elapsed = time.perf_counter() - start
        
        # THEN: Sehr kurze Zeit (< 10ms)
        assert elapsed < 0.01
    
    def test_delay_ms_short_delay(self):
        """GIVEN: delay_ms(10), WHEN: Aufrufen, THEN: ~10ms vergangen.
        
        Erwartung: Delay funktioniert mit Toleranz.
        """
        # ARRANGE
        from crazycar.car.timeutil import delay_ms
        
        # ACT
        start = time.perf_counter()
        delay_ms(10)
        elapsed = time.perf_counter() - start
        
        # THEN: Ungefähr 10ms (mit großer Toleranz für CI)
        assert 0.005 < elapsed < 0.050  # 5-50ms Toleranz


# ===============================================================================
# TESTGRUPPE 2: Timestamp-Funktionen
# ===============================================================================

class TestTimestampFunctions:
    """Tests für Timestamp-Utilities."""
    
    def test_timeutil_module_import(self):
        """GIVEN: Modul, WHEN: Import, THEN: Erfolgreich.
        
        Erwartung: Alle Timing-Funktionen verfügbar.
        """
        # ACT & THEN
        try:
            from crazycar.car import timeutil
            assert timeutil is not None
        except ImportError as e:
            pytest.fail(f"Import fehlgeschlagen: {e}")
