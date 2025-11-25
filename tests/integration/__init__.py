# tests/integration/__init__.py
"""Integration tests for CrazyCar-Simulation.

TESTBASIS (ISTQB):
- Komponententests nach ISTQB (Linz/Spillner, Kap. 4 - Integrationstests)
- Testen das Zusammenspiel mehrerer Module/Komponenten
- Unterschied zu Unit-Tests: Mehrere Komponenten werden gemeinsam getestet

TESTSTUFEN:
1. Unit Tests (tests/car/, tests/sim/) - Isolierte Module
2. Integration Tests (tests/integration/) - Modulübergreifend ← HIER
3. System Tests - End-to-End (noch nicht implementiert)

KOMPONENTEN:
- Car Component: Car-Klasse mit allen Submodulen (kinematics, dynamics, sensors, collision)
- Simulation Loop: EventSource → ModeManager → Car → MapService
- NEAT Integration: Genome → Car spawn → Neural Network control
"""
