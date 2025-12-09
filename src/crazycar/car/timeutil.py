# crazycar/car/timeutil.py
"""Time helpers (optional pygame dependency).

- delay_ms(ms): waits approximately ms milliseconds.
  * prefers pygame Clock (compatible with original)
  * fallback to time.sleep() if pygame missing/not initialized
"""

from __future__ import annotations
from typing import Final

# Soft dependency: only import pygame if available
try:
    import pygame  # type: ignore
    _HAVE_PYGAME = True
except Exception:
    pygame = None  # type: ignore
    _HAVE_PYGAME = False

import time

# Target tick rate (only relevant for pygame loop)
_PYGAME_TICKS_PER_SEC: Final[int] = 100


def _delay_ms_pygame(ms: int) -> None:
    """Wait via pygame.Clock – as in original code."""
    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < ms:
        # Limit loop to ~100 Hz to prevent CPU from burning
        clock.tick(_PYGAME_TICKS_PER_SEC)


def _delay_ms_sleep(ms: int) -> None:
    """Fallback without pygame: simple sleep loop."""
    target = time.perf_counter() + (ms / 1000.0)
    # A short sleep loop is more efficient than busy-wait
    while True:
        now = time.perf_counter()
        if now >= target:
            break
        # Sleep small slice; adapts to target
        remaining = target - now
        time.sleep(min(remaining, 0.005))  # Max 5ms sleep granularity


def delay_ms(ms: int) -> None:
    """Wait approximately ms milliseconds.

    Uses pygame if imported *and* initialized; otherwise fallback to time.sleep().
    """
    if ms <= 0:
        return

    if _HAVE_PYGAME:
        # pygame must be initialized (otherwise get_ticks() == 0 in some environments)
        try:
            if pygame.get_init():
                _delay_ms_pygame(ms)
                return
        except Exception:
            pass

    _delay_ms_sleep(ms)


__all__ = ["delay_ms"]
