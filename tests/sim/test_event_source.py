# tests/sim/test_event_source.py
"""Unit-Tests für EventSource (pygame-Event-Normalisierung).

TESTBASIS (ISTQB):
- Anforderung: pygame-Events → SimEvent-Normalisierung (QUIT, KEYDOWN, MOUSEBUTTONDOWN, VIDEORESIZE)
- Module: crazycar.sim.event_source
- Klasse: EventSource (headless/non-headless Modus)

TESTVERFAHREN:
- Äquivalenzklassen: Headless (keine Events), Non-Headless (Event-Mapping)
- Zustandsübergänge: pygame.event.get() → SimEvent-Liste
- Grenzwertanalyse: Leere Event-Liste, unbekannte Event-Types
- Mock-basiert: pygame.event.get() gemockt für deterministisches Testing
"""
import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock, patch
import pygame

from crazycar.sim.event_source import EventSource
from crazycar.sim.state import SimEvent


# ===============================================================================
# FIXTURES: Event-Factories
# ===============================================================================

@pytest.fixture
def mock_pygame_event():
    """Factory für pygame-Event-Mock."""
    def _create(event_type, **kwargs):
        event = Mock()
        event.type = event_type
        for key, val in kwargs.items():
            setattr(event, key, val)
        return event
    return _create


@pytest.fixture
def event_source_headless():
    """EventSource im Headless-Modus."""
    return EventSource(headless=True)


@pytest.fixture
def event_source_normal():
    """EventSource im normalen Modus."""
    return EventSource(headless=False)


# ===============================================================================
# TESTGRUPPE 1: Headless-Modus
# ===============================================================================


@pytest.mark.parametrize("method_name", ["poll", "poll_resize"])
def test_event_source_headless_methods_return_empty(event_source_headless, method_name):
    """Testbedingung: Headless-Modus → alle Event-Methoden liefern [].
    
    Erwartung: Keine Events im Headless-Modus.
    """
    # ACT
    method = getattr(event_source_headless, method_name)
    result = method()
    
    # ASSERT
    assert result == []


def test_event_source_headless_last_raw_empty(event_source_headless):
    """Testbedingung: last_raw() im Headless-Modus → [].
    
    Erwartung: Keine rohen Events gespeichert.
    """
    # ACT
    event_source_headless.poll()
    result = event_source_headless.last_raw()
    
    # ASSERT
    assert result == []


# ===============================================================================
# TESTGRUPPE 2: Event-Normalisierung (Non-Headless)
# ===============================================================================


# ------------------- poll_resize() -------------------

@patch("pygame.event.get")
def test_poll_resize_filters_videoresize_events(mock_get):
    """GIVEN: VIDEORESIZE-Event, WHEN: poll_resize(), THEN: SimEvent VIDEORESIZE."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.VIDEORESIZE
    mock_event.size = (1280, 720)
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll_resize()
    # THEN
    assert len(result) == 1
    assert result[0].type == "VIDEORESIZE"
    assert result[0].payload["size"] == (1280, 720)
    mock_get.assert_called_once_with(pygame.VIDEORESIZE)


@patch("pygame.event.get")
def test_poll_resize_empty_when_no_resize_events(mock_get):
    """GIVEN: Keine VIDEORESIZE-Events, WHEN: poll_resize(), THEN: []."""
    # GIVEN
    mock_get.return_value = []
    source = EventSource(headless=False)
    # WHEN
    result = source.poll_resize()
    # THEN
    assert result == []


@patch("pygame.event.get")
def test_poll_resize_updates_last_raw(mock_get):
    """GIVEN: VIDEORESIZE-Event, WHEN: poll_resize(), THEN: last_raw() enthält Event."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.VIDEORESIZE
    mock_event.size = (800, 600)
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    source.poll_resize()
    raw = source.last_raw()
    # THEN
    assert len(raw) == 1
    assert raw[0].type == pygame.VIDEORESIZE


# ------------------- poll() - QUIT -------------------

@patch("pygame.event.get")
def test_poll_quit_event(mock_get):
    """GIVEN: pygame.QUIT, WHEN: poll(), THEN: SimEvent QUIT."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.QUIT
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert len(result) == 1
    assert result[0].type == "QUIT"
    assert result[0].payload == {}




@pytest.mark.parametrize("key, expected_type", [
    (pygame.K_SPACE, "SPACE"),
    (pygame.K_ESCAPE, "ESC"),
    (pygame.K_t, "TOGGLE_TRACKS"),
    (pygame.K_BACKSPACE, "BACKSPACE"),
])
@patch("pygame.event.get")
def test_poll_special_keys(mock_get, key, expected_type):
    """Testbedingung: KEYDOWN Special-Key → SimEvent mit spezifischem Typ.
    
    Erwartung: Korrekte Typ-Zuordnung für SPACE, ESC, TOGGLE_TRACKS, BACKSPACE.
    """
    # ARRANGE
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.KEYDOWN
    mock_event.key = key
    mock_event.unicode = ""
    mock_get.return_value = [mock_event]
    source = EventSource(headless=False)
    
    # ACT
    result = source.poll()
    
    # ASSERT
    assert len(result) == 1
    assert result[0].type == expected_type




@pytest.mark.parametrize("key, unicode_char", [
    (pygame.K_a, "a"),
    (pygame.K_z, "z"),
    (pygame.K_0, "0"),
    (pygame.K_9, "9"),
])
@patch("pygame.event.get")
def test_poll_alphanumeric_char(mock_get, key, unicode_char):
    """Testbedingung: KEYDOWN alphanumerisch → SimEvent KEY_CHAR mit payload.
    
    Erwartung: char im payload.
    """
    # ARRANGE
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.KEYDOWN
    mock_event.key = key
    mock_event.unicode = unicode_char
    mock_get.return_value = [mock_event]
    source = EventSource(headless=False)
    
    # ACT
    result = source.poll()
    
    # ASSERT
    assert len(result) == 1
    assert result[0].type == "KEY_CHAR"
    assert result[0].payload["char"] == unicode_char


@patch("pygame.event.get")
def test_poll_ignores_non_alphanumeric_unicode(mock_get):
    """GIVEN: KEYDOWN mit Sonderzeichen, WHEN: poll(), THEN: Ignoriert."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.KEYDOWN
    mock_event.key = pygame.K_PERIOD
    mock_event.unicode = "."
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert result == []  # Nicht alphanumerisch, ignoriert


# ------------------- poll() - MOUSEBUTTONDOWN -------------------

@patch("pygame.event.get")
def test_poll_mouse_button_down(mock_get):
    """GIVEN: MOUSEBUTTONDOWN, WHEN: poll(), THEN: SimEvent MOUSE_DOWN."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.pos = (100, 200)
    mock_event.button = 1
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert len(result) == 1
    assert result[0].type == "MOUSE_DOWN"
    assert result[0].payload["pos"] == (100, 200)
    assert result[0].payload["button"] == 1


@patch("pygame.event.get")
def test_poll_mouse_right_button(mock_get):
    """GIVEN: MOUSEBUTTONDOWN rechte Taste, WHEN: poll(), THEN: button=3."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.pos = (50, 75)
    mock_event.button = 3
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert result[0].payload["button"] == 3


# ------------------- poll() - Mehrere Events -------------------

@patch("pygame.event.get")
def test_poll_multiple_events_all_converted(mock_get):
    """GIVEN: Mehrere Events, WHEN: poll(), THEN: Alle konvertiert."""
    # GIVEN
    quit_event = Mock(spec=pygame.event.Event)
    quit_event.type = pygame.QUIT
    
    space_event = Mock(spec=pygame.event.Event)
    space_event.type = pygame.KEYDOWN
    space_event.key = pygame.K_SPACE
    
    mouse_event = Mock(spec=pygame.event.Event)
    mouse_event.type = pygame.MOUSEBUTTONDOWN
    mouse_event.pos = (10, 20)
    mouse_event.button = 1
    
    mock_get.return_value = [quit_event, space_event, mouse_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert len(result) == 3
    assert result[0].type == "QUIT"
    assert result[1].type == "SPACE"
    assert result[2].type == "MOUSE_DOWN"


@patch("pygame.event.get")
def test_poll_ignores_unknown_event_types(mock_get):
    """GIVEN: Unbekannter Event-Typ, WHEN: poll(), THEN: Ignoriert."""
    # GIVEN
    unknown_event = Mock(spec=pygame.event.Event)
    unknown_event.type = 9999  # Nicht definiert
    
    quit_event = Mock(spec=pygame.event.Event)
    quit_event.type = pygame.QUIT
    
    mock_get.return_value = [unknown_event, quit_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert len(result) == 1
    assert result[0].type == "QUIT"


# ------------------- last_raw() -------------------

@patch("pygame.event.get")
def test_last_raw_returns_copy_of_events(mock_get):
    """GIVEN: poll() aufgerufen, WHEN: last_raw(), THEN: Kopie der Roh-Events."""
    # GIVEN
    mock_event1 = Mock(spec=pygame.event.Event)
    mock_event1.type = pygame.QUIT
    
    mock_event2 = Mock(spec=pygame.event.Event)
    mock_event2.type = pygame.KEYDOWN
    mock_event2.key = pygame.K_SPACE
    
    mock_get.return_value = [mock_event1, mock_event2]
    
    source = EventSource(headless=False)
    source.poll()
    # WHEN
    raw = source.last_raw()
    # THEN
    assert len(raw) == 2
    assert raw[0].type == pygame.QUIT
    assert raw[1].type == pygame.KEYDOWN


@patch("pygame.event.get")
def test_last_raw_isolated_from_internal_list(mock_get):
    """GIVEN: last_raw() aufgerufen, WHEN: Liste modifiziert, THEN: Interne Liste unverändert."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.QUIT
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    source.poll()
    # WHEN
    raw1 = source.last_raw()
    raw1.clear()  # Externe Liste löschen
    raw2 = source.last_raw()
    # THEN
    assert len(raw2) == 1  # Interne Liste nicht betroffen


# ------------------- Eigenschaften -------------------

def test_event_source_default_headless_false():
    """GIVEN: Kein Parameter, WHEN: EventSource(), THEN: headless=False."""
    # GIVEN / WHEN
    source = EventSource()
    # THEN
    assert source.headless is False


def test_event_source_explicit_headless_true():
    """GIVEN: headless=True, WHEN: EventSource(), THEN: Attribut gesetzt."""
    # GIVEN / WHEN
    source = EventSource(headless=True)
    # THEN
    assert source.headless is True


@patch("pygame.event.get")
def test_poll_returns_list_of_sim_events(mock_get):
    """GIVEN: Events, WHEN: poll(), THEN: Liste von SimEvent-Objekten."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.QUIT
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll()
    # THEN
    assert isinstance(result, list)
    assert all(isinstance(e, SimEvent) for e in result)


@patch("pygame.event.get")
def test_poll_resize_returns_list_of_sim_events(mock_get):
    """GIVEN: VIDEORESIZE, WHEN: poll_resize(), THEN: Liste von SimEvent."""
    # GIVEN
    mock_event = Mock(spec=pygame.event.Event)
    mock_event.type = pygame.VIDEORESIZE
    mock_event.size = (1024, 768)
    mock_get.return_value = [mock_event]
    
    source = EventSource(headless=False)
    # WHEN
    result = source.poll_resize()
    # THEN
    assert isinstance(result, list)
    assert all(isinstance(e, SimEvent) for e in result)
