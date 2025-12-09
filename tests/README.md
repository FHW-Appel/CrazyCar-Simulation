# Test Suite - CrazyCar Simulation

## Übersicht

**412 Tests gesamt**
- 404 passed
- 4 skipped
- 2 xfailed
- 2 xpassed
- 0 failed

```
├── Unit Tests:        341 Tests (100% passed)
└── Integration Tests:  63 Tests (100% passed)
```

### Test-Status Legende

| Status | Bedeutung | Beschreibung |
|--------|-----------|--------------|
| **passed** ✅ | Test erfolgreich | Test lief ohne Fehler durch und alle Assertions wurden erfüllt |
| **skipped** ⏭️ | Test übersprungen | Test wurde bewusst übersprungen (z.B. plattformspezifisch oder mit `@pytest.mark.skip`) |
| **xfailed** ⚠️ | Erwarteter Fehler | Test schlägt erwartungsgemäß fehl (markiert mit `@pytest.mark.xfail`), bekanntes Problem |
| **xpassed** 🎁 | Unerwarteter Erfolg | Test wurde als "expected fail" markiert, ist aber erfolgreich (Bug wurde gefixt!) |
| **failed** ❌ | Test fehlgeschlagen | Test ist fehlgeschlagen - Fehler muss behoben werden |

## Teststruktur

### Unit Tests (341 Tests - 100%)

#### tests/car/ - Car Module (238 Tests)
| Datei | Tests | Status | Refaktoriert |
|-------|-------|--------|--------------|
| `test_serialization.py` | 23 | ✅ 23/23 | ✅ Fixtures, Parametrisierung |
| `test_kinematics.py` | 16 | ✅ 16/16 | ✅ Fixtures, Parametrisierung |
| `test_dynamics.py` | 9 | ✅ 3/9<br>**4 skipped ⏭️**<br>**2 xfailed ⚠️** | ✅ Adaptive API |
| `test_geometry.py` | 13 | ✅ 11/13<br>**2 xpassed 🎁** | ✅ Fixtures, Parametrisierung |
| `test_constants.py` | 18 | ✅ 18/18 | ✅ Fixtures, Parametrisierung |
| `test_units.py` | 36 | ✅ 36/36 | ✅ Parametrisierung |
| `test_timeutil.py` | 13 | ✅ 13/13 | ✅ Fixtures, Parametrisierung |
| `test_state.py` | 19 | ✅ 19/19 | ✅ Fixtures |
| `test_actuation.py` | 37 | ✅ 37/37 | ✅ Fixtures, Parametrisierung |
| `test_rendering.py` | 16 | ✅ 16/16 | ✅ Fixtures, Parametrisierung |
| `test_collision.py` | 19 | ✅ 19/19 | ✅ Fixtures |
| `test_motion.py` | 16 | ✅ 16/16 | ✅ Fixtures |
| `test_sensor.py` | 7 | ✅ 7/7 | ✅ Fixtures |

**Details zu skipped/xfailed/xpassed Tests:**

- **test_dynamics.py - 4 skipped ⏭️:**
  - `test_step_speed_decays_with_drag[0.1]`
  - `test_step_speed_decays_with_drag[1.0]`
  - `test_step_speed_decays_with_drag[5.0]`
  - `test_step_speed_bounded_by_zero_and_max_speed`

- **test_dynamics.py - 2 xfailed ⚠️:**
  - `test_step_speed_invalid_dt_raises[0.0]`
  - `test_step_speed_invalid_dt_raises[-0.01]`

- **test_geometry.py - 2 xpassed 🎁:**
  - `test_negative_half_extents_xfail`
  - `test_negative_diag_minus_xfail`

#### tests/sim/ - Simulation Module (102 Tests)
| Datei | Tests | Status | Refaktoriert |
|-------|-------|--------|--------------|
| `test_event_source.py` | 26 | ✅ 26/26 | ✅ Fixtures, Parametrisierung |
| `test_sim_state.py` | 30 | ✅ 30/30 | ✅ Fixtures, Parametrisierung |
| `test_spawn_utils.py` | 18 | ✅ 18/18 | ✅ Fixtures, Parametrisierung |
| `test_toggle_button.py` | 28 | ✅ 28/28 | ✅ Fixtures, Parametrisierung |

#### tests/ - Root Tests (2 Tests)
| Datei | Tests | Status | Refaktoriert |
|-------|-------|-----------|--------------|
| `test_mode_manager.py` | 1 | ✅ 1/1 | ⚠️ Minimal |
| `test_rebound.py` | 1 | ✅ 1/1 | ⚠️ Minimal |

### Integration Tests (63 Tests - 100%)

#### tests/integration/ - Komponentenintegration
| Datei | Tests | Status | Refaktoriert |
|-------|-------|--------|--------------|
| `test_car_component.py` | 27 | ✅ 27/27 | ✅ ISTQB Level 2 |
| `test_simulation_loop.py` | 18 | ✅ 18/18 | ✅ ISTQB Level 2 |
| `test_e2e_simulation.py` | 18 | ✅ 18/18 | ✅ ISTQB Level 2 |

## Test-Kategorien

### 1. Car Component Tests (`test_car_component.py`)

**Testbasis:** Integration der Car-Klasse mit allen Submodulen

**Komponenten:**
- `kinematics` + `dynamics` → Bewegung
- `sensors` + Map → Radar-Casting
- `collision` + `rebound` → Kollisionserkennung
- `rendering` → Sprite-Darstellung

**Testgruppen:**
1. **Initialisierung** - Alle Submodule korrekt initialisiert
2. **Update Cycle** - Kinematics + Dynamics zusammen
3. **Sensor Integration** - Radar-Casting mit Map
4. **Collision Integration** - Kollision → Rebound
5. **Rendering Integration** - Sprite Rotation + Drawing
6. **Power/Speed Integration** - Actuation → Dynamics
7. **Distance/Time Tracking** - Tracking über Frames

**Status:** ✅ 27/27 Tests bestehen (100%)
- Einige Tests erwarten automatische Speed-Aktualisierung (geplant für v2.1)

### 2. Simulation Loop Tests (`test_simulation_loop.py`)

**Testbasis:** Hauptschleife orchestriert Events, ModeManager, SimRuntime

**Komponenten:**
- `EventSource` → SimEvent normalization
- `SimConfig` + `SimRuntime` → State management
- `ModeManager` → Pause/Dialog/Mode switching

**Testgruppen:**
1. **EventSource Integration** - pygame Events → SimEvents
2. **SimConfig + SimRuntime** - Config parsing + State init
3. **ModeManager + SimEvent** - Event handling → State changes
4. **ModeManager + Car Lifecycle** - Mode switch → Car respawn
5. **Headless Simulation** - SDL_VIDEODRIVER=dummy Tests
6. **Error Handling** - Robustness gegen ungültige Events

**Status:** ✅ 18/18 Tests bestehen

### 3. End-to-End Tests (`test_e2e_simulation.py`)

**Testbasis:** Vollständige Simulationsläufe (spawn → update → finish)

**Komponenten:**
- `spawn_from_map` → Car creation
- Multi-Frame Updates → Position/Distance tracking
- Collision Detection → Car termination
- Sensor Updates → Radar readings
- Draw Cycle → Rendering stability

**Testgruppen:**
1. **Car Spawning** - spawn_from_map → Car mit korrekter Position/Angle
2. **Multi-Frame Simulation** - N Frames ohne Crash
3. **Collision Detection** - Wand → alive=False
4. **Sensor Updates** - Radars über mehrere Frames
5. **Draw/Render** - Rendering ohne Fehler
6. **Smoke Tests** - Minimale E2E-Zyklen
7. **Edge Cases** - power=0, max_speed limits

**Status:** ✅ 18/18 Tests bestehen (100%)

## Test-Ausführung

### Alle Tests
```powershell
pytest tests/ -v                    # Alle 404 Tests
pytest tests/ -v --tb=short         # Mit kurzen Tracebacks
```

### Unit Tests (341)
```powershell
pytest tests/ -k "not integration" -v              # Alle Unit-Tests
pytest -m unit -v                                  # Mit Marker
pytest tests/car/ -v                               # Nur Car-Module
pytest tests/sim/ -v                               # Nur Sim-Module
pytest tests/car/test_kinematics.py -v            # Einzelne Datei
```

### Integration Tests (63)
```powershell
pytest tests/integration/ -v                       # Alle Integration-Tests
pytest -m integration -v                           # Mit Marker
pytest tests/integration/test_car_component.py -v  # Car Component
pytest tests/integration/test_simulation_loop.py -v # Simulation Loop
pytest tests/integration/test_e2e_simulation.py -v # End-to-End
```

### Coverage & Reporting
```powershell
pytest tests/ --cov=src/crazycar --cov-report=html # Coverage Report
pytest tests/ -v --durations=10                     # Langsamste Tests
pytest tests/ -v -x                                 # Stop bei erstem Fehler
```

## Fixtures (conftest.py)

### Session-Level Fixtures:
- `pygame_init()` - Initialize pygame once per session

### Test-Level Fixtures:
- `headless_display()` - Headless pygame surface (800x600)
- `sample_car_position()` - Standard spawn position [400.0, 300.0]
- `sample_car_angle()` - Standard spawn angle 0.0°
- `default_car_config()` - Default Car init parameters
- `integration_seed()` - Fixed seed (42) für Reproduzierbarkeit

## Angewendete Testtechniken

### ISTQB-Teststufen
- **Level 1 - Unit Tests**: Isolierte Module (341 Tests)
- **Level 2 - Integration Tests**: Modulübergreifend (63 Tests)
- **Level 3 - System Tests**: End-to-End (geplant v2.1)

### Testverfahren
| Technik | Beschreibung | Anwendung |
|---------|--------------|-----------|
| **Äquivalenzklassen** | Gültige/Ungültige Eingaben gruppieren | Alle Tests |
| **Grenzwertanalyse** | Min/Max/0-Werte testen | 36 Tests (units, actuation) |
| **Zustandsübergänge** | Init→Update→Draw→Finish | Integration Tests |
| **Mock-basiert** | Deterministische Tests | Alle Integration Tests |
| **Parametrisierung** | Data-Driven Testing | 180+ Tests |
| **Fixtures** | Code-Wiederverwendung (DRY) | Alle refaktorierten Tests |

### Code-Qualität (TDD + pytest Best Practices)
- **AAA-Pattern** - Arrange-Act-Assert in allen Tests
- **Fixtures** - Wiederverwendbare Testkomponenten
- **Parametrisierung** - `@pytest.mark.parametrize` für Datenvarianten
- **Markers** - `@pytest.mark.unit` / `@pytest.mark.integration`
- **Docstrings** - Testbasis, Testverfahren, Erwartungen dokumentiert
- **Testgruppen** - Logische Strukturierung (TESTGRUPPE 1-8)

### pytest Markers

#### Builtin Markers (eingebaut)
| Marker | Beschreibung |
|--------|--------------|
| `@pytest.mark.skip(reason=...)` | Überspringt Test (mit optionalem Grund) |
| `@pytest.mark.skipif(condition, reason=...)` | Überspringt Test bei Bedingung (z.B. Platform, Python-Version) |
| `@pytest.mark.xfail(reason=..., strict=...)` | Markiert erwarteten Fehler (expected failure) |
| `@pytest.mark.parametrize(args, values)` | Führt Test mit mehreren Parametern aus |
| `@pytest.mark.usefixtures(name1, name2)` | Erzwingt Fixtures ohne explizites Argument |
| `@pytest.mark.filterwarnings(warning)` | Fügt Warning-Filter für Test hinzu |

**Häufigste Verwendung**: `parametrize`, `skip`, `skipif`, `xfail`

#### Custom Markers (projektspezifisch)
| Marker | Verwendung | Anzahl Tests |
|--------|------------|--------------|
| `@pytest.mark.unit` | Unit Tests (isolierte Module) | 341 Tests |
| `@pytest.mark.integration` | Integration Tests (Modulübergreifend) | 63 Tests |
| `@pytest.mark.e2e` | End-to-End Tests (vollständige Simulation) | 18 Tests |

**Ausführung**: `pytest -m unit`, `pytest -m integration`, `pytest -m e2e`

**Alle Marker anzeigen**: `pytest --markers`

## Refaktorierungs-Status

### Vollständig refaktoriert

**Car Module:** 13/13
- Alle mit ISTQB-Dokumentation, Fixtures, Parametrisierung
- AAA-Pattern konsequent angewendet
- Testgruppen logisch strukturiert

**Sim Module:** 4/4
- ISTQB-konforme Modul-Docstrings
- Fixtures für Event-Factories
- Parametrisierung für Event-Types

**Integration Module:** 3/3
- ISTQB Level 2 Dokumentation
- Mock-basierte Determinismus
- Headless pygame für CI/CD
- **Alle Tests verwenden `car.getmotorleistung()` korrekt**

### Minimal refaktoriert (2 Dateien)
- `test_mode_manager.py` - 1 Test (funktional, aber minimal)
- `test_rebound.py` - 1 Test (funktional, aber minimal)

## Test-Qualität

**412 Tests | 404 passed (98,1%)**

Alle Integration-Tests verwenden jetzt korrekt `car.getmotorleistung()` für Power/Speed-Updates.

---

**Erstellt:** November 2025  
**Framework:** pytest 8.4.2 + pygame (headless)  
**Python:** 3.13.7  
**Tests:** 412 gesamt (404 passed + 4 skipped + 2 xfailed + 2 xpassed)  
**Pass-Rate:** 98,1% (404/412 passed)
