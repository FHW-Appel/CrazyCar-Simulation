# =============================================================================
# crazycar/sim/snapshot_service.py  —  Artefakte: Snapshot & Recovery
# -----------------------------------------------------------------------------
# Aufgabe:
# - Speichert/liest Momentaufnahmen (Pickle) der Fahrzeugzustände.
# - Nutzt car.serialization.serialize_car(...) zum stabilen Datenformat.
#
# Öffentliche API:
# - moment_aufnahmen(cars: list[Car]) -> None
# - moment_recover(file_text_date: str) -> list[Car]
#
# Format/Ort:
# - Dateien unter sim/MomentAufnahme/Momentaufnahme_<cnt>_<stamp>.pkl
# - Position wird skaliert gespeichert (f_scale), beim Laden wieder hochskaliert.
#
# Hinweise:
# - IO-Fehler abfangen, Pfade via os.path sicher bilden; Ordner bei Bedarf anlegen.
# =============================================================================

from __future__ import annotations
import os
import datetime
import logging
import pickle
from typing import List, Optional

from ..car.model import Car, f
from ..car.serialization import serialize_car

log = logging.getLogger("crazycar.sim.snapshot")

def moment_aufnahmen(cars: List[Car],
                     base_dir: Optional[str] = None,
                     now: Optional[datetime.datetime] = None) -> str:
    """
    Speichert eine Momentaufnahme der übergebenen Fahrzeuge als .pkl.
    Rückgabe: vollständiger Dateipfad.
    """
    if now is None:
        now = datetime.datetime.now()
    count = 1
    date = now.strftime("%d%M%S")
    doc_text = f"Momentaufnahme_{count}_{date}.pkl"

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    file_path = os.path.join(base_dir, "MomentAufnahme", doc_text)

    data_to_serialize = [serialize_car(acar, f_scale=f) for acar in cars]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as auf:
        pickle.dump(data_to_serialize, auf)
    log.info("Momentaufnahme geschrieben: %s", file_path)
    return file_path


def moment_recover(file_text_date: str,
                   base_dir: Optional[str] = None) -> List[Car]:
    """
    Lädt eine Momentaufnahme anhand des Datums-/Suffix-Strings (file_text_date).
    Rückgabe: Liste rekonstruierter Cars.
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

    log.info("Momentaufnahme geladen: %s  (cars=%d)", file_path, len(recover_cars))
    return recover_cars
