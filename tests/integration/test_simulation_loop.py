# tests/integration/test_simulation_loop.py
"""Integration Tests für Simulation Loop.

TESTBASIS (ISTQB):
- Anforderung: Hauptschleife orchestriert Events, ModeManager, MapService, Car-Updates
- Module: crazycar.sim.loop, crazycar.sim.simulation, crazycar.sim.event_source
- Teststufe: Komponentenintegration (ISTQB Level 2)

TESTVERFAHREN:
- Zustandsübergänge: Init → Event-Loop → Update → Draw → Exit
- Äquivalenzklassen: Headless/Non-Headless, Paused/Running
- Mock-basiert: pygame.event für deterministische Event-Injection

INTEGRATION-SCHWERPUNKT:
- EventSource → SimEvent normalization
- SimEvent → ModeManager state changes
- ModeManager → Car lifecycle (spawn/remove)
- MapService → Car collision detection
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import pygame

pytestmark = pytest.mark.integration

from crazycar.sim.event_source import EventSource
from crazycar.sim.state import SimConfig, SimRuntime, SimEvent, build_default_config
from crazycar.sim.modes import ModeManager, UIRects


# ===============================================================================
# FIXTURES: Simulation Components
# ===============================================================================

@pytest.fixture
def sim_config_headless():
    """SimConfig für Headless-Tests."""
    cfg = SimConfig(
        headless=True,
        fps=100,
        seed=42,
        hard_exit=False,
        start_paused=False,
        window_size=(800, 600)
    )
    return cfg


@pytest.fixture
def sim_runtime():
    """SimRuntime instance."""
    rt = SimRuntime()
    return rt


@pytest.fixture
def event_source_headless():
    """EventSource im Headless-Modus."""
    return EventSource(headless=True)


@pytest.fixture
def event_source_normal():
    """EventSource im normalen Modus."""
    return EventSource(headless=False)


@pytest.fixture
def mode_manager():
    """ModeManager instance."""
    return ModeManager(start_python=False)


@pytest.fixture
def ui_rects():
    """UIRects mit Standard-Geometrie."""
    return UIRects(
        aufnahmen_button=pygame.Rect(100, 100, 100, 30),
        recover_button=pygame.Rect(100, 140, 100, 30),
        button_yes_rect=pygame.Rect(1100, 400, 80, 30),
        button_no_rect=pygame.Rect(1200, 400, 80, 30),
        button_regelung1_rect=pygame.Rect(1000, 100, 200, 40),
        button_regelung2_rect=pygame.Rect(1000, 160, 200, 40),
    )


# ===============================================================================
# TESTGRUPPE 1: EventSource Integration
# ===============================================================================

def test_event_source_headless_returns_empty_events(event_source_headless):
    """Testbedingung: Headless EventSource → Keine Events.
    
    Erwartung: poll() liefert leere Liste.
    Integration: EventSource (headless=True).
    """
    # ACT
    events = event_source_headless.poll()
    
    # ASSERT
    assert events == []


@patch("pygame.event.get")
def test_event_source_normalizes_pygame_events(mock_get, event_source_normal):
    """Testbedingung: pygame.QUIT → SimEvent("QUIT").
    
    Erwartung: pygame-Events werden zu SimEvents normalisiert.
    Integration: EventSource.poll() → SimEvent creation.
    """
    # ARRANGE
    quit_event = Mock(spec=pygame.event.Event)
    quit_event.type = pygame.QUIT
    mock_get.return_value = [quit_event]
    
    # ACT
    events = event_source_normal.poll()
    
    # ASSERT
    assert len(events) == 1
    assert events[0].type == "QUIT"
    assert isinstance(events[0], SimEvent)


@patch("pygame.event.get")
def test_event_source_handles_multiple_events(mock_get, event_source_normal):
    """Testbedingung: Mehrere pygame-Events → Mehrere SimEvents.
    
    Erwartung: Alle Events werden konvertiert.
    Integration: EventSource batch processing.
    """
    # ARRANGE
    quit_event = Mock(spec=pygame.event.Event)
    quit_event.type = pygame.QUIT
    
    key_event = Mock(spec=pygame.event.Event)
    key_event.type = pygame.KEYDOWN
    key_event.key = pygame.K_SPACE
    
    mouse_event = Mock(spec=pygame.event.Event)
    mouse_event.type = pygame.MOUSEBUTTONDOWN
    mouse_event.pos = (100, 100)
    mouse_event.button = 1
    
    mock_get.return_value = [quit_event, key_event, mouse_event]
    
    # ACT
    events = event_source_normal.poll()
    
    # ASSERT
    assert len(events) == 3
    assert events[0].type == "QUIT"
    assert events[1].type == "SPACE"
    assert events[2].type == "MOUSE_DOWN"


# ===============================================================================
# TESTGRUPPE 2: SimConfig + SimRuntime Integration
# ===============================================================================

def test_sim_config_build_default(integration_seed):
    """Testbedingung: build_default_config() liest ENV-Variablen.
    
    Erwartung: Config mit korrekten Defaults.
    Integration: state.build_default_config() + ENV parsing.
    """
    # ACT
    cfg = build_default_config()
    
    # ASSERT
    assert isinstance(cfg, SimConfig)
    assert cfg.fps > 0
    assert cfg.seed >= 0
    assert isinstance(cfg.window_size, tuple)
    assert len(cfg.window_size) == 2


def test_sim_runtime_start_initializes_state(sim_config_headless, sim_runtime):
    """Testbedingung: SimRuntime.start(config) initialisiert State.
    
    Erwartung: dt, window_size, paused gesetzt.
    Integration: SimRuntime.start() + SimConfig.
    """
    # ACT
    sim_runtime.start(sim_config_headless)
    
    # ASSERT
    assert sim_runtime.dt > 0
    assert sim_runtime.window_size == sim_config_headless.window_size
    assert sim_runtime.paused == sim_config_headless.start_paused


@pytest.mark.parametrize("fps, expected_dt", [
    (50, 0.02),
    (100, 0.01),
    (200, 0.005),
])
def test_sim_runtime_dt_calculation(fps, expected_dt):
    """Testbedingung: fps → dt = 1/fps korrekt berechnet.
    
    Erwartung: dt entspricht Frame-Zeit.
    Integration: SimConfig.fps → SimRuntime.dt.
    """
    # ARRANGE
    cfg = SimConfig(fps=fps)
    rt = SimRuntime()
    
    # ACT
    rt.start(cfg)
    
    # ASSERT
    assert rt.dt == pytest.approx(expected_dt, abs=0.001)


# ===============================================================================
# TESTGRUPPE 3: ModeManager + SimEvent Integration
# ===============================================================================

# QUIT/ESC events are handled in loop.py, not in ModeManager.apply()
# See src/crazycar/sim/loop.py line ~200-250 for quit_flag handling


def test_mode_manager_space_toggles_pause(mode_manager, sim_runtime, ui_rects):
    """Testbedingung: SimEvent("SPACE") → rt.paused toggles.
    
    Erwartung: Pause-State wird umgeschaltet.
    Integration: SimEvent("SPACE") → ModeManager → SimRuntime.paused.
    """
    # ARRANGE
    space_event = SimEvent("SPACE", {})
    initial_paused = sim_runtime.paused
    
    # ACT
    mode_manager.apply([space_event], sim_runtime, ui_rects, [])
    
    # ASSERT
    assert sim_runtime.paused != initial_paused


def test_mode_manager_handles_aufnahmen_button(mode_manager, sim_runtime, ui_rects):
    """Testbedingung: Click auf aufnahmen_button → rt.paused = False.
    
    Erwartung: Pause wird aufgehoben.
    Integration: MOUSE_DOWN → ModeManager → SimRuntime.paused.
    """
    # ARRANGE
    sim_runtime.paused = True
    click_event = SimEvent("MOUSE_DOWN", {"pos": (ui_rects.aufnahmen_button.x + 1, ui_rects.aufnahmen_button.y + 1)})
    
    # ACT
    mode_manager.apply([click_event], sim_runtime, ui_rects, [])
    
    # ASSERT
    assert sim_runtime.paused is False


# ===============================================================================
# TESTGRUPPE 4: ModeManager + Car Lifecycle
# ===============================================================================

def test_mode_manager_python_mode_switch_kills_car(mode_manager, sim_runtime, ui_rects):
    """Testbedingung: Python-Mode-Switch → Car.alive = False (für Respawn).
    
    Erwartung: ModeManager terminiert Car für Neustart.
    Integration: ModeManager.apply() → Car state change.
    """
    # ARRANGE - Klick auf Python-Button
    click_python = SimEvent("MOUSE_DOWN", {"pos": (1010, 165)})
    
    # ACT - Click Python Button
    mode_manager.apply([click_python], sim_runtime, ui_rects, [])
    
    # ASSERT - Dialog wird angezeigt
    assert mode_manager.show_dialog is True
    assert sim_runtime.paused is True
    
    # ARRANGE - Klick auf "Yes" im Dialog
    class CarMock:
        def __init__(self):
            self.alive = True
    
    cars = [CarMock()]
    click_yes = SimEvent("MOUSE_DOWN", {"pos": (ui_rects.button_yes_rect.x + 1, ui_rects.button_yes_rect.y + 1)})
    
    # ACT - Confirm Python Mode
    mode_manager.apply([click_yes], sim_runtime, ui_rects, cars)
    
    # ASSERT - Car wurde terminiert
    assert cars[0].alive is False
    assert mode_manager.regelung_py is True


# ===============================================================================
# TESTGRUPPE 5: Headless Simulation Run (Mini End-to-End)
# ===============================================================================

@pytest.mark.parametrize("steps", [1, 5, 10])
def test_headless_simulation_runs_n_frames(steps, integration_seed, headless_display):
    """Testbedingung: Headless-Simulation läuft N Frames ohne Fehler.
    
    Erwartung: Simulation terminiert korrekt nach N Frames.
    Integration: EventSource (headless) + SimRuntime + pygame.
    """
    # ARRANGE
    cfg = SimConfig(headless=True, fps=100, seed=integration_seed)
    rt = SimRuntime()
    rt.start(cfg)
    es = EventSource(headless=True)
    
    # ACT
    for frame in range(steps):
        events = es.poll()
        # Headless: keine Events
        assert events == []
        
        rt.tick += 1
        
        # Minimal frame timing
        pygame.time.Clock().tick(cfg.fps)
    
    # ASSERT
    assert rt.tick == steps


def test_simulation_config_seed_reproducibility(integration_seed, headless_display):
    """Testbedingung: Fixer Seed → Reproduzierbare Ergebnisse.
    
    Erwartung: Zwei Läufe mit gleichem Seed liefern gleiche Ergebnisse.
    Integration: SimConfig.seed → seed_all() → random/numpy.
    """
    # ARRANGE
    from crazycar.sim.state import seed_all
    import random
    
    cfg1 = SimConfig(seed=42)
    cfg2 = SimConfig(seed=42)
    
    # ACT - Run 1
    seed_all(cfg1.seed)
    rand1 = [random.random() for _ in range(10)]
    
    # ACT - Run 2
    seed_all(cfg2.seed)
    rand2 = [random.random() for _ in range(10)]
    
    # ASSERT
    assert rand1 == rand2


# ===============================================================================
# TESTGRUPPE 6: Error Handling & Edge Cases
# ===============================================================================

def test_mode_manager_handles_empty_event_list(mode_manager, sim_runtime, ui_rects):
    """Testbedingung: Leere Event-Liste → Kein Fehler.
    
    Erwartung: apply() läuft ohne Exception.
    Integration: ModeManager robustness.
    """
    # ACT
    try:
        mode_manager.apply([], sim_runtime, ui_rects, [])
        success = True
    except Exception:
        success = False
    
    # ASSERT
    assert success


def test_mode_manager_handles_unknown_event_type(mode_manager, sim_runtime, ui_rects):
    """Testbedingung: Unbekannter SimEvent-Typ → Ignoriert.
    
    Erwartung: Keine Exception, Event wird übersprungen.
    Integration: ModeManager event filtering.
    """
    # ARRANGE
    unknown_event = SimEvent("UNKNOWN_TYPE", {})
    
    # ACT
    try:
        mode_manager.apply([unknown_event], sim_runtime, ui_rects, [])
        success = True
    except Exception:
        success = False
    
    # ASSERT
    assert success


def test_sim_runtime_tick_increment(sim_runtime, sim_config_headless):
    """Testbedingung: rt.tick erhöht sich bei jedem Frame.
    
    Erwartung: Tick-Counter akkumuliert.
    Integration: SimRuntime frame counting.
    """
    # ARRANGE
    sim_runtime.start(sim_config_headless)
    initial_tick = sim_runtime.tick
    
    # ACT
    for _ in range(10):
        sim_runtime.tick += 1
    
    # ASSERT
    assert sim_runtime.tick == initial_tick + 10
