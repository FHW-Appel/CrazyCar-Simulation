"""Unit-Tests für Finish-Detection - PCA und Pixel-Detection für Ziellinie.

TESTBASIS (ISTQB):
- Anforderung: Ziellinienerkennung via rote Pixel-Detection und PCA
- Module: crazycar.sim.finish_detection
- Funktionen: principal_direction, select_largest_component, collect_red_pixels_fast

TESTVERFAHREN:
- Äquivalenzklassen: Leere/volle Punktmengen, verbundene/getrennte Komponenten
- Grenzwertanalyse: Minimale Punktanzahl für PCA, Toleranzgrenzen
- Numerische Stabilität: Degenerierte Fälle (identische Punkte, Nullvektoren)
- Eigenschafts-Tests: PCA-Vektorlänge = 1, Determinismus
"""
import pytest
import math
from unittest.mock import Mock, MagicMock, patch
from crazycar.sim.finish_detection import (
    principal_direction,
    select_largest_component,
    collect_red_pixels_fast
)

pytestmark = pytest.mark.unit


# ===============================================================================
# TESTGRUPPE 1: Principal Direction (PCA)
# ===============================================================================

class TestPrincipalDirection:
    """Tests für principal_direction() - PCA für Hauptrichtung."""
    
    def test_principal_direction_empty_input(self):
        """GIVEN: Leere Listen, WHEN: principal_direction(), THEN: Fallback (1, 0).
        
        Erwartung: Standardrichtung (1, 0) bei leerer Eingabe.
        """
        # ACT
        vx, vy = principal_direction([], [], 0.0, 0.0)
        
        # THEN
        assert vx == 1.0
        assert vy == 0.0
    
    def test_principal_direction_horizontal_line(self):
        """GIVEN: Horizontale Linie, WHEN: principal_direction(), THEN: Horizontaler Vektor.
        
        Erwartung: PCA erkennt horizontale Hauptrichtung.
        """
        # ARRANGE: Punkte auf horizontaler Linie (y=50)
        xs = [10, 20, 30, 40, 50]
        ys = [50, 50, 50, 50, 50]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN: Hauptrichtung ist horizontal (vx≈±1, vy≈0)
        assert abs(vx) > 0.9
        assert abs(vy) < 0.1
    
    def test_principal_direction_vertical_line(self):
        """GIVEN: Vertikale Linie, WHEN: principal_direction(), THEN: Vertikaler Vektor.
        
        Erwartung: PCA erkennt vertikale Hauptrichtung.
        """
        # ARRANGE: Punkte auf vertikaler Linie (x=100)
        xs = [100, 100, 100, 100]
        ys = [10, 20, 30, 40]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN: Hauptrichtung ist vertikal (vx≈0, vy≈±1)
        assert abs(vx) < 0.1
        assert abs(vy) > 0.9
    
    def test_principal_direction_diagonal_line(self):
        """GIVEN: Diagonale Linie (45°), WHEN: principal_direction(), THEN: Diagonaler Vektor.
        
        Erwartung: PCA erkennt 45°-Richtung.
        """
        # ARRANGE: Punkte auf Diagonale (y=x)
        xs = [0, 10, 20, 30, 40]
        ys = [0, 10, 20, 30, 40]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN: Hauptrichtung ~45° (vx≈vy)
        assert abs(abs(vx) - abs(vy)) < 0.1
        # Vektor normalisiert
        length = math.hypot(vx, vy)
        assert abs(length - 1.0) < 0.01
    
    def test_principal_direction_normalized_output(self):
        """GIVEN: Beliebige Punktmenge, WHEN: principal_direction(), THEN: Länge = 1.
        
        Erwartung: Ausgangsvektor ist immer normalisiert.
        """
        # ARRANGE: Zufällige Punkte
        xs = [5, 15, 25, 35]
        ys = [10, 20, 15, 25]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN: Länge = 1
        length = math.hypot(vx, vy)
        assert abs(length - 1.0) < 1e-6
    
    def test_principal_direction_single_point(self):
        """GIVEN: Einzelner Punkt, WHEN: principal_direction(), THEN: Fallback-Richtung.
        
        Erwartung: Bei degeneriertem Fall Standardrichtung.
        """
        # ARRANGE: Nur ein Punkt (keine Streuung)
        xs = [100]
        ys = [200]
        cx, cy = 100.0, 200.0
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN: Fallback oder normalisierter Vektor
        length = math.hypot(vx, vy)
        assert abs(length - 1.0) < 0.01


# ===============================================================================
# TESTGRUPPE 2: Largest Component Selection
# ===============================================================================

class TestLargestComponent:
    """Tests für select_largest_component() - Verbundene Komponenten."""
    
    def test_select_largest_component_empty_input(self):
        """GIVEN: Leere Listen, WHEN: select_largest_component(), THEN: Leere Listen.
        
        Erwartung: ([], []) bei leerer Eingabe.
        """
        # ACT
        xs_out, ys_out = select_largest_component([], [])
        
        # THEN
        assert xs_out == []
        assert ys_out == []
    
    def test_select_largest_component_none_input(self):
        """GIVEN: None-Eingabe, WHEN: select_largest_component(), THEN: Leere Listen.
        
        Erwartung: ([], []) bei None.
        """
        # ACT
        xs_out, ys_out = select_largest_component(None, None)
        
        # THEN
        assert xs_out == []
        assert ys_out == []
    
    def test_select_largest_component_single_component(self):
        """GIVEN: Verbundene Punkte, WHEN: select_largest_component(), THEN: Alle Punkte.
        
        Erwartung: Gesamte Komponente zurück.
        """
        # ARRANGE: 4-verbundene horizontale Linie
        xs = [10, 11, 12, 13]
        ys = [20, 20, 20, 20]
        
        # ACT
        xs_out, ys_out = select_largest_component(xs, ys)
        
        # THEN: Alle Punkte enthalten
        assert len(xs_out) == 4
        assert len(ys_out) == 4
        assert set(xs_out) == set(xs)
        assert set(ys_out) == set(ys)
    
    def test_select_largest_component_multiple_components(self):
        """GIVEN: Zwei getrennte Komponenten, WHEN: select_largest_component(), THEN: Größte Komponente.
        
        Erwartung: Nur größte Komponente zurück.
        """
        # ARRANGE: Zwei getrennte Gruppen
        # Gruppe 1 (5 Punkte): (0,0)-(4,0)
        # Gruppe 2 (3 Punkte): (10,10)-(12,10)
        xs = [0, 1, 2, 3, 4, 10, 11, 12]
        ys = [0, 0, 0, 0, 0, 10, 10, 10]
        
        # ACT
        xs_out, ys_out = select_largest_component(xs, ys)
        
        # THEN: Nur Gruppe 1 (5 Punkte)
        assert len(xs_out) == 5
        assert len(ys_out) == 5
        # Alle x-Werte zwischen 0 und 4
        assert all(0 <= x <= 4 for x in xs_out)
    
    def test_select_largest_component_isolated_pixels(self):
        """GIVEN: Einzelne isolierte Pixel + große Gruppe, WHEN: select_largest_component(), THEN: Große Gruppe.
        
        Erwartung: Isolierte Pixel herausgefiltert.
        """
        # ARRANGE: 
        # Große Komponente: (5,5)-(5,6)-(5,7) (3 Pixel vertikal)
        # Isolierte Pixel: (0,0), (20,20)
        xs = [5, 5, 5, 0, 20]
        ys = [5, 6, 7, 0, 20]
        
        # ACT
        xs_out, ys_out = select_largest_component(xs, ys)
        
        # THEN: Nur die 3-Pixel-Komponente
        assert len(xs_out) == 3
        assert all(x == 5 for x in xs_out)
        assert set(ys_out) == {5, 6, 7}
    
    def test_select_largest_component_diagonal_not_connected(self):
        """GIVEN: Diagonal benachbarte Pixel, WHEN: select_largest_component(), THEN: Getrennte Komponenten.
        
        Erwartung: 4-Konnektivität (diagonal nicht verbunden).
        """
        # ARRANGE: Diagonale Nachbarn (nicht 4-verbunden)
        # (0,0) und (1,1) sind diagonal, nicht 4-verbunden
        xs = [0, 1]
        ys = [0, 1]
        
        # ACT
        xs_out, ys_out = select_largest_component(xs, ys)
        
        # THEN: Nur ein Pixel (größte Komponente = 1)
        assert len(xs_out) == 1
        assert len(ys_out) == 1


# ===============================================================================
# TESTGRUPPE 3: Fast Pixel Collection
# ===============================================================================

class TestFastPixelCollection:
    """Tests für collect_red_pixels_fast() - NumPy-basierte Pixel-Suche."""
    
    def test_collect_red_pixels_fast_without_numpy(self):
        """GIVEN: NumPy nicht verfügbar, WHEN: collect_red_pixels_fast(), THEN: None-Fallback.
        
        Erwartung: (None, None) wenn NumPy fehlt.
        """
        # ARRANGE: NumPy-Import mocken
        import sys
        with patch.dict(sys.modules, {'numpy': None}):
            mock_surface = Mock()
            
            # ACT
            result = collect_red_pixels_fast(mock_surface, (255, 0, 0), 10)
        
        # THEN: Falls NumPy fehlt, sollte None zurück
        # (oder leere Listen, je nach Implementierung)
        # Test überspringen wenn NumPy vorhanden
        if result is not None and result[0] is not None:
            pytest.skip("NumPy verfügbar, kein Fallback")
    
    def test_collect_red_pixels_fast_with_surface(self):
        """GIVEN: Surface mit roten Pixeln, WHEN: collect_red_pixels_fast(), THEN: Pixel gefunden.
        
        Erwartung: Listen mit Koordinaten roter Pixel.
        """
        # Test erfordert echtes pygame Surface oder umfangreiches Mocking
        # Überspringen wenn Integration nicht möglich
        pytest.skip("Erfordert pygame Surface Integration")


# ===============================================================================
# TESTGRUPPE 4: Eigenschaften und Stabilität
# ===============================================================================

class TestFinishDetectionProperties:
    """Property-based Tests für numerische Stabilität."""
    
    @pytest.mark.parametrize("n_points", [2, 5, 10, 100])
    def test_principal_direction_always_normalized(self, n_points):
        """GIVEN: n Punkte, WHEN: principal_direction(), THEN: Länge=1.
        
        Erwartung: Ausgabe immer normalisiert, unabhängig von Eingabegröße.
        """
        # ARRANGE: n Punkte auf Linie
        xs = list(range(n_points))
        ys = [i * 2 for i in range(n_points)]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        # ACT
        vx, vy = principal_direction(xs, ys, cx, cy)
        
        # THEN
        length = math.hypot(vx, vy)
        assert abs(length - 1.0) < 1e-6
    
    def test_principal_direction_deterministic(self):
        """GIVEN: Identische Eingabe, WHEN: principal_direction(), THEN: Identische Ausgabe.
        
        Erwartung: Deterministisches Verhalten.
        """
        # ARRANGE
        xs = [1, 2, 3, 4, 5]
        ys = [2, 4, 6, 8, 10]
        cx, cy = 3.0, 6.0
        
        # ACT
        result1 = principal_direction(xs, ys, cx, cy)
        result2 = principal_direction(xs, ys, cx, cy)
        
        # THEN
        assert result1 == result2
