# tests/control/test_optimizer_api_helpers.py
"""Unit Tests für optimizer_api.py Helper Functions.

TESTBASIS:
- Modul crazycar.control.optimizer_api - Helper Functions
- _try_get(), _apply_status_message()
- Module imports and public API (simulate_car, run_optimization)

TESTVERFAHREN:
- Mock-basiert: Queue, Status messages
- Functional: Helper logic, Queue operations
- Smoke Tests: Module imports and function existence

ISTQB Test Level: Unit Testing
ISTQB Test Type: Functional Testing (helper logic)
ISTQB Test Technique: Branch Coverage (all decision paths), Error Guessing (edge cases)
"""
import pytest
from unittest.mock import Mock, MagicMock
import queue as _queue
import os
import sys
import types


pytestmark = pytest.mark.unit


# ==============================================================================
# TESTGRUPPE 1: _try_get() Tests
# ==============================================================================

class TestTryGet:
    """Tests für _try_get() helper function."""
    
    def test_try_get_returns_item_when_available(self):
        """GIVEN: Queue mit Item, WHEN: _try_get, THEN: Item returned.
        
        TESTBASIS:
            Function _try_get() - Normal case
        
        TESTVERFAHREN:
            Functional: Queue.get() success
        
        Erwartung: Item wird zurückgegeben.
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _try_get
        
        mock_queue = Mock()
        mock_queue.get_nowait.return_value = {"status": "finished"}
        
        # ACT
        result = _try_get(mock_queue)
        
        # THEN
        assert result == {"status": "finished"}
        mock_queue.get_nowait.assert_called_once()
    
    def test_try_get_returns_none_on_empty_queue(self):
        """GIVEN: Leere Queue, WHEN: _try_get, THEN: None returned.
        
        TESTBASIS:
            Function _try_get() - Empty Queue
        
        TESTVERFAHREN:
            Exception Handling: queue.Empty
        
        Erwartung: None bei leerer Queue.
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _try_get
        
        mock_queue = Mock()
        mock_queue.get_nowait.side_effect = _queue.Empty()
        
        # ACT
        result = _try_get(mock_queue)
        
        # THEN
        assert result is None


# ==============================================================================
# TESTGRUPPE 2: _apply_status_message() Tests
# ==============================================================================

class TestApplyStatusMessage:
    """Tests für _apply_status_message() helper function."""
    
    def test_apply_status_message_with_aborted(self):
        """GIVEN: Message + aborted, WHEN: _apply_status_message, THEN: Keine Exception.
        
        TESTBASIS:
            Function _apply_status_message() - Aborted state
        
        TESTVERFAHREN:
            State Test: aborted=True
        
        Erwartung: Function läuft ohne Exception.
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"type": "abort"}
        
        # ACT & THEN: Should not raise
        _apply_status_message(msg, aborted=True, finished_ok=False, runtime=5.0)
    
    def test_apply_status_message_with_finished_ok(self):
        """GIVEN: Message + finished, WHEN: _apply_status_message, THEN: Keine Exception.
        
        TESTBASIS:
            Function _apply_status_message() - Finished state
        
        TESTVERFAHREN:
            State Test: finished_ok=True
        
        Erwartung: Function läuft ohne Exception.
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"type": "finished", "time": 10.5}
        
        # ACT & THEN: Should not raise
        _apply_status_message(msg, aborted=False, finished_ok=True, runtime=10.5)
    
    def test_apply_status_message_with_none_runtime(self):
        """GIVEN: Message + None runtime, WHEN: _apply_status_message, THEN: Keine Exception.
        
        TESTBASIS:
            Function _apply_status_message() - None runtime
        
        TESTVERFAHREN:
            Boundary: runtime=None
        
        Erwartung: Function toleriert None runtime.
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"type": "timeout"}
        
        # ACT & THEN: Should not raise
        _apply_status_message(msg, aborted=False, finished_ok=False, runtime=None)
    
    def test_apply_status_message_handles_ok_message(self):
        """Unit Test: _apply_status_message handles 'ok' status from run_neat_entry.
        
        Test Objective:
            Verify _apply_status_message() correctly processes messages with
            status="ok" (realistic message format from run_neat_entry).
        
        Pre-Conditions:
            - Message: {"status": "ok", "runtime": 0.42}
            - aborted=False, finished_ok=False, runtime=0.42
        
        Test Steps:
            1. Create message with status="ok" and runtime
            2. Call _apply_status_message with message
            3. Assert no exception raised
        
        Expected Results:
            - Function completes without exception
            - Status="ok" message handled correctly
        
        ISTQB Coverage:
            - Branch Coverage: status="ok" branch
            - Integration: Realistic message format from adapter
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"status": "ok", "runtime": 0.42}
        
        # ACT & THEN: Should not raise
        _apply_status_message(msg, aborted=False, finished_ok=False, runtime=0.42)
    
    def test_apply_status_message_handles_aborted_message(self):
        """Unit Test: _apply_status_message handles 'aborted' status from run_neat_entry.
        
        Test Objective:
            Verify _apply_status_message() correctly processes messages with
            status="aborted" (realistic message format from SystemExit catch).
        
        Pre-Conditions:
            - Message: {"status": "aborted"}
            - aborted=True, finished_ok=False, runtime=None
        
        Test Steps:
            1. Create message with status="aborted"
            2. Call _apply_status_message with aborted=True
            3. Assert no exception raised
        
        Expected Results:
            - Function completes without exception
            - Status="aborted" message handled correctly
        
        ISTQB Coverage:
            - Branch Coverage: status="aborted" branch
            - Error Handling: Abort scenario
        """
        # ARRANGE
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"status": "aborted"}
        
        # ACT & THEN: Should not raise
        _apply_status_message(msg, aborted=True, finished_ok=False, runtime=None)
    
    def test_apply_status_message_handles_error_message(self):
        """Unit Test: _apply_status_message handles 'error' status from run_neat_entry.
        
        Test Objective:
            Verify _apply_status_message() correctly processes messages with
            status="error" (realistic message format from exception catch).
        
        Pre-Conditions:
            - Message: {"status": "error", "error": "boom"}
            - aborted=False, finished_ok=False, runtime=1.0
        
        Test Steps:
            1. Create message with status="error" and error description
            2. Call _apply_status_message
            3. Assert RuntimeError raised with error message
        
        Expected Results:
            - RuntimeError raised with message "Simulation error (child): boom"
            - Status="error" message handled correctly (raises exception)
        
        ISTQB Coverage:
            - Branch Coverage: status="error" branch
            - Error Handling: Error message processing (exception raised)
        """
        # ARRANGE
        import pytest
        from crazycar.control.optimizer_api import _apply_status_message
        
        msg = {"status": "error", "error": "boom"}
        
        # ACT & THEN: Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Simulation error.*boom"):
            _apply_status_message(msg, aborted=False, finished_ok=False, runtime=1.0)


# ==============================================================================
# TESTGRUPPE 3: Module Constants & Imports
# ==============================================================================

class TestOptimizerApiModule:
    """Tests für optimizer_api module structure."""
    
    @pytest.mark.smoke
    def test_module_imports(self):
        """GIVEN: optimizer_api, WHEN: Import, THEN: Success.
        
        TESTBASIS:
            Module crazycar.control.optimizer_api - Imports
        
        TESTVERFAHREN:
            Structural: Module importable
        
        Erwartung: Module kann importiert werden.
        """
        # ACT & THEN
        try:
            from crazycar.control import optimizer_api
            assert optimizer_api is not None
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    @pytest.mark.smoke
    def test_simulate_car_function_exists(self):
        """GIVEN: optimizer_api, WHEN: Check functions, THEN: simulate_car exists.
        
        TESTBASIS:
            Module crazycar.control.optimizer_api - Public API
        
        TESTVERFAHREN:
            Structural: Function existence
        
        Erwartung: simulate_car() function existiert.
        """
        # ACT
        from crazycar.control.optimizer_api import simulate_car
        
        # THEN
        assert callable(simulate_car)
    
    @pytest.mark.smoke
    def test_run_optimization_function_exists(self):
        """GIVEN: optimizer_api, WHEN: Check functions, THEN: run_optimization exists.
        
        TESTBASIS:
            Module crazycar.control.optimizer_api - Public API
        
        TESTVERFAHREN:
            Structural: Function existence
        
        Erwartung: run_optimization() function existiert.
        """
        # ACT
        from crazycar.control.optimizer_api import run_optimization
        
        # THEN
        assert callable(run_optimization)
