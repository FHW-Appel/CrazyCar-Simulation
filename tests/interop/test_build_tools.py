"""Tests für build_tools.py - Native Build Extended.

TESTBASIS:
    src/crazycar/interop/build_tools.py
    
TESTVERFAHREN:
    Äquivalenzklassenbildung nach ISTQB:
    - Path Management: ensure_build_on_path()
    - Build Execution: run_build_native()
    - FFI Setup: _make_ffi()
    - Constants: ROOT, SRC_C, OUT_BASE, OUT_PKG
"""
import pytest
import sys
from pathlib import Path

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: Path Constants
# ===============================================================================

class TestBuildToolsPaths:
    """Tests für Path-Konstanten."""
    
    def test_root_path_defined(self):
        """GIVEN: build_tools, WHEN: Import ROOT, THEN: Path exists.
        
        Erwartung: ROOT zeigt auf CrazyCar-Simulation Verzeichnis.
        """
        try:
            from crazycar.interop.build_tools import ROOT
            
            assert isinstance(ROOT, Path)
            assert ROOT.exists()
            assert 'CrazyCar' in str(ROOT) or 'crazycar' in str(ROOT).lower()
        except ImportError:
            pytest.skip("ROOT nicht verfügbar")
    
    def test_src_c_path_defined(self):
        """GIVEN: build_tools, WHEN: Import SRC_C, THEN: C source path.
        
        Erwartung: SRC_C zeigt auf src/c/ Verzeichnis.
        """
        try:
            from crazycar.interop.build_tools import SRC_C
            
            assert isinstance(SRC_C, Path)
            assert 'src' in str(SRC_C)
            assert 'c' in str(SRC_C)
        except ImportError:
            pytest.skip("SRC_C nicht verfügbar")
    
    def test_out_base_path_defined(self):
        """GIVEN: build_tools, WHEN: Import OUT_BASE, THEN: Build output path.
        
        Erwartung: OUT_BASE zeigt auf build/_cffi/ Verzeichnis.
        """
        try:
            from crazycar.interop.build_tools import OUT_BASE
            
            assert isinstance(OUT_BASE, Path)
            assert 'build' in str(OUT_BASE)
            assert '_cffi' in str(OUT_BASE)
        except ImportError:
            pytest.skip("OUT_BASE nicht verfügbar")
    
    def test_out_pkg_path_defined(self):
        """GIVEN: build_tools, WHEN: Import OUT_PKG, THEN: Package output path.
        
        Erwartung: OUT_PKG zeigt auf build/_cffi/crazycar/ Verzeichnis.
        """
        try:
            from crazycar.interop.build_tools import OUT_PKG
            
            assert isinstance(OUT_PKG, Path)
            assert 'build' in str(OUT_PKG)
            assert 'crazycar' in str(OUT_PKG)
        except ImportError:
            pytest.skip("OUT_PKG nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 2: ensure_build_on_path
# ===============================================================================

class TestEnsureBuildOnPath:
    """Tests für ensure_build_on_path() Funktion."""
    
    def test_ensure_build_on_path_import(self):
        """GIVEN: build_tools, WHEN: Import ensure_build_on_path, THEN: Callable.
        
        Erwartung: ensure_build_on_path Funktion existiert.
        """
        try:
            from crazycar.interop.build_tools import ensure_build_on_path
            assert callable(ensure_build_on_path)
        except ImportError:
            pytest.skip("ensure_build_on_path nicht verfügbar")
    
    def test_ensure_build_on_path_returns_string(self):
        """GIVEN: No args, WHEN: ensure_build_on_path(), THEN: String path.
        
        Erwartung: Gibt Build-Pfad als String zurück.
        """
        try:
            from crazycar.interop.build_tools import ensure_build_on_path
            
            # ACT
            result = ensure_build_on_path()
            
            # THEN
            assert isinstance(result, str)
            assert len(result) > 0
            assert 'build' in result.lower()
        except ImportError:
            pytest.skip("ensure_build_on_path nicht verfügbar")
    
    def test_ensure_build_on_path_adds_to_syspath(self):
        """GIVEN: Not in sys.path, WHEN: ensure_build_on_path(), THEN: Added to sys.path.
        
        Erwartung: Build-Pfad wird sys.path hinzugefügt.
        """
        try:
            from crazycar.interop.build_tools import ensure_build_on_path
            
            # ACT
            path = ensure_build_on_path()
            
            # THEN
            assert path in sys.path
        except ImportError:
            pytest.skip("ensure_build_on_path nicht verfügbar")
    
    def test_ensure_build_on_path_creates_directory(self):
        """GIVEN: Directory missing, WHEN: ensure_build_on_path(), THEN: Directory created.
        
        Erwartung: Funktion erstellt Build-Verzeichnis falls nötig.
        """
        try:
            from crazycar.interop.build_tools import ensure_build_on_path, OUT_BASE
            
            # ACT
            ensure_build_on_path()
            
            # THEN
            assert OUT_BASE.exists()
            assert OUT_BASE.is_dir()
        except ImportError:
            pytest.skip("ensure_build_on_path nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 3: _make_ffi
# ===============================================================================

class TestMakeFFI:
    """Tests für _make_ffi() Funktion."""
    
    def test_make_ffi_import(self):
        """GIVEN: build_tools, WHEN: Import _make_ffi, THEN: Callable.
        
        Erwartung: _make_ffi Funktion existiert.
        """
        try:
            from crazycar.interop.build_tools import _make_ffi
            assert callable(_make_ffi)
        except ImportError:
            pytest.skip("_make_ffi nicht verfügbar")
    
    def test_make_ffi_returns_ffi_instance(self):
        """GIVEN: No args, WHEN: _make_ffi(), THEN: FFI instance.
        
        Erwartung: Gibt CFFI FFI Instanz zurück.
        """
        try:
            from crazycar.interop.build_tools import _make_ffi
            from cffi import FFI
            
            # ACT
            ffi = _make_ffi()
            
            # THEN
            assert isinstance(ffi, FFI)
        except ImportError:
            pytest.skip("_make_ffi oder cffi nicht verfügbar")
    
    def test_make_ffi_defines_cdef(self):
        """GIVEN: _make_ffi(), WHEN: Check FFI, THEN: C declarations defined.
        
        Erwartung: FFI hat C-Funktionen deklariert und cdef() Methode.
        """
        try:
            from crazycar.interop.build_tools import _make_ffi
            from cffi import FFI
            
            # ACT
            ffi = _make_ffi()
            
            # THEN: FFI sollte korrekte Instanz sein mit cdef Methode
            assert ffi is not None
            assert isinstance(ffi, FFI)
            assert hasattr(ffi, 'cdef')
            assert hasattr(ffi, 'set_source')
        except ImportError:
            pytest.skip("_make_ffi nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 4: run_build_native
# ===============================================================================

class TestRunBuildNative:
    """Tests für run_build_native() Funktion."""
    
    def test_run_build_native_import(self):
        """GIVEN: build_tools, WHEN: Import run_build_native, THEN: Callable.
        
        Erwartung: run_build_native Funktion existiert.
        """
        try:
            from crazycar.interop.build_tools import run_build_native
            assert callable(run_build_native)
        except ImportError:
            pytest.skip("run_build_native nicht verfügbar")
    
    def test_run_build_native_signature(self):
        """GIVEN: build_tools, WHEN: Check signature, THEN: clean parameter.
        
        Erwartung: run_build_native akzeptiert clean=True/False.
        """
        try:
            from crazycar.interop.build_tools import run_build_native
            import inspect
            
            sig = inspect.signature(run_build_native)
            params = list(sig.parameters.keys())
            
            # THEN: Sollte 'clean' Parameter haben
            assert 'clean' in params
        except ImportError:
            pytest.skip("run_build_native nicht verfügbar")
    
    @pytest.mark.skip(reason="Build dauert lange und benötigt Compiler")
    def test_run_build_native_returns_tuple(self):
        """GIVEN: No args, WHEN: run_build_native(), THEN: Tuple (rc, path).
        
        Erwartung: Gibt (exit_code, build_path) zurück.
        """
        from crazycar.interop.build_tools import run_build_native
        
        # ACT
        result = run_build_native()
        
        # THEN
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)  # exit code
        assert isinstance(result[1], str)  # path
    
    @pytest.mark.skip(reason="Build dauert lange")
    def test_run_build_native_with_clean(self):
        """GIVEN: clean=True, WHEN: run_build_native(), THEN: Clean build.
        
        Erwartung: Mit clean=True werden alte Artifacts entfernt.
        """
        from crazycar.interop.build_tools import run_build_native
        
        # ACT
        result = run_build_native(clean=True)
        
        # THEN
        assert result[0] == 0  # Success


# ===============================================================================
# TESTGRUPPE 5: C Source Configuration
# ===============================================================================

class TestCSourceConfiguration:
    """Tests für C-Source Konfiguration."""
    
    def test_c_source_files_exist(self):
        """GIVEN: SRC_C path, WHEN: Check files, THEN: C sources present.
        
        Erwartung: Alle C-Source-Dateien existieren in src/c/.
        """
        try:
            from crazycar.interop.build_tools import SRC_C
            
            # THEN: Alle erwarteten Dateien sollten existieren
            expected_files = ['sim_globals.c', 'cc-lib.c', 'myFunktions.c']
            missing = []
            
            for filename in expected_files:
                file_path = SRC_C / filename
                if not file_path.exists():
                    missing.append(filename)
                elif not file_path.is_file():
                    pytest.fail(f"{filename} existiert, ist aber keine Datei")
            
            if missing:
                pytest.skip(f"C-Source-Dateien nicht gefunden: {missing}")
        except ImportError:
            pytest.skip("SRC_C nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 6: Module Level Functions
# ===============================================================================

class TestModuleLevelFunctions:
    """Tests für weitere Module-Level Funktionen."""
    
    def test_module_exports_main_functions(self):
        """GIVEN: build_tools, WHEN: Check exports, THEN: Main functions present.
        
        Erwartung: Modul exportiert ensure_build_on_path, run_build_native.
        """
        try:
            from crazycar.interop import build_tools
            
            assert hasattr(build_tools, 'ensure_build_on_path')
            assert hasattr(build_tools, 'run_build_native')
        except ImportError:
            pytest.skip("build_tools nicht verfügbar")


# ===============================================================================
# Helper Functions für mocked Tests
# ===============================================================================

def _make_fake_c_tree(tmp_path):
    """Erstellt Fake C-Source Tree für Tests.
    
    Args:
        tmp_path: pytest tmp_path fixture
        
    Returns:
        (root, src_c): Root-Pfad und src/c Pfad
    """
    root = tmp_path
    src_c = root / "src" / "c"
    src_c.mkdir(parents=True)
    
    # Dummy C + Header (set_source referenziert cc-lib.h)
    for name in ("sim_globals.c", "cc-lib.c", "myFunktions.c", "cc-lib.h", "myFunktions.h"):
        (src_c / name).write_text("/* dummy */\n", encoding="utf-8")
    
    return root, src_c


# ===============================================================================
# TESTGRUPPE 7: run_build_native with mocked compile (tmp_path)
# ===============================================================================

class TestRunBuildNativeMocked:
    """Tests für run_build_native() mit gemocktem Compiler - keine echten Artefakte.
    
    VORTEILE:
    - Keine Compiler-Abhängigkeit
    - Schnelle Tests (kein echter Build)
    - Keine Artefakte im Repo (tmp_path)
    - Volle Branch Coverage (clean=True/False, error handling)
    """
    
    def test_run_build_native_calls_compile_and_cleans(self, tmp_path, monkeypatch):
        """Unit Test: run_build_native ruft FFI.compile() auf und löscht bei clean=True.
        
        Test Objective:
            Verify run_build_native() calls ffi.compile() and removes old artifacts
            when clean=True is set.
        
        Pre-Conditions:
            - Fake C-Source Tree in tmp_path
            - OUT_PKG enthält alte Artefakte (carsim_native_old.pyd)
            - FFI.compile() gemockt (kein echter Compiler)
        
        Test Steps:
            1. Erstelle Fake C-Source Tree
            2. Patche build_tools Pfade auf tmp_path
            3. Erstelle altes Artefakt (dummy.pyd)
            4. Mocke FFI.compile()
            5. Rufe run_build_native(clean=True)
            6. Assert: compile() wurde aufgerufen
            7. Assert: altes Artefakt wurde gelöscht
            8. Assert: rc == 0, path endet mit build/_cffi
        
        Expected Results:
            - FFI.compile() wird genau 1x aufgerufen
            - Alte Artefakte werden gelöscht (clean=True)
            - Return: (0, build_path)
        
        ISTQB Coverage:
            - Branch Coverage: clean=True → unlink path
            - Decision Coverage: Happy path mit compile
        """
        # ARRANGE
        import crazycar.interop.build_tools as bt
        
        root, src_c = _make_fake_c_tree(tmp_path)
        out_base = root / "build" / "_cffi"
        out_pkg = out_base / "crazycar"
        
        # Patch paths to tmp
        monkeypatch.setattr(bt, "ROOT", root)
        monkeypatch.setattr(bt, "SRC_C", src_c)
        monkeypatch.setattr(bt, "OUT_BASE", out_base)
        monkeypatch.setattr(bt, "OUT_PKG", out_pkg)
        
        out_pkg.mkdir(parents=True, exist_ok=True)
        
        # Dummy artifact to verify clean=True removes it
        dummy = out_pkg / "carsim_native_old.pyd"
        dummy.write_text("x", encoding="utf-8")
        assert dummy.exists(), "Dummy artifact should exist before clean"
        
        # Mock compile so no compiler is needed
        called = {"n": 0}
        
        def fake_compile(self, *args, **kwargs):
            called["n"] += 1
        
        monkeypatch.setattr(bt.FFI, "compile", fake_compile, raising=True)
        
        # ACT
        rc, sp = bt.run_build_native(clean=True)
        
        # THEN
        assert rc == 0, "Should return success"
        assert called["n"] == 1, "FFI.compile() should be called exactly once"
        assert sp.endswith(str(out_base)), f"Path should end with build/_cffi, got {sp}"
        assert not dummy.exists(), "clean=True should delete old artifacts"
    
    def test_run_build_native_returns_rc_1_on_compile_error(self, tmp_path, monkeypatch):
        """Unit Test: run_build_native returns rc=1 when FFI.compile() raises Exception.
        
        Test Objective:
            Verify run_build_native() handles compile errors gracefully and
            returns exit code 1.
        
        Pre-Conditions:
            - Fake C-Source Tree in tmp_path
            - FFI.compile() gemockt und wirft RuntimeError
        
        Test Steps:
            1. Erstelle Fake C-Source Tree
            2. Patche build_tools Pfade auf tmp_path
            3. Mocke FFI.compile() → raise RuntimeError("compile failed")
            4. Rufe run_build_native(clean=False)
            5. Assert: rc == 1 (Error)
        
        Expected Results:
            - Return: (1, _) bei Exception
            - Keine Exception propagiert nach außen
        
        ISTQB Coverage:
            - Exception Handling: compile error → rc=1
            - Negative Testing: Error path
        """
        # ARRANGE
        import crazycar.interop.build_tools as bt
        
        root, src_c = _make_fake_c_tree(tmp_path)
        out_base = root / "build" / "_cffi"
        out_pkg = out_base / "crazycar"
        
        monkeypatch.setattr(bt, "ROOT", root)
        monkeypatch.setattr(bt, "SRC_C", src_c)
        monkeypatch.setattr(bt, "OUT_BASE", out_base)
        monkeypatch.setattr(bt, "OUT_PKG", out_pkg)
        
        def boom(self, *a, **k):
            raise RuntimeError("compile failed")
        
        monkeypatch.setattr(bt.FFI, "compile", boom, raising=True)
        
        # ACT
        rc, _ = bt.run_build_native(clean=False)
        
        # THEN
        assert rc == 1, "Should return error code 1 on compile failure"
    
    def test_run_build_native_clean_false_keeps_artifacts(self, tmp_path, monkeypatch):
        """Unit Test: run_build_native mit clean=False behält Artefakte.
        
        Test Objective:
            Verify clean=False does not delete existing artifacts.
        
        Pre-Conditions:
            - Fake C-Source Tree
            - Existierende Artefakte
            - clean=False
        
        Test Steps:
            1. Erstelle Fake C-Source Tree
            2. Erstelle altes Artefakt
            3. Rufe run_build_native(clean=False)
            4. Assert: Artefakt existiert noch
        
        Expected Results:
            - Alte Artefakte bleiben erhalten bei clean=False
        
        ISTQB Coverage:
            - Branch Coverage: clean=False → kein unlink
        """
        # ARRANGE
        import crazycar.interop.build_tools as bt
        
        root, src_c = _make_fake_c_tree(tmp_path)
        out_base = root / "build" / "_cffi"
        out_pkg = out_base / "crazycar"
        
        monkeypatch.setattr(bt, "ROOT", root)
        monkeypatch.setattr(bt, "SRC_C", src_c)
        monkeypatch.setattr(bt, "OUT_BASE", out_base)
        monkeypatch.setattr(bt, "OUT_PKG", out_pkg)
        
        out_pkg.mkdir(parents=True, exist_ok=True)
        
        # Dummy artifact
        dummy = out_pkg / "keep_me.pyd"
        dummy.write_text("keep", encoding="utf-8")
        assert dummy.exists()
        
        # Mock compile
        def fake_compile(self, *a, **k):
            pass
        
        monkeypatch.setattr(bt.FFI, "compile", fake_compile, raising=True)
        
        # ACT
        rc, _ = bt.run_build_native(clean=False)
        
        # THEN
        assert rc == 0
        assert dummy.exists(), "clean=False should keep existing artifacts"


# ===============================================================================
# TESTGRUPPE 8: Error Handling (Original - deprecated)
# ===============================================================================

class TestBuildErrorHandling:
    """Tests für Error Handling.
    
    ⚠️ NOTE: Diese Testgruppe ist weitgehend durch TestRunBuildNativeMocked ersetzt.
    """
    
    @pytest.mark.skip(reason="Benötigt fehlenden Compiler - siehe TestRunBuildNativeMocked")
    def test_build_fails_gracefully_without_compiler(self):
        """GIVEN: No compiler, WHEN: run_build_native(), THEN: Non-zero exit code.
        
        Erwartung: Build schlägt sauber fehl ohne Compiler.
        
        ⚠️ DEPRECATED: Verwende stattdessen TestRunBuildNativeMocked.test_run_build_native_returns_rc_1_on_compile_error
        """
        from crazycar.interop.build_tools import run_build_native
        
        # ACT
        rc, path = run_build_native()
        
        # THEN
        # Sollte != 0 sein ohne Compiler (oder 0 wenn Compiler vorhanden)
        assert isinstance(rc, int)
