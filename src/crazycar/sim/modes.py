# src/crazycar/sim/modes.py
# Aufgabe:
# - Zentraler Umschalter zwischen Python- und C-Regelung.
# - Bietet sowohl eine Enum-API (ControlMode) als auch eine bool-basierte API
#   für rückwärtskompatible Aufrufe aus bestehendem Code (mode_python: bool).
# - Keine Abhängigkeit zu simulation.py (um Import-Zyklen zu vermeiden).

from __future__ import annotations
from enum import Enum
from typing import List
import logging

from ..control.interface import Interface
from ..car.model import Car

log = logging.getLogger("crazycar.sim.modes")
if not logging.getLogger().handlers:
    import os
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.modes] %(message)s",
    )

# UI-Texte (wie in deiner simulation.py verwendet)
LABEL_C = "c_regelung"
LABEL_PY = "python_regelung"


class ControlMode(Enum):
    """Expliziter Modus statt reinem Bool – erleichtert Lesbarkeit & Tests."""
    PYTHON = "python"
    C = "c"

    @staticmethod
    def from_bool(mode_python: bool) -> "ControlMode":
        return ControlMode.PYTHON if mode_python else ControlMode.C

    def to_bool(self) -> bool:
        return self is ControlMode.PYTHON

    def ui_label(self) -> str:
        return LABEL_PY if self is ControlMode.PYTHON else LABEL_C


def apply_control(mode_python: bool, cars: List[Car]) -> None:
    """
    Rückwärtskompatible API (bool): True = Python, False = C
    """
    apply_control_mode(ControlMode.from_bool(mode_python), cars)


def apply_control_mode(mode: ControlMode, cars: List[Car]) -> None:
    """
    Neue, explizite API (Enum).
    Ruft die entsprechende Regelungsfunktion aus Interface auf.
    """
    try:
        if mode is ControlMode.PYTHON:
            Interface.regelungtechnik_python(cars)
        else:
            Interface.regelungtechnik_c(cars)
    except Exception:
        # Schutz: Regelung darf die Loop nicht crashen lassen.
        log.exception("Fehler in apply_control_mode(%s)", mode.value)


def toggle_bool(mode_python: bool) -> bool:
    """Hilfsfunktion: toggelt den bool-Modus."""
    return not mode_python


def next_mode(mode: ControlMode) -> ControlMode:
    """Hilfsfunktion: wechselt zyklisch zwischen den Modi (nützlich für Buttons)."""
    return ControlMode.C if mode is ControlMode.PYTHON else ControlMode.PYTHON


def label_for_bool(mode_python: bool) -> str:
    """UI-Label zum aktuellen Modus (kompatibel zu bisherigen Button-Texten)."""
    return LABEL_PY if mode_python else LABEL_C


__all__ = [
    "ControlMode",
    "apply_control",
    "apply_control_mode",
    "toggle_bool",
    "next_mode",
    "label_for_bool",
    "LABEL_C",
    "LABEL_PY",
]
