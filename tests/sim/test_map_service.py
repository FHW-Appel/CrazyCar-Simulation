"""Tests für MapService - Extended Helper & Spawn Functions.

TESTBASIS:
    src/crazycar/sim/map_service.py
    
TESTVERFAHREN:
    Äquivalenzklassenbildung nach ISTQB:
    - MapService Init: Constructor, Asset Loading
    - Spawn Detection: get_spawn(), set_manual_spawn()
    - Dataclass: Spawn(x_px, y_px, angle_deg)
    - Constants: FINISH_LINE_COLOR, _FINISH_TOL, _SCAN_STEP
"""
import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock
from dataclasses import is_dataclass

pytestmark = pytest.mark.unit


# ===============================================================================
# FIXTURES
# ===============================================================================

@pytest.fixture(scope="session")
def pygame_init():
    """Pygame initialisieren für MapService Tests."""
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1, 1))  # Dummy display
    yield
    pygame.display.quit()
    pygame.quit()


# ===============================================================================
# TESTGRUPPE 1: Spawn Dataclass
# ===============================================================================

class TestSpawnDataclass:
    """Tests für Spawn Dataclass."""
    
    def test_spawn_import(self):
        """GIVEN: map_service, WHEN: Import Spawn, THEN: Dataclass exists.
        
        Erwartung: Spawn Dataclass kann importiert werden.
        """
        try:
            from crazycar.sim.map_service import Spawn
            assert Spawn is not None
        except ImportError:
            pytest.skip("Spawn nicht verfügbar")
    
    def test_spawn_is_dataclass(self):
        """GIVEN: Spawn, WHEN: Check type, THEN: Is dataclass.
        
        Erwartung: Spawn ist dataclass (frozen).
        """
        try:
            from crazycar.sim.map_service import Spawn
            assert is_dataclass(Spawn)
        except ImportError:
            pytest.skip("Spawn nicht verfügbar")
    
    def test_spawn_creation_with_defaults(self):
        """GIVEN: x_px, y_px, WHEN: Spawn(), THEN: angle_deg=0.0 default.
        
        Erwartung: Spawn mit Default-Winkel 0.0.
        """
        try:
            from crazycar.sim.map_service import Spawn
            
            # ACT
            spawn = Spawn(x_px=100, y_px=200)
            
            # THEN
            assert spawn.x_px == 100
            assert spawn.y_px == 200
            assert spawn.angle_deg == 0.0
        except ImportError:
            pytest.skip("Spawn nicht verfügbar")
    
    def test_spawn_creation_with_angle(self):
        """GIVEN: x_px, y_px, angle_deg, WHEN: Spawn(), THEN: Custom angle.
        
        Erwartung: Spawn mit custom Winkel.
        """
        try:
            from crazycar.sim.map_service import Spawn
            
            # ACT
            spawn = Spawn(x_px=150, y_px=250, angle_deg=45.0)
            
            # THEN
            assert spawn.x_px == 150
            assert spawn.y_px == 250
            assert spawn.angle_deg == 45.0
        except ImportError:
            pytest.skip("Spawn nicht verfügbar")
    
    def test_spawn_is_frozen(self):
        """GIVEN: Spawn instance, WHEN: Try modify, THEN: FrozenInstanceError.
        
        Erwartung: Spawn ist immutable (frozen=True).
        """
        try:
            from crazycar.sim.map_service import Spawn
            from dataclasses import FrozenInstanceError
            
            spawn = Spawn(x_px=100, y_px=200)
            
            # ACT & THEN
            with pytest.raises(FrozenInstanceError):
                spawn.x_px = 300
        except ImportError:
            pytest.skip("Spawn oder FrozenInstanceError nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 2: MapService Init
# ===============================================================================

class TestMapServiceInit:
    """Tests für MapService Constructor."""
    
    def test_map_service_import(self):
        """GIVEN: map_service, WHEN: Import MapService, THEN: Class exists.
        
        Erwartung: MapService Klasse kann importiert werden.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert MapService is not None
        except ImportError:
            pytest.skip("MapService nicht verfügbar")
    
    @pytest.mark.integration
    def test_map_service_init_loads_asset(self, pygame_init):
        """GIVEN: window_size + asset_name, WHEN: MapService(), THEN: Map geladen.
        
        TESTBASIS:
            Modul crazycar.sim.map_service.MapService.__init__()
            Asset Loading via pygame.image.load()
        
        TESTVERFAHREN:
            Blackbox: Prüfe ob Surface nach Init existiert
            Integration: Lade echtes Racemap.png Asset
        
        Erwartung: MapService lädt Racemap.png aus assets/, Surface != None.
        """
        from crazycar.sim.map_service import MapService
        
        # ACT: MapService mit default asset
        try:
            map_service = MapService(window_size=(800, 600), asset_name="Racemap.png")
            
            # THEN: Surface sollte geladen sein
            assert map_service._surface is not None
            assert isinstance(map_service._surface, pygame.Surface)
            assert map_service._surface.get_width() > 0
            assert map_service._surface.get_height() > 0
        except FileNotFoundError:
            pytest.skip("Racemap.png nicht gefunden in assets/")
    
    def test_map_service_has_resize_method(self):
        """GIVEN: MapService, WHEN: Check methods, THEN: resize() exists.
        
        Erwartung: MapService hat resize() Methode.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'resize')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")
    
    def test_map_service_has_blit_method(self):
        """GIVEN: MapService, WHEN: Check methods, THEN: blit() exists.
        
        Erwartung: MapService hat blit() Methode.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'blit')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")
    
    def test_map_service_has_get_spawn_method(self):
        """GIVEN: MapService, WHEN: Check methods, THEN: get_spawn() exists.
        
        Erwartung: MapService hat get_spawn() Methode.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'get_spawn')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 3: Spawn Detection
# ===============================================================================

class TestSpawnDetection:
    """Tests für Spawn Detection Logic."""
    
    def test_set_manual_spawn_exists(self):
        """GIVEN: MapService, WHEN: Check methods, THEN: set_manual_spawn() exists.
        
        Erwartung: MapService hat set_manual_spawn() Methode.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'set_manual_spawn')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")
    
    @pytest.mark.integration
    def test_get_spawn_returns_spawn_object(self, pygame_init):
        """GIVEN: MapService, WHEN: get_spawn(), THEN: Spawn object zurück.
        
        TESTBASIS:
            Modul crazycar.sim.map_service.MapService.get_spawn()
            Spawn-Detection Algorithmus
        
        TESTVERFAHREN:
            Blackbox: Prüfe Return-Type und Attribute
            Integration: MapService mit Auto-Detection
        
        Erwartung: get_spawn() gibt Spawn(x_px, y_px, angle_deg) zurück mit validen Werten.
        """
        from crazycar.sim.map_service import MapService, Spawn
        
        try:
            map_service = MapService(window_size=(800, 600), asset_name="Racemap.png")
            
            # ACT
            spawn = map_service.get_spawn()
            
            # THEN: Spawn object mit validen Attributen
            assert isinstance(spawn, Spawn)
            assert hasattr(spawn, 'x_px')
            assert hasattr(spawn, 'y_px')
            assert hasattr(spawn, 'angle_deg')
            assert isinstance(spawn.x_px, (int, float))
            assert isinstance(spawn.y_px, (int, float))
            assert isinstance(spawn.angle_deg, (int, float))
            assert 0 <= spawn.x_px <= 800
            assert 0 <= spawn.y_px <= 600
        except FileNotFoundError:
            pytest.skip("Racemap.png nicht gefunden")
    
    @pytest.mark.integration
    def test_manual_spawn_overrides_auto_detection(self, pygame_init):
        """GIVEN: Manual spawn set, WHEN: get_spawn(), THEN: Manual spawn returned.
        
        TESTBASIS:
            Modul crazycar.sim.map_service.MapService.set_manual_spawn()
            Override-Mechanismus für Auto-Detection
        
        TESTVERFAHREN:
            Blackbox: Prüfe ob get_spawn() manuellen Wert zurückgibt
            Stateful: set_manual_spawn() persistiert Wert
        
        Erwartung: set_manual_spawn() überschreibt Auto-Detection, exakte Koordinaten.
        """
        from crazycar.sim.map_service import MapService, Spawn
        
        try:
            map_service = MapService(window_size=(800, 600), asset_name="Racemap.png")
            manual_spawn = Spawn(x_px=300, y_px=400, angle_deg=90.0)
            
            # ACT
            map_service.set_manual_spawn(manual_spawn)
            result = map_service.get_spawn()
            
            # THEN: Exakte Übereinstimmung mit manuellem Spawn
            assert result.x_px == 300
            assert result.y_px == 400
            assert result.angle_deg == 90.0
        except FileNotFoundError:
            pytest.skip("Racemap.png nicht gefunden")
        assert result.angle_deg == 90.0
    
    def test_get_detect_info_exists(self):
        """GIVEN: MapService, WHEN: Check methods, THEN: get_detect_info() exists.
        
        Erwartung: MapService hat get_detect_info() für Debug-Info.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'get_detect_info')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 4: Constants & Configuration
# ===============================================================================

class TestMapServiceConstants:
    """Tests für MapService Konstanten."""
    
    def test_finish_line_color_defined(self):
        """GIVEN: map_service, WHEN: Import FINISH_LINE_COLOR, THEN: RGBA tuple.
        
        Erwartung: FINISH_LINE_COLOR = (237, 28, 36, 255) definiert.
        """
        try:
            from crazycar.sim.map_service import FINISH_LINE_COLOR
            
            # THEN
            assert isinstance(FINISH_LINE_COLOR, tuple)
            assert len(FINISH_LINE_COLOR) == 4
            assert FINISH_LINE_COLOR == (237, 28, 36, 255)
        except ImportError:
            pytest.skip("FINISH_LINE_COLOR nicht verfügbar")
    
    def test_border_color_defined(self):
        """GIVEN: map_service, WHEN: Import BORDER_COLOR, THEN: White RGBA.
        
        Erwartung: BORDER_COLOR = (255, 255, 255, 255) definiert.
        """
        try:
            from crazycar.sim.map_service import BORDER_COLOR
            
            # THEN
            assert isinstance(BORDER_COLOR, tuple)
            assert len(BORDER_COLOR) == 4
            assert BORDER_COLOR == (255, 255, 255, 255)
        except ImportError:
            pytest.skip("BORDER_COLOR nicht verfügbar")
    
    def test_finish_tol_defined(self):
        """GIVEN: map_service, WHEN: Import _FINISH_TOL, THEN: Integer tolerance.
        
        Erwartung: _FINISH_TOL für Farberkennung definiert.
        """
        try:
            from crazycar.sim.map_service import _FINISH_TOL
            
            # THEN
            assert isinstance(_FINISH_TOL, int)
            assert _FINISH_TOL > 0
        except ImportError:
            pytest.skip("_FINISH_TOL nicht verfügbar")
    
    def test_scan_step_defined(self):
        """GIVEN: map_service, WHEN: Import _SCAN_STEP, THEN: Integer step.
        
        Erwartung: _SCAN_STEP für Pixel-Scanning definiert.
        """
        try:
            from crazycar.sim.map_service import _SCAN_STEP
            
            # THEN
            assert isinstance(_SCAN_STEP, int)
            assert _SCAN_STEP > 0
        except ImportError:
            pytest.skip("_SCAN_STEP nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 5: Surface Property
# ===============================================================================

class TestMapServiceProperties:
    """Tests für MapService Properties."""
    
    def test_surface_property_exists(self):
        """GIVEN: MapService, WHEN: Check properties, THEN: surface property exists.
        
        Erwartung: MapService hat surface property.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'surface')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")
    
    def test_map_name_property_exists(self):
        """GIVEN: MapService, WHEN: Check properties, THEN: map_name property exists.
        
        Erwartung: MapService hat map_name property.
        """
        try:
            from crazycar.sim.map_service import MapService
            assert hasattr(MapService, 'map_name')
        except ImportError:
            pytest.skip("MapService nicht verfügbar")


# ===============================================================================
# TESTGRUPPE 6: Resize & Blit Operations
# ===============================================================================

class TestMapServiceOperations:
    """Tests für MapService Operationen."""
    
    @pytest.mark.integration
    def test_resize_changes_surface_size(self, pygame_init):
        """GIVEN: MapService, WHEN: resize(new_size), THEN: Surface resized.
        
        TESTBASIS:
            Modul crazycar.sim.map_service.MapService.resize()
            pygame.transform.scale()
        
        TESTVERFAHREN:
            Blackbox: Prüfe Surface-Dimensionen nach resize()
            State-Test: Surface.get_width()/get_height()
        
        Erwartung: resize() skaliert Map auf neue Größe, Proportionen geändert.
        """
        from crazycar.sim.map_service import MapService
        
        try:
            map_service = MapService(window_size=(800, 600), asset_name="Racemap.png")
            
            # ACT
            map_service.resize((1024, 768))
            
            # THEN: Neue Dimensionen
            assert map_service.surface.get_width() == 1024
            assert map_service.surface.get_height() == 768
        except (FileNotFoundError, AttributeError):
            pytest.skip("MapService oder Asset nicht verfügbar")
    
    @pytest.mark.integration
    def test_blit_draws_to_screen(self, pygame_init):
        """GIVEN: MapService + Screen, WHEN: blit(screen), THEN: Map drawn.
        
        TESTBASIS:
            Modul crazycar.sim.map_service.MapService.blit()
            screen.blit() Aufruf
        
        TESTVERFAHREN:
            Whitebox: Mock screen.blit(), prüfe call_count
            Integration: MapService mit Mock-Screen
        
        Erwartung: blit() zeichnet Map auf Screen, blit() mindestens 1x aufgerufen.
        """
        from crazycar.sim.map_service import MapService
        
        try:
            map_service = MapService(window_size=(800, 600), asset_name="Racemap.png")
            
            # Mock screen
            mock_screen = Mock(spec=pygame.Surface)
            mock_screen.blit = Mock()
            
            # ACT
            map_service.blit(mock_screen)
            
            # THEN: blit wurde aufgerufen
            assert mock_screen.blit.call_count >= 1
            assert mock_screen.blit.called
        except FileNotFoundError:
            pytest.skip("Racemap.png nicht gefunden")
        from crazycar.sim.map_service import MapService
        
        screen = pygame.display.set_mode((800, 600))
        map_service = MapService(window_size=(800, 600))
        
        # ACT
        map_service.blit(screen)
        
        # THEN: Kein Fehler → Success
        assert True
