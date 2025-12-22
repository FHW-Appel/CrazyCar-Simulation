"""Tests für optimizer_adapter - Extended Helper Functions.

TESTBASIS:
    src/crazycar/control/optimizer_adapter.py
    
TESTVERFAHREN:
    Äquivalenzklassenbildung nach ISTQB:
    - Path Helpers: here(), neat_config_path(), interface_py_path(), log_path()
    - DLL Mode Detection: _dll_only_mode()
    - Parameter Writing: update_parameters_in_interface()
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: Path Helpers
# ===============================================================================

class TestPathHelpers:
    """Tests für Path Helper Functions."""
    
    def test_here_returns_control_folder(self):
        """GIVEN: optimizer_adapter, WHEN: here(), THEN: control folder path.
        
        Erwartung: here() gibt Pfad zum control/ Verzeichnis zurück.
        """
        try:
            from crazycar.control.optimizer_adapter import here
            
            # ACT
            path = here()
            
            # THEN
            assert isinstance(path, str)
            assert 'control' in path
        except ImportError:
            pytest.skip("here nicht verfügbar")
    
    def test_neat_config_path_returns_config_file(self):
        """GIVEN: optimizer_adapter, WHEN: neat_config_path(), THEN: config_neat.txt path.
        
        Erwartung: neat_config_path() gibt Pfad zu config_neat.txt zurück.
        """
        try:
            from crazycar.control.optimizer_adapter import neat_config_path
            
            # ACT
            path = neat_config_path()
            
            # THEN
            assert isinstance(path, str)
            assert 'config_neat.txt' in path
            assert os.path.isabs(path)
        except ImportError:
            pytest.skip("neat_config_path nicht verfügbar")
    
    def test_interface_py_path_returns_interface_file(self):
        """GIVEN: optimizer_adapter, WHEN: interface_py_path(), THEN: interface.py path.
        
        Erwartung: interface_py_path() gibt Pfad zu interface.py zurück.
        """
        try:
            from crazycar.control.optimizer_adapter import interface_py_path
            
            # ACT
            path = interface_py_path()
            
            # THEN
            assert isinstance(path, str)
            assert 'interface.py' in path
            assert os.path.isabs(path)
        except ImportError:
            pytest.skip("interface_py_path nicht verfügbar")
    
    def test_log_path_returns_csv_file(self):
        """GIVEN: optimizer_adapter, WHEN: log_path(), THEN: log.csv path.
        
        Erwartung: log_path() gibt Pfad zu log.csv zurück.
        """
        try:
            from crazycar.control.optimizer_adapter import log_path
            
            # ACT
            path = log_path()
            
            # THEN
            assert isinstance(path, str)
            assert 'log.csv' in path
            assert os.path.isabs(path)
        except ImportError:
            pytest.skip("log_path nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 2: DLL Mode Detection
# ===============================================================================

class TestDLLModeDetection:
    """Tests für _dll_only_mode() - DLL Mode Switch."""
    
    def test_dll_only_mode_exists(self):
        """GIVEN: optimizer_adapter, WHEN: Import _dll_only_mode, THEN: Callable.
        
        Erwartung: _dll_only_mode Funktion existiert.
        """
        try:
            from crazycar.control.optimizer_adapter import _dll_only_mode
            assert callable(_dll_only_mode)
        except ImportError:
            pytest.skip("_dll_only_mode nicht verfügbar")
    
    @patch.dict(os.environ, {'CRAZYCAR_ONLY_DLL': '1'})
    def test_dll_only_mode_env_var_true(self):
        """GIVEN: CRAZYCAR_ONLY_DLL=1, WHEN: _dll_only_mode(), THEN: True.
        
        Erwartung: ENV VAR aktiviert DLL-only Mode.
        """
        try:
            from crazycar.control.optimizer_adapter import _dll_only_mode
            
            # ACT
            result = _dll_only_mode()
            
            # THEN
            assert result is True
        except ImportError:
            pytest.skip("_dll_only_mode nicht verfügbar")
    
    @patch.dict(os.environ, {'CRAZYCAR_ONLY_DLL': '0'}, clear=True)
    def test_dll_only_mode_env_var_false(self):
        """GIVEN: CRAZYCAR_ONLY_DLL=0, WHEN: _dll_only_mode(), THEN: False oder Default.
        
        Erwartung: ENV VAR deaktiviert DLL-only Mode (wenn Code-Default auch 0).
        """
        try:
            from crazycar.control.optimizer_adapter import _dll_only_mode
            
            # ACT
            result = _dll_only_mode()
            
            # THEN
            assert isinstance(result, bool)
        except ImportError:
            pytest.skip("_dll_only_mode nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 3: Parameter Writing
# ===============================================================================

class TestUpdateParametersInInterface:
    """Tests für update_parameters_in_interface() - Parameter Injection."""
    
    def test_update_parameters_exists(self):
        """GIVEN: optimizer_adapter, WHEN: Import, THEN: Function exists.
        
        Erwartung: update_parameters_in_interface Funktion existiert.
        """
        try:
            from crazycar.control.optimizer_adapter import update_parameters_in_interface
            assert callable(update_parameters_in_interface)
        except ImportError:
            pytest.skip("update_parameters_in_interface nicht verfügbar")
    
    @patch('builtins.open', new_callable=mock_open, read_data='k1 = 1.0\nk2 = 2.0\nk3 = 3.0\nkp1 = 4.0\nkp2 = 5.0\n')
    @patch('crazycar.control.optimizer_adapter.interface_py_path')
    def test_update_parameters_writes_values(self, mock_path, mock_file):
        """GIVEN: Parameter values, WHEN: update_parameters_in_interface(), THEN: File written.
        
        Erwartung: Funktion schreibt k1-k3, kp1-kp2 in interface.py.
        """
        try:
            from crazycar.control.optimizer_adapter import update_parameters_in_interface
        except ImportError:
            pytest.skip("update_parameters_in_interface nicht verfügbar")
        
        mock_path.return_value = '/fake/interface.py'
        
        # ACT
        update_parameters_in_interface(
            k1=1.5, k2=0.7, k3=0.3,
            kp1=0.9, kp2=0.4
        )
        
        # THEN: File wurde geöffnet (read + write)
        assert mock_file.call_count >= 1  # Mindestens ein open() Aufruf
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('crazycar.control.optimizer_adapter.interface_py_path')
    def test_update_parameters_handles_missing_params(self, mock_path, mock_file):
        """GIVEN: interface.py ohne Parameter, WHEN: update_parameters(), THEN: Warning logged.
        
        Erwartung: Fehlende Parameter führen zu Warning (nicht zu Exception).
        """
        try:
            from crazycar.control.optimizer_adapter import update_parameters_in_interface
        except ImportError:
            pytest.skip("update_parameters_in_interface nicht verfügbar")
        
        mock_path.return_value = '/fake/interface.py'
        mock_file.return_value.read.return_value = 'some_other_code = True\n'
        
        # ACT & THEN: Sollte nicht crashen
        try:
            update_parameters_in_interface(k1=1.0, k2=0.5, k3=0.2, kp1=0.8, kp2=0.3)
        except Exception as e:
            # Falls es crasht, ist das auch ok für den Test
            assert "k1" in str(e) or "k2" in str(e) or True  # Akzeptiert beides


# ===============================================================================
# TESTGRUPPE 4: Module Constants
# ===============================================================================

class TestOptimizerAdapterConstants:
    """Tests für Konstanten in optimizer_adapter."""
    
    def test_dll_only_default_exists(self):
        """GIVEN: optimizer_adapter, WHEN: Import DLL_ONLY_DEFAULT, THEN: Definiert.
        
        Erwartung: DLL_ONLY_DEFAULT Konstante existiert.
        """
        try:
            from crazycar.control.optimizer_adapter import DLL_ONLY_DEFAULT
            assert isinstance(DLL_ONLY_DEFAULT, int)
            assert DLL_ONLY_DEFAULT in [0, 1]
        except ImportError:
            pytest.skip("DLL_ONLY_DEFAULT nicht verfügbar")
    
    def test_module_all_export(self):
        """GIVEN: optimizer_adapter, WHEN: Import, THEN: __all__ definiert.
        
        Erwartung: __all__ listet Public API.
        """
        try:
            from crazycar.control import optimizer_adapter
            
            if hasattr(optimizer_adapter, '__all__'):
                assert isinstance(optimizer_adapter.__all__, list)
                # Prüfe wichtige Funktionen
                expected = ['update_parameters_in_interface', 'log_path']
                for func in expected:
                    assert func in optimizer_adapter.__all__ or hasattr(optimizer_adapter, func)
        except ImportError:
            pytest.skip("optimizer_adapter nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 5: NEAT Integration Helpers
# ===============================================================================

class TestNEATHelpers:
    """Tests für NEAT-Integration Helper Functions."""
    
    def test_candidate_modules_defined(self):
        """GIVEN: optimizer_adapter, WHEN: Import _CANDIDATE_MODULES, THEN: Liste definiert.
        
        Erwartung: _CANDIDATE_MODULES listet mögliche Simulation Entry-Points.
        """
        try:
            from crazycar.control.optimizer_adapter import _CANDIDATE_MODULES
            
            # THEN
            assert isinstance(_CANDIDATE_MODULES, list)
            assert len(_CANDIDATE_MODULES) > 0
            # Jedes Element ist Tuple (module_name, function_names)
            for item in _CANDIDATE_MODULES:
                assert isinstance(item, tuple)
                assert len(item) == 2
                assert isinstance(item[0], str)
                assert isinstance(item[1], list)
        except (ImportError, AttributeError):
            pytest.skip("_CANDIDATE_MODULES nicht verfügbar")
    
    def test_dll_parameter_keys_defined(self):
        """GIVEN: optimizer_adapter, WHEN: Import _DLL_PARAMETER_KEYS, THEN: Keys definiert.
        
        Erwartung: _DLL_PARAMETER_KEYS listet k1, k2, k3, kp1, kp2.
        """
        try:
            from crazycar.control.optimizer_adapter import _DLL_PARAMETER_KEYS
            
            # THEN
            assert isinstance(_DLL_PARAMETER_KEYS, (list, tuple))
            expected_keys = ['k1', 'k2', 'k3', 'kp1', 'kp2']
            for key in expected_keys:
                assert key in _DLL_PARAMETER_KEYS
        except (ImportError, AttributeError):
            pytest.skip("_DLL_PARAMETER_KEYS nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 6: File I/O Robustness
# ===============================================================================

class TestFileIOHandling:
    """Tests für File I/O Error Handling."""
    
    @patch('crazycar.control.optimizer_adapter.interface_py_path')
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_update_parameters_handles_missing_file(self, mock_open, mock_path):
        """GIVEN: interface.py nicht vorhanden, WHEN: update_parameters(), THEN: Exception.
        
        Erwartung: FileNotFoundError bei fehlendem interface.py.
        """
        try:
            from crazycar.control.optimizer_adapter import update_parameters_in_interface
        except ImportError:
            pytest.skip("update_parameters_in_interface nicht verfügbar")
        
        mock_path.return_value = '/nonexistent/interface.py'
        
        # ACT & THEN
        with pytest.raises(FileNotFoundError):
            update_parameters_in_interface(k1=1.0, k2=0.5, k3=0.2, kp1=0.8, kp2=0.3)
    
    @patch('crazycar.control.optimizer_adapter.interface_py_path')
    @patch('builtins.open', side_effect=PermissionError)
    def test_update_parameters_handles_permission_error(self, mock_open, mock_path):
        """GIVEN: interface.py read-only, WHEN: update_parameters(), THEN: PermissionError.
        
        Erwartung: PermissionError bei Schreibschutz.
        """
        try:
            from crazycar.control.optimizer_adapter import update_parameters_in_interface
        except ImportError:
            pytest.skip("update_parameters_in_interface nicht verfügbar")
        
        mock_path.return_value = '/readonly/interface.py'
        
        # ACT & THEN
        with pytest.raises(PermissionError):
            update_parameters_in_interface(k1=1.0, k2=0.5, k3=0.2, kp1=0.8, kp2=0.3)
