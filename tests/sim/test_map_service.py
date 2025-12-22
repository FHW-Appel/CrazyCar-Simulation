"""Unit-Tests für MapService - Track-Loading, Skalierung, Spawn-Detection.

TESTBASIS (ISTQB):
- Anforderung: Map-Laden, Fenster-Skalierung, Spawn-Position ermitteln
- Module: crazycar.sim.map_service
- Klasse: MapService, Spawn
- Funktionen: __init__, resize, blit, get_spawn, set_manual_spawn

TESTVERFAHREN:
- Äquivalenzklassen: Gültige/ungültige Fenstergrößen, mit/ohne Spawn-Override
- Zustandsübergänge: Laden → Skalieren → Spawn ermitteln
- Grenzwertanalyse: Minimale/maximale Fenstergrößen
- Eigenschafts-Tests: Resize löscht Spawn-Cache, Manual-Spawn hat Vorrang
"""
import os
import pytest
import pygame
from unittest.mock import Mock, MagicMock, patch
from crazycar.sim.map_service import MapService, Spawn

pytestmark = pytest.mark.unit


# ===============================================================================
# FIXTURES: Setup und Helper
# ===============================================================================

@pytest.fixture(scope="session")
def pygame_init():
    """Einmalige pygame-Initialisierung für alle Tests."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def mock_map_surface():
    """Mock für pygame Surface (Map)."""
    surface = Mock(spec=pygame.Surface)
    surface.get_width.return_value = 800
    surface.get_height.return_value = 600
    return surface


# ===============================================================================
# TESTGRUPPE 1: Konstruktor und Grundfunktionen
# ===============================================================================

class TestMapServiceConstruction:
    """Tests für MapService.__init__."""
    
    def test_map_service_creation(self, pygame_init):
        """GIVEN: Gültige Fenstergröße, WHEN: MapService(), THEN: Instanz erstellt.
        
        Erwartung: MapService-Objekt ohne Exception.
        """
        # ARRANGE & ACT
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                # WHEN
                map_service = MapService((1920, 1080), "Racemap.png")
        
        # THEN
        assert map_service is not None
        assert map_service.map_name == "Racemap.png"
    
    def test_map_service_loads_asset(self, pygame_init):
        """GIVEN: Asset-Name, WHEN: MapService(), THEN: Bild geladen.
        
        Erwartung: pygame.image.load aufgerufen mit korrektem Pfad.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                # ACT
                MapService((800, 600), "Testmap.png")
        
        # THEN
        mock_load.assert_called_once()
        call_path = mock_load.call_args[0][0]
        assert "Testmap.png" in call_path


# ===============================================================================
# TESTGRUPPE 2: Resize-Funktion
# ===============================================================================

class TestMapServiceResize:
    """Tests für resize() Methode."""
    
    def test_resize_scales_map(self, pygame_init):
        """GIVEN: MapService mit Größe, WHEN: resize(), THEN: Skaliert auf neue Größe.
        
        Erwartung: pygame.transform.scale mit neuer Größe aufgerufen.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_raw = Mock(spec=pygame.Surface)
            mock_raw.convert_alpha.return_value = mock_raw
            mock_load.return_value = mock_raw
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scaled = Mock(spec=pygame.Surface)
                mock_scale.return_value = mock_scaled
                
                map_service = MapService((800, 600))
                mock_scale.reset_mock()
                
                # ACT
                map_service.resize((1024, 768))
        
        # THEN
        mock_scale.assert_called_with(mock_raw, (1024, 768))
    
    def test_resize_clears_spawn_cache(self, pygame_init):
        """GIVEN: MapService mit gecachtem Spawn, WHEN: resize(), THEN: Cache geleert.
        
        Erwartung: Nach resize() wird Spawn neu berechnet.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                map_service = MapService((800, 600))
                
                # Spawn-Detect mocken
                with patch.object(map_service, '_spawn_from_finish_line') as mock_spawn:
                    mock_spawn.return_value = Spawn(100, 100, 0.0)
                    
                    # Ersten Spawn abrufen (cachen)
                    spawn1 = map_service.get_spawn()
                    assert mock_spawn.call_count == 1
                    
                    # Nochmal abrufen (aus Cache, kein neuer Call)
                    spawn2 = map_service.get_spawn()
                    assert mock_spawn.call_count == 1  # Immer noch 1
                    
                    # WHEN: Resize
                    map_service.resize((1024, 768))
                    
                    # THEN: Spawn neu berechnet
                    spawn3 = map_service.get_spawn()
                    assert mock_spawn.call_count == 2  # Jetzt 2


# ===============================================================================
# TESTGRUPPE 3: Blit-Funktion
# ===============================================================================

class TestMapServiceBlit:
    """Tests für blit() Methode."""
    
    def test_blit_draws_to_screen(self, pygame_init):
        """GIVEN: Screen-Surface, WHEN: blit(), THEN: Map auf Screen gezeichnet.
        
        Erwartung: screen.blit aufgerufen mit Map-Surface.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scaled = Mock(spec=pygame.Surface)
                mock_scale.return_value = mock_scaled
                
                map_service = MapService((800, 600))
                screen = Mock(spec=pygame.Surface)
                
                # ACT
                map_service.blit(screen)
        
        # THEN
        screen.blit.assert_called_once_with(mock_scaled, (0, 0))


# ===============================================================================
# TESTGRUPPE 4: Spawn-Ermittlung
# ===============================================================================

class TestMapServiceSpawn:
    """Tests für get_spawn() und set_manual_spawn()."""
    
    def test_get_spawn_returns_spawn_object(self, pygame_init):
        """GIVEN: MapService, WHEN: get_spawn(), THEN: Spawn-Objekt zurück.
        
        Erwartung: Spawn mit x_px, y_px, angle_deg.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                map_service = MapService((800, 600))
                
                # ACT
                spawn = map_service.get_spawn()
        
        # THEN
        assert isinstance(spawn, Spawn)
        assert hasattr(spawn, 'x_px')
        assert hasattr(spawn, 'y_px')
        assert hasattr(spawn, 'angle_deg')
    
    def test_manual_spawn_overrides_auto_detect(self, pygame_init):
        """GIVEN: Manual Spawn gesetzt, WHEN: get_spawn(), THEN: Manual Spawn zurück.
        
        Erwartung: Manueller Spawn hat Vorrang vor Auto-Detect.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                map_service = MapService((800, 600))
                manual_spawn = Spawn(250, 350, 45.0)
                
                # ACT
                map_service.set_manual_spawn(manual_spawn)
                result = map_service.get_spawn()
        
        # THEN
        assert result == manual_spawn
        assert result.x_px == 250
        assert result.y_px == 350
        assert result.angle_deg == 45.0
    
    def test_set_manual_spawn_none_clears_override(self, pygame_init):
        """GIVEN: Manual Spawn gesetzt, WHEN: set_manual_spawn(None), THEN: Override entfernt.
        
        Erwartung: Nach None wird wieder Auto-Detect verwendet.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                map_service = MapService((800, 600))
                
                # Manual Spawn setzen
                map_service.set_manual_spawn(Spawn(100, 100, 0.0))
                assert map_service.get_spawn().x_px == 100
                
                # ACT: Auf None setzen
                map_service.set_manual_spawn(None)
                
                # THEN: Verwendet jetzt wieder Auto-Detect oder Fallback
                spawn = map_service.get_spawn()
                assert spawn.x_px != 100 or spawn.y_px != 100 or spawn.angle_deg != 0.0


# ===============================================================================
# TESTGRUPPE 5: Eigenschaften und Edge-Cases
# ===============================================================================

class TestMapServiceProperties:
    """Tests für Properties und Grenzfälle."""
    
    def test_surface_property_returns_current_surface(self, pygame_init):
        """GIVEN: MapService, WHEN: .surface, THEN: Aktuelles Surface zurück.
        
        Erwartung: Property gibt skaliertes Surface zurück.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scaled = Mock(spec=pygame.Surface)
                mock_scale.return_value = mock_scaled
                
                map_service = MapService((800, 600))
                
                # ACT
                surface = map_service.surface
        
        # THEN
        assert surface is mock_scaled
    
    def test_map_name_property_returns_asset_name(self, pygame_init):
        """GIVEN: MapService mit Asset, WHEN: .map_name, THEN: Asset-Name zurück.
        
        Erwartung: Property gibt korrekten Dateinamen zurück.
        """
        # ARRANGE
        with patch('pygame.image.load') as mock_load:
            mock_surface = Mock(spec=pygame.Surface)
            mock_surface.convert_alpha.return_value = mock_surface
            mock_load.return_value = mock_surface
            
            with patch('pygame.transform.scale') as mock_scale:
                mock_scale.return_value = mock_surface
                
                map_service = MapService((800, 600), "MyTrack.png")
                
                # ACT
                name = map_service.map_name
        
        # THEN
        assert name == "MyTrack.png"


# ===============================================================================
# TESTGRUPPE 6: Spawn Dataclass
# ===============================================================================

class TestSpawnDataclass:
    """Tests für Spawn Dataclass."""
    
    def test_spawn_creation(self):
        """GIVEN: Koordinaten, WHEN: Spawn(), THEN: Spawn-Objekt erstellt.
        
        Erwartung: Spawn mit allen Attributen.
        """
        # ACT
        spawn = Spawn(100, 200, 90.0)
        
        # THEN
        assert spawn.x_px == 100
        assert spawn.y_px == 200
        assert spawn.angle_deg == 90.0
    
    def test_spawn_default_angle(self):
        """GIVEN: Nur x/y, WHEN: Spawn(), THEN: angle_deg=0.0 als Default.
        
        Erwartung: Standard-Winkel ist 0.
        """
        # ACT
        spawn = Spawn(50, 75)
        
        # THEN
        assert spawn.angle_deg == 0.0
    
    def test_spawn_is_frozen(self):
        """GIVEN: Spawn-Objekt, WHEN: Attribut ändern, THEN: FrozenInstanceError.
        
        Erwartung: Spawn ist immutable (frozen dataclass).
        """
        # ARRANGE
        spawn = Spawn(100, 100, 0.0)
        
        # ACT & THEN
        with pytest.raises(Exception):  # FrozenInstanceError oder AttributeError
            spawn.x_px = 200
