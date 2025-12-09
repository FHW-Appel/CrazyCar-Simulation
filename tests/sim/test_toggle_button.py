# tests/sim/test_toggle_button.py
"""Unit-Tests für ToggleButton UI-Widget.

TESTBASIS (ISTQB):
- Anforderung: 3-State-Toggle-Button für UI (Grün/Rot/Blau)
- Module: crazycar.sim.toggle_button
- Klasse: ToggleButton
- Verhalten: State-Cycling (0→1→2→0), Click-Detection, Rendering

TESTVERFAHREN:
- Zustandsübergänge: state=0 → click() → state=1 → click() → state=2 → click() → state=0
- Äquivalenzklassen: Innerhalb Button (click), Außerhalb Button (kein click)
- Mock-basiert: pygame.font.Font, pygame.Surface für isoliertes UI-Testing
- Invarianten: 3 Texte, 3 Farben, rect.width=215, rect.height=45
"""
import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock, MagicMock, patch
import pygame

from crazycar.sim.toggle_button import ToggleButton


# ===============================================================================
# FIXTURES: Mock-Factories
# ===============================================================================

@pytest.fixture
def mock_font():
    """Mock für pygame.font.Font."""
    font = MagicMock()
    font.render.side_effect = lambda txt, aa, col: f"Surface({txt})"
    return font


@pytest.fixture
def toggle_button(mock_font):
    """Factory für ToggleButton mit gemockter Font."""
    def _create(x=0, y=0, text1="A", text2="B", text3="C"):
        with patch("pygame.font.Font", return_value=mock_font):
            return ToggleButton(x, y, text1, text2, text3)
    return _create


# ===============================================================================
# TESTGRUPPE 1: Initialisierung
# ===============================================================================


@pytest.mark.parametrize("x, y, expected_x, expected_y", [
    (0, 0, 0, 0),
    (100, 200, 100, 200),
    (500, 300, 500, 300),
])
def test_toggle_button_init_position(toggle_button, x, y, expected_x, expected_y):
    """Testbedingung: Position (x, y) → rect.x, rect.y korrekt gesetzt.
    
    Erwartung: rect.topleft = (x, y).
    """
    # ACT
    btn = toggle_button(x, y)
    
    # ASSERT
    assert btn.rect.x == expected_x
    assert btn.rect.y == expected_y
    assert btn.rect.width == 215
    assert btn.rect.height == 45


def test_toggle_button_init_creates_three_texts(toggle_button):
    """Testbedingung: 3 Text-Strings → 3 gerenderte Surfaces.
    
    Erwartung: btn.text hat 3 Elemente.
    """
    # ACT
    btn = toggle_button(text1="Text1", text2="Text2", text3="Text3")
    
    # ASSERT
    assert len(btn.text) == 3
    assert btn.text[0] == "Surface(Text1)"
    assert btn.text[1] == "Surface(Text2)"
    assert btn.text[2] == "Surface(Text3)"


def test_toggle_button_init_creates_three_colors(toggle_button):
    """Testbedingung: Init → 3 Farben (Grün, Rot, Blau).
    
    Erwartung: btn.color = [(20,255,0), (255,0,0), (0,0,255)].
    """
    # ACT
    btn = toggle_button()
    
    # ASSERT
    assert len(btn.color) == 3
    assert btn.color[0] == (20, 255, 0)   # Grün
    assert btn.color[1] == (255, 0, 0)    # Rot
    assert btn.color[2] == (0, 0, 255)    # Blau


def test_toggle_button_init_state_zero(toggle_button):
    """Testbedingung: Initialer State → state=0.
    
    Erwartung: Startzustand ist 0 (Grün).
    """
    # ACT
    btn = toggle_button()
    
    # ASSERT
    assert btn.state == 0


# ===============================================================================
# TESTGRUPPE 2: get_status()
# ===============================================================================


@pytest.mark.parametrize("state, expected", [
    (0, 0),
    (1, 1),
    (2, 2),
])
def test_get_status_returns_current_state(toggle_button, state, expected):
    """Testbedingung: state=X → get_status() liefert X.
    
    Erwartung: Rückgabewert == state.
    """
    # ARRANGE
    btn = toggle_button()
    btn.state = state
    
    # ACT
    status = btn.get_status()
    
    # ASSERT
    assert status == expected


# ===============================================================================
# TESTGRUPPE 3: handle_event() - State Cycling
# ===============================================================================


@pytest.mark.parametrize("initial_state, zahl, expected_state", [
    (0, 2, 1),  # 2-state: 0→1
    (1, 2, 0),  # 2-state: 1→0 (wrap)
    (0, 3, 1),  # 3-state: 0→1
    (1, 3, 2),  # 3-state: 1→2
    (2, 3, 0),  # 3-state: 2→0 (wrap)
])
def test_handle_event_cycles_state(toggle_button, initial_state, zahl, expected_state):
    """Testbedingung: Click in rect → state = (state+1) % zahl.
    
    Erwartung: Zustandswechsel gemäß zahl-Parameter.
    """
    # ARRANGE
    btn = toggle_button(x=100, y=100)
    btn.state = initial_state
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (150, 120)  # Inside rect (100,100,215,45)
    
    # ACT
    btn.handle_event(mock_event, zahl=zahl)
    
    # ASSERT
    assert btn.state == expected_state


def test_handle_event_three_clicks_full_cycle(toggle_button):
    """Testbedingung: 3 Clicks mit zahl=3 → 0→1→2→0.
    
    Erwartung: Vollständiger Zyklus durch alle 3 Zustände.
    """
    # ARRANGE
    btn = toggle_button(x=100, y=100)
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (150, 120)
    
    # ACT & ASSERT
    assert btn.state == 0
    btn.handle_event(mock_event, zahl=3)
    assert btn.state == 1
    btn.handle_event(mock_event, zahl=3)
    assert btn.state == 2
    btn.handle_event(mock_event, zahl=3)
    assert btn.state == 0


# ===============================================================================
# TESTGRUPPE 4: handle_event() - Click Detection
# ===============================================================================



@pytest.mark.parametrize("click_pos, inside", [
    ((150, 120), True),   # Innerhalb rect
    ((50, 50), False),    # Außerhalb links oben
    ((400, 200), False),  # Außerhalb rechts unten
])
def test_handle_event_click_detection(toggle_button, click_pos, inside):
    """Testbedingung: Click-Position → rect.collidepoint() bestimmt State-Änderung.
    
    Erwartung: inside=True → state+=1, inside=False → state unverändert.
    """
    # ARRANGE
    btn = toggle_button(x=100, y=100)
    initial_state = btn.state
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = click_pos
    
    # ACT
    btn.handle_event(mock_event, zahl=3)
    
    # ASSERT
    if inside:
        assert btn.state == (initial_state + 1) % 3
    else:
        assert btn.state == initial_state
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (50, 50)  # Außerhalb
    
    # WHEN
    btn.handle_event(mock_event, zahl=2)
    # THEN
    assert btn.state == 0


def test_handle_event_right_click_ignored():
    """GIVEN: Rechtsklick, WHEN: handle_event(), THEN: state unverändert."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 3  # Rechte Maustaste
    mock_event.pos = (150, 120)
    
    # WHEN
    btn.handle_event(mock_event, zahl=2)
    # THEN
    assert btn.state == 0


def test_handle_event_non_mouse_event_ignored():
    """GIVEN: KEYDOWN-Event, WHEN: handle_event(), THEN: state unverändert."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_event = Mock()
    mock_event.type = pygame.KEYDOWN
    mock_event.key = pygame.K_SPACE
    
    # WHEN
    btn.handle_event(mock_event, zahl=2)
    # THEN
    assert btn.state == 0


# ------------------- draw() -------------------

@patch("pygame.draw.rect")
def test_draw_calls_pygame_draw_rect(mock_draw):
    """GIVEN: Button, WHEN: draw(), THEN: pygame.draw.rect aufgerufen."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_screen = Mock()
    # WHEN
    btn.draw(mock_screen)
    # THEN
    mock_draw.assert_called_once()
    args = mock_draw.call_args[0]
    assert args[0] == mock_screen
    assert args[1] == btn.color[0]  # State 0 → Farbe 0
    assert args[2] == btn.rect


def test_draw_blits_correct_text_for_state():
    """GIVEN: state=1, WHEN: draw(), THEN: text[1] geblittet."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
        btn.state = 1
    
    mock_screen = Mock()
    # WHEN
    with patch("pygame.draw.rect"):
        btn.draw(mock_screen)
    # THEN
    mock_screen.blit.assert_called_once_with(btn.text[1], (btn.rect.x, btn.rect.centery))


def test_draw_uses_correct_color_for_state():
    """GIVEN: state=2, WHEN: draw(), THEN: color[2] verwendet."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
        btn.state = 2
    
    mock_screen = Mock()
    # WHEN
    with patch("pygame.draw.rect") as mock_draw:
        btn.draw(mock_screen)
    # THEN
    args = mock_draw.call_args[0]
    assert args[1] == btn.color[2]  # Blau


# ------------------- Edge-Cases -------------------

def test_handle_event_rect_boundary_click_detected():
    """GIVEN: Click exakt auf rect-Grenze, WHEN: handle_event(), THEN: State ändert sich."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    # rect ist (100, 100, 215, 45) → right edge bei x=315
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (100, 100)  # Top-left corner
    
    # WHEN
    btn.handle_event(mock_event, zahl=2)
    # THEN
    assert btn.state == 1  # Click erkannt


def test_handle_event_zahl_1_wraps_immediately():
    """GIVEN: zahl=1, WHEN: Click, THEN: state bleibt 0 (0+1)%1=0."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (150, 120)
    
    # WHEN
    btn.handle_event(mock_event, zahl=1)
    # THEN
    assert btn.state == 0


def test_draw_does_not_crash_with_mock_screen():
    """GIVEN: Mock-Screen, WHEN: draw(), THEN: Kein Crash."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(50, 50, "X", "Y", "Z")
    
    mock_screen = Mock()
    # WHEN / THEN
    try:
        with patch("pygame.draw.rect"):
            btn.draw(mock_screen)
    except Exception as e:
        pytest.fail(f"draw() sollte nicht crashen: {e}")


def test_multiple_clicks_cycle_correctly():
    """GIVEN: zahl=2, WHEN: 10x Click, THEN: state alterniert."""
    # GIVEN
    with patch("pygame.font.Font"):
        btn = ToggleButton(100, 100, "A", "B", "C")
    
    mock_event = Mock()
    mock_event.type = pygame.MOUSEBUTTONDOWN
    mock_event.button = 1
    mock_event.pos = (150, 120)
    
    # WHEN
    for i in range(10):
        btn.handle_event(mock_event, zahl=2)
    # THEN
    assert btn.state == 0  # 10 % 2 = 0
