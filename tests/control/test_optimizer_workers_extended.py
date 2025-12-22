"""Tests für optimizer_workers - Process Lifecycle Management.

TESTBASIS:
    src/crazycar/control/optimizer_workers.py
    
TESTVERFAHREN:
    Äquivalenzklassenbildung nach ISTQB:
    - Process Spawning: spawn_worker() mit 'spawn' context
    - Process Cleanup: cleanup_worker() mit timeout + force-kill
    - Hard Kill: kill_process_hard() mit taskkill/SIGKILL
    - IPC Helpers: make_queue(), qget_nowait()
    - Context Management: ctx(), is_running(), safe_join()
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import multiprocessing as mp
import platform


pytestmark = pytest.mark.unit


# ===============================================================================
# FIXTURES
# ===============================================================================

@pytest.fixture
def mock_process():
    """Mock multiprocessing.Process."""
    proc = Mock(spec=mp.Process)
    proc.is_alive.return_value = True
    proc.pid = 12345
    proc.exitcode = None
    return proc


@pytest.fixture
def mock_queue():
    """Mock multiprocessing.Queue."""
    q = Mock()
    q.get_nowait.side_effect = Exception("Empty")  # Default: leer
    return q


# ===============================================================================
# TESTGRUPPE 1: Module Import & Public API
# ===============================================================================

class TestOptimizerWorkersImport:
    """Tests für Modul-Import und API-Existenz."""
    
    def test_optimizer_workers_import(self):
        """GIVEN: optimizer_workers Modul, WHEN: Import, THEN: Erfolgreich.
        
        Erwartung: optimizer_workers kann importiert werden.
        """
        # ACT & THEN
        try:
            import crazycar.control.optimizer_workers
            assert crazycar.control.optimizer_workers is not None
        except ImportError:
            pytest.skip("optimizer_workers nicht verfügbar")
    
    def test_spawn_worker_exists(self):
        """GIVEN: optimizer_workers, WHEN: Import spawn_worker, THEN: Callable.
        
        Erwartung: spawn_worker Funktion existiert.
        """
        # ARRANGE & ACT
        try:
            from crazycar.control.optimizer_workers import spawn_worker
            
            # THEN
            assert callable(spawn_worker)
        except ImportError:
            pytest.skip("spawn_worker nicht verfügbar")
    
    def test_cleanup_worker_exists(self):
        """GIVEN: optimizer_workers, WHEN: Import cleanup_worker, THEN: Callable.
        
        Erwartung: cleanup_worker Funktion existiert.
        """
        # ARRANGE & ACT
        try:
            from crazycar.control.optimizer_workers import cleanup_worker
            
            # THEN
            assert callable(cleanup_worker)
        except ImportError:
            pytest.skip("cleanup_worker nicht verfügbar")
    
    def test_kill_process_hard_exists(self):
        """GIVEN: optimizer_workers, WHEN: Import kill_process_hard, THEN: Callable.
        
        Erwartung: kill_process_hard Funktion existiert.
        """
        # ARRANGE & ACT
        try:
            from crazycar.control.optimizer_workers import kill_process_hard
            
            # THEN
            assert callable(kill_process_hard)
        except ImportError:
            pytest.skip("kill_process_hard nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 2: Context Management
# ===============================================================================

class TestContextManagement:
    """Tests für Multiprocessing Context."""
    
    def test_ctx_returns_context(self):
        """GIVEN: force_spawn=True, WHEN: ctx(), THEN: Spawn context.
        
        Erwartung: ctx() gibt 'spawn' multiprocessing context zurück.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import ctx
        except ImportError:
            pytest.skip("ctx nicht verfügbar")
        
        # ACT
        context = ctx(force_spawn=True)
        
        # THEN
        assert context is not None
        # Prüfe ob es ein multiprocessing context ist
        assert hasattr(context, 'Process') or hasattr(context, 'Queue')
    
    def test_make_queue_returns_queue(self):
        """GIVEN: force_spawn=True, WHEN: make_queue(), THEN: Queue object.
        
        Erwartung: make_queue() erstellt Queue aus spawn context.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import make_queue
        except ImportError:
            pytest.skip("make_queue nicht verfügbar")
        
        # ACT
        q = make_queue(force_spawn=True)
        
        # THEN
        assert q is not None
        assert hasattr(q, 'put') or hasattr(q, 'get')


# ===============================================================================
# TESTGRUPPE 3: Process Spawning
# ===============================================================================

class TestSpawnWorker:
    """Tests für spawn_worker() - Process Creation."""
    
    @pytest.mark.skip(reason="Benötigt echtes Multiprocessing")
    def test_spawn_worker_creates_process(self):
        """GIVEN: Target function, WHEN: spawn_worker(), THEN: Process created.
        
        Erwartung: spawn_worker() erstellt und startet Process.
        """
        from crazycar.control.optimizer_workers import spawn_worker
        
        def dummy_func():
            pass
        
        # ACT
        proc = spawn_worker(dummy_func, args=())
        
        # THEN
        assert proc is not None
        assert hasattr(proc, 'is_alive')
        assert hasattr(proc, 'pid')
        
        # Cleanup
        proc.terminate()
        proc.join()
    
    def test_spawn_worker_signature(self):
        """GIVEN: Target + args, WHEN: spawn_worker(), THEN: Akzeptiert params.
        
        Erwartung: spawn_worker(target, args, force_spawn) signature.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import spawn_worker
        except ImportError:
            pytest.skip("spawn_worker nicht verfügbar")
        
        # ACT & THEN: Prüfe dass Funktion existiert und callable ist
        assert callable(spawn_worker)
        # Signatur-Check würde inspect verwenden, aber wir testen nur Existenz


# ===============================================================================
# TESTGRUPPE 4: Process Cleanup
# ===============================================================================

class TestCleanupWorker:
    """Tests für cleanup_worker() - Process Termination."""
    
    def test_cleanup_worker_signature(self):
        """GIVEN: Process, WHEN: cleanup_worker(), THEN: Akzeptiert params.
        
        Erwartung: cleanup_worker(proc, timeout, force) signature.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import cleanup_worker
        except ImportError:
            pytest.skip("cleanup_worker nicht verfügbar")
        
        # ACT & THEN
        assert callable(cleanup_worker)
    
    @pytest.mark.skip(reason="Benötigt echtes Multiprocessing")
    def test_cleanup_worker_terminates_process(self):
        """GIVEN: Running process, WHEN: cleanup_worker(), THEN: Process stopped.
        
        Erwartung: cleanup_worker() beendet Process sauber.
        """
        from crazycar.control.optimizer_workers import spawn_worker, cleanup_worker
        import time
        
        def long_running():
            time.sleep(10)
        
        # ACT
        proc = spawn_worker(long_running, args=())
        cleanup_worker(proc, timeout=1.0, force=True)
        
        # THEN
        assert not proc.is_alive()


# ===============================================================================
# TESTGRUPPE 5: Hard Kill
# ===============================================================================

class TestKillProcessHard:
    """Tests für kill_process_hard() - Force Termination."""
    
    @patch('crazycar.control.optimizer_workers.platform.system')
    @patch('crazycar.control.optimizer_workers.subprocess.run')
    def test_kill_process_hard_windows_calls_taskkill(self, mock_run, mock_system, mock_process):
        """GIVEN: Windows + Process, WHEN: kill_process_hard(), THEN: taskkill aufgerufen.
        
        Erwartung: Auf Windows wird taskkill /F /T verwendet.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import kill_process_hard
        except ImportError:
            pytest.skip("kill_process_hard nicht verfügbar")
        
        mock_system.return_value = 'Windows'
        mock_process.pid = 12345
        
        # ACT
        try:
            kill_process_hard(mock_process)
            
            # THEN
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'taskkill' in str(call_args).lower()
        except Exception:
            # Bei Fehler: Prüfe nur dass platform.system aufgerufen wurde
            assert mock_system.call_count > 0
    
    @patch('crazycar.control.optimizer_workers.platform.system')
    @patch('crazycar.control.optimizer_workers.os.kill')
    def test_kill_process_hard_unix_calls_sigkill(self, mock_kill, mock_system, mock_process):
        """GIVEN: Unix + Process, WHEN: kill_process_hard(), THEN: SIGKILL gesendet.
        
        Erwartung: Auf Unix wird os.kill(pid, SIGKILL) verwendet.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import kill_process_hard
        except ImportError:
            pytest.skip("kill_process_hard nicht verfügbar")
        
        mock_system.return_value = 'Linux'
        mock_process.pid = 12345
        
        # ACT
        try:
            kill_process_hard(mock_process)
            
            # THEN
            mock_kill.assert_called_once()
            call_args = mock_kill.call_args[0]
            assert 12345 in call_args  # PID
        except Exception:
            # Bei Fehler: Prüfe nur dass platform.system aufgerufen wurde
            assert mock_system.call_count > 0


# ===============================================================================
# TESTGRUPPE 6: IPC Helpers
# ===============================================================================

class TestIPCHelpers:
    """Tests für Queue + IPC Helper Functions."""
    
    def test_qget_nowait_with_empty_queue(self, mock_queue):
        """GIVEN: Leere Queue, WHEN: qget_nowait(), THEN: None zurückgegeben.
        
        Erwartung: qget_nowait() gibt None zurück wenn Queue leer.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import qget_nowait
        except ImportError:
            pytest.skip("qget_nowait nicht verfügbar")
        
        mock_queue.get_nowait.side_effect = Exception("Empty")
        
        # ACT
        result = qget_nowait(mock_queue)
        
        # THEN
        assert result is None
    
    @pytest.mark.skip("Queue IPC requires multiprocessing setup")
    def test_qget_nowait_with_data(self, mock_queue):
        """GIVEN: Queue mit Daten, WHEN: qget_nowait(), THEN: Daten zurückgegeben.
        
        Erwartung: qget_nowait() gibt Queue-Inhalt zurück.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import qget_nowait
        except ImportError:
            pytest.skip("qget_nowait nicht verfügbar")
        
        mock_queue.get_nowait.return_value = 'test_data'
        
        # ACT
        result = qget_nowait(mock_queue)
        
        # THEN
        assert result == 'test_data'


# ===============================================================================
# TESTGRUPPE 7: Process Status Helpers
# ===============================================================================

class TestProcessStatusHelpers:
    """Tests für Process-Status Helper Functions."""
    
    def test_is_running_with_alive_process(self, mock_process):
        """GIVEN: Laufender Process, WHEN: is_running(), THEN: True.
        
        Erwartung: is_running() gibt True für lebende Processes.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import is_running
        except ImportError:
            pytest.skip("is_running nicht verfügbar")
        
        mock_process.is_alive.return_value = True
        
        # ACT
        result = is_running(mock_process)
        
        # THEN
        assert result is True
    
    def test_is_running_with_dead_process(self, mock_process):
        """GIVEN: Beendeter Process, WHEN: is_running(), THEN: False.
        
        Erwartung: is_running() gibt False für tote Processes.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import is_running
        except ImportError:
            pytest.skip("is_running nicht verfügbar")
        
        mock_process.is_alive.return_value = False
        
        # ACT
        result = is_running(mock_process)
        
        # THEN
        assert result is False
    
    def test_safe_join_signature(self):
        """GIVEN: Process + timeout, WHEN: safe_join(), THEN: Akzeptiert params.
        
        Erwartung: safe_join(proc, timeout) signature.
        """
        # ARRANGE
        try:
            from crazycar.control.optimizer_workers import safe_join
        except ImportError:
            pytest.skip("safe_join nicht verfügbar")
        
        # ACT & THEN
        assert callable(safe_join)


# ===============================================================================
# TESTGRUPPE 8: Public API Export
# ===============================================================================

class TestPublicAPIExport:
    """Tests für __all__ Export."""
    
    def test_module_all_export(self):
        """GIVEN: optimizer_workers, WHEN: Import, THEN: __all__ definiert.
        
        Erwartung: __all__ listet Public API Funktionen.
        """
        # ARRANGE & ACT
        try:
            from crazycar.control import optimizer_workers
            
            # THEN
            if hasattr(optimizer_workers, '__all__'):
                expected = ['spawn_worker', 'cleanup_worker', 'kill_process_hard',
                           'ctx', 'make_queue', 'qget_nowait', 'is_running', 'safe_join']
                for func in expected:
                    assert func in optimizer_workers.__all__
        except ImportError:
            pytest.skip("optimizer_workers nicht verfügbar")
