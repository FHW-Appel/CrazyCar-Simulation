"""Tests für optimizer_adapter - High Coverage ohne pygame/NEAT Runtime.

TESTBASIS:
    src/crazycar/control/optimizer_adapter.py
    
TESTVERFAHREN:
    Mock-basierte Tests mit hoher Branch Coverage:
    - _find_direct_entry(): required-params skip + duration kwargs + signature-fail
    - _run_direct_simulation(): kwargs-call + runtime-Messung
    - run_neat_simulation(): NEAT-Branch mit DLL-only=False, pop_size-Override-except
    - run_neat_entry() + _queue_close_safe(): ok/aborted/error + exception-suppression
    
ZIEL:
    Coverage von ~32% auf >70-90% erhöhen ohne echtes pygame/NEAT zu starten.
"""
import sys
import types
import pytest

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: _find_direct_entry - Entry Point Discovery
# ===============================================================================

def test_find_direct_entry_prefers_optional_duration_s(monkeypatch):
    """Unit Test: _find_direct_entry bevorzugt Funktionen mit optionalem duration_s Parameter.
    
    Test Objective:
        Verify _find_direct_entry() prefers functions with optional parameters
        over functions requiring positional arguments (like NEAT genomes, config).
    
    Pre-Conditions:
        - Mocked _CANDIDATE_MODULES with 2 modules
        - m1.run_loop requires (genomes, config) → should be skipped
        - m2.run_direct has optional (duration_s=None) → should be selected
    
    Test Steps:
        1. Mock two modules with different function signatures
        2. Mock _CANDIDATE_MODULES to list both
        3. Call _find_direct_entry()
        4. Assert: returns (run_direct, {"duration_s": None})
    
    Expected Results:
        - Function with optional params is selected
        - kwargs dict contains duration_s=None
    
    ISTQB Coverage:
        - Branch Coverage: Optional params path
        - Decision Coverage: Required params → skip branch
    """
    import crazycar.control.optimizer_adapter as oa

    def neat_like(genomes, config):  # muss übersprungen werden (required params)
        return None

    def direct(duration_s=None):  # soll genommen werden
        return duration_s

    mod1 = types.SimpleNamespace(run_loop=neat_like)
    mod2 = types.SimpleNamespace(run_direct=direct)

    monkeypatch.setattr(
        oa,
        "_CANDIDATE_MODULES",
        [("m1", ["run_loop"]), ("m2", ["run_direct"])],
    )

    def fake_import(name):
        if name == "m1":
            return mod1
        if name == "m2":
            return mod2
        raise ImportError(name)

    monkeypatch.setattr(oa, "import_module", fake_import)

    fn, kwargs = oa._find_direct_entry()
    assert fn is direct
    assert kwargs == {"duration_s": None}


def test_find_direct_entry_signature_inspection_fails_returns_blind(monkeypatch):
    """Unit Test: _find_direct_entry bei signature() Fehler → (fn, None) zurück.
    
    Test Objective:
        Verify _find_direct_entry() returns function with kwargs=None
        when inspect.signature() raises exception.
    
    Pre-Conditions:
        - Module with entry function exists
        - inspect.signature() mocked to raise ValueError
    
    Test Steps:
        1. Mock module with entry function
        2. Mock inspect.signature to raise ValueError
        3. Call _find_direct_entry()
        4. Assert: returns (entry, None)
    
    Expected Results:
        - Function is returned
        - kwargs is None (blind call without params)
    
    ISTQB Coverage:
        - Exception Handling: signature inspection failure
        - Fallback path: blind function call
    """
    import crazycar.control.optimizer_adapter as oa

    def entry():
        return None

    mod = types.SimpleNamespace(main=entry)
    monkeypatch.setattr(oa, "_CANDIDATE_MODULES", [("m", ["main"])])
    monkeypatch.setattr(oa, "import_module", lambda name: mod)

    # signature() soll crashen -> dann muss (fn, None) zurückkommen
    monkeypatch.setattr(oa.inspect, "signature", lambda _: (_ for _ in ()).throw(ValueError("no sig")))

    fn, kwargs = oa._find_direct_entry()
    assert fn is entry
    assert kwargs is None


# ===============================================================================
# TESTGRUPPE 2: _run_direct_simulation - Direct Execution with Runtime Measurement
# ===============================================================================

def test_run_direct_simulation_calls_entry_with_kwargs_and_measures(monkeypatch):
    """Unit Test: _run_direct_simulation ruft Entry mit kwargs auf und misst Zeit.
    
    Test Objective:
        Verify _run_direct_simulation() calls entry function with kwargs
        and measures runtime.
    
    Pre-Conditions:
        - _find_direct_entry() mocked to return (entry, {"duration_s": None})
        - time.time() mocked to return deterministic values
    
    Test Steps:
        1. Mock entry function to track calls
        2. Mock _find_direct_entry() to return (entry, kwargs)
        3. Mock time.time() to return [100.0, 100.25]
        4. Call _run_direct_simulation()
        5. Assert: entry called with kwargs
        6. Assert: runtime == 0.25s
    
    Expected Results:
        - Entry function called exactly once
        - kwargs passed correctly
        - Runtime measured as 0.25s
    
    ISTQB Coverage:
        - Statement Coverage: kwargs call path
        - Measurement: Runtime calculation
    """
    import crazycar.control.optimizer_adapter as oa

    called = {"n": 0, "kwargs": None}

    def entry(**kwargs):
        called["n"] += 1
        called["kwargs"] = kwargs

    monkeypatch.setattr(oa, "_find_direct_entry", lambda: (entry, {"duration_s": None}))

    times = iter([100.0, 100.25])
    monkeypatch.setattr(oa.time, "time", lambda: next(times))

    rt = oa._run_direct_simulation()
    assert called["n"] == 1
    assert called["kwargs"] == {"duration_s": None}
    assert rt == pytest.approx(0.25, rel=1e-12)


# ===============================================================================
# TESTGRUPPE 3: run_neat_simulation - NEAT Branch Coverage (ohne echtes pygame)
# ===============================================================================

def test_run_neat_simulation_neat_branch_is_executed(monkeypatch, tmp_path):
    """Unit Test: run_neat_simulation NEAT-Branch wird ausgeführt (DLL-only=False).
    
    Test Objective:
        Verify run_neat_simulation() executes NEAT branch when DLL-only is False.
        Tests NEAT config loading, population setup, pop_size override exception,
        and logging without starting real pygame/NEAT.
    
    Pre-Conditions:
        - DLL-only mode is False
        - Config files in tmp_path
        - NEAT modules mocked (neat.config, neat.population, etc.)
        - Simulation module mocked (no pygame import)
    
    Test Steps:
        1. Set _dll_only_mode() to return False
        2. Create fake config_neat.txt in tmp_path
        3. Mock all NEAT submodules (config, genome, population, etc.)
        4. Mock crazycar.sim.simulation.run_simulation
        5. Mock time.time() for deterministic runtime
        6. Call run_neat_simulation(pop_size=7)
        7. Assert: runtime measured
        8. Assert: Population.run() called
        9. Assert: log.csv written
        10. Assert: pop_size override exception caught (AttributeError)
    
    Expected Results:
        - NEAT Config loaded from tmp_path
        - Population created and run() called once
        - log.csv contains output
        - pop_size override AttributeError suppressed
        - Runtime measured as 0.5s
    
    ISTQB Coverage:
        - Branch Coverage: DLL-only=False → NEAT path
        - Exception Handling: pop_size override AttributeError
        - Integration: NEAT config + population + logging
    """
    import crazycar.control.optimizer_adapter as oa

    # DLL-only AUS, sonst kommst du nie in den NEAT-Teil
    monkeypatch.setattr(oa, "_dll_only_mode", lambda: False)

    # Pfade auf tmp umbiegen (kein Repo-FS nötig)
    cfg = tmp_path / "config_neat.txt"
    cfg.write_text("dummy", encoding="utf-8")
    logf = tmp_path / "log.csv"
    monkeypatch.setattr(oa, "neat_config_path", lambda: str(cfg))
    monkeypatch.setattr(oa, "log_path", lambda: str(logf))

    # fake simulation evaluator (verhindert pygame-import)
    sim_mod = types.ModuleType("crazycar.sim.simulation")
    def run_simulation(genomes, config):
        return None
    sim_mod.run_simulation = run_simulation
    monkeypatch.setitem(sys.modules, "crazycar.sim.simulation", sim_mod)

    # --- Fake NEAT Package/Submodules, damit Imports im Adapter klappen ---
    neat_pkg = types.ModuleType("neat")
    monkeypatch.setitem(sys.modules, "neat", neat_pkg)

    neat_config = types.ModuleType("neat.config")
    neat_genome = types.ModuleType("neat.genome")
    neat_repro = types.ModuleType("neat.reproduction")
    neat_species = types.ModuleType("neat.species")
    neat_stag = types.ModuleType("neat.stagnation")
    neat_pop = types.ModuleType("neat.population")
    neat_reporting = types.ModuleType("neat.reporting")
    neat_stats = types.ModuleType("neat.statistics")

    # Dummy config: pop_size setzbar, aber beim Override soll er einmal in except laufen
    class DummyConfig:
        def __init__(self, *a, **k):
            self.pop_size = 2
        def __setattr__(self, name, value):
            # initial setzen erlauben, späteres Override pop_size einmal crashen lassen
            if name == "pop_size" and hasattr(self, "pop_size"):
                raise AttributeError("locked")
            object.__setattr__(self, name, value)

    neat_config.Config = DummyConfig
    neat_genome.DefaultGenome = object
    neat_repro.DefaultReproduction = object
    neat_species.DefaultSpeciesSet = object
    neat_stag.DefaultStagnation = object

    class DummyPop:
        last = None
        def __init__(self, config):
            self.config = config
            self.reporters = []
            self.run_called = 0
            DummyPop.last = self
        def add_reporter(self, r):
            self.reporters.append(r)
        def run(self, evaluator, n):
            self.run_called += 1

    neat_pop.Population = DummyPop
    neat_reporting.StdOutReporter = lambda *a, **k: object()
    neat_stats.StatisticsReporter = lambda *a, **k: object()

    monkeypatch.setitem(sys.modules, "neat.config", neat_config)
    monkeypatch.setitem(sys.modules, "neat.genome", neat_genome)
    monkeypatch.setitem(sys.modules, "neat.reproduction", neat_repro)
    monkeypatch.setitem(sys.modules, "neat.species", neat_species)
    monkeypatch.setitem(sys.modules, "neat.stagnation", neat_stag)
    monkeypatch.setitem(sys.modules, "neat.population", neat_pop)
    monkeypatch.setitem(sys.modules, "neat.reporting", neat_reporting)
    monkeypatch.setitem(sys.modules, "neat.statistics", neat_stats)

    # Zeit deterministisch machen
    times = iter([10.0, 10.5])
    monkeypatch.setattr(oa.time, "time", lambda: next(times))

    rt = oa.run_neat_simulation(1, 2, 3, 4, 5, pop_size=7)

    assert rt == pytest.approx(0.5, rel=1e-12)
    assert DummyPop.last is not None
    assert DummyPop.last.run_called == 1
    assert logf.read_text(encoding="utf-8") != ""


# ===============================================================================
# TESTGRUPPE 4: run_neat_entry + _queue_close_safe - Error Handling & Queue
# ===============================================================================

def test_run_neat_entry_ok_aborted_error_and_queue_close(monkeypatch):
    """Unit Test: run_neat_entry testet ok/aborted/error + _queue_close_safe exception suppression.
    
    Test Objective:
        Verify run_neat_entry() handles all status paths (ok, aborted, error)
        and _queue_close_safe() suppresses exceptions from queue.close() and join_thread().
    
    Pre-Conditions:
        - Mock Queue with items list to track put() calls
        - Mock Queue.close() and join_thread() to raise exceptions
        - time.sleep() mocked to not block
    
    Test Steps:
        1. Test OK path:
           - Mock run_neat_simulation to return 0.42
           - Call run_neat_entry()
           - Assert: status="ok", runtime in queue item
        
        2. Test ABORTED path:
           - Mock run_neat_simulation to raise SystemExit
           - Call run_neat_entry()
           - Assert: status="aborted" in queue item
        
        3. Test ERROR path:
           - Mock run_neat_simulation to raise RuntimeError("boom")
           - Call run_neat_entry()
           - Assert: status="error", "boom" in error field
        
        4. Test _queue_close_safe exception suppression:
           - Queue.close() raises RuntimeError("close fail")
           - Queue.join_thread() raises RuntimeError("join fail")
           - Assert: exceptions suppressed, no crash
    
    Expected Results:
        - OK: status="ok", runtime present
        - ABORTED: status="aborted" on SystemExit
        - ERROR: status="error", error message contains "boom"
        - Queue close/join exceptions suppressed
    
    ISTQB Coverage:
        - Branch Coverage: All 3 status paths (ok, aborted, error)
        - Exception Handling: _queue_close_safe suppression
        - Error Guessing: Queue cleanup failures
    """
    import crazycar.control.optimizer_adapter as oa

    class Q:
        def __init__(self):
            self.items = []
            self.closed = 0
            self.joined = 0
        def put(self, x):
            self.items.append(x)
        def close(self):
            self.closed += 1
            raise RuntimeError("close fail")  # _queue_close_safe muss das schlucken
        def join_thread(self):
            self.joined += 1
            raise RuntimeError("join fail")

    monkeypatch.setattr(oa.time, "sleep", lambda _: None)

    # OK
    q = Q()
    monkeypatch.setattr(oa, "run_neat_simulation", lambda *a, **k: 0.42)
    oa.run_neat_entry(q, 1, 2, 3, 4, 5, pop_size=2)
    assert q.items[-1]["status"] == "ok"
    assert "runtime" in q.items[-1]

    # ABORTED
    q = Q()
    def raise_exit(*a, **k):
        raise SystemExit()
    monkeypatch.setattr(oa, "run_neat_simulation", raise_exit)
    oa.run_neat_entry(q, 1, 2, 3, 4, 5, pop_size=2)
    assert q.items[-1]["status"] == "aborted"

    # ERROR
    q = Q()
    def raise_err(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(oa, "run_neat_simulation", raise_err)
    oa.run_neat_entry(q, 1, 2, 3, 4, 5, pop_size=2)
    assert q.items[-1]["status"] == "error"
    assert "boom" in q.items[-1]["error"]
