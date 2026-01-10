"""
PLCForge GUI Themes

Provides light and dark mode themes with syntax highlighting for IEC 61131-3 languages.
"""

from plcforge.gui.themes.syntax_highlighter import (
    InstructionListHighlighter,
    LadderHighlighter,
    StructuredTextHighlighter,
)
from plcforge.gui.themes.theme_manager import Theme, ThemeManager

__all__ = [
    'ThemeManager',
    'Theme',
    'StructuredTextHighlighter',
    'LadderHighlighter',
    'InstructionListHighlighter',
]
