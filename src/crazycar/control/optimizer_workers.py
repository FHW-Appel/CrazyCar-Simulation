"""Optimizer Workers - Process lifecycle management.

Responsibilities:
- Uniform child process creation (Windows-safe via 'spawn')
- Robust cleanup with hard-kill fallback (taskkill/SIGKILL)
- IPC helpers (Queue non-blocking reads)
- Cross-platform process management

Public API:
- spawn_worker(
      target: Callable,
      args: tuple = (),
      force_spawn: bool = True
  ) -> mp.Process:
      Create and start a child process
      Uses 'spawn' context for cross-platform safety
      
- cleanup_worker(
      proc: mp.Process,
      timeout: float = 5.0,
      force: bool = True
  ) -> None:
      Clean up child process gracefully
      Hard-kill if timeout exceeded
      
- kill_process_hard(proc: mp.Process) -> None:
      Force-terminate process (taskkill on Windows, SIGKILL on Unix)

Helpers:
- ctx(force_spawn: bool = True) -> mp.context.BaseContext:
      Get multiprocessing context ('spawn' for consistency)
      
- make_queue(force_spawn: bool = True) -> Queue:
      Create Queue from spawn context
      
- qget_nowait(q: Queue, default=None) -> Any:
      Non-blocking queue read with default fallback
      
- is_running(proc: mp.Process) -> bool:
      Check if process is still alive
      
- safe_join(proc: mp.Process, timeout: float) -> bool:
      Join with timeout, returns success status

Usage:
    # Spawn worker
    proc = spawn_worker(target_function, args=(arg1, arg2))
    
    # Clean up when done
    cleanup_worker(proc, timeout=5.0, force=True)
    
    # Non-blocking queue read
    status = qget_nowait(queue, default='unknown')

Notes:
- Does NOT configure logging (app responsibility)
- Uses 'spawn' for Windows/Pygame/SDL compatibility
- Hard-kill uses taskkill /F /T on Windows
- Hard-kill uses SIGKILL on Unix systems
- Ensures no orphaned child processes
"""
# src/crazycar/control/optimizer_workers.py
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
    # Optional helpers (useful for API/tests)
    "ctx",
    "make_queue",
    "qget_nowait",
    "is_running",
    "safe_join",
]

# Module logger
log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Context & IPC helpers
# -----------------------------------------------------------------------------
def ctx(force_spawn: bool = True) -> mp.context.BaseContext:
    """
    Returns a multiprocessing context.
    - On Windows, 'spawn' is required.
    - On POSIX, 'fork' is default, but 'spawn' is often more robust for Pygame/GUI/SDL.
      Therefore we use force_spawn=True by default for consistent behavior.
    """
    if force_spawn:
        try:
            return mp.get_context("spawn")
        except ValueError:
            # Fallback (should practically never occur)
            return mp.get_context()
    return mp.get_context()


def make_queue(force_spawn: bool = True) -> Any:
    """
    Creates a queue from a suitable context (default 'spawn').
    Return type is intentionally 'Any' to avoid type conflicts with mp.queues.
    """
    q = ctx(force_spawn).Queue()
    log.debug("IPC queue created (spawn=%s)", force_spawn)
    return q


def qget_nowait(q) -> Any | None:
    """
    Non-blocking read from a queue.
    Returns None if queue is empty or error occurs.
    """
    try:
        return q.get_nowait()
    except _queue.Empty:
        return None
    except Exception as e:
        log.debug("Queue nowait read ignored error: %r", e)
        return None


def is_running(p: Optional[mp.Process]) -> bool:
    """True if the process exists and is still alive."""
    return bool(p and p.is_alive())


def safe_join(p: Optional[mp.Process], timeout: float | None = None) -> None:
    """
    Join with logging; doesn't propagate exceptions.
    Prevents cleanup routines from hanging.
    """
    if p is None:
        return
    try:
        log.debug("Join on process pid=%s timeout=%s", getattr(p, "pid", None), timeout)
        p.join(timeout=timeout)
    except Exception as e:
        log.warning("Join failed (pid=%s): %r", getattr(p, "pid", None), e)


# -----------------------------------------------------------------------------
# Process creation
# -----------------------------------------------------------------------------
def spawn_worker(
    target: Callable,
    *,
    args=(),
    kwargs=None,
    daemon: bool = True
) -> mp.Process:
    """
    Central place for starting a (test) process.
    Pytest/mocking can easily patch the start via this seam.

    Args:
        target: Child entry point (Callable must be top-level picklable)
        args:   Positional args
        kwargs: Keyword args
        daemon: Daemon flag (True → terminates automatically with parent)

    Returns:
        Multiprocessing process (already started).
    """
    if kwargs is None:
        kwargs = {}

    # For robust GUI/SDL/NEAT combinations we systematically use 'spawn'
    C = ctx(True)  # force_spawn=True
    p = C.Process(target=target, args=args, kwargs=kwargs, daemon=daemon)

    log.info(
        "Starting child process: target=%s daemon=%s start_method=spawn",
        getattr(target, "__name__", str(target)),
        daemon,
    )
    p.start()
    log.debug("Child started: pid=%s alive=%s", p.pid, p.is_alive())

    return p


# -----------------------------------------------------------------------------
# Hard termination (Windows/Posix)
# -----------------------------------------------------------------------------
def kill_process_hard(pid: int) -> None:
    """
    Platform-appropriate hard termination.
    - Windows: taskkill /F /PID <pid>
    - POSIX:   SIGKILL (9)
    Errors are intentionally swallowed – cleanup should never hang.
    """
    try:
        if platform.system().lower().startswith("win"):
            log.warning("Hard-Kill (Windows taskkill) for pid=%s", pid)
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            log.warning("Hard-Kill (POSIX SIGKILL) for pid=%s", pid)
            os.kill(pid, 9)  # SIGKILL
    except Exception as e:
        # No hard errors in cleanup – only log
        log.debug("Hard-Kill ignored error (pid=%s): %r", pid, e)


# -----------------------------------------------------------------------------
# Cleanup / Shutdown
# -----------------------------------------------------------------------------
def cleanup_worker(p: Optional[mp.Process], timeout: float = 2.0) -> None:
    """
    Robust cleanup of a process:
        terminate() → join(timeout) → if still alive → hard kill → join(timeout)

    Never throw exceptions outward; caller should never hang here.
    """
    if p is None:
        log.debug("cleanup_worker: no process object (None) – nothing to do.")
        return

    try:
        pid = getattr(p, "pid", None)
        if is_running(p):
            log.info("Cleanup: terminate() pid=%s", pid)
            try:
                p.terminate()
            except Exception as e:
                log.debug("terminate() ignored error (pid=%s): %r", pid, e)

        safe_join(p, timeout=timeout)

        if is_running(p):
            log.warning("Cleanup: Process still alive after terminate+join → Hard-Kill pid=%s", pid)
            try:
                kill_process_hard(pid)
            finally:
                safe_join(p, timeout=timeout)

        # Log exit code (can be None if never started)
        log.debug("Cleanup complete: pid=%s exitcode=%s", pid, getattr(p, "exitcode", None))

    except Exception as e:
        # Never propagate exceptions – cleanup should be uncritical.
        log.debug("cleanup_worker: ignored error: %r", e)
