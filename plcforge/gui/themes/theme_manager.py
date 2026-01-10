"""
Theme Manager for PLCForge

Supports light and dark themes with seamless switching.
"""

from dataclasses import dataclass
from enum import Enum

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


class Theme(Enum):
    """Available themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system


@dataclass
class ThemeColors:
    """Theme color definitions"""
    # Background colors
    background: str
    background_alt: str
    background_panel: str

    # Text colors
    text_primary: str
    text_secondary: str
    text_disabled: str

    # Accent colors
    accent_primary: str
    accent_secondary: str
    accent_success: str
    accent_warning: str
    accent_error: str

    # Border colors
    border: str
    border_focus: str

    # Syntax highlighting colors
    syntax_keyword: str
    syntax_type: str
    syntax_string: str
    syntax_number: str
    syntax_comment: str
    syntax_function: str
    syntax_operator: str
    syntax_variable: str


# Light theme colors
LIGHT_THEME = ThemeColors(
    # Backgrounds
    background="#FFFFFF",
    background_alt="#F5F5F5",
    background_panel="#FAFAFA",

    # Text
    text_primary="#212121",
    text_secondary="#757575",
    text_disabled="#BDBDBD",

    # Accents
    accent_primary="#1976D2",
    accent_secondary="#455A64",
    accent_success="#388E3C",
    accent_warning="#F57C00",
    accent_error="#D32F2F",

    # Borders
    border="#E0E0E0",
    border_focus="#1976D2",

    # Syntax highlighting
    syntax_keyword="#0000FF",
    syntax_type="#008080",
    syntax_string="#008000",
    syntax_number="#098658",
    syntax_comment="#808080",
    syntax_function="#795E26",
    syntax_operator="#000000",
    syntax_variable="#001080",
)


# Dark theme colors
DARK_THEME = ThemeColors(
    # Backgrounds
    background="#1E1E1E",
    background_alt="#252526",
    background_panel="#2D2D30",

    # Text
    text_primary="#D4D4D4",
    text_secondary="#9E9E9E",
    text_disabled="#616161",

    # Accents
    accent_primary="#569CD6",
    accent_secondary="#4EC9B0",
    accent_success="#6A9955",
    accent_warning="#DCDCAA",
    accent_error="#F44747",

    # Borders
    border="#3C3C3C",
    border_focus="#569CD6",

    # Syntax highlighting
    syntax_keyword="#569CD6",
    syntax_type="#4EC9B0",
    syntax_string="#CE9178",
    syntax_number="#B5CEA8",
    syntax_comment="#6A9955",
    syntax_function="#DCDCAA",
    syntax_operator="#D4D4D4",
    syntax_variable="#9CDCFE",
)


class ThemeManager:
    """
    Manages application themes and provides theme switching.

    Usage:
        theme_manager = ThemeManager(app)
        theme_manager.set_theme(Theme.DARK)
    """

    _instance = None

    def __new__(cls, app: QApplication = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app: QApplication = None):
        if self._initialized:
            return

        self._app = app or QApplication.instance()
        self._current_theme = Theme.LIGHT
        self._colors = LIGHT_THEME
        self._initialized = True

    @property
    def current_theme(self) -> Theme:
        """Get current theme."""
        return self._current_theme

    @property
    def colors(self) -> ThemeColors:
        """Get current theme colors."""
        return self._colors

    def set_theme(self, theme: Theme) -> None:
        """
        Set application theme.

        Args:
            theme: Theme to apply
        """
        if theme == Theme.AUTO:
            # Detect system theme (simplified - always use dark for now)
            theme = Theme.DARK

        self._current_theme = theme
        self._colors = DARK_THEME if theme == Theme.DARK else LIGHT_THEME
        self._apply_theme()

    def toggle_theme(self) -> Theme:
        """Toggle between light and dark themes."""
        new_theme = Theme.LIGHT if self._current_theme == Theme.DARK else Theme.DARK
        self.set_theme(new_theme)
        return new_theme

    def _apply_theme(self) -> None:
        """Apply the current theme to the application."""
        if not self._app:
            return

        # Create palette
        palette = QPalette()
        colors = self._colors

        # Set palette colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.background_alt))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.background_panel))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors.background_panel))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text_primary))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors.accent_error))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors.accent_primary))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.accent_primary))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors.text_disabled))

        # Disabled colors
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(colors.text_disabled)
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(colors.text_disabled)
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(colors.text_disabled)
        )

        self._app.setPalette(palette)

        # Apply stylesheet for more control
        self._app.setStyleSheet(self._generate_stylesheet())

    def _generate_stylesheet(self) -> str:
        """Generate Qt stylesheet for current theme."""
        colors = self._colors

        return f"""
        /* Global */
        QWidget {{
            background-color: {colors.background};
            color: {colors.text_primary};
            font-family: "Segoe UI", "Roboto", sans-serif;
        }}

        /* Main Window */
        QMainWindow {{
            background-color: {colors.background};
        }}

        /* Menu Bar */
        QMenuBar {{
            background-color: {colors.background_panel};
            color: {colors.text_primary};
            border-bottom: 1px solid {colors.border};
        }}

        QMenuBar::item:selected {{
            background-color: {colors.accent_primary};
            color: white;
        }}

        QMenu {{
            background-color: {colors.background_panel};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
        }}

        QMenu::item:selected {{
            background-color: {colors.accent_primary};
            color: white;
        }}

        /* Toolbar */
        QToolBar {{
            background-color: {colors.background_panel};
            border-bottom: 1px solid {colors.border};
            spacing: 5px;
            padding: 5px;
        }}

        QToolBar QPushButton {{
            background-color: {colors.background_alt};
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 60px;
        }}

        QToolBar QPushButton:hover {{
            background-color: {colors.accent_primary};
            color: white;
            border-color: {colors.accent_primary};
        }}

        QToolBar QPushButton:pressed {{
            background-color: {colors.accent_secondary};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {colors.accent_primary};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {colors.accent_secondary};
        }}

        QPushButton:pressed {{
            background-color: {colors.background_panel};
        }}

        QPushButton:disabled {{
            background-color: {colors.text_disabled};
            color: {colors.text_secondary};
        }}

        /* Text Inputs */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.background_alt};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {colors.accent_primary};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors.border_focus};
        }}

        /* Combo Box */
        QComboBox {{
            background-color: {colors.background_alt};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 6px;
            min-width: 100px;
        }}

        QComboBox:hover {{
            border-color: {colors.border_focus};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {colors.background_panel};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            selection-background-color: {colors.accent_primary};
        }}

        /* Check Box */
        QCheckBox {{
            color: {colors.text_primary};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {colors.border};
            border-radius: 3px;
            background-color: {colors.background_alt};
        }}

        QCheckBox::indicator:checked {{
            background-color: {colors.accent_primary};
            border-color: {colors.accent_primary};
        }}

        /* Tree Widget */
        QTreeWidget {{
            background-color: {colors.background_alt};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            alternate-background-color: {colors.background_panel};
        }}

        QTreeWidget::item:selected {{
            background-color: {colors.accent_primary};
            color: white;
        }}

        QTreeWidget::item:hover {{
            background-color: {colors.background_panel};
        }}

        QTreeWidget::branch {{
            background-color: {colors.background_alt};
        }}

        /* Table Widget */
        QTableWidget {{
            background-color: {colors.background_alt};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            gridline-color: {colors.border};
            alternate-background-color: {colors.background_panel};
        }}

        QTableWidget::item:selected {{
            background-color: {colors.accent_primary};
            color: white;
        }}

        QHeaderView::section {{
            background-color: {colors.background_panel};
            color: {colors.text_primary};
            border: none;
            border-right: 1px solid {colors.border};
            border-bottom: 1px solid {colors.border};
            padding: 6px;
            font-weight: bold;
        }}

        /* Tab Widget */
        QTabWidget::pane {{
            background-color: {colors.background};
            border: 1px solid {colors.border};
            border-top: none;
        }}

        QTabBar::tab {{
            background-color: {colors.background_panel};
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {colors.background};
            border-bottom: 2px solid {colors.accent_primary};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {colors.background_alt};
        }}

        QTabBar::close-button {{
            image: none;
            subcontrol-position: right;
        }}

        /* Group Box */
        QGroupBox {{
            color: {colors.text_primary};
            border: 1px solid {colors.border};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 12px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: {colors.background};
            color: {colors.accent_primary};
        }}

        /* Progress Bar */
        QProgressBar {{
            background-color: {colors.background_alt};
            border: 1px solid {colors.border};
            border-radius: 4px;
            text-align: center;
            color: {colors.text_primary};
        }}

        QProgressBar::chunk {{
            background-color: {colors.accent_primary};
            border-radius: 3px;
        }}

        /* Scroll Bar */
        QScrollBar:vertical {{
            background-color: {colors.background_alt};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors.border};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors.text_disabled};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background-color: {colors.background_alt};
            height: 12px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {colors.border};
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {colors.text_disabled};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* Dock Widget */
        QDockWidget {{
            color: {colors.text_primary};
            titlebar-close-icon: none;
        }}

        QDockWidget::title {{
            background-color: {colors.background_panel};
            padding: 6px;
            border-bottom: 1px solid {colors.border};
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: {colors.accent_primary};
            color: white;
        }}

        QStatusBar QLabel {{
            color: white;
            padding: 2px 8px;
        }}

        /* Splitter */
        QSplitter::handle {{
            background-color: {colors.border};
        }}

        QSplitter::handle:horizontal {{
            width: 4px;
        }}

        QSplitter::handle:vertical {{
            height: 4px;
        }}

        /* Dialog */
        QDialog {{
            background-color: {colors.background};
        }}

        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}

        /* Labels */
        QLabel {{
            color: {colors.text_primary};
        }}

        /* Message Box */
        QMessageBox {{
            background-color: {colors.background};
        }}

        QMessageBox QLabel {{
            color: {colors.text_primary};
        }}
        """

    def get_editor_stylesheet(self) -> str:
        """Get stylesheet specifically for code editor."""
        colors = self._colors

        return f"""
        QTextEdit, QPlainTextEdit {{
            font-family: "Consolas", "Monaco", "Courier New", monospace;
            font-size: 12px;
            line-height: 1.5;
            background-color: {colors.background_alt};
            color: {colors.text_primary};
            border: none;
            selection-background-color: {colors.accent_primary};
            selection-color: white;
        }}
        """
