# crazycar/car/timeutil.py
"""Zeit-Helfer (optionale pygame-Abhängigkeit).

- delay_ms(ms): wartet ~ms Millisekunden.
  * bevorzugt pygame-Clock (kompatibel zu deinem Original)
  * Fallback auf time.sleep(), wenn pygame fehlt/nicht init
"""

from __future__ import annotations
from typing import Final

# weiche Abhängigkeit: pygame nur importieren, wenn vorhanden
try:
    import pygame  # type: ignore
    _HAVE_PYGAME = True
except Exception:
    pygame = None  # type: ignore
    _HAVE_PYGAME = False

import time

# Ziel-Tickrate (nur relevant für pygame-Loop)
_PYGAME_TICKS_PER_SEC: Final[int] = 100


def _delay_ms_pygame(ms: int) -> None:
    """Warten per pygame.Clock – wie im Originalcode."""
    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < ms:
        # Begrenze Loop auf ~100 Hz, damit CPU nicht glüht
        clock.tick(_PYGAME_TICKS_PER_SEC)


def _delay_ms_sleep(ms: int) -> None:
    """Fallback ohne pygame: einfache Sleep-Schleife."""
    target = time.perf_counter() + (ms / 1000.0)
    # Eine kurze Sleepschleife ist effizienter als Busy-Wait
    while True:
        now = time.perf_counter()
        if now >= target:
            break
        # kleine Scheibe schlafen; passt sich Ziel an
        remaining = target - now
        time.sleep(min(remaining, 0.005))  # max 5ms Sleep-Granularität


def delay_ms(ms: int) -> None:
    """Wartet ca. ms Millisekunden.

    Nutzt pygame, wenn importiert *und* initialisiert; sonst Fallback auf time.sleep().
    """
    if ms <= 0:
        return

    if _HAVE_PYGAME:
        # pygame muss initialisiert sein (sonst get_ticks() == 0 in manchen Umgebungen)
        try:
            if pygame.get_init():
                _delay_ms_pygame(ms)
                return
        except Exception:
            pass

    _delay_ms_sleep(ms)


__all__ = ["delay_ms"]
