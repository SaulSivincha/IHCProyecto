#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global Theme Configuration
Defines the color palette and semantic colors for the entire application.
All colors are in BGR format (Blue, Green, Red) for OpenCV compatibility.
"""

class ColorPalette:
    """Primitive colors (BGR)"""
    # Grayscale
    WHITE = (255, 255, 255)
    LIGHT_GRAY = (240, 240, 240)
    GRAY = (150, 150, 150)
    DARK_GRAY = (100, 100, 100)
    DARKER_GRAY = (50, 50, 50)
    CHARCOAL = (40, 40, 40)
    BLACK = (0, 0, 0)
    
    # "Adventure Mode" Palette (Bright & Colorful)
    BLUE_SKY = (235, 206, 135)    # #87CEEB (BGR) - Background Main
    CYAN_LIGHT = (250, 247, 224)  # #E0F7FA (BGR) - Background Gradient End
    
    # Semantic Colors (High Saturation for Buttons/Highlights)
    ORANGE_VIVID = (0, 140, 251)  # #FB8C00 (BGR)
    BLUE_VIVID = (255, 144, 30)   # #1E90FF (BGR) - Dodger Blue (Darker than Sky)
    GREEN_VIVID = (50, 205, 50)   # #32CD32 (BGR) - Lime Green
    RED_VIVID = (34, 34, 178)     # #B22222 (BGR) - Firebrick (Darker Red)
    
    # Legacy Soft Colors (kept for compatibility but remapped if needed)
    GREEN_SOFT = (100, 255, 100)
    BLUE_SOFT_PASTEL = (255, 200, 100) 
    RED_SOFT_PASTEL = (100, 100, 255)
    
    # Text Colors
    BLUE_DARK_TEXT = (100, 50, 25) # #193264 (BGR) - Deep Blue for text (High contrast on Sky Blue)


class Theme:
    """Semantic color definitions - Matching 'Adventure Mode' Style"""
    
    # --- Typography ---
    # High contrast text for light backgrounds
    TEXT_PRIMARY = ColorPalette.BLUE_DARK_TEXT
    TEXT_SECONDARY = ColorPalette.CHARCOAL
    TEXT_DISABLED = ColorPalette.GRAY
    TEXT_HIGHLIGHT = ColorPalette.ORANGE_VIVID
    TEXT_ON_DARK = ColorPalette.WHITE  # For buttons with dark background
    TEXT_ON_LIGHT = ColorPalette.BLUE_DARK_TEXT # For light buttons/panels
    
    # --- Backgrounds ---
    BG_MAIN = ColorPalette.BLUE_SKY
    BG_GRADIENT_START = ColorPalette.BLUE_SKY
    BG_GRADIENT_END = ColorPalette.CYAN_LIGHT
    BG_OVERLAY = (50, 50, 50)
    BG_HEADER = ColorPalette.ORANGE_VIVID
    BG_PANEL = ColorPalette.WHITE       # Semi-transparent panels usually
    BG_INPUT = ColorPalette.WHITE       # Input fields should be white
    
    # --- Buttons / UI Elements ---
    # Standardized Button Colors
    BTN_PRIMARY_BG = ColorPalette.BLUE_VIVID
    BTN_PRIMARY_TEXT = ColorPalette.WHITE
    
    BTN_SECONDARY_BG = ColorPalette.WHITE
    BTN_SECONDARY_TEXT = ColorPalette.BLUE_DARK_TEXT
    
    BTN_SUCCESS_BG = ColorPalette.GREEN_VIVID
    BTN_SUCCESS_TEXT = ColorPalette.WHITE
    
    BTN_WARNING_BG = ColorPalette.ORANGE_VIVID
    BTN_WARNING_TEXT = ColorPalette.WHITE
    
    BTN_DANGER_BG = ColorPalette.RED_VIVID
    BTN_DANGER_TEXT = ColorPalette.WHITE
    
    # Generic mappings for backward compatibility
    # INFO changed to VIVID blue (darker) for white text contrast
    INFO = ColorPalette.BLUE_VIVID      
    SUCCESS = ColorPalette.GREEN_VIVID
    WARNING = ColorPalette.ORANGE_VIVID 
    ERROR = ColorPalette.RED_VIVID
    
    BORDER_DEFAULT = ColorPalette.WHITE
    BORDER_FOCUS = ColorPalette.ORANGE_VIVID
    BORDER_ACTIVE = ColorPalette.ORANGE_VIVID
    
    # --- Difficulty Levels ---
    DIFFICULTY_BASIC = ColorPalette.GREEN_VIVID
    DIFFICULTY_INTERMEDIATE = ColorPalette.ORANGE_VIVID
    DIFFICULTY_ADVANCED = ColorPalette.RED_VIVID
    
    # --- Instrument / Piano ---
    KEY_WHITE = ColorPalette.WHITE
    KEY_BLACK = ColorPalette.BLACK
    KEY_HIGHLIGHT_WHITE = ColorPalette.ORANGE_VIVID
    KEY_HIGHLIGHT_BLACK = ColorPalette.BLUE_VIVID
    
    # --- Progress Bars ---
    PROGRESS_BG = ColorPalette.LIGHT_GRAY
    PROGRESS_FILL = ColorPalette.GREEN_VIVID
    PROGRESS_BORDER = ColorPalette.WHITE
    
    # --- Pass-through Aliases (for compatibility) ---
    BLUE_SOFT = ColorPalette.BLUE_VIVID # Remapped to Vivid for contrast
    BLUE_DARK = ColorPalette.BLUE_DARK_TEXT
    GREEN_SOFT = ColorPalette.GREEN_VIVID
    RED_SOFT = ColorPalette.RED_VIVID
    ORANGE_SOFT = ColorPalette.ORANGE_VIVID
    
    # Direct access to VIVID colors (required by some UI files)
    BLUE_VIVID = ColorPalette.BLUE_VIVID
    GREEN_VIVID = ColorPalette.GREEN_VIVID
    RED_VIVID = ColorPalette.RED_VIVID
    ORANGE_VIVID = ColorPalette.ORANGE_VIVID
    GRAY = ColorPalette.GRAY
    LIGHT_GRAY = ColorPalette.LIGHT_GRAY

    # Selection
    SELECTION_BG = ColorPalette.ORANGE_VIVID
    SELECTION_BORDER = ColorPalette.WHITE

    @staticmethod
    def to_hex(bgr_tuple):
        """Converts BGR tuple to Hex string for Qt/CSS"""
        b, g, r = bgr_tuple
        return f"#{r:02x}{g:02x}{b:02x}"
