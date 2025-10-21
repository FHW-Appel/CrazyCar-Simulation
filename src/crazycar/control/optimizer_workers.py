# src/crazycar/control/optimizer_workers.py
from __future__ import annotations
"""
Prozess-Lifecycle für den Optimizer.

Aufgaben:
- Einheitliche Erstellung von Child-Prozessen (Windows-sicher via 'spawn')
- Robustes Cleanup inkl. Hard-Kill-Fallback (taskkill/SIGKILL)
- Kleine IPC-Helfer (Queue ohne Blockieren lesen)

Wichtig:
Dieses Modul konfiguriert KEINE Logger-Handler. Die Applikation (z. B. main.py)
soll das Logging konfigurieren (Level/Formatter/Handler).
"""
import logging
import os
import platform
import subprocess
import multiprocessing as mp
import queue as _queue
from typing import Callable, Optional, Any

__all__ = [
    "spawn_worker",
    "cleanup_worker",
    "kill_process_hard",
    # optionale Helfer (nützlich für API/Tests)
    "ctx",
    "make_queue",
    "qget_nowait",
    "is_running",
    "safe_join",
]

# Modul-Logger
log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Kontext & IPC-Helfer
# -----------------------------------------------------------------------------
def ctx(force_spawn: bool = True) -> mp.context.BaseContext:
    """
    Liefert einen Multiprocessing-Kontext.
    - Unter Windows ist 'spawn' Pflicht.
    - Unter POSIX ist 'fork' Standard, aber 'spawn' ist für Pygame/GUI/SDL oftmals robuster.
      Darum nutzen wir per Default force_spawn=True für konsistentes Verhalten.
    """
    if force_spawn:
        try:
            return mp.get_context("spawn")
        except ValueError:
            # Fallback (sollte praktisch nie auftreten)
            return mp.get_context()
    return mp.get_context()


def make_queue(force_spawn: bool = True) -> Any:
    """
    Erstellt eine Queue aus einem passenden Kontext (standardmäßig 'spawn').
    Rückgabe-Typ ist absichtlich 'Any', um Typkonflikte mit mp.queues zu vermeiden.
    """
    q = ctx(force_spawn).Queue()
    log.debug("IPC-Queue erstellt (spawn=%s)", force_spawn)
    return q


def qget_nowait(q) -> Any | None:
    """
    Nicht-blockierendes Lesen aus einer Queue.
    Gibt None zurück, wenn die Queue leer ist oder ein Fehler auftritt.
    """
    try:
        return q.get_nowait()
    except _queue.Empty:
        return None
    except Exception as e:
        log.debug("Queue nowait read ignorierter Fehler: %r", e)
        return None


def is_running(p: Optional[mp.Process]) -> bool:
    """True, wenn der Prozess existiert und noch lebt."""
    return bool(p and p.is_alive())


def safe_join(p: Optional[mp.Process], timeout: float | None = None) -> None:
    """
    Join mit Logging; wirft keine Exceptions weiter.
    Verhindert, dass Aufräum-Routinen selbst hängen bleiben.
    """
    if p is None:
        return
    try:
        log.debug("Join auf Prozess pid=%s timeout=%s", getattr(p, "pid", None), timeout)
        p.join(timeout=timeout)
    except Exception as e:
        log.warning("Join fehlgeschlagen (pid=%s): %r", getattr(p, "pid", None), e)


# -----------------------------------------------------------------------------
# Prozess-Erzeugung
# -----------------------------------------------------------------------------
def spawn_worker(
    target: Callable,
    *,
    args=(),
    kwargs=None,
    daemon: bool = True
) -> mp.Process:
    """
    Zentrale Stelle zum Starten eines (Test-)Prozesses.
    Über diese Naht kann pytest/mocking den Start leicht patchen.

    Args:
        target: Child-Entry-Point (Callable muss top-level picklable sein)
        args:   Positional args
        kwargs: Keyword args
        daemon: Daemon-Flag (True → beendet sich automatisch mit dem Parent)

    Returns:
        Multiprocessing-Process (bereits gestartet).
    """
    if kwargs is None:
        kwargs = {}

    # Für robuste GUI/SDL/NEAT-Kombinationen nutzen wir systematisch 'spawn'
    C = ctx(True)  # force_spawn=True
    p = C.Process(target=target, args=args, kwargs=kwargs, daemon=daemon)

    log.info(
        "Starte Child-Prozess: target=%s daemon=%s start_method=spawn",
        getattr(target, "__name__", str(target)),
        daemon,
    )
    p.start()
    log.debug("Child gestartet: pid=%s alive=%s", p.pid, p.is_alive())

    return p


# -----------------------------------------------------------------------------
# Harte Terminierung (Windows/Posix)
# -----------------------------------------------------------------------------
def kill_process_hard(pid: int) -> None:
    """
    Plattformgerechtes hartes Beenden.
    - Windows: taskkill /F /PID <pid>
    - POSIX:   SIGKILL (9)
    Fehler werden bewusst geschluckt – Cleanup soll nie hängen.
    """
    try:
        if platform.system().lower().startswith("win"):
            log.warning("Hard-Kill (Windows taskkill) für pid=%s", pid)
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            log.warning("Hard-Kill (POSIX SIGKILL) für pid=%s", pid)
            os.kill(pid, 9)  # SIGKILL
    except Exception as e:
        # Keine harten Fehler im Cleanup – nur loggen
        log.debug("Hard-Kill ignorierter Fehler (pid=%s): %r", pid, e)


# -----------------------------------------------------------------------------
# Cleanup / Shutdown
# -----------------------------------------------------------------------------
def cleanup_worker(p: Optional[mp.Process], timeout: float = 2.0) -> None:
    """
    Robustes Aufräumen eines Prozesses:
        terminate() → join(timeout) → falls noch alive → harter Kill → join(timeout)

    Niemals Exceptions nach außen werfen; der Aufrufer soll hier nie hängen bleiben.
    """
    if p is None:
        log.debug("cleanup_worker: kein Prozessobjekt (None) – nichts zu tun.")
        return

    try:
        pid = getattr(p, "pid", None)
        if is_running(p):
            log.info("Cleanup: terminate() pid=%s", pid)
            try:
                p.terminate()
            except Exception as e:
                log.debug("terminate() ignorierter Fehler (pid=%s): %r", pid, e)

        safe_join(p, timeout=timeout)

        if is_running(p):
            log.warning("Cleanup: Prozess lebt noch nach terminate+join → Hard-Kill pid=%s", pid)
            try:
                kill_process_hard(pid)
            finally:
                safe_join(p, timeout=timeout)

        # Exitcode protokollieren (kann None sein, wenn nie gestartet)
        log.debug("Cleanup abgeschlossen: pid=%s exitcode=%s", pid, getattr(p, "exitcode", None))

    except Exception as e:
        # Niemals Exceptions weiterwerfen – Cleanup soll unkritisch sein.
        log.debug("cleanup_worker: ignorierter Fehler: %r", e)
