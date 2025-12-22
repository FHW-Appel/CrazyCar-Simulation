"""Extended Unit Tests for interface.py Controller Classes.

TESTBASIS:
- src/crazycar/control/interface.py (PythonController, CController, Interface)

TESTVERFAHREN:
- Äquivalenzklassenbildung: Python/C controller modes, sensor feeds
- Grenzwertanalyse: Power/steering limits
- Fehlervermutung: Missing symbols, invalid genomes


"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from crazycar.control import interface
from crazycar.car.model import Car


# ==============================================================================
# ControllerInterface ABC Tests
# ==============================================================================


class TestControllerInterface:
    """Tests for ControllerInterface ABC."""
    
    # TESTBASIS: interface.MyInterface ABC
    # TESTVERFAHREN: Äquivalenzklassenbildung - ABC contract
    
    def test_my_interface_is_abstract(self):
        """GIVEN: MyInterface class
        WHEN: checking class type
        THEN: should be ABC."""
        from abc import ABC
        assert issubclass(interface.MyInterface, ABC)
    
    def test_my_interface_has_regelungtechnik_c(self):
        """GIVEN: MyInterface class
        WHEN: checking methods
        THEN: should have regelungtechnik_c abstract method."""
        assert hasattr(interface.MyInterface, 'regelungtechnik_c')
    
    def test_my_interface_has_regelungtechnik_python(self):
        """GIVEN: MyInterface class
        WHEN: checking methods
        THEN: should have regelungtechnik_python abstract method."""
        assert hasattr(interface.MyInterface, 'regelungtechnik_python')


# ==============================================================================
# Interface Class Tests
# ==============================================================================


class TestInterfaceClass:
    """Tests for Interface class."""
    
    # TESTBASIS: interface.Interface main class
    # TESTVERFAHREN: Äquivalenzklassenbildung - Interface instantiation
    
    def test_interface_inherits_my_interface(self):
        """GIVEN: Interface class
        WHEN: checking inheritance
        THEN: should inherit from MyInterface."""
        assert issubclass(interface.Interface, interface.MyInterface)
    
    def test_interface_can_be_instantiated(self):
        """GIVEN: Interface class
        WHEN: creating instance
        THEN: should succeed."""
        iface = interface.Interface()
        assert iface is not None
    
    def test_interface_has_regelungtechnik_c_implementation(self):
        """GIVEN: Interface instance
        WHEN: checking methods
        THEN: should implement regelungtechnik_c."""
        iface = interface.Interface()
        assert hasattr(iface, 'regelungtechnik_c')
        assert callable(iface.regelungtechnik_c)
    
    def test_interface_has_regelungtechnik_python_implementation(self):
        """GIVEN: Interface instance
        WHEN: checking methods
        THEN: should implement regelungtechnik_python."""
        iface = interface.Interface()
        assert hasattr(iface, 'regelungtechnik_python')
        assert callable(iface.regelungtechnik_python)


# ==============================================================================
# Module-Level Globals Tests
# ==============================================================================


class TestModuleGlobals:
    """Tests for module-level global variables."""
    
    # TESTBASIS: interface.py module globals
    # TESTVERFAHREN: Äquivalenzklassenbildung - global state
    
    def test_module_has_ffi_global(self):
        """GIVEN: interface module
        WHEN: checking ffi global
        THEN: should exist (may be None)."""
        assert hasattr(interface, 'ffi')
    
    def test_module_has_lib_global(self):
        """GIVEN: interface module
        WHEN: checking lib global
        THEN: should exist (may be None)."""
        assert hasattr(interface, 'lib')
    
    def test_module_has_native_ok_flag(self):
        """GIVEN: interface module
        WHEN: checking _NATIVE_OK flag
        THEN: should exist as boolean."""
        assert hasattr(interface, '_NATIVE_OK')
        assert isinstance(interface._NATIVE_OK, bool)
    
    def test_module_has_set_power_resolver(self):
        """GIVEN: interface module
        WHEN: checking _set_power
        THEN: should exist."""
        assert hasattr(interface, '_set_power')
    
    def test_module_has_set_steer_resolver(self):
        """GIVEN: interface module
        WHEN: checking _set_steer
        THEN: should exist."""
        assert hasattr(interface, '_set_steer')
    
    def test_module_has_k1_parameter(self):
        """GIVEN: interface module
        WHEN: checking k1
        THEN: should exist as float."""
        assert hasattr(interface, 'k1')
        assert isinstance(interface.k1, (int, float))
        assert interface.k1 == 1.1
    
    def test_module_has_k2_parameter(self):
        """GIVEN: interface module
        WHEN: checking k2
        THEN: should exist as float."""
        assert hasattr(interface, 'k2')
        assert isinstance(interface.k2, (int, float))
        assert interface.k2 == 1.1
    
    def test_module_has_k3_parameter(self):
        """GIVEN: interface module
        WHEN: checking k3
        THEN: should exist as float."""
        assert hasattr(interface, 'k3')
        assert isinstance(interface.k3, (int, float))
        assert interface.k3 == 1.1
    
    def test_module_has_kp1_parameter(self):
        """GIVEN: interface module
        WHEN: checking kp1
        THEN: should exist as float."""
        assert hasattr(interface, 'kp1')
        assert isinstance(interface.kp1, (int, float))
        assert interface.kp1 == 1.1
    
    def test_module_has_kp2_parameter(self):
        """GIVEN: interface module
        WHEN: checking kp2
        THEN: should exist as float."""
        assert hasattr(interface, 'kp2')
        assert isinstance(interface.kp2, (int, float))
        assert interface.kp2 == 1.1
    
    def test_module_has_width_constant(self):
        """GIVEN: interface module
        WHEN: checking WIDTH
        THEN: should exist."""
        assert hasattr(interface, 'WIDTH')
    
    def test_module_has_height_constant(self):
        """GIVEN: interface module
        WHEN: checking HEIGHT
        THEN: should exist."""
        assert hasattr(interface, 'HEIGHT')


# ==============================================================================
# Required Symbol Tests
# ==============================================================================


class TestRequiredSymbols:
    """Tests for required C symbol constants."""
    
    # TESTBASIS: REQUIRED_ANY_POWER, REQUIRED_ANY_STEER, REQUIRED_ALWAYS
    # TESTVERFAHREN: Äquivalenzklassenbildung - symbol validation
    
    def test_required_any_power_exists(self):
        """GIVEN: interface module
        WHEN: checking REQUIRED_ANY_POWER
        THEN: should exist as tuple."""
        assert hasattr(interface, 'REQUIRED_ANY_POWER')
        assert isinstance(interface.REQUIRED_ANY_POWER, tuple)
    
    def test_required_any_power_contains_getfahr(self):
        """GIVEN: REQUIRED_ANY_POWER
        WHEN: checking contents
        THEN: should contain 'getfahr'."""
        assert 'getfahr' in interface.REQUIRED_ANY_POWER
    
    def test_required_any_power_contains_fahr(self):
        """GIVEN: REQUIRED_ANY_POWER
        WHEN: checking contents
        THEN: should contain 'fahr'."""
        assert 'fahr' in interface.REQUIRED_ANY_POWER
    
    def test_required_any_steer_exists(self):
        """GIVEN: interface module
        WHEN: checking REQUIRED_ANY_STEER
        THEN: should exist as tuple."""
        assert hasattr(interface, 'REQUIRED_ANY_STEER')
        assert isinstance(interface.REQUIRED_ANY_STEER, tuple)
    
    def test_required_any_steer_contains_getservo(self):
        """GIVEN: REQUIRED_ANY_STEER
        WHEN: checking contents
        THEN: should contain 'getservo'."""
        assert 'getservo' in interface.REQUIRED_ANY_STEER
    
    def test_required_any_steer_contains_servo(self):
        """GIVEN: REQUIRED_ANY_STEER
        WHEN: checking contents
        THEN: should contain 'servo'."""
        assert 'servo' in interface.REQUIRED_ANY_STEER
    
    def test_required_always_exists(self):
        """GIVEN: interface module
        WHEN: checking REQUIRED_ALWAYS
        THEN: should exist as tuple."""
        assert hasattr(interface, 'REQUIRED_ALWAYS')
        assert isinstance(interface.REQUIRED_ALWAYS, tuple)
    
    def test_required_always_contains_regelungtechnik(self):
        """GIVEN: REQUIRED_ALWAYS
        WHEN: checking contents
        THEN: should contain 'regelungtechnik'."""
        assert 'regelungtechnik' in interface.REQUIRED_ALWAYS
    
    def test_required_always_contains_getfwert(self):
        """GIVEN: REQUIRED_ALWAYS
        WHEN: checking contents
        THEN: should contain 'getfwert'."""
        assert 'getfwert' in interface.REQUIRED_ALWAYS
    
    def test_required_always_contains_getswert(self):
        """GIVEN: REQUIRED_ALWAYS
        WHEN: checking contents
        THEN: should contain 'getswert'."""
        assert 'getswert' in interface.REQUIRED_ALWAYS
    
    def test_required_always_contains_sensor_getters(self):
        """GIVEN: REQUIRED_ALWAYS
        WHEN: checking sensor functions
        THEN: should contain all sensor getters."""
        assert 'getabstandvorne' in interface.REQUIRED_ALWAYS
        assert 'getabstandrechts' in interface.REQUIRED_ALWAYS
        assert 'getabstandlinks' in interface.REQUIRED_ALWAYS


# ==============================================================================
# _prefer_build_import Tests
# ==============================================================================


class TestPreferBuildImport:
    """Tests for _prefer_build_import function."""
    
    # TESTBASIS: interface._prefer_build_import()
    # TESTVERFAHREN: Fehlervermutung - import failures, missing symbols
    
    def test_prefer_build_import_exists(self):
        """GIVEN: interface module
        WHEN: checking _prefer_build_import
        THEN: should exist as callable."""
        assert hasattr(interface, '_prefer_build_import')
        assert callable(interface._prefer_build_import)
    
    def test_prefer_build_import_returns_tuple(self):
        """GIVEN: _prefer_build_import function
        WHEN: calling it
        THEN: should return 4-tuple."""
        result = interface._prefer_build_import()
        assert isinstance(result, tuple)
        assert len(result) == 4
    
    def test_prefer_build_import_first_element_is_bool(self):
        """GIVEN: _prefer_build_import result
        WHEN: checking first element
        THEN: should be boolean."""
        ok, ffi, lib, mf = interface._prefer_build_import()
        assert isinstance(ok, bool)
    
    def test_prefer_build_import_last_element_is_string(self):
        """GIVEN: _prefer_build_import result
        WHEN: checking last element (module file)
        THEN: should be string."""
        ok, ffi, lib, mf = interface._prefer_build_import()
        assert isinstance(mf, str)
    
    @patch('crazycar.control.interface.importlib.import_module')
    def test_prefer_build_import_handles_import_error(self, mock_import):
        """GIVEN: import_module raises exception
        WHEN: calling _prefer_build_import
        THEN: should return (False, None, None, '')."""
        mock_import.side_effect = ImportError("No module")
        
        ok, ffi, lib, mf = interface._prefer_build_import()
        
        assert ok is False
        assert ffi is None
        assert lib is None
        assert mf == ""
    
    @patch('crazycar.control.interface.importlib.import_module')
    def test_prefer_build_import_validates_lib_not_none(self, mock_import):
        """GIVEN: imported module with lib=None
        WHEN: calling _prefer_build_import
        THEN: should return ok=False."""
        mock_mod = Mock()
        mock_mod.ffi = Mock()
        mock_mod.lib = None
        mock_import.return_value = mock_mod
        
        ok, ffi, lib, mf = interface._prefer_build_import()
        
        assert ok is False
    
    @patch('crazycar.control.interface.importlib.import_module')
    def test_prefer_build_import_validates_power_symbols(self, mock_import):
        """GIVEN: imported module missing power symbols
        WHEN: calling _prefer_build_import
        THEN: should return ok=False."""
        mock_mod = Mock()
        mock_mod.ffi = Mock()
        mock_lib = Mock(spec=[])  # No attributes
        mock_mod.lib = mock_lib
        mock_import.return_value = mock_mod
        
        ok, ffi, lib, mf = interface._prefer_build_import()
        
        assert ok is False
    
    @patch('crazycar.control.interface.importlib.import_module')
    def test_prefer_build_import_validates_steer_symbols(self, mock_import):
        """GIVEN: imported module missing steer symbols
        WHEN: calling _prefer_build_import
        THEN: should return ok=False."""
        mock_mod = Mock()
        mock_mod.ffi = Mock()
        mock_lib = Mock(spec=['getfahr'])  # Only power symbol, no steer
        mock_mod.lib = mock_lib
        mock_import.return_value = mock_mod
        
        ok, ffi, lib, mf = interface._prefer_build_import()
        
        # Will fail because missing steer symbols (getservo/servo)
        assert ok is False


# ==============================================================================
# Module Imports Tests
# ==============================================================================


class TestModuleImports:
    """Tests for module-level imports."""
    
    # TESTBASIS: interface.py imports
    # TESTVERFAHREN: Fehlervermutung - verify dependencies
    
    def test_module_imports_car_model(self):
        """GIVEN: interface module
        WHEN: checking imports
        THEN: should import model."""
        assert hasattr(interface, 'model')
    
    def test_module_imports_actuation(self):
        """GIVEN: interface module
        WHEN: checking actuation imports
        THEN: should import servo_to_angle, clip_steer, apply_power."""
        from crazycar.car import actuation
        assert interface.servo_to_angle is actuation.servo_to_angle
        assert interface.clip_steer is actuation.clip_steer
        assert interface.apply_power is actuation.apply_power
    
    def test_module_has_logger(self):
        """GIVEN: interface module
        WHEN: checking log
        THEN: should have logger instance."""
        assert hasattr(interface, 'log')
        import logging
        assert isinstance(interface.log, logging.Logger)


# ==============================================================================
# Build Directory Tests
# ==============================================================================


class TestBuildDirectory:
    """Tests for build directory handling."""
    
    # TESTBASIS: interface._build_dir initialization
    # TESTVERFAHREN: Fehlervermutung - build path setup
    
    def test_module_has_build_dir_variable(self):
        """GIVEN: interface module
        WHEN: checking _build_dir
        THEN: should exist."""
        assert hasattr(interface, '_build_dir')
    
    def test_build_dir_is_string_or_none(self):
        """GIVEN: interface._build_dir
        WHEN: checking type
        THEN: should be str or None."""
        assert isinstance(interface._build_dir, (str, type(None)))
