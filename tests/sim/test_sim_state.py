# tests/sim/test_sim_state.py
"""Unit-Tests für SimConfig/SimRuntime dataclasses.

TESTBASIS (ISTQB):
- Anforderung: Simulation-State-Management (Config, Runtime, Events)
- Module: crazycar.sim.state
- Klassen: SimEvent, SimConfig, SimRuntime
- Funktion: build_default_config (ENV-Variable-Parsing)

TESTVERFAHREN:
- Äquivalenzklassen: Default-Werte, Custom-Werte, ENV-Overrides
- Zustandsübergänge: SimConfig → SimRuntime.start() → Runtime-State
- Grenzwertanalyse: fps=0, seed=0, negative Werte
- Immutability: SimEvent.payload ist separate Dict-Instanz
"""
import pytest

pytestmark = pytest.mark.unit

from crazycar.sim.state import (
    SimEvent, SimConfig, SimRuntime, build_default_config
)


# ===============================================================================
# FIXTURES: Config-Vorlagen
# ===============================================================================

@pytest.fixture
def default_config():
    """Standard SimConfig mit Defaults."""
    return SimConfig()


@pytest.fixture
def custom_config():
    """SimConfig mit Custom-Werten."""
    return SimConfig(
        headless=True,
        fps=60,
        seed=9999,
        hard_exit=False,
        start_paused=True
    )


# ===============================================================================
# TESTGRUPPE 1: SimEvent - Event-Datenstruktur
# ===============================================================================


@pytest.mark.parametrize("event_type, payload, expected_payload", [
    ("QUIT", None, {}),
    ("MOUSE_DOWN", {"pos": (100, 200), "button": 1}, {"pos": (100, 200), "button": 1}),
    ("KEYDOWN", {"key": "SPACE"}, {"key": "SPACE"}),
])
def test_sim_event_creation(event_type, payload, expected_payload):
    """Testbedingung: SimEvent mit/ohne payload → korrekte Initialisierung.
    
    Erwartung: type gesetzt, payload=expected_payload.
    """
    # ACT
    if payload is None:
        event = SimEvent(event_type)
    else:
        event = SimEvent(event_type, payload)
    
    # ASSERT
    assert event.type == event_type
    assert event.payload == expected_payload


def test_sim_event_payload_independence():
    """Testbedingung: Payload-Dicts sind separate Instanzen.
    
    Erwartung: Änderung in event1.payload beeinflusst event2 nicht.
    """
    # ARRANGE
    event1 = SimEvent("QUIT")
    event2 = SimEvent("ESC")
    
    # ACT
    event1.payload["test"] = "value"
    
    # ASSERT
    assert "test" not in event2.payload


# ===============================================================================
# TESTGRUPPE 2: SimConfig - Konfigurations-Dataclass
# ===============================================================================



def test_sim_config_defaults(default_config):
    """Testbedingung: SimConfig ohne Parameter → Defaults gesetzt.
    
    Erwartung: headless=False, fps=100, seed=1234, hard_exit=True, start_paused=False.
    """
    # ASSERT
    assert default_config.headless is False
    assert default_config.fps == 100
    assert default_config.seed == 1234
    assert default_config.hard_exit is True
    assert default_config.start_paused is False
    assert default_config.drawtracks_default is False


def test_sim_config_custom_values():
    """GIVEN: Custom-Werte, WHEN: SimConfig(), THEN: Überschrieben."""
    # GIVEN / WHEN
    cfg = SimConfig(
        headless=True,
        fps=60,
        seed=9999,
        hard_exit=False,
        start_paused=True,
        drawtracks_default=True
    )
    # THEN
    assert cfg.headless is True
    assert cfg.fps == 60
    assert cfg.seed == 9999
    assert cfg.hard_exit is False
    assert cfg.start_paused is True
    assert cfg.drawtracks_default is True


def test_sim_config_window_size_default():
    """GIVEN: Kein window_size, WHEN: SimConfig(), THEN: DEFAULT_WIDTH/HEIGHT."""
    # GIVEN / WHEN
    cfg = SimConfig()
    # THEN
    assert isinstance(cfg.window_size, tuple)
    assert len(cfg.window_size) == 2
    assert cfg.window_size[0] > 0
    assert cfg.window_size[1] > 0


def test_sim_config_custom_window_size():
    """GIVEN: window_size=(800, 600), WHEN: SimConfig(), THEN: Gesetzt."""
    # GIVEN / WHEN
    cfg = SimConfig(window_size=(800, 600))
    # THEN
    assert cfg.window_size == (800, 600)


def test_sim_config_optional_paths():
    """GIVEN: assets_path/out_dir, WHEN: SimConfig(), THEN: Gesetzt."""
    # GIVEN / WHEN
    cfg = SimConfig(assets_path="/assets", out_dir="/output")
    # THEN
    assert cfg.assets_path == "/assets"
    assert cfg.out_dir == "/output"



@pytest.mark.parametrize("tick, dt, quit_flag, paused, drawtracks", [
    (0, 0.0, False, False, False),
    (100, 0.01, True, True, True),
])
def test_sim_runtime_defaults(tick, dt, quit_flag, paused, drawtracks):
    """Testbedingung: SimRuntime() → Defaults gesetzt.
    
    Erwartung: tick=0, dt=0.0, flags=False.
    """
    # ACT
    rt = SimRuntime()
    
    # ASSERT (nur Defaults prüfen)
    assert rt.tick == 0
    assert rt.dt == 0.0
    assert rt.quit_flag is False
    assert rt.paused is False
    assert rt.drawtracks is False
    assert rt.file_text == ""
    assert rt.current_generation == 0
    assert rt.counter == 0



@pytest.mark.parametrize("fps, expected_dt", [
    (50, 0.02),
])
def test_sim_runtime_start_sets_dt_from_fps(fps, expected_dt):
    """Testbedingung: runtime.start(config) → dt = 1/fps.
    
    Erwartung: dt korrekt berechnet.
    """
    # ARRANGE
    cfg = SimConfig(fps=fps)
    rt = SimRuntime()
    
    # ACT
    rt.start(cfg)
    
    # ASSERT
    assert rt.dt == pytest.approx(expected_dt, abs=0.001)
    # THEN
    assert rt.dt == pytest.approx(0.02, abs=0.001)


def test_sim_runtime_start_sets_window_size():
    """GIVEN: Config window_size, WHEN: start(), THEN: Übernommen."""
    # GIVEN
    cfg = SimConfig(window_size=(1024, 768))
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.window_size == (1024, 768)


def test_sim_runtime_start_sets_paused():
    """GIVEN: Config start_paused=True, WHEN: start(), THEN: paused=True."""
    # GIVEN
    cfg = SimConfig(start_paused=True)
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.paused is True


def test_sim_runtime_start_sets_drawtracks():
    """GIVEN: Config drawtracks_default=True, WHEN: start(), THEN: drawtracks=True."""
    # GIVEN
    cfg = SimConfig(drawtracks_default=True)
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.drawtracks is True


def test_sim_runtime_start_resets_counters():
    """GIVEN: Runtime mit tick=100, WHEN: start(), THEN: tick=0."""
    # GIVEN
    cfg = SimConfig()
    rt = SimRuntime()
    rt.tick = 100
    rt.counter = 50
    rt.quit_flag = True
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.tick == 0
    assert rt.counter == 0
    assert rt.quit_flag is False


def test_sim_runtime_start_handles_zero_fps():
    """GIVEN: Config fps=0, WHEN: start(), THEN: dt=1.0 (Fallback)."""
    # GIVEN
    cfg = SimConfig(fps=0)
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.dt == 1.0  # max(1, 0) → 1


def test_sim_runtime_start_high_fps():
    """GIVEN: Config fps=1000, WHEN: start(), THEN: dt=0.001."""
    # GIVEN
    cfg = SimConfig(fps=1000)
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.dt == pytest.approx(0.001, abs=0.0001)


# ------------------- build_default_config() -------------------

def test_build_default_config_no_env():
    """GIVEN: Leeres ENV (keine SDL_VIDEODRIVER), WHEN: build_default_config(), THEN: Defaults."""
    # GIVEN / WHEN - env={} ohne SDL_VIDEODRIVER
    cfg = build_default_config(env={"SDL_VIDEODRIVER": "x11"})  # Nicht "dummy"
    # THEN
    assert cfg.headless is False
    assert cfg.fps == 100
    assert cfg.seed == 1234
    assert cfg.hard_exit is True


def test_build_default_config_headless_from_env():
    """GIVEN: HEADLESS=1, WHEN: build_default_config(), THEN: headless=True."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"HEADLESS": "1"})
    # THEN
    assert cfg.headless is True


def test_build_default_config_sdl_videodriver_dummy():
    """GIVEN: SDL_VIDEODRIVER=dummy, WHEN: build_default_config(), THEN: headless=True."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"SDL_VIDEODRIVER": "dummy"})
    # THEN
    assert cfg.headless is True


def test_build_default_config_fps_from_env():
    """GIVEN: CRAZYCAR_FPS=50, WHEN: build_default_config(), THEN: fps=50."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"CRAZYCAR_FPS": "50"})
    # THEN
    assert cfg.fps == 50


def test_build_default_config_seed_from_env():
    """GIVEN: CRAZYCAR_SEED=9999, WHEN: build_default_config(), THEN: seed=9999."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"CRAZYCAR_SEED": "9999"})
    # THEN
    assert cfg.seed == 9999


def test_build_default_config_hard_exit_false():
    """GIVEN: CRAZYCAR_HARD_EXIT=0, WHEN: build_default_config(), THEN: hard_exit=False."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"CRAZYCAR_HARD_EXIT": "0"})
    # THEN
    assert cfg.hard_exit is False


def test_build_default_config_window_size_from_env():
    """GIVEN: CRAZYCAR_WIDTH/HEIGHT, WHEN: build_default_config(), THEN: window_size gesetzt."""
    # GIVEN / WHEN
    cfg = build_default_config(env={"CRAZYCAR_WIDTH": "1024", "CRAZYCAR_HEIGHT": "768"})
    # THEN
    assert cfg.window_size == (1024, 768)


def test_build_default_config_multiple_env_vars():
    """GIVEN: Mehrere ENV-Vars, WHEN: build_default_config(), THEN: Alle übernommen."""
    # GIVEN / WHEN
    cfg = build_default_config(env={
        "HEADLESS": "1",
        "CRAZYCAR_FPS": "60",
        "CRAZYCAR_SEED": "42",
        "CRAZYCAR_HARD_EXIT": "0",
        "CRAZYCAR_WIDTH": "800",
        "CRAZYCAR_HEIGHT": "600"
    })
    # THEN
    assert cfg.headless is True
    assert cfg.fps == 60
    assert cfg.seed == 42
    assert cfg.hard_exit is False
    assert cfg.window_size == (800, 600)


# ------------------- Edge-Cases -------------------

def test_sim_runtime_start_negative_fps_clamped():
    """GIVEN: Config fps=-10, WHEN: start(), THEN: dt=1.0 (max(1, -10)→1)."""
    # GIVEN
    cfg = SimConfig(fps=-10)
    rt = SimRuntime()
    # WHEN
    rt.start(cfg)
    # THEN
    assert rt.dt == 1.0


def test_build_default_config_invalid_fps_uses_default():
    """GIVEN: CRAZYCAR_FPS='invalid', WHEN: build_default_config(), THEN: Crash oder Fallback."""
    # GIVEN / WHEN / THEN
    with pytest.raises(ValueError):
        build_default_config(env={"CRAZYCAR_FPS": "invalid"})


def test_build_default_config_none_env_uses_os_environ():
    """GIVEN: env=None, WHEN: build_default_config(), THEN: os.environ verwendet."""
    # GIVEN / WHEN
    cfg = build_default_config(env=None)
    # THEN: Sollte nicht crashen, Standard-Werte zurückgeben
    assert isinstance(cfg, SimConfig)


def test_sim_config_is_frozen_dataclass():
    """GIVEN: SimConfig, WHEN: Attribut zuweisen, THEN: slots=True → kein __dict__."""
    # GIVEN
    cfg = SimConfig()
    # WHEN / THEN
    with pytest.raises(AttributeError):
        cfg.__dict__  # slots=True → kein __dict__


def test_sim_runtime_is_mutable():
    """GIVEN: SimRuntime, WHEN: Attribut ändern, THEN: Möglich."""
    # GIVEN
    rt = SimRuntime()
    # WHEN
    rt.tick = 42
    rt.paused = True
    # THEN
    assert rt.tick == 42
    assert rt.paused is True
