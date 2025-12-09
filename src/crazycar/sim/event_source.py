"""Event Source - Normalized event pipeline (pygame/headless).

Responsibilities:
- Read raw pygame events and deliver normalized events
- Events are strings + payload, independent of pygame details
- Separate polling for resize events
- Maintains last raw event batch for UI widgets

Public API:
- class EventSource:
      __init__(headless: bool = False)
      
      poll() -> list[SimEvent]:
          Active/current inputs (keys, mouse, UI)
          
      poll_resize() -> list[SimEvent]:
          Only VIDEORESIZE events
          
      last_raw() -> list[pygame.Event]:
          Raw events from last poll() cycle

Event Types (normalized examples):
- "QUIT": Window close requested
- "ESC": Escape key pressed
- "SPACE": Space bar pressed (pause)
- "TOGGLE_TRACKS": T key (toggle track trails)
- "KEY_CHAR": Alphanumeric character typed
- "BACKSPACE": Backspace key
- "MOUSE_DOWN": Mouse button clicked
- "VIDEORESIZE": Window resized

Usage:
    es = EventSource(headless=False)
    
    # Process resize events separately
    resize_events = es.poll_resize()
    for event in resize_events:
        if event.type == "VIDEORESIZE":
            new_size = event.payload["size"]
            
    # Process all other events
    events = es.poll()
    for event in events:
        if event.type == "SPACE":
            toggle_pause()
            
    # Access raw events for UI widgets
    raw = es.last_raw()
    toggle_button.update(raw)

Notes:
- Headless mode: Returns empty event lists
- Headless requires SDL_VIDEODRIVER=dummy environment variable
- Events are consumed on poll (not replayable)
- last_raw() provides pygame events for legacy widget code
"""

from __future__ import annotations
from typing import List
import pygame

from .state import SimEvent


class EventSource:
    """Encapsulates pygame.event.get() and normalizes to SimEvent.
    
    - Headless: Always returns []
    - poll_resize(): Only VIDEORESIZE events (consumes them)
    - poll(): All other events (consumes them)
    - last_raw(): Last raw events read (for UI widgets)
    """
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._last_raw: List[pygame.event.Event] = []

    def poll_resize(self) -> List[SimEvent]:
        if self.headless:
            self._last_raw = []
            return []
        raw = pygame.event.get(pygame.VIDEORESIZE)
        self._last_raw = raw
        out: List[SimEvent] = []
        for e in raw:
            size = getattr(e, "size", None)
            out.append(SimEvent("VIDEORESIZE", {"size": size}))
        return out

    def poll(self) -> List[SimEvent]:
        if self.headless:
            self._last_raw = []
            return []
        raw = pygame.event.get()  # alle verbleibenden Events
        self._last_raw = raw
        out: List[SimEvent] = []
        for e in raw:
            t = e.type
            if t == pygame.QUIT:
                out.append(SimEvent("QUIT"))
            elif t == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    out.append(SimEvent("SPACE"))
                elif e.key == pygame.K_ESCAPE:
                    out.append(SimEvent("ESC"))
                elif e.key == pygame.K_t:
                    out.append(SimEvent("TOGGLE_TRACKS"))
                elif getattr(e, "unicode", "") and e.unicode.isalnum():
                    out.append(SimEvent("KEY_CHAR", {"char": e.unicode}))
                elif e.key == pygame.K_BACKSPACE:
                    out.append(SimEvent("BACKSPACE"))
            elif t == pygame.MOUSEBUTTONDOWN:
                out.append(SimEvent("MOUSE_DOWN", {
                    "pos": getattr(e, "pos", (0, 0)),
                    "button": getattr(e, "button", 1),
                }))
            # Other events are intentionally ignored
        return out

    def last_raw(self) -> List[pygame.event.Event]:
        return list(self._last_raw)

__all__ = ["EventSource"]
