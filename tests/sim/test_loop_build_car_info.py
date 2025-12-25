# tests/sim/test_loop_build_car_info.py
"""Unit Tests für loop.py build_car_info_lines Function.

TESTBASIS:
- Modul crazycar.sim.loop - build_car_info_lines() Funktion
- HUD Text Formatting für Car Telemetrie
- ISTQB: Funktionale Tests für String Formatting

TESTVERFAHREN:
- Äquivalenzklassenbildung: Normal, Edge Cases
- Grenzwertanalyse: 0 values, extreme values
- State-Based: Python vs C control flag
"""
import pytest
from crazycar.sim.loop import build_car_info_lines
from crazycar.car.model import Car
from unittest.mock import Mock


pytestmark = pytest.mark.unit


# ==============================================================================
# TESTGRUPPE 1: build_car_info_lines() Normal Cases
# ==============================================================================

class TestBuildCarInfoLines:
    """Tests für build_car_info_lines() function."""
    
    def test_build_car_info_lines_python_control(self):
        """GIVEN: Car, WHEN: Python control, THEN: Info lines mit 'Python' Label.
        
        TESTBASIS:
            Function build_car_info_lines() - Python Control Mode
            HUD Text Generation
        
        TESTVERFAHREN:
            Functional: use_python_control=True
            State-Test: "Python" Label erscheint
        
        Erwartung: Lines enthalten "Python" Regelung Label.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=45.0,
            power=50,
            speed_set=1,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=150.0,
            time=5.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN
        assert isinstance(lines, list), "Should return list"
        assert len(lines) > 10, "Should have multiple lines"
        assert any("Python" in line for line in lines), "Should contain 'Python' label"
    
    def test_build_car_info_lines_c_control(self):
        """GIVEN: Car, WHEN: C control, THEN: Info lines mit 'C' Label.
        
        TESTBASIS:
            Function build_car_info_lines() - C Control Mode
            Control Mode Switch
        
        TESTVERFAHREN:
            Functional: use_python_control=False
            State-Test: "C" Label erscheint
        
        Erwartung: Lines enthalten "C" Regelung Label.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=45.0,
            power=50,
            speed_set=1,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=150.0,
            time=5.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=False)
        
        # THEN
        assert isinstance(lines, list), "Should return list"
        assert any("C" in line for line in lines), "Should contain 'C' label"
    
    def test_build_car_info_lines_contains_telemetry(self):
        """GIVEN: Car, WHEN: build_car_info_lines, THEN: Alle Telemetrie-Daten.
        
        TESTBASIS:
            Function build_car_info_lines() - Complete Telemetry
            Position, Speed, Sensors, Distance, Time
        
        TESTVERFAHREN:
            Functional: Check all telemetry fields
            Content-Test: Alle wichtigen Werte vorhanden
        
        Erwartung: Lines enthalten Position, Speed, Radars, Distance, Time.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=90.0,
            power=75,
            speed_set=2,
            radars=[(100, 50), (110, 60), (120, 70), (130, 80), (140, 90)],
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=250.0,
            time=10.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        lines_text = "\\n".join(lines)
        
        # THEN: All telemetry present
        assert "Position" in lines_text, "Should contain position"
        assert "Angle" in lines_text, "Should contain angle"
        assert "Speed" in lines_text, "Should contain speed"
        assert "power" in lines_text, "Should contain power"
        assert "Radars" in lines_text, "Should contain radar info"
        assert "Distance" in lines_text, "Should contain distance"
        assert "Time" in lines_text, "Should contain time"
    
    def test_build_car_info_lines_zero_values(self):
        """GIVEN: Car mit 0 Werten, WHEN: build_car_info_lines, THEN: Keine Crashes.
        
        TESTBASIS:
            Function build_car_info_lines() - Zero Values Handling
            Grenzwerte: 0.0 für alle numerischen Werte
        
        TESTVERFAHREN:
            Boundary: 0 values für speed, distance, time
            Robustheit: Keine Division by Zero, Format Errors
        
        Erwartung: Function läuft mit 0 values ohne Exception.
        """
        # ARRANGE
        car = Car(
            position=[0.0, 0.0],
            carangle=0.0,
            power=0,
            speed_set=0,
            radars=[(0, 0)] * 5,
            bit_volt_wert_list=[(0, 0.0)] * 5,
            distance=0.0,
            time=0.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN: No exception, valid list
        assert isinstance(lines, list), "Should return list"
        assert len(lines) > 0, "Should have lines even with 0 values"
    
    def test_build_car_info_lines_extreme_values(self):
        """GIVEN: Car mit extremen Werten, WHEN: build_car_info_lines, THEN: Formatierung OK.
        
        TESTBASIS:
            Function build_car_info_lines() - Extreme Values
            Grenzwerte: Sehr große/kleine Werte
        
        TESTVERFAHREN:
            Boundary: 9999 distance, 360° angle
            Format-Test: Strings korrekt formatiert
        
        Erwartung: Extreme Werte werden korrekt formatiert.
        """
        # ARRANGE
        car = Car(
            position=[9999.0, 9999.0],
            carangle=359.99,
            power=100,
            speed_set=10,
            radars=[(1000, 999)] * 5,
            bit_volt_wert_list=[(1023, 5.0)] * 5,
            distance=99999.0,
            time=9999.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN: No exception, formatted strings
        assert isinstance(lines, list), "Should return list"
        assert all(isinstance(line, str) for line in lines), "All lines should be strings"
        assert len(lines) > 10, "Should have complete telemetry"
    
    def test_build_car_info_lines_radar_count(self):
        """GIVEN: Car mit 5 Radars, WHEN: build_car_info_lines, THEN: Alle 5 Radars angezeigt.
        
        TESTBASIS:
            Function build_car_info_lines() - Radar Array Handling
            5 Sensor Values
        
        TESTVERFAHREN:
            Functional: Check radar data in output
            Count: 5 radar values formatiert
        
        Erwartung: Alle 5 Radar-Werte erscheinen in Lines.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=0.0,
            power=50,
            speed_set=1,
            radars=[(10, 10), (20, 20), (30, 30), (40, 40), (50, 50)],
            bit_volt_wert_list=[(100, 0.5), (200, 1.0), (300, 1.5), (400, 2.0), (500, 2.5)],
            distance=100.0,
            time=1.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        lines_text = "\\n".join(lines)
        
        # THEN: Should contain radar info
        assert "Radars" in lines_text, "Should mention radars"
        # Alle 5 distance values sollten erscheinen
        assert "10px" in lines_text or "10" in lines_text, "Should contain first radar"
        assert "50px" in lines_text or "50" in lines_text, "Should contain last radar"
    
    def test_build_car_info_lines_round_time(self):
        """GIVEN: Car mit round_time, WHEN: build_car_info_lines, THEN: Rundenzeit angezeigt.
        
        TESTBASIS:
            Function build_car_info_lines() - Round Time Display
            Lap Time Tracking
        
        TESTVERFAHREN:
            Functional: round_time field displayed
            Lap-Tracking Feature
        
        Erwartung: Rundenzeit erscheint in Output.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=0.0,
            power=50,
            speed_set=1,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=100.0,
            time=10.0
        )
        car.round_time = 12.34
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        lines_text = "\\n".join(lines)
        
        # THEN
        assert "Rundenzeit" in lines_text, "Should contain 'Rundenzeit' label"
        assert "12.34" in lines_text, "Should show round_time value"


# ==============================================================================
# TESTGRUPPE 2: build_car_info_lines() Format Tests
# ==============================================================================

class TestBuildCarInfoLinesFormat:
    """Format und Structure Tests für build_car_info_lines()."""
    
    def test_build_car_info_lines_returns_list_of_strings(self):
        """GIVEN: Car, WHEN: build_car_info_lines, THEN: List[str] returned.
        
        TESTBASIS:
            Function build_car_info_lines() - Return Type
            Type Signature Validation
        
        TESTVERFAHREN:
            Type-Test: isinstance check
            Structure: List of strings
        
        Erwartung: Returns List[str] wie dokumentiert.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=0.0,
            power=50,
            speed_set=1,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=100.0,
            time=1.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN
        assert isinstance(lines, list), "Should return list"
        assert all(isinstance(line, str) for line in lines), "All elements should be strings"
    
    def test_build_car_info_lines_non_empty(self):
        """GIVEN: Car, WHEN: build_car_info_lines, THEN: Liste nicht leer.
        
        TESTBASIS:
            Function build_car_info_lines() - Non-Empty Result
            Minimum Output Requirement
        
        TESTVERFAHREN:
            Content-Test: len() > 0
            Functional: Always produces output
        
        Erwartung: Mindestens eine Line wird zurückgegeben.
        """
        # ARRANGE
        car = Car(
            position=[400.0, 300.0],
            carangle=0.0,
            power=50,
            speed_set=1,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=100.0,
            time=1.0
        )
        
        # ACT
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN
        assert len(lines) > 0, "Should return at least one line"
        assert len(lines) >= 15, "Should have comprehensive telemetry (>=15 lines)"
    
    def test_build_car_info_lines_no_nested_f_strings(self):
        """GIVEN: Car, WHEN: build_car_info_lines, THEN: Keine nested f-string Fehler.
        
        TESTBASIS:
            Function build_car_info_lines() - String Formatting Stability
            Docstring: "Stable formatting without nested f-strings"
        
        TESTVERFAHREN:
            Robustheit: Function sollte ohne Format Errors laufen
            Stability: Konsistente String-Erzeugung
        
        Erwartung: Keine SyntaxError oder Format-Exceptions.
        """
        # ARRANGE
        car = Car(
            position=[123.456, 789.012],
            carangle=12.34,
            power=56,
            speed_set=2,
            radars=[(100, 50)] * 5,
            bit_volt_wert_list=[(512, 2.5)] * 5,
            distance=123.45,
            time=6.78
        )
        
        # ACT: Should not raise any formatting exceptions
        lines = build_car_info_lines(car, use_python_control=True)
        
        # THEN: All lines are valid strings
        assert all(isinstance(line, str) for line in lines), "All lines should be strings"
        assert all(len(line) < 200 for line in lines), "Lines should be reasonable length"
