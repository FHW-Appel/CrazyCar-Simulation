"""Test Suite for Control Interface - NEAT/C Controller Integration.

This module provides comprehensive tests for the control interface layer that
bridges NEAT neural networks and native C controllers to car actuation.

Test Strategy:
- Unit Tests: Isolated testing of _apply_outputs_to_car, _prefer_build_import
- Integration Tests: Controller logic with mocked dependencies
- Branch Coverage: All control paths (Python/C, normal/fallback)
- Mocking Strategy: Replace heavy dependencies (NEAT, CFFI, pygame)
- Dummy Objects: Lightweight car stub with minimal state

Core Components Under Test:
- Interface._apply_outputs_to_car(): Actuator output mapping
- Interface.regelungtechnik_python(): Python P-controller logic
- Interface.regelungtechnik_c(): Native C controller wrapper
- _prefer_build_import(): CFFI module loading with symbol validation

Test Classes:
- DummyCar: Minimal car stub with sensors, actuators, control flags

Coverage Goals:
- _apply_outputs_to_car: Normal path + fallback when apply_power fails
- regelungtechnik_python: Skip conditions + 3 control ranges (>100, 50-100, <50)
- regelungtechnik_c: Native unavailable, disabled flags, insufficient data, happy path, error fallback
- _prefer_build_import: Import failure, symbol validation success

Branch Coverage Matrix:
┌─────────────────────────────────┬──────────────┬──────────────┐
│ Function                         │ Branch       │ Test Case    │
├─────────────────────────────────┼──────────────┼──────────────┤
│ _apply_outputs_to_car            │ Normal       │ test_..._normal_path │
│                                  │ Fallback     │ test_..._fallback... │
├─────────────────────────────────┼──────────────┼──────────────┤
│ regelungtechnik_python           │ Skips        │ test_..._skips │
│                                  │ dist>100     │ test_..._main_branches[150] │
│                                  │ 50<dist<=100 │ test_..._main_branches[80] │
│                                  │ dist<=50     │ test_..._main_branches[40] │
├─────────────────────────────────┼──────────────┼──────────────┤
│ regelungtechnik_c                │ No native    │ test_..._falls_back... │
│                                  │ Disabled     │ test_..._skips... │
│                                  │ Insufficient │ test_..._insufficient... │
│                                  │ Happy path   │ test_..._happy_path... │
│                                  │ Error        │ test_..._error_falls... │
└─────────────────────────────────┴──────────────┴──────────────┘

See Also:
- interface.py: Implementation under test
- actuation.py: Actuator mapping functions (clip_steer, servo_to_angle, apply_power)
- model.py: Car physics and simulation parameters

ISTQB Test Level: Unit Testing + Integration Testing
ISTQB Test Type: Functional Testing (controller logic), Error Handling (fallbacks)
ISTQB Test Technique: Equivalence Partitioning (distance ranges), Decision Coverage (branches)
"""

import types
import pytest

import crazycar.control.interface as iface


# ============================================================================
# Dummy Classes - Lightweight Car Stub
# ============================================================================

class DummyCar:
    """Minimal car stub for controller testing.
    
    Purpose:
        Provide lightweight car object with sensors, actuators, and control flags.
        Avoids heavy physics simulation while satisfying controller interface.
    
    Attributes:
        Control Flags:
            radars_enable: Enable/disable radar sensor processing
            regelung_enable: Enable/disable controller execution
        
        Python Controller Inputs:
            radar_dist: List of 3 distances in px [left, front, right]
        
        C Controller Inputs:
            bit_volt_wert_list: List of (digital_bit, voltage) tuples for sensors
            radar_angle: Radar heading offset in degrees
        
        Actuator State:
            radangle: Steering angle in radians
            power: Motor power level (0-100)
            speed: Current speed in px/tick
            fwert: Forward control signal (raw output)
            swert: Steering control signal (raw output)
    
    Methods:
        Geschwindigkeit(power): Speed mapping function (power → speed)
        getmotorleistung(power): Legacy setter for motor power
    
    Test Usage:
        Create instances with default values, modify for specific test scenarios.
        Validates controller reads inputs correctly and writes outputs.
    """
    def __init__(self):
        # Control flags (enable/disable controller features)
        self.radars_enable = True
        self.regelung_enable = True

        # Python controller inputs (radar distances in pixels)
        self.radar_dist = [200, 200, 200]  # [left, front, right]

        # C controller inputs (analog sensor values + heading)
        self.bit_volt_wert_list = [(10, 1.0), (20, 2.0), (30, 3.0)]
        self.radar_angle = 0.0  # degrees

        # Actuator state (steering + motor)
        self.radangle = 0.0  # radians
        self.power = 0.0     # 0-100
        self.speed = 0.0     # px/tick
        self.fwert = 0.0     # raw forward signal
        self.swert = 0.0     # raw steering signal

    def Geschwindigkeit(self, power: float) -> float:
        """Speed mapping function: power → speed.
        
        Simple deterministic mapping for testing.
        
        Args:
            power: Motor power level (0-100)
        
        Returns:
            Speed in px/tick (power * 0.1)
        """
        return float(power) * 0.1

    def getmotorleistung(self, power: float) -> None:
        """Legacy setter for motor power.
        
        Maintains backwards compatibility with old actuator API.
        
        Args:
            power: Motor power level to set
        
        Side Effects:
            Sets self.power to input value
        """
        self.power = float(power)


# ============================================================================
# Test Cases - Actuator Output Mapping
# ============================================================================

def test_apply_outputs_to_car_normal_path(monkeypatch):
    """Unit Test: _apply_outputs_to_car normal execution path.
    
    Test Objective:
        Verify _apply_outputs_to_car correctly:
        - Converts steering signal to radangle via clip_steer + servo_to_angle
        - Calls apply_power with correct parameters
        - Updates car.power from apply_power return
        - Updates car.speed from Geschwindigkeit(power)
    
    Test Strategy:
        Mock clip_steer, servo_to_angle, apply_power to return deterministic values.
        Verify car state updated correctly from mocked outputs.
    
    Pre-Conditions:
        - clip_steer, servo_to_angle stubbed to identity functions
        - apply_power returns (55.0, 9.9)
        - DummyCar.Geschwindigkeit returns power * 0.1
    
    Test Steps:
        1. Create DummyCar with default state
        2. Stub clip_steer → identity, servo_to_angle → identity
        3. Stub apply_power → return (55.0, 9.9)
        4. Call _apply_outputs_to_car(car, fwert=70.0, swert=10.0)
        5. Verify car.radangle == -(servo_to_angle(clip_steer(10.0))) == -10.0
        6. Verify car.power == 55.0 (from apply_power)
        7. Verify car.speed == 5.5 (from Geschwindigkeit(55.0))
    
    Expected Results:
        - car.radangle == -10.0 (steering mapped correctly)
        - car.power == 55.0 (apply_power output)
        - car.speed ≈ 5.5 (Geschwindigkeit(55.0) = 5.5)
    
    ISTQB Coverage:
        - Statement Coverage: Normal path through _apply_outputs_to_car
        - Branch Coverage: apply_power success branch
    """
    car = DummyCar()

    # Stub steering conversion (identity for simplicity)
    monkeypatch.setattr(iface, "clip_steer", lambda x: x)
    monkeypatch.setattr(iface, "servo_to_angle", lambda x: x)

    # Stub apply_power to return deterministic values
    def _fake_apply_power(*, fwert, current_power, current_speed_px, maxpower, speed_fn, delay_fn):
        return 55.0, 9.9

    monkeypatch.setattr(iface, "apply_power", _fake_apply_power)

    # Execute actuation
    iface.Interface._apply_outputs_to_car(car, fwert=70.0, swert=10.0)

    # Verify steering: radangle = -servo_to_angle(clip_steer(swert))
    assert car.radangle == -10.0, "Steering should be converted via servo_to_angle"
    
    # Verify power: from apply_power return
    assert car.power == 55.0, "Power should be updated from apply_power"
    
    # Verify speed: Geschwindigkeit(car.power) = 55.0 * 0.1 = 5.5
    assert car.speed == pytest.approx(5.5, rel=1e-6), "Speed should be computed from Geschwindigkeit"


def test_apply_outputs_to_car_fallback_when_apply_power_raises(monkeypatch):
    """Unit Test: _apply_outputs_to_car fallback when apply_power fails.
    
    Test Objective:
        Verify _apply_outputs_to_car handles apply_power exception gracefully:
        - Catches exception from apply_power
        - Falls back to legacy getmotorleistung(fwert) path
        - Still updates speed via Geschwindigkeit(power)
        - Steering still processed correctly
    
    Test Strategy:
        Stub apply_power to raise RuntimeError.
        Verify fallback path calls getmotorleistung with fwert.
    
    Pre-Conditions:
        - car.power = 12.0 initially
        - apply_power raises RuntimeError("boom")
        - clip_steer, servo_to_angle stubbed to identity
    
    Test Steps:
        1. Create DummyCar with car.power=12.0
        2. Stub apply_power to raise RuntimeError
        3. Call _apply_outputs_to_car(car, fwert=33.0, swert=5.0)
        4. Verify car.power == 33.0 (from getmotorleistung fallback)
        5. Verify car.speed == 3.3 (from Geschwindigkeit(33.0))
        6. Verify car.radangle == -5.0 (steering still processed)
    
    Expected Results:
        - car.power == 33.0 (getmotorleistung(fwert) called)
        - car.speed ≈ 3.3 (Geschwindigkeit(33.0) = 3.3)
        - car.radangle == -5.0 (steering path unaffected)
        - No exception propagated (graceful fallback)
    
    ISTQB Coverage:
        - Error Handling: Exception caught and fallback executed
        - Branch Coverage: apply_power exception branch
    """
    car = DummyCar()
    car.power = 12.0

    # Stub steering conversion
    monkeypatch.setattr(iface, "clip_steer", lambda x: x)
    monkeypatch.setattr(iface, "servo_to_angle", lambda x: x)
    
    # Stub apply_power to raise exception (trigger fallback)
    monkeypatch.setattr(iface, "apply_power", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    # Execute actuation (should catch exception and use fallback)
    iface.Interface._apply_outputs_to_car(car, fwert=33.0, swert=5.0)

    # Fallback: getmotorleistung(fwert) sets car.power = 33.0
    assert car.power == pytest.approx(33.0, rel=1e-6), "Fallback should call getmotorleistung(fwert)"
    
    # Speed computed from new power: 33.0 * 0.1 = 3.3
    assert car.speed == pytest.approx(3.3, rel=1e-6), "Speed should be computed via Geschwindigkeit"
    
    # Steering still processed correctly
    assert car.radangle == -5.0, "Steering should be processed even in fallback path"


# ============================================================================
# Test Cases - Python Controller Logic
# ============================================================================

def test_regelungtechnik_python_skips(monkeypatch):
    """Integration Test: regelungtechnik_python skip conditions.
    
    Test Objective:
        Verify Python controller skips cars when:
        - radars_enable = False
        - regelung_enable = False
        - radar_dist has insufficient elements (<3)
    
    Test Strategy:
        Create cars with each skip condition, verify _apply_outputs_to_car not called.
    
    Pre-Conditions:
        - _apply_outputs_to_car stubbed to track calls
        - sim_to_real stubbed to identity
        - Controller gains k1,k2,k3,kp1,kp2 = 1.0
    
    Test Steps:
        1. Stub _apply_outputs_to_car to record calls
        2. Test car with radars_enable=False → no calls
        3. Test car with regelung_enable=False → no calls
        4. Test car with radar_dist=[1,2] (len<3) → no calls
    
    Expected Results:
        - All three skip conditions prevent _apply_outputs_to_car calls
        - calls list remains empty for each scenario
    
    ISTQB Coverage:
        - Branch Coverage: All skip conditions (radars, regelung, insufficient data)
        - Guard Clause Coverage: Early returns before controller logic
    """
    calls = []

    # Stub actuation to track calls
    monkeypatch.setattr(iface.Interface, "_apply_outputs_to_car", 
                       lambda car, fwert, swert: calls.append((fwert, swert)))
    
    # Stub distance conversion (identity for simplicity)
    monkeypatch.setattr(iface.model, "sim_to_real", lambda x: x)
    
    # Set controller gains to 1.0
    monkeypatch.setattr(iface, "k1", 1.0)
    monkeypatch.setattr(iface, "k2", 1.0)
    monkeypatch.setattr(iface, "k3", 1.0)
    monkeypatch.setattr(iface, "kp1", 1.0)
    monkeypatch.setattr(iface, "kp2", 1.0)

    # Test 1: radars_enable = False
    car = DummyCar()
    car.radars_enable = False
    iface.Interface.regelungtechnik_python([car])
    assert calls == [], "radars_enable=False should skip controller"

    # Test 2: regelung_enable = False
    car = DummyCar()
    car.regelung_enable = False
    iface.Interface.regelungtechnik_python([car])
    assert calls == [], "regelung_enable=False should skip controller"

    # Test 3: Insufficient radar_dist elements
    car = DummyCar()
    car.radar_dist = [1, 2]  # Only 2 elements, need 3
    iface.Interface.regelungtechnik_python([car])
    assert calls == [], "Insufficient radar_dist should skip controller"


@pytest.mark.parametrize(
    "dist_front, car_power, expect_fwert_range",
    [
        (150, 10, ("gt", 0)),      # dist>100 and power<60 -> increase fwert
        (80,  30, ("ge", 18)),     # 50<dist<=100 and power>18 -> decrease fwert (min 18)
        (40,  10, ("lt", 0)),      # dist<=50 -> negative fwert (reverse)
    ],
)
def test_regelungtechnik_python_main_branches(monkeypatch, dist_front, car_power, expect_fwert_range):
    """Integration Test: Python controller longitudinal control branches.
    
    Test Objective:
        Verify regelungtechnik_python implements correct P-controller logic
        for three distance ranges:
        - dist > 100: Accelerate if power < 60 (fwert positive, increasing)
        - 50 < dist <= 100: Decelerate if power > 18 (fwert >= 18, min limit)
        - dist <= 50: Reverse (fwert negative)
    
    Test Strategy:
        Parametrized test with 3 distance ranges.
        Set lateral sensors to trigger lateral control (dist_left < 130).
        Verify fwert matches expected range for each distance/power combination.
    
    Pre-Conditions:
        - _apply_outputs_to_car stubbed to capture outputs
        - sim_to_real = identity
        - Controller gains = 1.0
        - Lateral control active (dist_left=120 < 130)
    
    Test Steps (per parameter set):
        1. Create DummyCar with car.power = car_power
        2. Set radar_dist = [120, dist_front, 200] (left < 130 → lateral active)
        3. Call regelungtechnik_python([car])
        4. Verify _apply_outputs_to_car called once
        5. Check fwert against expected range (gt/ge/lt comparison)
        6. Verify swert != 0 (lateral control active)
    
    Expected Results (per parameter set):
        - dist=150, power=10: fwert > 0 (accelerate)
        - dist=80, power=30: fwert >= 18 (decelerate with min limit)
        - dist=40, power=10: fwert < 0 (reverse)
        - swert != 0 for all cases (lateral control active)
    
    ISTQB Coverage:
        - Equivalence Partitioning: 3 distance ranges [>100, 50-100, <=50]
        - Boundary Testing: Implicit at 100 and 50 thresholds
        - Decision Coverage: All if/elif branches in longitudinal control
    """
    calls = []

    # Stub actuation to track calls
    monkeypatch.setattr(iface.Interface, "_apply_outputs_to_car", 
                       lambda car, fwert, swert: calls.append((fwert, swert)))
    
    # Stub distance conversion (identity)
    monkeypatch.setattr(iface.model, "sim_to_real", lambda x: x)
    
    # Set controller gains to 1.0 (P controller)
    monkeypatch.setattr(iface, "k1", 1.0)
    monkeypatch.setattr(iface, "k2", 1.0)
    monkeypatch.setattr(iface, "k3", 1.0)
    monkeypatch.setattr(iface, "kp1", 1.0)
    monkeypatch.setattr(iface, "kp2", 1.0)

    # Create car with specified power
    car = DummyCar()
    car.power = float(car_power)

    # Set radar distances: left < 130 to activate lateral control
    car.radar_dist = [120, dist_front, 200]  # [left, front, right]

    # Execute controller
    iface.Interface.regelungtechnik_python([car])

    # Verify _apply_outputs_to_car called exactly once
    assert len(calls) == 1, "Controller should call _apply_outputs_to_car once"
    fwert, swert = calls[0]

    # Verify fwert matches expected range
    op, val = expect_fwert_range
    if op == "gt":
        assert fwert > val, f"Expected fwert > {val}, got {fwert}"
    elif op == "ge":
        assert fwert >= val, f"Expected fwert >= {val}, got {fwert}"
    elif op == "lt":
        assert fwert < val, f"Expected fwert < {val}, got {fwert}"

    # Verify lateral control active (swert modified)
    assert swert != 0, "Lateral control should be active (dist_left < 130)"


# ============================================================================
# Test Cases - C Controller Logic
# ============================================================================

def test_regelungtechnik_c_falls_back_when_no_native(monkeypatch):
    """Integration Test: C controller fallback when native module unavailable.
    
    Test Objective:
        Verify regelungtechnik_c falls back to regelungtechnik_python
        when _NATIVE_OK=False or lib=None.
    
    Test Strategy:
        Set _NATIVE_OK=False, stub regelungtechnik_python to track calls.
        Verify Python controller called instead of C controller.
    
    Pre-Conditions:
        - _NATIVE_OK = False
        - lib = None
        - regelungtechnik_python stubbed to count calls
    
    Test Steps:
        1. Set _NATIVE_OK=False, lib=None
        2. Stub regelungtechnik_python to increment call counter
        3. Call regelungtechnik_c([DummyCar()])
        4. Verify Python controller called once
    
    Expected Results:
        - regelungtechnik_python called exactly once
        - No attempt to call native C functions
    
    ISTQB Coverage:
        - Error Handling: Graceful fallback when native unavailable
        - Branch Coverage: _NATIVE_OK=False branch
    """
    # Simulate native module unavailable
    monkeypatch.setattr(iface, "_NATIVE_OK", False)
    monkeypatch.setattr(iface, "lib", None)

    # Track Python controller calls
    called = {"py": 0}
    monkeypatch.setattr(iface.Interface, "regelungtechnik_python", 
                       lambda cars: called.__setitem__("py", called["py"] + 1))

    # Execute C controller (should fallback to Python)
    iface.Interface.regelungtechnik_c([DummyCar()])
    
    assert called["py"] == 1, "Should fallback to Python controller when native unavailable"


def test_regelungtechnik_c_skips_when_disabled(monkeypatch):
    """Integration Test: C controller skips cars with radars_enable=False.
    
    Test Objective:
        Verify C controller skips cars when radars_enable or regelung_enable
        is False, without calling _apply_outputs_to_car.
    
    Test Strategy:
        Create car with radars_enable=False, verify no actuation applied.
    
    Pre-Conditions:
        - _NATIVE_OK = True
        - lib with all required methods stubbed
        - _apply_outputs_to_car stubbed to track calls
    
    Test Steps:
        1. Set _NATIVE_OK=True, stub lib with minimal methods
        2. Stub _set_power, _set_steer
        3. Stub _apply_outputs_to_car to count calls
        4. Create car with radars_enable=False
        5. Call regelungtechnik_c([car])
        6. Verify _apply_outputs_to_car not called
    
    Expected Results:
        - _apply_outputs_to_car call count == 0
        - Car skipped without processing
    
    ISTQB Coverage:
        - Branch Coverage: radars_enable=False skip condition
        - Guard Clause Coverage: Early return before C controller logic
    """
    monkeypatch.setattr(iface, "_NATIVE_OK", True)

    # Stub native lib with minimal methods
    class LibOK:
        def getabstandvorne(self, x): pass
        def getabstandrechts(self, x, y): pass
        def getabstandlinks(self, x, y): pass
        def regelungtechnik(self): pass
        def getfwert(self): return 1
        def getswert(self): return 2

    monkeypatch.setattr(iface, "lib", LibOK())
    monkeypatch.setattr(iface, "_set_power", lambda x: None)
    monkeypatch.setattr(iface, "_set_steer", lambda x: None)

    # Track actuation calls
    applied = {"n": 0}
    monkeypatch.setattr(iface.Interface, "_apply_outputs_to_car", 
                       lambda car, fwert, swert: applied.__setitem__("n", applied["n"] + 1))

    # Create car with radars disabled
    car = DummyCar()
    car.radars_enable = False
    
    # Execute C controller
    iface.Interface.regelungtechnik_c([car])

    assert applied["n"] == 0, "Should skip car when radars_enable=False"


def test_regelungtechnik_c_insufficient_analog_values_calls_python_per_car(monkeypatch):
    """Integration Test: C controller fallback for insufficient analog values.
    
    Test Objective:
        Verify C controller falls back to Python controller per-car when
        bit_volt_wert_list has < 3 elements (insufficient sensor data).
    
    Test Strategy:
        Create car with bit_volt_wert_list=[2 elements], verify Python
        controller called for this specific car.
    
    Pre-Conditions:
        - _NATIVE_OK = True
        - lib with all required methods stubbed
        - car.bit_volt_wert_list has only 2 elements
    
    Test Steps:
        1. Set _NATIVE_OK=True, stub lib
        2. Stub regelungtechnik_python to count calls
        3. Create car with bit_volt_wert_list=[(1,0.1), (2,0.2)] (len=2 < 3)
        4. Call regelungtechnik_c([car])
        5. Verify regelungtechnik_python called once
    
    Expected Results:
        - regelungtechnik_python called exactly once for this car
        - C controller skipped for this car
    
    ISTQB Coverage:
        - Error Handling: Per-car fallback for insufficient data
        - Branch Coverage: len(bit_volt_wert_list) < 3 branch
    """
    monkeypatch.setattr(iface, "_NATIVE_OK", True)

    # Stub native lib
    class LibOK:
        def getabstandvorne(self, x): pass
        def getabstandrechts(self, x, y): pass
        def getabstandlinks(self, x, y): pass
        def regelungtechnik(self): pass
        def getfwert(self): return 1
        def getswert(self): return 2

    monkeypatch.setattr(iface, "lib", LibOK())
    monkeypatch.setattr(iface, "_set_power", lambda x: None)
    monkeypatch.setattr(iface, "_set_steer", lambda x: None)

    # Track Python controller calls
    called = {"py": 0}
    monkeypatch.setattr(iface.Interface, "regelungtechnik_python", 
                       lambda cars: called.__setitem__("py", called["py"] + 1))

    # Create car with insufficient analog values (need 3, have 2)
    car = DummyCar()
    car.bit_volt_wert_list = [(1, 0.1), (2, 0.2)]  # Only 2 elements
    
    # Execute C controller
    iface.Interface.regelungtechnik_c([car])

    assert called["py"] == 1, "Should fallback to Python controller for car with insufficient data"


def test_regelungtechnik_c_happy_path_reads_outputs(monkeypatch):
    """Integration Test: C controller happy path with complete data.
    
    Test Objective:
        Verify C controller executes complete cycle:
        - Sets power/steer inputs via _set_power, _set_steer
        - Calls lib.getabstandvorne/rechts/links with sensor data
        - Calls lib.regelungtechnik() to compute outputs
        - Reads lib.getfwert(), lib.getswert() for results
        - Calls _apply_outputs_to_car with computed values
        - Bonus: Test debug getters (getabstandvorne1, etc.)
    
    Test Strategy:
        Stub lib with call tracking, verify all methods called in correct order.
        Verify outputs (fwert=42, swert=-7) passed to _apply_outputs_to_car.
        Test debug getters return correct values.
    
    Pre-Conditions:
        - _NATIVE_OK = True
        - lib.getfwert() returns 42, lib.getswert() returns -7
        - car with complete data (3 sensor values, radar_angle=30°)
        - Debug getters return 11, 22, 33
    
    Test Steps:
        1. Create lib stub with call tracking
        2. Set _NATIVE_OK=True, _set_power, _set_steer
        3. Stub _apply_outputs_to_car to capture outputs
        4. Create car with power=10, radangle=5, radar_angle=30°
        5. Call regelungtechnik_c([car])
        6. Verify lib.regelungtechnik() called
        7. Verify _apply_outputs_to_car called with fwert=42, swert=-7
        8. Test debug getters: getabstandvorne1()==11, etc.
    
    Expected Results:
        - _apply_outputs_to_car(car, fwert=42, swert=-7) called
        - lib.regelungtechnik() in call history
        - Debug getters return correct values (11, 22, 33)
    
    ISTQB Coverage:
        - Statement Coverage: Complete C controller path
        - Integration Coverage: lib → _apply_outputs_to_car flow
        - API Coverage: Debug getter methods
    """
    monkeypatch.setattr(iface, "_NATIVE_OK", True)

    # Stub native lib with call tracking
    class LibOK:
        def __init__(self):
            self.calls = []
        
        def getabstandvorne(self, x): 
            self.calls.append(("v", x))
        
        def getabstandrechts(self, x, y): 
            self.calls.append(("r", x, y))
        
        def getabstandlinks(self, x, y): 
            self.calls.append(("l", x, y))
        
        def regelungtechnik(self): 
            self.calls.append(("run",))
        
        def getfwert(self): 
            return 42
        
        def getswert(self): 
            return -7
        
        # Debug getters for testing Interface.getabstandXXX1() methods
        def get_abstandvorne(self): 
            return 11
        
        def get_abstandlinks(self): 
            return 22
        
        def get_abstandrechts(self): 
            return 33

    lib = LibOK()
    monkeypatch.setattr(iface, "lib", lib)
    monkeypatch.setattr(iface, "_set_power", lambda x: None)
    monkeypatch.setattr(iface, "_set_steer", lambda x: None)

    # Track actuation calls
    applied = {}
    monkeypatch.setattr(iface.Interface, "_apply_outputs_to_car", 
                       lambda car, fwert, swert: applied.update({"f": fwert, "s": swert}))

    # Create car with complete sensor data
    car = DummyCar()
    car.power = 10
    car.radangle = 5
    car.radar_angle = 30.0
    car.bit_volt_wert_list = [(10, 0.1), (20, 0.2), (30, 0.3)]

    # Execute C controller
    iface.Interface.regelungtechnik_c([car])

    # Verify outputs applied correctly
    assert applied == {"f": 42, "s": -7}, "Should apply C controller outputs"
    assert ("run",) in lib.calls, "Should call lib.regelungtechnik()"

    # Test debug getters
    assert iface.Interface.getabstandvorne1() == 11, "Debug getter should return 11"
    assert iface.Interface.getabstandlinks1() == 22, "Debug getter should return 22"
    assert iface.Interface.getabstandrechts1() == 33, "Debug getter should return 33"


def test_regelungtechnik_c_error_falls_back(monkeypatch):
    """Integration Test: C controller error fallback to Python controller.
    
    Test Objective:
        Verify C controller catches exceptions during C library calls
        and falls back to Python controller for all cars in list.
    
    Test Strategy:
        Stub lib methods to raise RuntimeError, verify Python controller called.
    
    Pre-Conditions:
        - _NATIVE_OK = True
        - All lib methods raise RuntimeError("bad")
        - regelungtechnik_python stubbed to count calls
    
    Test Steps:
        1. Set _NATIVE_OK=True
        2. Create lib stub where all methods raise RuntimeError
        3. Stub regelungtechnik_python to count calls
        4. Call regelungtechnik_c([DummyCar()])
        5. Verify Python controller called once
    
    Expected Results:
        - regelungtechnik_python called exactly once
        - Exception caught and not propagated
        - Graceful fallback to Python controller
    
    ISTQB Coverage:
        - Error Handling: Exception during C controller execution
        - Branch Coverage: Exception catch block in C controller
    """
    monkeypatch.setattr(iface, "_NATIVE_OK", True)

    # Stub lib where all methods raise errors
    class LibBad:
        def getabstandvorne(self, x): 
            raise RuntimeError("bad")
        
        def getabstandrechts(self, x, y): 
            raise RuntimeError("bad")
        
        def getabstandlinks(self, x, y): 
            raise RuntimeError("bad")
        
        def regelungtechnik(self): 
            raise RuntimeError("bad")
        
        def getfwert(self): 
            raise RuntimeError("bad")
        
        def getswert(self): 
            raise RuntimeError("bad")

    monkeypatch.setattr(iface, "lib", LibBad())
    monkeypatch.setattr(iface, "_set_power", lambda x: None)
    monkeypatch.setattr(iface, "_set_steer", lambda x: None)

    # Track Python controller fallback calls
    called = {"py": 0}
    monkeypatch.setattr(iface.Interface, "regelungtechnik_python", 
                       lambda cars: called.__setitem__("py", called["py"] + 1))

    # Execute C controller (should catch exception and fallback)
    iface.Interface.regelungtechnik_c([DummyCar()])
    
    assert called["py"] == 1, "Should fallback to Python controller on C controller error"


# ============================================================================
# Test Cases - Native Module Import Logic
# ============================================================================

def test_prefer_build_import_fail(monkeypatch):
    """Unit Test: _prefer_build_import fails gracefully on import error.
    
    Test Objective:
        Verify _prefer_build_import returns failure state when
        importlib.import_module raises ImportError.
    
    Test Strategy:
        Stub import_module to raise ImportError, verify return values indicate failure.
    
    Pre-Conditions:
        - importlib.import_module raises ImportError("nope")
    
    Test Steps:
        1. Stub importlib.import_module to raise ImportError
        2. Call _prefer_build_import()
        3. Verify ok=False, ffi=None, lib=None, mf=""
    
    Expected Results:
        - ok == False
        - ffi == None
        - lib == None
        - mf == "" (empty string for module file)
    
    ISTQB Coverage:
        - Error Handling: Import failure handled gracefully
        - Return Value Testing: All return values correct on failure
    """
    # Stub import_module to raise ImportError
    monkeypatch.setattr(iface.importlib, "import_module", 
                       lambda name: (_ for _ in ()).throw(ImportError("nope")))
    
    # Execute import attempt
    ok, ffi, lib, mf = iface._prefer_build_import()
    
    # Verify failure state
    assert ok is False, "Should return ok=False on import error"
    assert ffi is None, "Should return ffi=None on import error"
    assert lib is None, "Should return lib=None on import error"
    assert mf == "", "Should return empty string for module file on import error"


def test_prefer_build_import_success(monkeypatch):
    """Unit Test: _prefer_build_import succeeds with complete symbols.
    
    Test Objective:
        Verify _prefer_build_import successfully imports and validates
        carsim_native module with all required symbols present.
    
    Test Strategy:
        Stub import chain and create fake module with all required symbols.
        Verify return values indicate success with correct objects.
    
    Pre-Conditions:
        - crazycar.interop.build_tools.ensure_build_on_path returns fake path
        - Fake module has ffi, lib with all required symbols:
          - Power setters: getfahr OR fahr
          - Steer setters: getservo OR servo
          - Always required: regelungtechnik, getfwert, getswert,
            getabstandvorne, getabstandrechts, getabstandlinks
    
    Test Steps:
        1. Create fake build_tools module with ensure_build_on_path
        2. Inject into sys.modules
        3. Create FakeLib with all required methods
        4. Create fake_mod with __file__, ffi, lib
        5. Stub import_module to return fake_mod
        6. Call _prefer_build_import()
        7. Verify ok=True, ffi/lib not None, mf contains "carsim_native"
    
    Expected Results:
        - ok == True
        - ffi is not None
        - lib is not None
        - "carsim_native" in mf (module file path)
    
    ISTQB Coverage:
        - Statement Coverage: Success path through _prefer_build_import
        - Symbol Validation: All required symbols checked
    """
    import types as _types
    import sys as _sys

    # Fake build_tools module for "from crazycar.interop.build_tools import ensure_build_on_path"
    fake_bt = _types.ModuleType("crazycar.interop.build_tools")
    fake_bt.ensure_build_on_path = lambda: "X:\\fake_build"
    _sys.modules["crazycar.interop.build_tools"] = fake_bt

    # Fake lib with all required symbols
    class FakeLib:
        # Power setters (any of these)
        def getfahr(self, x): pass
        # Steer setters (any of these)
        def getservo(self, x): pass
        # Always required
        def regelungtechnik(self): pass
        def getfwert(self): return 0
        def getswert(self): return 0
        def getabstandvorne(self, x): pass
        def getabstandrechts(self, x, y): pass
        def getabstandlinks(self, x, y): pass

    # Fake module with ffi, lib, __file__
    fake_mod = types.SimpleNamespace(
        __file__="X:\\fake_build\\crazycar\\carsim_native.pyd",
        ffi=object(),
        lib=FakeLib(),
    )

    # Stub import_module to return fake module
    monkeypatch.setattr(iface.importlib, "import_module", lambda name: fake_mod)

    # Execute import
    ok, ffi, lib, mf = iface._prefer_build_import()
    
    # Verify success state
    assert ok is True, "Should return ok=True when all symbols present"
    assert ffi is not None, "Should return ffi object"
    assert lib is not None, "Should return lib object"
    assert "carsim_native" in mf, "Module file should contain 'carsim_native'"
