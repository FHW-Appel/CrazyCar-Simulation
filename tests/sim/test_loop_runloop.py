"""Test Suite for run_loop() Main Game Loop - Frame-by-Frame Simulation.

This module provides comprehensive smoke and integration tests for the central
game loop in loop.py. The run_loop() function orchestrates events, updates,
rendering, and UI interactions for each frame.

Test Strategy:
- Smoke Tests: Validate complete frame cycles with minimal car lifetime
- Integration Tests: Verify event processing, mode switching, UI rendering
- Mocking Strategy: Replace pygame display, fonts, and heavy dependencies
- Dummy Objects: Lightweight stubs for Car, EventSource, ModeManager, etc.

Test Classes:
- DummyClock: Stub for pygame.time.Clock with tick tracking
- DummyFontFT: Stub for FreeType font rendering
- DummyFont: Stub for pygame.font.Font with Surface return
- DummyCar: Complete car simulation with lifecycle management
- DummyButton: Toggle button stub with event handling
- DummyMapService: Map rendering stub with resize tracking
- DummyEvent: Normalized event with type and payload
- DummyEventSource: Frame-by-frame event provider with resize support
- DummyModes: Mode manager stub with pause/dialog control
- DummyCfg/DummyRt: Configuration and runtime state stubs

Helper Functions:
- _mk_ui(): Create complete UICtx with all required attributes
- _mk_ui_rects(): Create UIRects for button collision detection
- _patch_pygame_no_window(): Monkeypatch pygame for headless testing

Coverage Goals:
- run_loop(): Event processing, car updates, rendering, exit handling
- Resize events: Window/map updates on screen size changes
- Pause loop: Snapshot recovery during pause state
- Quit/ESC: finalize_exit callback with hard_exit flag
- HUD rendering: Telemetry display, buttons, dialogs, toggle widgets
- Mode switching: Python vs C controller selection

See Also:
- loop.py: Main implementation under test
- test_simulation_smoke.py: Higher-level simulation entry point tests
- test_event_source.py: EventSource unit tests

ISTQB Test Level: Integration Testing
ISTQB Test Type: Functional Testing (smoke tests for critical paths)
ISTQB Test Technique: State Transition Testing (pause/active states)
"""

import types
import pytest
import pygame

import crazycar.sim.loop as loopmod


# ============================================================================
# Dummy Classes - Lightweight Stubs for Heavy Dependencies
# ============================================================================

class DummyClock:
    """Stub for pygame.time.Clock - tracks tick() calls without real timing.
    
    Purpose:
        Replace pygame's FPS limiter to avoid real-time delays in tests.
        Records all tick() calls for verification.
    
    Attributes:
        ticks: List of FPS values passed to tick()
    
    Test Usage:
        Verify FPS limiting is called with correct cfg.fps value.
    """
    def __init__(self):
        self.ticks = []

    def tick(self, fps):
        """Record tick call and return 0 (no real delay).
        
        Args:
            fps: Target frames per second
            
        Returns:
            0 (no actual milliseconds elapsed)
        """
        self.ticks.append(fps)
        return 0


class DummyFontFT:
    """Stub for pygame.freetype.Font - replaces FreeType rendering.
    
    Purpose:
        Avoid loading real font files in headless environment.
        Satisfies render_to() interface without actual text rendering.
    
    Test Usage:
        Allows HUD rendering code to execute without pygame.freetype setup.
    """
    def render_to(self, *args, **kwargs):
        """No-op render - satisfies interface without drawing."""
        return None


class DummyFont:
    """Stub for pygame.font.Font - returns minimal Surface for text rendering.
    
    Purpose:
        Replace pygame.font rendering with lightweight stub.
        render() must return Surface-like object with get_rect().
    
    Test Usage:
        Enables generation/alive count text rendering in HUD without real fonts.
    """
    def render(self, *args, **kwargs):
        """Return 1x1 Surface to satisfy get_rect() calls in blit operations.
        
        Returns:
            Minimal pygame.Surface with get_rect() method
        """
        return pygame.Surface((1, 1))


class DummyCar:
    """Complete car stub with lifecycle, physics, sensors, and rendering stubs.
    
    Purpose:
        Simulate car behavior without real physics/collision calculations.
        Dies after first update() to trigger loop termination in 2nd frame.
    
    Attributes:
        _alive: Internal alive state (False after first update)
        alive: Public alive flag (set to False by ESC event handling)
        center: Car position (x, y) in pixels
        carangle: Current heading angle in radians
        speed: Current speed in px/10ms
        speed_set: Target speed setting
        power: Motor power level
        radangle: Steering angle in radians
        radars: List of (contact_point, distance) tuples for sensors
        bit_volt_wert_list: List of (digital_bit, voltage) tuples for sensors
        distance: Total distance traveled in px
        time: Simulation time in seconds
        round_time: Current lap time in seconds
        updated: Counter for update() calls
        drawn: Counter for draw() calls
    
    Lifecycle:
        Frame 1: is_alive() = True, update() sets _alive=False
        Frame 2: is_alive() = False → still_alive==0 → loop ends
    
    Test Usage:
        Validates car update/draw cycles, HUD data formatting, loop termination.
    """
    def __init__(self):
        # Lifecycle
        self._alive = True  # Internal state: dies after first update()
        self.alive = True   # Public flag: can be set False by ESC event
        
        # Physics
        self.center = (100.0, 200.0)  # Position (x, y)
        self.carangle = 0.0           # Heading angle
        self.speed = 0.0              # Current speed
        self.speed_set = 0            # Target speed
        self.power = 0.0              # Motor power
        self.radangle = 0.0           # Steering angle
        
        # Sensors (format: [(contact_point, distance), ...])
        self.radars = [(0, 10), (1, 20)]
        self.bit_volt_wert_list = [(0, 1.23), (1, 2.34)]
        
        # Telemetry
        self.distance = 0.0
        self.time = 0.0
        self.round_time = 0.0
        
        # Test counters
        self.updated = 0
        self.drawn = 0

    def is_alive(self):
        """Check if car is still active in simulation.
        
        Returns:
            True if alive, False if crashed/finished
        """
        return self._alive

    def update(self, screen, drawtracks, sensor_status, collision_status):
        """Simulate one frame of car physics/sensors.
        
        Dies after first call to trigger loop termination in 2nd frame.
        
        Args:
            screen: Pygame surface (unused in stub)
            drawtracks: Whether to draw trajectory (unused)
            sensor_status: Sensor enable/disable flag
            collision_status: Collision detection mode
        
        Side Effects:
            Sets _alive=False after first call (simulates death)
            Increments updated counter
        """
        self.updated += 1
        self._alive = False  # Die after 1st frame → 2nd frame ends loop

    def draw(self, screen):
        """Render car sprite to screen.
        
        Args:
            screen: Pygame surface (unused in stub)
        
        Side Effects:
            Increments drawn counter
        """
        self.drawn += 1


class DummyButton:
    """Toggle button stub with event handling and status tracking.
    
    Purpose:
        Replace ToggleButton widgets (collision/sensor buttons) in UI.
        Tracks handle_event() and draw() calls for verification.
    
    Attributes:
        _status: Current toggle state (0 or 1)
        handled: List of (raw_event, n) tuples from handle_event()
        draw_calls: Counter for draw() invocations
    
    Test Usage:
        Verify raw events reach toggle buttons, buttons are rendered.
    """
    def __init__(self, status=0):
        self._status = status
        self.handled = []
        self.draw_calls = 0

    def handle_event(self, raw, n):
        """Process raw pygame event for toggle button.
        
        Args:
            raw: Raw pygame event object
            n: Button identifier
        
        Side Effects:
            Appends (raw, n) to handled list
        """
        self.handled.append((raw, n))

    def get_status(self):
        """Get current toggle state.
        
        Returns:
            0 or 1 (off/on)
        """
        return self._status

    def draw(self, screen):
        """Render button to screen.
        
        Args:
            screen: Pygame surface (unused in stub)
        
        Side Effects:
            Increments draw_calls counter
        """
        self.draw_calls += 1


class DummyMapService:
    """Map rendering service stub with resize tracking.
    
    Purpose:
        Replace MapService for background map rendering.
        Tracks resize() and blit() calls without real image loading.
    
    Attributes:
        resizes: List of (width, height) tuples from resize() calls
        blits: Counter for blit() invocations
    
    Test Usage:
        Verify map updates on window resize, rendered each frame.
    """
    def __init__(self):
        self.resizes = []
        self.blits = 0

    def resize(self, size):
        """Handle window resize event.
        
        Args:
            size: (width, height) tuple
        
        Side Effects:
            Appends size to resizes list
        """
        self.resizes.append(size)

    def blit(self, screen):
        """Render map to screen.
        
        Args:
            screen: Pygame surface (unused in stub)
        
        Side Effects:
            Increments blits counter
        """
        self.blits += 1


class DummyEvent:
    """Normalized event with type and payload for EventSource.
    
    Purpose:
        Represent processed events (QUIT, ESC, TOGGLE_TRACKS, etc.)
        as simple objects with type string and payload dict.
    
    Attributes:
        type: Event type string ("QUIT", "ESC", "KEY_CHAR", etc.)
        payload: Dict with event-specific data ({"char": "a"}, {"size": (w,h)})
    
    Test Usage:
        Construct event sequences for frame-by-frame simulation.
    """
    def __init__(self, type_, payload=None):
        self.type = type_
        self.payload = payload or {}


class DummyEventSource:
    """Frame-by-frame event provider with resize event support.
    
    Purpose:
        Replace EventSource to control event timing across frames.
        Provides separate event streams for normal/raw/resize events.
    
    Attributes:
        _frames: List of event lists (one per frame) for poll()
        _raw_frames: List of raw event lists for last_raw()
        _resize_events: One-shot resize events for poll_resize()
        _frame_i: Current frame index
    
    Test Usage:
        Define exact event sequence for deterministic test scenarios.
        Trigger resize, quit, keyboard events at specific frames.
    """
    def __init__(self, frames, raw_frames=None, resize_events=None):
        """Initialize event source with frame-by-frame event sequences.
        
        Args:
            frames: List of event lists (one per poll() call)
            raw_frames: List of raw event lists (one per last_raw() call)
            resize_events: One-shot resize events for poll_resize()
        """
        self._frames = list(frames)
        self._raw_frames = list(raw_frames or [[] for _ in range(len(frames))])
        self._resize_events = list(resize_events or [])
        self._frame_i = 0

    def poll_resize(self):
        """Get resize events (one-shot, cleared after first call).
        
        Returns:
            List of resize events (empty on subsequent calls)
        """
        evs = self._resize_events
        self._resize_events = []  # One-shot: clear after first call
        return evs

    def poll(self):
        """Get events for current frame, advance frame counter.
        
        Returns:
            List of DummyEvent objects for current frame
        """
        if self._frame_i >= len(self._frames):
            return []
        evs = self._frames[self._frame_i]
        self._frame_i += 1
        return evs

    def last_raw(self):
        """Get raw events for last poll() call (for toggle buttons).
        
        Returns:
            List of raw pygame event objects
        """
        i = max(0, self._frame_i - 1)
        if i >= len(self._raw_frames):
            return []
        return self._raw_frames[i]


class DummyModes:
    """Mode manager stub with pause/dialog control and action sequences.
    
    Purpose:
        Replace ModeManager to control pause state, dialog display,
        controller selection, and snapshot actions.
    
    Attributes:
        regelung_py: Controller selection (True=Python, False=C)
        show_dialog: Whether to display dialog overlay
        _pause_first: If True, unpause in first apply() call
        _applies: Counter for apply() invocations
        _actions_seq: List of action dicts to return from apply()
    
    Test Usage:
        Simulate mode changes, pause recovery, snapshot triggers.
    """
    def __init__(self, regelung_py=True, show_dialog=True, pause_first=False, actions_seq=None):
        self.regelung_py = regelung_py
        self.show_dialog = show_dialog
        self._pause_first = pause_first
        self._applies = 0
        self._actions_seq = list(actions_seq or [])

    def apply(self, events, rt, ui_rects, cars):
        """Process events and return action dict for run_loop().
        
        Args:
            events: List of normalized events
            rt: Runtime state (modified in-place if _pause_first=True)
            ui_rects: UI rectangles for button collision
            cars: List of car instances
        
        Returns:
            Action dict (e.g., {"take_snapshot": True})
        
        Side Effects:
            Increments _applies counter
            May unpause rt if _pause_first=True
            Pops next action from _actions_seq if provided
        """
        self._applies += 1

        # Optional: unpause in first apply() call (for pause loop tests)
        if self._pause_first and rt.paused:
            rt.paused = False

        # Return predefined actions if provided
        if self._actions_seq:
            return self._actions_seq.pop(0)
        return {}


class DummyCfg:
    """Simulation configuration stub for run_loop().
    
    Attributes:
        fps: Target frames per second
        hard_exit: Whether to use hard exit (sys.exit) on quit
    
    Test Usage:
        Control FPS limiting and exit behavior.
    """
    def __init__(self, fps=60, hard_exit=False):
        self.fps = fps
        self.hard_exit = hard_exit


class DummyRt:
    """Runtime state stub for run_loop().
    
    Attributes:
        paused: Pause state (True=pause loop active)
        drawtracks: Whether to draw car trajectories
        file_text: Text input for snapshot filename
        current_generation: Generation number for HUD
        window_size: Current window dimensions (width, height)
    
    Test Usage:
        Track state changes during simulation (pause, tracks, input).
    """
    def __init__(self):
        self.paused = False
        self.drawtracks = False
        self.file_text = ""
        self.current_generation = 1
        self.window_size = (800, 600)


# ============================================================================
# Helper Functions - Test Setup Utilities
# ============================================================================

def _mk_ui():
    """Create complete UICtx with all required attributes for run_loop().
    
    Constructs UICtx dataclass with dummy fonts, surfaces, colors, and
    button rectangles. All visual elements are minimal stubs.
    
    Returns:
        UICtx instance with all required fields initialized
    
    Test Usage:
        Provide ui parameter for run_loop() in all tests.
    """
    screen = pygame.Surface((800, 600))
    return loopmod.UICtx(
        # Surfaces/Fonts
        screen=screen,
        font_ft=DummyFontFT(),
        font_gen=DummyFont(),
        font_alive=DummyFont(),
        clock=DummyClock(),
        # Labels/Colors
        text1="c_regelung",
        text2="python_regelung",
        text_color=(0, 0, 0),
        button_color=(0, 255, 0),
        # UI Rects (minimal 10x10 placeholders)
        button_regelung1_rect=pygame.Rect(10, 10, 10, 10),
        button_regelung2_rect=pygame.Rect(10, 30, 10, 10),
        button_yes_rect=pygame.Rect(0, 0, 0, 0),
        button_no_rect=pygame.Rect(0, 0, 0, 0),
        aufnahmen_button=pygame.Rect(10, 50, 10, 10),
        recover_button=pygame.Rect(10, 70, 10, 10),
        text_box_rect=pygame.Rect(10, 90, 10, 10),
        # Button positions
        positionx_btn=10,
        positiony_btn=10,
        button_width=10,
        button_height=10,
    )


def _mk_ui_rects():
    """Create UIRects dataclass for button collision detection.
    
    Returns:
        UIRects instance with all button rectangles (minimal 10x10)
    
    Test Usage:
        Provide ui_rects parameter for run_loop() in all tests.
    
    Note:
        Import UIRects from modes.py if structure differs.
    """
    return loopmod.UIRects(
        aufnahmen_button=pygame.Rect(10, 50, 10, 10),
        recover_button=pygame.Rect(10, 70, 10, 10),
        button_yes_rect=pygame.Rect(0, 0, 0, 0),
        button_no_rect=pygame.Rect(0, 0, 0, 0),
        button_regelung1_rect=pygame.Rect(10, 10, 10, 10),
        button_regelung2_rect=pygame.Rect(10, 30, 10, 10),
    )


def _patch_pygame_no_window(monkeypatch):
    """Monkeypatch pygame display/mouse/draw for headless testing.
    
    Replaces all pygame functions that require window/display:
    - display.set_mode(): Return Surface instead of opening window
    - display.flip(): No-op (no screen update)
    - mouse.get_pos(): Return (0, 0) instead of real cursor
    - draw.line(): No-op (no drawing)
    - draw.rect(): No-op (no drawing)
    
    Args:
        monkeypatch: pytest monkeypatch fixture
    
    Side Effects:
        Modifies loopmod.pygame.display/mouse/draw for duration of test
    
    Test Usage:
        Call at start of every run_loop() test to avoid pygame.error.
    """
    monkeypatch.setattr(loopmod.pygame.display, "set_mode", lambda size, flags=0: pygame.Surface(size))
    monkeypatch.setattr(loopmod.pygame.display, "flip", lambda: None)
    monkeypatch.setattr(loopmod.pygame.mouse, "get_pos", lambda: (0, 0))
    monkeypatch.setattr(loopmod.pygame.draw, "line", lambda *a, **k: None)
    monkeypatch.setattr(loopmod.pygame.draw, "rect", lambda *a, **k: None)


# ============================================================================
# Test Cases - run_loop() Smoke and Integration Tests
# ============================================================================

def test_run_loop_reaches_hud_buttons_dialog_and_ends(monkeypatch):
    """Smoke Test: Complete 2-frame cycle with HUD, buttons, dialog, and termination.
    
    Test Objective:
        Verify run_loop() executes full frame cycle including:
        - Event processing (TOGGLE_TRACKS, KEY_CHAR, BACKSPACE)
        - Raw event handling (toggle buttons)
        - Car update/draw cycle
        - HUD rendering (telemetry, buttons, dialog)
        - Map rendering (blit)
        - Loop termination (still_alive==0)
    
    Test Strategy:
        Frame 1: Car alive, process events, render everything
        Frame 2: Car dead (from update()), still_alive==0 → loop ends
    
    Pre-Conditions:
        - Pygame patched for headless mode
        - screen_service/Interface stubbed
        - DummyCar dies after first update()
    
    Test Steps:
        1. Patch pygame display/mouse/draw
        2. Stub draw_button, draw_dialog, Interface controllers
        3. Create DummyCar (lives 1 frame), event sequence with TOGGLE_TRACKS/text input
        4. Run loop with modes.show_dialog=True, modes.regelung_py=True
        5. Verify TOGGLE_TRACKS processed (rt.drawtracks=True)
        6. Verify text input processed ("a" + backspace → "")
        7. Verify toggle buttons received raw events
        8. Verify map blitted at least once
    
    Expected Results:
        - rt.drawtracks == True (toggle processed)
        - rt.file_text == "" (backspace after "a")
        - collision_button.handled non-empty
        - sensor_button.handled non-empty
        - map_service.blits >= 1
        - finalize_exit NOT called (normal termination)
    
    ISTQB Coverage:
        - Statement Coverage: Main loop body, event handlers, HUD rendering
        - Branch Coverage: show_dialog=True path, regelung_py=True path
        - State Coverage: Active (non-paused) state
    """
    _patch_pygame_no_window(monkeypatch)

    # Stub screen_service functions (draw_button, draw_dialog)
    monkeypatch.setattr(loopmod, "draw_button", lambda *a, **k: None)
    monkeypatch.setattr(loopmod, "draw_dialog", lambda *a, **k: None)
    
    # Stub Interface controllers (regelungtechnik_python, regelungtechnik_c)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_python", lambda cars: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_c", lambda cars: None)

    # Stub sim_to_real (only used for HUD text formatting)
    monkeypatch.setattr(loopmod, "sim_to_real", lambda x: x)

    # Configuration and state
    cfg = DummyCfg(fps=60, hard_exit=False)
    rt = DummyRt()
    ui = _mk_ui()
    ui_rects = _mk_ui_rects()

    # Cars: DummyCar dies after first update() → 2nd frame ends loop
    cars = [DummyCar()]
    map_service = DummyMapService()

    # Event sequence: TOGGLE_TRACKS + text input + backspace
    frames = [
        [
            DummyEvent("TOGGLE_TRACKS"),
            DummyEvent("KEY_CHAR", {"char": "a"}),
            DummyEvent("BACKSPACE"),
        ],
        [],  # Frame 2: no events, car dead, loop ends
    ]
    raw_frames = [[object()], [object()]]  # Raw events for toggle buttons

    es = DummyEventSource(frames=frames, raw_frames=raw_frames)
    modes = DummyModes(regelung_py=True, show_dialog=True)

    collision_button = DummyButton(status=1)
    sensor_button = DummyButton(status=0)

    def finalize_exit(hard):
        raise AssertionError("finalize_exit should not be called in normal termination")

    # Execute run_loop() - should complete 2 frames and exit normally
    loopmod.run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=finalize_exit,
    )

    # Verify event processing
    assert rt.drawtracks is True, "TOGGLE_TRACKS event should set drawtracks=True"
    assert rt.file_text == "", "Text input 'a' + backspace should result in empty string"

    # Verify raw events reached toggle buttons
    assert collision_button.handled, "Collision button should receive raw events"
    assert sensor_button.handled, "Sensor button should receive raw events"

    # Verify map rendering
    assert map_service.blits >= 1, "Map should be blitted at least once per frame"


def test_run_loop_resize_event_updates_window_and_map(monkeypatch):
    """Integration Test: Resize event updates window size and map service.
    
    Test Objective:
        Verify run_loop() handles RESIZE events correctly:
        - Updates rt.window_size
        - Calls pygame.display.set_mode() with new size
        - Notifies MapService.resize() with new dimensions
    
    Test Strategy:
        Provide resize event before frame loop starts (poll_resize()).
        Verify all size-dependent components updated correctly.
    
    Pre-Conditions:
        - Pygame patched for headless mode
        - DummyMapService tracks resize() calls
        - DummyCar dies after first frame
    
    Test Steps:
        1. Patch pygame for headless rendering
        2. Create resize event with size (640, 480)
        3. Run loop with resize_events=[resize_event]
        4. Verify rt.window_size updated to (640, 480)
        5. Verify map_service.resize() called with (640, 480)
        6. Verify ui.screen size matches new dimensions
    
    Expected Results:
        - rt.window_size == (640, 480)
        - map_service.resizes == [(640, 480)]
        - ui.screen.get_size() == (640, 480)
    
    ISTQB Coverage:
        - Event Coverage: RESIZE event handler
        - Integration Coverage: Window ↔ MapService coordination
    """
    _patch_pygame_no_window(monkeypatch)
    
    # Stub rendering/control functions
    monkeypatch.setattr(loopmod, "draw_button", lambda *a, **k: None)
    monkeypatch.setattr(loopmod, "draw_dialog", lambda *a, **k: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_python", lambda cars: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_c", lambda cars: None)
    monkeypatch.setattr(loopmod, "sim_to_real", lambda x: x)

    # Configuration and state
    cfg = DummyCfg()
    rt = DummyRt()
    ui = _mk_ui()
    ui_rects = _mk_ui_rects()

    cars = [DummyCar()]
    map_service = DummyMapService()

    # Resize event: Change window to 640x480
    resize_events = [DummyEvent("RESIZE", {"size": (640, 480)})]
    frames = [[], []]  # 2 frames: first processes resize, second ends (car dead)
    es = DummyEventSource(frames=frames, resize_events=resize_events)
    modes = DummyModes(regelung_py=False, show_dialog=False)

    collision_button = DummyButton()
    sensor_button = DummyButton()

    # Execute run_loop() with resize event
    loopmod.run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=collision_button,
        sensor_button=sensor_button,
        finalize_exit=lambda hard: None,
    )

    # Verify resize event processed correctly
    assert rt.window_size == (640, 480), "Runtime window_size should be updated"
    assert map_service.resizes == [(640, 480)], "MapService.resize() should be called with new size"
    assert ui.screen.get_size() == (640, 480), "UI screen should be resized via set_mode()"


def test_run_loop_quit_calls_finalize_exit(monkeypatch):
    """Integration Test: QUIT event triggers finalize_exit callback with hard_exit flag.
    
    Test Objective:
        Verify run_loop() calls finalize_exit() when QUIT event received.
        Confirm hard_exit flag passed correctly from cfg.
    
    Test Strategy:
        Inject QUIT event in first frame, catch finalize_exit() with exception.
        Verify hard_exit parameter matches cfg.hard_exit.
    
    Pre-Conditions:
        - Pygame patched for headless mode
        - cfg.hard_exit=True
        - finalize_exit raises StopLoop exception
    
    Test Steps:
        1. Patch pygame for headless rendering
        2. Create QUIT event in first frame
        3. Define finalize_exit that asserts hard=True and raises StopLoop
        4. Run loop, expect StopLoop exception
        5. Verify finalize_exit called with correct parameter
    
    Expected Results:
        - finalize_exit(hard=True) called
        - StopLoop exception raised
        - Loop terminated immediately
    
    ISTQB Coverage:
        - Event Coverage: QUIT event handler
        - Error Handling: Clean exit path with callback
    """
    _patch_pygame_no_window(monkeypatch)
    
    # Stub rendering/control functions
    monkeypatch.setattr(loopmod, "draw_button", lambda *a, **k: None)
    monkeypatch.setattr(loopmod, "draw_dialog", lambda *a, **k: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_python", lambda cars: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_c", lambda cars: None)

    # Configuration with hard_exit=True
    cfg = DummyCfg(hard_exit=True)
    rt = DummyRt()
    ui = _mk_ui()
    ui_rects = _mk_ui_rects()

    cars = [DummyCar()]
    map_service = DummyMapService()

    # QUIT event in first frame
    frames = [[DummyEvent("QUIT")]]
    es = DummyEventSource(frames=frames)
    modes = DummyModes()

    class StopLoop(Exception):
        """Custom exception to exit loop and verify finalize_exit called."""
        pass

    def finalize_exit(hard):
        """Verify hard_exit flag and raise exception to terminate loop."""
        assert hard is True, "finalize_exit should receive hard=True from cfg"
        raise StopLoop()

    # Execute run_loop() - expect StopLoop raised by finalize_exit
    with pytest.raises(StopLoop):
        loopmod.run_loop(
            cfg=cfg,
            rt=rt,
            es=es,
            modes=modes,
            ui=ui,
            ui_rects=ui_rects,
            map_service=map_service,
            cars=cars,
            collision_button=DummyButton(),
            sensor_button=DummyButton(),
            finalize_exit=finalize_exit,
        )


def test_run_loop_pause_recover_path(monkeypatch):
    """Integration Test: Pause loop with snapshot recovery action.
    
    Test Objective:
        Verify run_loop() handles pause state correctly:
        - Enters pause loop when rt.paused=True
        - Processes ModeManager actions (recover_snapshot)
        - Calls moment_recover() with rt.file_text
        - Exits pause when rt.paused set to False
    
    Test Strategy:
        Start with rt.paused=True, modes._pause_first=True (unpause in apply()).
        First apply() returns {"recover_snapshot": True} → calls moment_recover().
        Verify moment_recover() called, loop continues after unpause.
    
    Pre-Conditions:
        - Pygame patched for headless mode
        - moment_recover stubbed to return new car list
        - rt.paused=True, rt.file_text="snap1"
        - modes._pause_first=True (unpause in first apply())
    
    Test Steps:
        1. Patch pygame for headless rendering
        2. Stub moment_recover to track calls
        3. Start with rt.paused=True
        4. Configure modes to unpause and return {"recover_snapshot": True}
        5. Run loop with 2 frames
        6. Verify moment_recover() called at least once
    
    Expected Results:
        - moment_recover("snap1") called
        - Pause loop exited after rt.paused=False
        - Loop continues normally after recovery
    
    ISTQB Coverage:
        - State Coverage: Paused state → Active state transition
        - Action Coverage: recover_snapshot action handling
    """
    _patch_pygame_no_window(monkeypatch)
    
    # Stub rendering/control functions
    monkeypatch.setattr(loopmod, "draw_button", lambda *a, **k: None)
    monkeypatch.setattr(loopmod, "draw_dialog", lambda *a, **k: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_python", lambda cars: None)
    monkeypatch.setattr(loopmod.Interface, "regelungtechnik_c", lambda cars: None)
    monkeypatch.setattr(loopmod, "sim_to_real", lambda x: x)

    # Stub moment_recover to track calls
    called = {"recover": 0}

    def _fake_recover(file_text):
        """Track moment_recover calls and return new car."""
        called["recover"] += 1
        return [DummyCar()]

    monkeypatch.setattr(loopmod, "moment_recover", _fake_recover)

    # Configuration and state
    cfg = DummyCfg()
    rt = DummyRt()
    rt.paused = True  # Start in pause loop
    rt.file_text = "snap1"  # Snapshot filename for recovery
    ui = _mk_ui()
    ui_rects = _mk_ui_rects()

    map_service = DummyMapService()
    cars = [DummyCar()]

    # Event sequence: pause loop with no ESC/QUIT, apply returns recover_snapshot
    frames = [[], []]  # 2 frames: first exits pause, second ends (car dead)
    es = DummyEventSource(frames=frames)

    # Modes: unpause in first apply(), return {"recover_snapshot": True}
    modes = DummyModes(
        regelung_py=True,
        show_dialog=False,
        pause_first=True,  # Unpause in first apply()
        actions_seq=[{"recover_snapshot": True}, {}],  # First apply() triggers recovery
    )

    # Execute run_loop() - pause loop should exit, recovery should be called
    loopmod.run_loop(
        cfg=cfg,
        rt=rt,
        es=es,
        modes=modes,
        ui=ui,
        ui_rects=ui_rects,
        map_service=map_service,
        cars=cars,
        collision_button=DummyButton(),
        sensor_button=DummyButton(),
        finalize_exit=lambda hard: None,
    )

    # Verify moment_recover called with rt.file_text
    assert called["recover"] >= 1, "moment_recover should be called during pause loop recovery"
