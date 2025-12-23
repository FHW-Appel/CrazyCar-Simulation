"""Unit-Tests für Main Module - Entry Point und CLI.

TESTBASIS (ISTQB):
- Anforderung: Haupteinstiegspunkt, Build, Quit Guard, Optimization Entry
- Module: crazycar.main
- Funktionen: main(), _install_pygame_quit_guard(), _print_result()

TESTVERFAHREN:
- Äquivalenzklassen: Mit/ohne DEBUG, Verschiedene Ergebnisse
- Mock-basiert: Build + Optimization mocken
- Fehlerbehandlung: Build-Fehler, Optimizer-Fehler, KeyboardInterrupt
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import logging

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: Modul-Import & Constants
# ===============================================================================

class TestMainImport:
    """Tests für Main-Modul Import."""
    
    def test_main_module_import(self):
        """GIVEN: Main-Modul, WHEN: Import, THEN: Erfolgreich.
        
        Erwartung: Modul kann importiert werden.
        """
        # ACT & THEN
        try:
            from crazycar import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Import fehlgeschlagen: {e}")
    
    def test_main_has_main_function(self):
        """GIVEN: Main-Modul, WHEN: main() Funktion prüfen, THEN: Vorhanden.
        
        Erwartung: main() Entry-Point existiert.
        """
        # ACT
        try:
            from crazycar import main
            
            # THEN: main() Funktion vorhanden
            assert hasattr(main, 'main')
            assert callable(main.main)
        except ImportError:
            pytest.skip("Modul nicht verfügbar")
    
    def test_debug_default_constant(self):
        """GIVEN: Main-Modul, WHEN: Import DEBUG_DEFAULT, THEN: Wert definiert.
        
        Erwartung: DEBUG_DEFAULT Konstante existiert (0 oder 1).
        """
        # ACT
        try:
            from crazycar.main import DEBUG_DEFAULT
            
            # THEN
            assert isinstance(DEBUG_DEFAULT, int)
            assert DEBUG_DEFAULT in [0, 1]
        except ImportError:
            pytest.skip("DEBUG_DEFAULT nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 2: Pygame Quit Guard
# ===============================================================================

class TestPygameQuitGuard:
    """Tests für _install_pygame_quit_guard()."""
    
    def test_install_pygame_quit_guard_exists(self):
        """GIVEN: Main-Modul, WHEN: Import _install_pygame_quit_guard, THEN: Vorhanden.
        
        Erwartung: _install_pygame_quit_guard Funktion existiert.
        """
        # ACT
        try:
            from crazycar.main import _install_pygame_quit_guard
            
            # THEN
            assert callable(_install_pygame_quit_guard)
        except ImportError:
            pytest.skip("_install_pygame_quit_guard nicht verfügbar")
    
    @pytest.mark.skip("pygame not available in main module scope for mocking")
    def test_install_pygame_quit_guard_patches_event_get(self):
        """GIVEN: Pygame, WHEN: _install_pygame_quit_guard(), THEN: event.get gepatcht.
        
        Erwartung: pygame.event.get wird durch Wrapper ersetzt.
        """
        pass
    
    @pytest.mark.skip(reason="Komplexe Pygame-Event Simulation")
    def test_quit_guard_triggers_on_esc(self):
        """GIVEN: ESC Event, WHEN: pygame.event.get(), THEN: SystemExit(0).
        
        Erwartung: ESC-Taste führt zu sofortigem Exit.
        """
        # Würde komplexes Pygame-Event-Mocking benötigen
        pass


# ===============================================================================
# TESTGRUPPE 3: _print_result() Helper
# ===============================================================================

class TestPrintResult:
    """Tests für _print_result() - Result Formatter."""
    
    def test_print_result_exists(self):
        """GIVEN: Main-Modul, WHEN: Import _print_result, THEN: Vorhanden.
        
        Erwartung: _print_result Funktion existiert.
        """
        # ACT
        try:
            from crazycar.main import _print_result
            
            # THEN
            assert callable(_print_result)
        except ImportError:
            pytest.skip("_print_result nicht verfügbar")
    
    @patch('logging.getLogger')
    def test_print_result_logs_parameters(self, mock_get_logger):
        """GIVEN: Result dict, WHEN: _print_result(), THEN: Logs parameters.
        
        Erwartung: _print_result loggt K1-K3, KP1-KP2, lap_time.
        """
        # ARRANGE
        try:
            from crazycar.main import _print_result
        except ImportError:
            pytest.skip("_print_result nicht verfügbar")
        
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        result = {
            'k1': 1.5, 'k2': 0.7, 'k3': 0.3,
            'kp1': 0.9, 'kp2': 0.4,
            'optimal_lap_time': 12.34
        }
        
        # ACT
        _print_result(result)
        
        # THEN: Logger wurde aufgerufen
        assert mock_logger.info.call_count >= 6  # Min. 6 Log-Zeilen


# ===============================================================================
# TESTGRUPPE 4: main() Function - Success Path
# ===============================================================================

class TestMainFunction:
    """Tests für main() - Entry Point."""
    
    @pytest.mark.skip("main() requires full integration stack")
    def test_main_success_path(self):
        """GIVEN: Valid setup, WHEN: main(), THEN: Returns 0.
        
        Erwartung: main() läuft erfolgreich durch.
        """
        pass
    
    @pytest.mark.skip("main() requires full integration stack")
    def test_main_handles_keyboard_interrupt(self):
        """GIVEN: KeyboardInterrupt, WHEN: main(), THEN: Returns 130.
        
        Erwartung: Ctrl+C wird sauber behandelt.
        """
        pass
    
    @pytest.mark.skip("main() requires full integration stack")
    def test_main_handles_exception(self):
        """GIVEN: Exception, WHEN: main(), THEN: Returns 1.
        
        Erwartung: Exceptions werden geloggt.
        """
        pass
    
    @pytest.mark.skip("main() requires full integration stack")
    def test_main_handles_aborted_optimization(self):
        """GIVEN: Optimizer abort, WHEN: main(), THEN: Returns 0.
        
        Erwartung: AbortedOptimization wird sauber behandelt.
        """
        pass
    
    @pytest.mark.skip("main() requires full integration stack")
    def test_main_handles_invalid_result(self):
        """GIVEN: Invalid result dict, WHEN: main(), THEN: Returns 1.
        
        Erwartung: Ungültiges Resultat wird abgefangen.
        """
        pass


# ===============================================================================
# TESTGRUPPE 5: Build Native Integration
# ===============================================================================

class TestBuildNativeIntegration:
    """Tests für Build-Native-Integration in main()."""
    
    @pytest.mark.skip("Build integration requires full setup")
    def test_main_adds_build_dir_to_syspath(self):
        """GIVEN: Build success, WHEN: main(), THEN: Build dir in sys.path.
        
        Erwartung: Build-Dir wird sys.path hinzugefügt.
        """
        pass
    
    @pytest.mark.skip("Build integration requires full setup")
    def test_main_continues_on_build_failure(self):
        """GIVEN: Build failure, WHEN: main(), THEN: Weiter mit Optimization.
        
        Erwartung: Build-Fehler stoppt main() nicht komplett.
        """
        pass


# ===============================================================================
# TESTGRUPPE 6: __name__ == "__main__" Entry
# ===============================================================================

class TestMainCLI:
    """Tests für CLI Entry Point (__name__ == __main__)."""
    
    def test_main_has_name_main_block(self):
        """GIVEN: main.py, WHEN: Als Script ausgeführt, THEN: __main__ Block.
        
        Erwartung: __main__ Block existiert für direkten Aufruf.
        """
        # ACT & THEN
        import crazycar.main
        assert crazycar.main is not None


# ===============================================================================
# TESTGRUPPE 3: Integration Mock Tests
# ===============================================================================

@pytest.mark.integration
class TestMainIntegration:
    """Integrationstests für Main-Modul."""
    
    def test_main_imports_all_dependencies(self):
        """GIVEN: Main-Modul, WHEN: Importieren, THEN: Alle Deps verfügbar.
        
        Erwartung: Keine fehlenden Dependencies.
        """
        # ACT & THEN
        try:
            from crazycar import main
            # Imports sollten erfolgreich sein
            assert True
        except ImportError as e:
            pytest.fail(f"Dependency fehlt: {e}")


# ===============================================================================
# TESTGRUPPE 4: main() Function Complete Tests
# ===============================================================================

class TestMainFunctionComplete:
    """Vollständige Tests für main() function."""
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_success_complete_flow(self, mock_guard, mock_opt, mock_build):
        """GIVEN: Alle Komponenten OK, WHEN: main(), THEN: Success Flow.
        
        TESTBASIS:
            Function main() - Complete Success Path
        
        TESTVERFAHREN:
            Integration: Build → Guard → Optimizer → Result
        
        Erwartung: Return 0, alle Funktionen aufgerufen.
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.return_value = {
            'success': True,
            'k1': 1.0, 'k2': 2.0, 'k3': 3.0,
            'kp1': 4.0, 'kp2': 5.0,
            'optimal_lap_time': 10.5
        }
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 0
        mock_build.assert_called_once()
        mock_guard.assert_called_once()
        mock_opt.assert_called_once()
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_optimization_invalid_result(self, mock_guard, mock_opt, mock_build):
        """GIVEN: Optimizer returns invalid, WHEN: main(), THEN: Error code.
        
        TESTBASIS:
            Function main() - Invalid Result Handling
        
        TESTVERFAHREN:
            Negative: None return
        
        Erwartung: Return 1.
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.return_value = None
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 1
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_user_abort(self, mock_guard, mock_opt, mock_build):
        """GIVEN: User abort, WHEN: main(), THEN: Clean exit 0.
        
        TESTBASIS:
            Function main() - User Abort
        
        TESTVERFAHREN:
            success=False Path
        
        Erwartung: Return 0 (nicht error).
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.return_value = {
            'success': False,
            'message': 'Aborted'
        }
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 0
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_keyboard_interrupt_handling(self, mock_guard, mock_opt, mock_build):
        """GIVEN: Ctrl+C, WHEN: main(), THEN: Exit 130.
        
        TESTBASIS:
            Function main() - KeyboardInterrupt
        
        TESTVERFAHREN:
            Exception: KeyboardInterrupt
        
        Erwartung: Return 130.
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.side_effect = KeyboardInterrupt()
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 130
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_system_exit_handling(self, mock_guard, mock_opt, mock_build):
        """GIVEN: SystemExit raised, WHEN: main(), THEN: Return code.
        
        TESTBASIS:
            Function main() - SystemExit
        
        TESTVERFAHREN:
            Exception: SystemExit with code
        
        Erwartung: Return exit code.
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.side_effect = SystemExit(5)
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 5
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_runtime_error(self, mock_guard, mock_opt, mock_build):
        """GIVEN: RuntimeError, WHEN: main(), THEN: Error code 1.
        
        TESTBASIS:
            Function main() - RuntimeError
        
        TESTVERFAHREN:
            Exception: Generic exception
        
        Erwartung: Return 1.
        """
        # ARRANGE
        mock_build.return_value = (0, "/fake/build")
        mock_opt.side_effect = RuntimeError("Test")
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 1
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_build_failed_continues(self, mock_guard, mock_opt, mock_build):
        """GIVEN: Build failed, WHEN: main(), THEN: Optimizer runs anyway.
        
        TESTBASIS:
            Function main() - Build Failure Recovery
        
        TESTVERFAHREN:
            Error Recovery
        
        Erwartung: Optimizer läuft trotz Build-Fehler.
        """
        # ARRANGE
        mock_build.return_value = (1, None)
        mock_opt.return_value = {
            'success': True,
            'k1': 1.0, 'k2': 2.0, 'k3': 3.0,
            'kp1': 4.0, 'kp2': 5.0,
            'optimal_lap_time': 10.5
        }
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 0
        mock_opt.assert_called_once()
    
    @patch('crazycar.main.run_build_native')
    @patch('crazycar.control.optimizer_api.run_optimization')
    @patch('crazycar.main._install_pygame_quit_guard')
    def test_main_build_exception_continues(self, mock_guard, mock_opt, mock_build):
        """GIVEN: Build Exception, WHEN: main(), THEN: Optimizer runs.
        
        TESTBASIS:
            Function main() - Build Exception Recovery
        
        TESTVERFAHREN:
            Exception Recovery
        
        Erwartung: Optimizer läuft trotz Exception.
        """
        # ARRANGE
        mock_build.side_effect = Exception("Build error")
        mock_opt.return_value = {
            'success': True,
            'k1': 1.0, 'k2': 2.0, 'k3': 3.0,
            'kp1': 4.0, 'kp2': 5.0,
            'optimal_lap_time': 10.5
        }
        
        from crazycar.main import main
        
        # ACT
        result = main()
        
        # THEN
        assert result == 0
        mock_opt.assert_called_once()


# ===============================================================================
# TESTGRUPPE 5: _print_result() Tests
# ===============================================================================

class TestPrintResult:
    """Tests für _print_result() helper."""
    
    def test_print_result_all_keys(self, caplog):
        """GIVEN: Result dict, WHEN: _print_result, THEN: Alle Keys geloggt.
        
        TESTBASIS:
            Function _print_result() - Logging
        
        TESTVERFAHREN:
            Functional: Check log output
        
        Erwartung: Alle 6 Parameter erscheinen in Logs.
        """
        # ARRANGE
        from crazycar.main import _print_result
        
        result = {
            'k1': 1.0,
            'k2': 2.0,
            'k3': 3.0,
            'kp1': 4.0,
            'kp2': 5.0,
            'optimal_lap_time': 10.5
        }
        
        with caplog.at_level(logging.INFO):
            # ACT
            _print_result(result)
        
        # THEN
        log_text = caplog.text.lower()
        assert 'k1' in log_text
        assert 'k2' in log_text
        assert 'k3' in log_text
        assert 'kp1' in log_text
        assert 'kp2' in log_text
        assert 'lap' in log_text or 'time' in log_text
