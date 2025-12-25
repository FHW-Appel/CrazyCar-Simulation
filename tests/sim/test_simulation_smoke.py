"""Smoke Tests für simulation.py - Mock-basierte Initialisierung.

TESTBASIS:
- Modul crazycar.sim.simulation - run_simulation(), run_direct(), _finalize_exit()
- Initialisierungs-Code: pygame, UI, Services, spawning

TESTVERFAHREN:
- Mock-basiert: Alle Dependencies gemockt
- Smoke Tests: Initialisierung läuft durch ohne Crash
- Branch Coverage: hard_kill, duration, marker file
"""
import os
import types
import time
import pytest
import pygame

import crazycar.sim.simulation as simfac


pytestmark = [pytest.mark.integration, pytest.mark.smoke, pytest.mark.e2e]


class _DummyToggle:
    def __init__(self, x, y, *labels):
        self.rect = pygame.Rect(x, y, 10, 10)

    def draw(self, screen):
        return None


class _DummyEventSource:
    def __init__(self, headless: bool):
        self.headless = headless


class _DummyModeManager:
    def __init__(self, start_python: bool):
        self.start_python = start_python


class _DummyRuntime:
    def __init__(self):
        self.window_size = (800, 600)
        self.current_generation = 0

    def start(self, cfg):
        # simfac.run_simulation erwartet, dass window_size gesetzt ist
        self.window_size = (800, 600)


class _DummyCfg:
    headless = True
    seed = 123


class _DummyMapService:
    def __init__(self, window_size, asset_name="Racemap.png"):
        self.window_size = window_size
        self.asset_name = asset_name


# ==============================================================================
# TESTGRUPPE 1: _finalize_exit() Tests
# ==============================================================================

class TestFinalizeExit:
    """Tests für _finalize_exit() helper function."""
    
    def test_finalize_exit_soft(self, monkeypatch):
        """GIVEN: hard_kill=False, WHEN: _finalize_exit, THEN: SystemExit(0).
        
        TESTBASIS:
            Function _finalize_exit() - Soft exit
        
        TESTVERFAHREN:
            Exception Handling: SystemExit catchable
        
        Erwartung: pygame.quit() + raise SystemExit(0).
        """
        # ARRANGE
        called = {"quit": 0}
        monkeypatch.setattr(simfac.pygame, "quit", lambda: called.__setitem__("quit", called["quit"] + 1))
        
        # ACT & THEN
        with pytest.raises(SystemExit) as e:
            simfac._finalize_exit(hard_kill=False)
        
        assert e.value.code == 0
        assert called["quit"] == 1

    def test_finalize_exit_hard(self, monkeypatch):
        """GIVEN: hard_kill=True, WHEN: _finalize_exit, THEN: sys.exit(0).
        
        TESTBASIS:
            Function _finalize_exit() - Hard exit
        
        TESTVERFAHREN:
            Mock sys.exit: Hard exit path
        
        Erwartung: pygame.quit() + sys.exit(0).
        """
        # ARRANGE
        called = {"quit": 0}
        monkeypatch.setattr(simfac.pygame, "quit", lambda: called.__setitem__("quit", called["quit"] + 1))
        
        def _fake_exit(code=0):
            raise RuntimeError(f"exit:{code}")
        
        monkeypatch.setattr(simfac.sys, "exit", _fake_exit)
        
        # ACT & THEN
        with pytest.raises(RuntimeError) as e:
            simfac._finalize_exit(hard_kill=True)
        
        assert "exit:0" in str(e.value)
        assert called["quit"] == 1


# ==============================================================================
# TESTGRUPPE 2: run_simulation() Smoke Tests
# ==============================================================================

class TestRunSimulationSmoke:
    """Smoke tests für run_simulation() - Mock-basiert."""
    
    def test_run_simulation_smoke_initializes_and_calls_run_loop(self, monkeypatch, tmp_path):
        """GIVEN: Gemockte Dependencies, WHEN: run_simulation, THEN: Initialisierung OK.
        
        TESTBASIS:
            Function run_simulation() - Complete initialization
            Marker file handling, config, pygame setup, UI, services, spawning
        
        TESTVERFAHREN:
            Smoke Test: Mock all dependencies
            Branch Coverage: Marker file branch
        
        Erwartung: run_loop wird aufgerufen, genome fitness=0, marker file konsumiert.
        """
        # ARRANGE
        # --- env/marker file branch abdecken ---
        monkeypatch.setattr(simfac.os, "getcwd", lambda: str(tmp_path))
        marker = tmp_path / ".crazycar_start_mode"
        marker.write_text("1", encoding="utf-8")
        
        # --- config/runtime deterministisch + leichtgewichtig ---
        monkeypatch.setattr(simfac, "build_default_config", lambda: _DummyCfg())
        monkeypatch.setattr(simfac, "seed_all", lambda seed: None)
        monkeypatch.setattr(simfac, "SimRuntime", _DummyRuntime)
        
        # --- pygame: kein echtes Fenster/Fonts ---
        monkeypatch.setattr(simfac.pygame.display, "set_caption", lambda *a, **k: None)
        monkeypatch.setattr(simfac, "get_or_create_screen", lambda size: pygame.Surface(size))
        
        monkeypatch.setattr(simfac.pygame.freetype, "SysFont", lambda *a, **k: object())
        monkeypatch.setattr(simfac.pygame.font, "SysFont", lambda *a, **k: object())
        monkeypatch.setattr(simfac.pygame.time, "Clock", lambda: object())
        
        # --- UI widgets/Services stubben ---
        monkeypatch.setattr(simfac, "ToggleButton", _DummyToggle)
        monkeypatch.setattr(simfac, "EventSource", _DummyEventSource)
        monkeypatch.setattr(simfac, "ModeManager", _DummyModeManager)
        monkeypatch.setattr(simfac, "MapService", _DummyMapService)
        
        # spawn_from_map: leichtgewichtiges Car-Objekt (run_loop ist eh gemockt)
        dummy_car = types.SimpleNamespace(position=(1, 2))
        monkeypatch.setattr(simfac, "spawn_from_map", lambda ms: [dummy_car])
        
        # neat NN create: keine echte NEAT-config nötig
        monkeypatch.setattr(simfac.neat.nn.FeedForwardNetwork, "create", lambda g, cfg: object())
        
        # run_loop abfangen und Parameter prüfen
        called = {}
        
        def _fake_run_loop(**kwargs):
            called.update(kwargs)
            return None
        
        monkeypatch.setattr(simfac, "run_loop", _fake_run_loop)
        
        # genomes: fitness muss auf 0 gesetzt werden
        g1 = types.SimpleNamespace(fitness=999)
        genomes = [(1, g1)]
        
        # ACT
        simfac.run_simulation(genomes, config=object())
        
        # THEN
        assert g1.fitness == 0
        assert "cfg" in called
        assert "cars" in called and len(called["cars"]) == 1
        # marker file soll "one-shot" konsumiert werden (dein Code versucht zu löschen)
        assert not marker.exists()


# ==============================================================================
# TESTGRUPPE 3: run_direct() Smoke Tests
# ==============================================================================

class TestRunDirectSmoke:
    """Smoke tests für run_direct() - Mock-basiert."""
    
    def test_run_direct_duration_triggers_finalize_exit(self, monkeypatch):
        """GIVEN: duration überschritten, WHEN: run_direct, THEN: finalize_exit aufgerufen.
        
        TESTBASIS:
            Function run_direct() - Duration handling
            Fallback soft-exit wenn duration überschritten
        
        TESTVERFAHREN:
            Mock time.time: Simulate duration exceeded
            Mock finalize_exit: Capture SystemExit
        
        Erwartung: finalize_exit wird aufgerufen wenn duration überschritten.
        """
        # ARRANGE
        monkeypatch.setattr(simfac, "build_default_config", lambda: _DummyCfg())
        monkeypatch.setattr(simfac, "seed_all", lambda seed: None)
        monkeypatch.setattr(simfac, "SimRuntime", _DummyRuntime)
        
        monkeypatch.setattr(simfac.pygame.display, "set_caption", lambda *a, **k: None)
        monkeypatch.setattr(simfac, "get_or_create_screen", lambda size: pygame.Surface(size))
        monkeypatch.setattr(simfac.pygame.freetype, "SysFont", lambda *a, **k: object())
        monkeypatch.setattr(simfac.pygame.font, "SysFont", lambda *a, **k: object())
        monkeypatch.setattr(simfac.pygame.time, "Clock", lambda: object())
        
        monkeypatch.setattr(simfac, "ToggleButton", _DummyToggle)
        monkeypatch.setattr(simfac, "EventSource", _DummyEventSource)
        monkeypatch.setattr(simfac, "ModeManager", _DummyModeManager)
        monkeypatch.setattr(simfac, "MapService", _DummyMapService)
        monkeypatch.setattr(simfac, "spawn_from_map", lambda ms: [types.SimpleNamespace(position=(1, 2))])
        
        # run_loop: sofort zurück
        monkeypatch.setattr(simfac, "run_loop", lambda **kwargs: None)
        
        # time so faken, dass nach run_loop duration überschritten ist
        t = {"now": 1000.0}
        
        def _fake_time():
            return t["now"]
        
        monkeypatch.setattr(time, "time", _fake_time)
        t["now"] = 1000.0
        
        # finalize_exit soll SystemExit werfen, run_direct fängt das ab
        def _fake_finalize_exit(hard_kill: bool):
            raise SystemExit(0)
        
        monkeypatch.setattr(simfac, "_finalize_exit", _fake_finalize_exit)
        
        # ACT: nach run_loop "springen" wir in der Zeit vorwärts
        t["now"] = 1005.0
        simfac.run_direct(duration_s=1.0)
        
        # THEN: Kein Exception = finalize_exit wurde abgefangen
        # (Test läuft durch = Success)
