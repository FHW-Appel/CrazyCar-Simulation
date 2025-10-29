# src/crazycar/sim/state.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, Literal

DialogTarget = Literal["python", "c"]

@dataclass
class SimState:
    """
    Zentraler, veränderlicher Zustand der Simulation.
    - Hält Flags wie Pause/Drawtracks/Modus
    - Hält Fenstergröße (für Resize)
    - Bietet kleine, side-effect-freie Helper für UI-/Loop-Logik
    """

    # Basis
    window_size: Tuple[int, int]

    # Laufzeit
    current_generation: int = 0
    tick_count: int = 0
    max_ticks: Optional[int] = None  # optionales Limit (nützlich für Tests)

    # UI/Flags
    paused: bool = False
    drawtracks: bool = False
    mode_python: bool = True  # True=python_regelung, False=c_regelung
    show_dialog: bool = False
    pending_switch: Optional[DialogTarget] = None  # "python" oder "c", solange der Dialog offen ist

    # Eingabetext (z. B. Dateitoken für Recover)
    file_text: str = ""

    # Optionale Overrides (z. B. Tests ohne echte Toggles)
    sensor_status_override: Optional[int] = None
    collision_status_override: Optional[int] = None

    # -----------------------
    # Convenience-Methoden
    # -----------------------
    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def set_paused(self, value: bool) -> None:
        self.paused = bool(value)

    def toggle_drawtracks(self) -> None:
        self.drawtracks = not self.drawtracks

    def set_window_size(self, size: Tuple[int, int]) -> None:
        self.window_size = (int(size[0]), int(size[1]))

    def next_generation(self) -> int:
        self.current_generation += 1
        return self.current_generation

    def inc_tick(self) -> int:
        self.tick_count += 1
        return self.tick_count

    # -----------------------
    # Modus / Dialogsteuerung
    # -----------------------
    def mode_label(self) -> str:
        """UI-Label passend zu deinem bisherigen Code."""
        return "python_regelung" if self.mode_python else "c_regelung"

    def set_mode_python(self) -> None:
        self.mode_python = True

    def set_mode_c(self) -> None:
        self.mode_python = False

    def toggle_mode(self) -> None:
        self.mode_python = not self.mode_python

    def open_switch_dialog(self, target: DialogTarget) -> None:
        """Dialog öffnen, Ziel vormerken (z. B. durch Button-Klick)."""
        self.show_dialog = True
        self.pending_switch = target

    def confirm_switch(self) -> None:
        """Dialog bestätigt: Modus wechseln und Dialog schließen."""
        if self.pending_switch == "python":
            self.set_mode_python()
        elif self.pending_switch == "c":
            self.set_mode_c()
        self.pending_switch = None
        self.show_dialog = False

    def cancel_switch(self) -> None:
        """Dialog abgebrochen: nichts ändern, nur schließen."""
        self.pending_switch = None
        self.show_dialog = False

    # -----------------------
    # Texteingabe-Helfer
    # -----------------------
    def add_char(self, ch: str) -> None:
        """Ein Zeichen anhängen (keine Filterung erzwungen)."""
        if ch:
            self.file_text += ch

    def backspace(self) -> None:
        self.file_text = self.file_text[:-1] if self.file_text else self.file_text

    # -----------------------
    # Status-Overrides (Tests)
    # -----------------------
    def set_sensor_status(self, value: Optional[int]) -> None:
        self.sensor_status_override = value

    def set_collision_status(self, value: Optional[int]) -> None:
        self.collision_status_override = value

    def get_sensor_status(self, default: int = 1) -> int:
        return self.sensor_status_override if self.sensor_status_override is not None else default

    def get_collision_status(self, default: int = 1) -> int:
        return self.collision_status_override if self.collision_status_override is not None else default
