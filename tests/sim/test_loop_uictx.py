# tests/sim/test_loop_uictx.py
"""Unit Tests für loop.py UICtx Dataclass.

TESTBASIS:
- Modul crazycar.sim.loop - UICtx Dataclass
- UI Context Bundling

TESTVERFAHREN:
- Structural: Dataclass attributes
- Type-Check: pygame objects
"""
import pytest
import pygame
from unittest.mock import Mock


# ==============================================================================
# TESTGRUPPE 1: UICtx Structure Tests
# ==============================================================================

class TestUICtxStructure:
    """Tests für UICtx dataclass structure."""
    
    def test_uictx_has_screen_attribute(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: screen exists.
        
        TESTBASIS:
            Class UICtx - Surface attribute
        
        TESTVERFAHREN:
            Structural: Attribute existence
        
        Erwartung: UICtx hat screen attribute.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert hasattr(UICtx, '__annotations__')
        assert 'screen' in UICtx.__annotations__
    
    def test_uictx_has_all_font_attributes(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: Alle fonts vorhanden.
        
        TESTBASIS:
            Class UICtx - Font attributes
        
        TESTVERFAHREN:
            Structural: font_ft, font_gen, font_alive
        
        Erwartung: UICtx hat 3 font attributes.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'font_ft' in UICtx.__annotations__
        assert 'font_gen' in UICtx.__annotations__
        assert 'font_alive' in UICtx.__annotations__
    
    def test_uictx_has_clock_attribute(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: clock vorhanden.
        
        TESTBASIS:
            Class UICtx - Clock attribute
        
        TESTVERFAHREN:
            Structural: pygame.time.Clock
        
        Erwartung: UICtx hat clock attribute.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'clock' in UICtx.__annotations__
    
    def test_uictx_has_button_rect_attributes(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: Alle button rects vorhanden.
        
        TESTBASIS:
            Class UICtx - Button rect attributes
        
        TESTVERFAHREN:
            Structural: 4 button rects
        
        Erwartung: UICtx hat regelung1, regelung2, yes, no rects.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'button_regelung1_rect' in UICtx.__annotations__
        assert 'button_regelung2_rect' in UICtx.__annotations__
        assert 'button_yes_rect' in UICtx.__annotations__
        assert 'button_no_rect' in UICtx.__annotations__
    
    def test_uictx_has_color_attributes(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: Color attributes vorhanden.
        
        TESTBASIS:
            Class UICtx - Color attributes
        
        TESTVERFAHREN:
            Structural: text_color, button_color
        
        Erwartung: UICtx hat 2 color attributes.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'text_color' in UICtx.__annotations__
        assert 'button_color' in UICtx.__annotations__
    
    def test_uictx_has_text_attributes(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: text1, text2 vorhanden.
        
        TESTBASIS:
            Class UICtx - Text label attributes
        
        TESTVERFAHREN:
            Structural: text1, text2
        
        Erwartung: UICtx hat text1 und text2.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'text1' in UICtx.__annotations__
        assert 'text2' in UICtx.__annotations__
    
    def test_uictx_has_position_attributes(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: Position attributes vorhanden.
        
        TESTBASIS:
            Class UICtx - Position attributes
        
        TESTVERFAHREN:
            Structural: positionx_btn, positiony_btn, widths
        
        Erwartung: UICtx hat button position/size attributes.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'positionx_btn' in UICtx.__annotations__
        assert 'positiony_btn' in UICtx.__annotations__
        assert 'button_width' in UICtx.__annotations__
        assert 'button_height' in UICtx.__annotations__
    
    def test_uictx_has_additional_buttons(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: aufnahmen, recover buttons.
        
        TESTBASIS:
            Class UICtx - Additional UI elements
        
        TESTVERFAHREN:
            Structural: aufnahmen_button, recover_button
        
        Erwartung: UICtx hat aufnahmen_button und recover_button.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'aufnahmen_button' in UICtx.__annotations__
        assert 'recover_button' in UICtx.__annotations__
    
    def test_uictx_has_text_box_rect(self):
        """GIVEN: UICtx, WHEN: Check attributes, THEN: text_box_rect vorhanden.
        
        TESTBASIS:
            Class UICtx - Text box attribute
        
        TESTVERFAHREN:
            Structural: text_box_rect
        
        Erwartung: UICtx hat text_box_rect.
        """
        # ACT
        from crazycar.sim.loop import UICtx
        
        # THEN
        assert 'text_box_rect' in UICtx.__annotations__
