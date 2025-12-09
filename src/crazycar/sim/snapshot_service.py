"""Snapshot & Recovery Service - Save/Load Vehicle State.

Implements snapshot system for debugging and replay:

Functions:
- moment_aufnahmen(): Saves Car states as pickle file
- moment_recover(): Loads Car states from pickle file

File Format:
- Path: sim/MomentAufnahme/Momentaufnahme_<count>_<timestamp>.pkl
- Content: List of serialized Car dicts (via serialize_car)
- Scaling: Positions stored normalized with f_scale

Workflow:
1. UI button 'Aufnahme' → moment_aufnahmen(cars)
2. Pickle file created with current timestamp
3. UI button 'Wiederherstellen' → moment_recover(filename)
4. Cars reconstructed with deserialize_car()

Constants:
- DEFAULT_SNAPSHOT_INDEX: 1 (counter for snapshot numbering)
- SNAPSHOT_SUBDIR: "MomentAufnahme" (folder name)

See Also:
- serialization.py: serialize_car(), deserialize_car()
- modes.py: ModeManager (trigger snapshot/recover)
"""

from __future__ import annotations
import os
import datetime
import logging
import pickle
from typing import List, Optional

from ..car.model import Car, f
from ..car.serialization import serialize_car

# Constants for snapshot system
DEFAULT_SNAPSHOT_INDEX = 1  # Start counter for numbering
SNAPSHOT_SUBDIR = "MomentAufnahme"  # Subdirectory for snapshots

log = logging.getLogger("crazycar.sim.snapshot")

def moment_aufnahmen(cars: List[Car],
                     base_dir: Optional[str] = None,
                     now: Optional[datetime.datetime] = None) -> str:
    """
    Save a snapshot of the given vehicles as .pkl file.
    Returns: full file path.
    """
    if now is None:
        now = datetime.datetime.now()
    count = DEFAULT_SNAPSHOT_INDEX
    date = now.strftime("%d%M%S")
    doc_text = f"Momentaufnahme_{count}_{date}.pkl"

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    file_path = os.path.join(base_dir, SNAPSHOT_SUBDIR, doc_text)

    data_to_serialize = [serialize_car(acar, f_scale=f) for acar in cars]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as auf:
        pickle.dump(data_to_serialize, auf)
    log.info("Snapshot written: %s", file_path)
    return file_path


def moment_recover(file_text_date: str,
                   base_dir: Optional[str] = None) -> List[Car]:
    """
    Loads a snapshot by date/suffix string (file_text_date).
    Returns: List of reconstructed Cars.
    """
    if not file_text_date:
        file_text_date = "p1"

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    count = 1
    doc_text = f"Momentaufnahme_{count}_{file_text_date}.pkl"
    file_path = os.path.join(base_dir, "MomentAufnahme", doc_text)

    with open(file_path, "rb") as ein:
        deserialized_data = pickle.load(ein)

    recover_cars: List[Car] = []
    for data in deserialized_data:
        position_x = data["position"][0] * f
        position_y = data["position"][1] * f
        recover_cars.append(
            Car(
                [position_x, position_y],
                data["carangle"],
                data["speed"],
                data["speed_set"],
                data["radars"],
                data["analog_wert_list"],
                data["distance"],
                data["time"],
            )
        )

    log.info("Snapshot loaded: %s  (cars=%d)", file_path, len(recover_cars))
    return recover_cars
