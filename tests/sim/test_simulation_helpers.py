"""Unit tests for simulation.py Helper Functions.

TESTBASIS:
- src/crazycar/sim/simulation.py (Helper functions)

TESTVERFAHREN:
- Äquivalenzklassenbildung: _finalize_exit modes, UI layout constants
- Grenzwertanalyse: UI positioning calculations
- Fehlervermutung: pygame.quit exceptions, sys.exit behavior

"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import pygame

from crazycar.sim import simulation


pytestmark = pytest.mark.unit


# ==============================================================================
# Constants Tests
# ==============================================================================


class TestUILayoutConstants:
    """Tests for UI layout constants."""
    
    # TESTBASIS: UI layout constant definitions
    # TESTVERFAHREN: Äquivalenzklassenbildung - validate constant ranges
    
    def test_ui_text_box_width_is_positive(self):
        """GIVEN: UI_TEXT_BOX_WIDTH constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_TEXT_BOX_WIDTH')
        assert simulation.UI_TEXT_BOX_WIDTH > 0
        assert simulation.UI_TEXT_BOX_WIDTH == 200
    
    def test_ui_text_box_height_is_positive(self):
        """GIVEN: UI_TEXT_BOX_HEIGHT constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_TEXT_BOX_HEIGHT')
        assert simulation.UI_TEXT_BOX_HEIGHT > 0
        assert simulation.UI_TEXT_BOX_HEIGHT == 30
    
    def test_ui_snapshot_button_width_is_positive(self):
        """GIVEN: UI_SNAPSHOT_BUTTON_WIDTH constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_SNAPSHOT_BUTTON_WIDTH')
        assert simulation.UI_SNAPSHOT_BUTTON_WIDTH > 0
        assert simulation.UI_SNAPSHOT_BUTTON_WIDTH == 100
    
    def test_ui_snapshot_button_height_is_positive(self):
        """GIVEN: UI_SNAPSHOT_BUTTON_HEIGHT constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_SNAPSHOT_BUTTON_HEIGHT')
        assert simulation.UI_SNAPSHOT_BUTTON_HEIGHT > 0
        assert simulation.UI_SNAPSHOT_BUTTON_HEIGHT == 30
    
    def test_ui_snapshot_button_offset_is_positive(self):
        """GIVEN: UI_SNAPSHOT_BUTTON_OFFSET constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_SNAPSHOT_BUTTON_OFFSET')
        assert simulation.UI_SNAPSHOT_BUTTON_OFFSET > 0
        assert simulation.UI_SNAPSHOT_BUTTON_OFFSET == 40
    
    def test_ui_collision_toggle_x_factor_is_valid(self):
        """GIVEN: UI_COLLISION_TOGGLE_X_FACTOR constant
        WHEN: checking value
        THEN: should be float >= 1.0."""
        assert hasattr(simulation, 'UI_COLLISION_TOGGLE_X_FACTOR')
        assert simulation.UI_COLLISION_TOGGLE_X_FACTOR >= 1.0
        assert simulation.UI_COLLISION_TOGGLE_X_FACTOR == 1.2
    
    def test_ui_collision_toggle_y_offset_is_positive(self):
        """GIVEN: UI_COLLISION_TOGGLE_Y_OFFSET constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_COLLISION_TOGGLE_Y_OFFSET')
        assert simulation.UI_COLLISION_TOGGLE_Y_OFFSET > 0
        assert simulation.UI_COLLISION_TOGGLE_Y_OFFSET == 5
    
    def test_ui_regelung_button_x_is_positive(self):
        """GIVEN: UI_REGELUNG_BUTTON_X constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_REGELUNG_BUTTON_X')
        assert simulation.UI_REGELUNG_BUTTON_X > 0
        assert simulation.UI_REGELUNG_BUTTON_X == 1700
    
    def test_ui_regelung_button_y_is_positive(self):
        """GIVEN: UI_REGELUNG_BUTTON_Y constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_REGELUNG_BUTTON_Y')
        assert simulation.UI_REGELUNG_BUTTON_Y > 0
        assert simulation.UI_REGELUNG_BUTTON_Y == 530
    
    def test_ui_regelung_button_spacing_is_positive(self):
        """GIVEN: UI_REGELUNG_BUTTON_SPACING constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_REGELUNG_BUTTON_SPACING')
        assert simulation.UI_REGELUNG_BUTTON_SPACING > 0
        assert simulation.UI_REGELUNG_BUTTON_SPACING == 30
    
    def test_ui_dialog_width_is_positive(self):
        """GIVEN: UI_DIALOG_WIDTH constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_WIDTH')
        assert simulation.UI_DIALOG_WIDTH > 0
        assert simulation.UI_DIALOG_WIDTH == 500
    
    def test_ui_dialog_height_is_positive(self):
        """GIVEN: UI_DIALOG_HEIGHT constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_HEIGHT')
        assert simulation.UI_DIALOG_HEIGHT > 0
        assert simulation.UI_DIALOG_HEIGHT == 200
    
    def test_ui_dialog_button_width_is_positive(self):
        """GIVEN: UI_DIALOG_BUTTON_WIDTH constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_BUTTON_WIDTH')
        assert simulation.UI_DIALOG_BUTTON_WIDTH > 0
        assert simulation.UI_DIALOG_BUTTON_WIDTH == 100
    
    def test_ui_dialog_button_height_is_positive(self):
        """GIVEN: UI_DIALOG_BUTTON_HEIGHT constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_BUTTON_HEIGHT')
        assert simulation.UI_DIALOG_BUTTON_HEIGHT > 0
        assert simulation.UI_DIALOG_BUTTON_HEIGHT == 30
    
    def test_ui_dialog_button_padding_is_positive(self):
        """GIVEN: UI_DIALOG_BUTTON_PADDING constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_BUTTON_PADDING')
        assert simulation.UI_DIALOG_BUTTON_PADDING > 0
        assert simulation.UI_DIALOG_BUTTON_PADDING == 30
    
    def test_ui_dialog_button_x_offset_is_positive(self):
        """GIVEN: UI_DIALOG_BUTTON_X_OFFSET constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_BUTTON_X_OFFSET')
        assert simulation.UI_DIALOG_BUTTON_X_OFFSET > 0
        assert simulation.UI_DIALOG_BUTTON_X_OFFSET == 100
    
    def test_ui_dialog_button_spacing_is_positive(self):
        """GIVEN: UI_DIALOG_BUTTON_SPACING constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'UI_DIALOG_BUTTON_SPACING')
        assert simulation.UI_DIALOG_BUTTON_SPACING > 0
        assert simulation.UI_DIALOG_BUTTON_SPACING == 100


class TestLogThreshold:
    """Tests for LOG_THRESHOLD_SECONDS constant."""
    
    # TESTBASIS: LOG_THRESHOLD_SECONDS definition
    # TESTVERFAHREN: Äquivalenzklassenbildung - validate logging threshold
    
    def test_log_threshold_seconds_is_positive(self):
        """GIVEN: LOG_THRESHOLD_SECONDS constant
        WHEN: checking value
        THEN: should be positive integer."""
        assert hasattr(simulation, 'LOG_THRESHOLD_SECONDS')
        assert simulation.LOG_THRESHOLD_SECONDS > 0
        assert isinstance(simulation.LOG_THRESHOLD_SECONDS, int)
        assert simulation.LOG_THRESHOLD_SECONDS == 20


# ==============================================================================
# _finalize_exit Tests
# ==============================================================================


class TestFinalizeExitHard:
    """Tests for _finalize_exit with hard_kill=True."""
    
    # TESTBASIS: simulation._finalize_exit(hard_kill=True)
    # TESTVERFAHREN: Äquivalenzklassenbildung - verify hard exit behavior
    
    @patch('crazycar.sim.simulation.pygame')
    @patch('crazycar.sim.simulation.sys')
    def test_finalize_exit_hard_calls_pygame_quit(self, mock_sys, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=True
        WHEN: calling function
        THEN: should call pygame.quit()."""
        simulation._finalize_exit(hard_kill=True)
        mock_pygame.quit.assert_called_once()
    
    @patch('crazycar.sim.simulation.pygame')
    @patch('crazycar.sim.simulation.sys')
    def test_finalize_exit_hard_calls_sys_exit(self, mock_sys, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=True
        WHEN: calling function
        THEN: should call sys.exit(0)."""
        simulation._finalize_exit(hard_kill=True)
        mock_sys.exit.assert_called_once_with(0)
    
    @patch('crazycar.sim.simulation.pygame')
    @patch('crazycar.sim.simulation.sys')
    def test_finalize_exit_hard_pygame_quit_before_exit(self, mock_sys, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=True
        WHEN: calling function
        THEN: pygame.quit() should be called before sys.exit()."""
        call_order = []
        mock_pygame.quit.side_effect = lambda: call_order.append('quit')
        mock_sys.exit.side_effect = lambda x: call_order.append('exit')
        
        simulation._finalize_exit(hard_kill=True)
        
        assert call_order == ['quit', 'exit']
    
    @pytest.mark.skip("Exception handling in finally block difficult to test")
    def test_finalize_exit_hard_handles_pygame_quit_exception(self):
        """GIVEN: _finalize_exit with hard_kill=True and pygame.quit raises
        WHEN: calling function
        THEN: should still call sys.exit(0)."""
        pass


class TestFinalizeExitSoft:
    """Tests for _finalize_exit with hard_kill=False."""
    
    # TESTBASIS: simulation._finalize_exit(hard_kill=False)
    # TESTVERFAHREN: Äquivalenzklassenbildung - verify soft exit behavior
    
    @patch('crazycar.sim.simulation.pygame')
    def test_finalize_exit_soft_calls_pygame_quit(self, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=False
        WHEN: calling function
        THEN: should call pygame.quit() and raise SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            simulation._finalize_exit(hard_kill=False)
        
        mock_pygame.quit.assert_called_once()
        assert exc_info.value.code == 0
    
    @patch('crazycar.sim.simulation.pygame')
    def test_finalize_exit_soft_raises_system_exit(self, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=False
        WHEN: calling function
        THEN: should raise SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            simulation._finalize_exit(hard_kill=False)
        
        assert exc_info.value.code == 0
    
    @patch('crazycar.sim.simulation.pygame')
    @patch('crazycar.sim.simulation.sys')
    def test_finalize_exit_soft_does_not_call_sys_exit(self, mock_sys, mock_pygame):
        """GIVEN: _finalize_exit with hard_kill=False
        WHEN: calling function
        THEN: should NOT call sys.exit()."""
        with pytest.raises(SystemExit):
            simulation._finalize_exit(hard_kill=False)
        
        mock_sys.exit.assert_not_called()
    
    @pytest.mark.skip("Exception handling in finally block difficult to test")
    def test_finalize_exit_soft_handles_pygame_quit_exception(self):
        """GIVEN: _finalize_exit with hard_kill=False and pygame.quit raises
        WHEN: calling function
        THEN: should still raise SystemExit."""
        pass


# ==============================================================================
# Module-Level Attributes
# ==============================================================================


class TestModuleAttributes:
    """Tests for module-level attributes and dependencies."""
    
    # TESTBASIS: simulation.py module structure
    # TESTVERFAHREN: Fehlervermutung - verify imports and globals
    
    def test_module_has_run_simulation_function(self):
        """GIVEN: simulation module
        WHEN: checking for run_simulation
        THEN: should have callable run_simulation."""
        assert hasattr(simulation, 'run_simulation')
        assert callable(simulation.run_simulation)
    
    def test_module_has_finalize_exit_function(self):
        """GIVEN: simulation module
        WHEN: checking for _finalize_exit
        THEN: should have callable _finalize_exit."""
        assert hasattr(simulation, '_finalize_exit')
        assert callable(simulation._finalize_exit)
    
    def test_module_has_log_logger(self):
        """GIVEN: simulation module
        WHEN: checking for log
        THEN: should have logger instance."""
        assert hasattr(simulation, 'log')
        import logging
        assert isinstance(simulation.log, logging.Logger)
    
    def test_module_imports_pygame(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import pygame."""
        assert hasattr(simulation, 'pygame')
        import pygame as pg
        assert simulation.pygame is pg
    
    def test_module_imports_neat(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import neat."""
        assert hasattr(simulation, 'neat')
    
    def test_module_imports_car_model(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import Car."""
        assert hasattr(simulation, 'Car')
    
    def test_module_imports_state(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import SimConfig, SimRuntime."""
        assert hasattr(simulation, 'SimConfig')
        assert hasattr(simulation, 'SimRuntime')
        assert hasattr(simulation, 'build_default_config')
        assert hasattr(simulation, 'seed_all')
    
    def test_module_imports_event_source(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import EventSource."""
        assert hasattr(simulation, 'EventSource')
    
    def test_module_imports_mode_manager(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import ModeManager."""
        assert hasattr(simulation, 'ModeManager')
        assert hasattr(simulation, 'UIRects')
    
    def test_module_imports_map_service(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import MapService."""
        assert hasattr(simulation, 'MapService')
    
    def test_module_imports_loop(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import run_loop, UICtx."""
        assert hasattr(simulation, 'run_loop')
        assert hasattr(simulation, 'UICtx')
    
    def test_module_imports_toggle_button(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import ToggleButton."""
        assert hasattr(simulation, 'ToggleButton')
    
    def test_module_imports_spawn_utils(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import spawn_from_map."""
        assert hasattr(simulation, 'spawn_from_map')
    
    def test_module_imports_screen_service(self):
        """GIVEN: simulation module
        WHEN: checking imports
        THEN: should import get_or_create_screen."""
        assert hasattr(simulation, 'get_or_create_screen')
