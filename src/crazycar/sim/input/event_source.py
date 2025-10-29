# src/crazycar/sim/input/event_source.py
# Aufgabe:
# - Einheitliche Schnittstelle, um Events aus pygame zu beziehen.
# - Optionaler FakeEventSource für Tests (headless), ohne pygame-Fenster.
# Hinweise:
# - Keine pygame-Initialisierung auf Modulebene!
# - Event-Factories helfen beim Erzeugen synthetischer Events in Tests.

from __future__ import annotations
from typing import List, Iterable, Optional
import pygame

# In pygame ist der Event-Typ direkt konstruierbar:
Event = pygame.event.Event  # Alias für Typannotationen


class PygameEventSource:
    """Dünner Wrapper um pygame.event.* für die Hauptschleife."""

    def poll(self) -> List[Event]:
        """Alle aktuell anstehenden Events holen."""
        return pygame.event.get()

    def poll_resize(self) -> List[Event]:
        """Nur VIDEORESIZE-Events holen (praktisch für getrennte Behandlung)."""
        return pygame.event.get(pygame.VIDEORESIZE)

    def pump(self) -> None:
        """Event-Queue verarbeiten (z. B. im Pause-Loop sinnvoll)."""
        pygame.event.pump()

    def clear(self) -> None:
        """Alle Events verwerfen (in seltenen Recovery-Fällen nützlich)."""
        pygame.event.clear()


class FakeEventSource:
    """
    Fake-Quelle für Tests/Headless-Betrieb.
    - Events werden vorab eingereiht; poll() liefert sie FIFO aus.
    - Unabhängige Queue für VIDEORESIZE, damit Tests die Loop-Logik nachbilden können.
    """

    def __init__(self, initial: Optional[Iterable[Event]] = None):
        self._queue: List[Event] = list(initial) if initial else []
        self._resize_queue: List[Event] = []

    # --------------------------
    # API kompatibel zu PygameEventSource
    # --------------------------
    def poll(self) -> List[Event]:
        evts = self._queue[:]
        self._queue.clear()
        return evts

    def poll_resize(self) -> List[Event]:
        evts = self._resize_queue[:]
        self._resize_queue.clear()
        return evts

    def pump(self) -> None:
        # Im Fake keine Aktion nötig.
        pass

    def clear(self) -> None:
        self._queue.clear()
        self._resize_queue.clear()

    # --------------------------
    # Helpers für Tests
    # --------------------------
    def push(self, *events: Event) -> None:
        """Beliebige Events (außer Resize) hinten anstellen."""
        for e in events:
            if e.type == pygame.VIDEORESIZE:
                # Sicherstellen, dass Resize-Events separat behandelt werden
                self._resize_queue.append(e)
            else:
                self._queue.append(e)

    def push_resize(self, size: tuple[int, int]) -> None:
        """Komfort: direkt ein VIDEORESIZE-Event einstellen."""
        w, h = size
        self._resize_queue.append(videoresize(w, h))


# --------------------------
# Event-Fabriken (praktisch für Tests)
# --------------------------

def keydown(key: int, unicode: str = "") -> Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "unicode": unicode})

def keyup(key: int) -> Event:
    return pygame.event.Event(pygame.KEYUP, {"key": key})

def mousebuttondown(pos: tuple[int, int], button: int = 1) -> Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button})

def mousebuttonup(pos: tuple[int, int], button: int = 1) -> Event:
    return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button})

def quit_event() -> Event:
    return pygame.event.Event(pygame.QUIT, {})

def videoresize(w: int, h: int) -> Event:
    # pygame erwartet size + w + h Felder beim VIDEORESIZE
    return pygame.event.Event(pygame.VIDEORESIZE, {"size": (w, h), "w": w, "h": h})


__all__ = [
    "Event",
    "PygameEventSource",
    "FakeEventSource",
    "keydown",
    "keyup",
    "mousebuttondown",
    "mousebuttonup",
    "quit_event",
    "videoresize",
]
