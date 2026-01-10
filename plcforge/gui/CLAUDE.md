# GUI Module

<!-- AUTO-MANAGED: module-description -->
PyQt6-based desktop interface with project explorer, code editor tabs, real-time device monitor, and AI assistant dock. Provides multi-vendor PLC programming environment with integrated password recovery wizard.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
gui/
├── __init__.py
├── main_window.py           # Main application window with all UI components
└── themes/
    ├── __init__.py          # Exports ThemeManager, Theme, highlighters
    ├── theme_manager.py     # Theme management (light/dark modes)
    └── syntax_highlighter.py # IEC 61131-3 syntax highlighting
```

**UI Layout:**
- Left panel: Project explorer (QTreeWidget)
- Center top: Code editor tabs (QTabWidget)
- Center bottom: Device monitor table (QTableWidget)
- Right dock: AI assistant with input/output (QDockWidget)
- Top: Menu bar and toolbar
- Bottom: Status bar

**Theme System:**
- `ThemeManager` singleton manages application theme
- `ThemeColors` dataclass with background, text, accent, border, syntax colors
- Light theme (`LIGHT_THEME`) and dark theme (`DARK_THEME`) presets
- Theme switching via `set_theme()` and `toggle_theme()`
- QPalette updates applied to entire application

**Syntax Highlighting:**
- `BasePLCHighlighter` abstract base for all language highlighters
- `StructuredTextHighlighter` for IEC 61131-3 ST
- `LadderHighlighter` for textual Ladder representation
- `InstructionListHighlighter` for IL
- Multi-line comment support with state tracking
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Window Structure:**
- `PLCForgeMainWindow` inherits from `QMainWindow`
- Minimum size: 1200x800 pixels
- Uses `QSplitter` for resizable panels

**Component Management:**
- `_connected_devices: Dict[str, UnifiedPLC]` - Active PLC connections
- `_current_project: Optional[Path]` - Current project path
- `_audit_logger` - Security audit logging

**Menu Structure:**
- File: New Project, Open Project, Save, Save As, Exit
- PLC: Connect, Disconnect, device operations
- AI: Code generation
- Tools: Password Recovery

**AI Assistant Integration:**
- Vendor selector: Siemens, Allen-Bradley, Delta, Omron, Generic IEC (combo box)
- Language selector: Structured Text, Ladder, Function Block, Instruction List (combo box)
- Input text area with placeholder: "Describe what you want to create... Example: Create a conveyor control with 3 stations and emergency stop"
- Output text area for generated code (read-only)
- "Generate Code" button triggers AI generation
- Docked to right side or bottom of main window

**Welcome Tab:**
- Displayed by default on application startup
- Quick start instructions: Connect to PLC (Ctrl+K), Open Project, AI Code Generation, Password Recovery
- Lists supported vendors: Siemens S7-300/400/1200/1500, Allen-Bradley CompactLogix/ControlLogix, Delta DVP, Omron CP/CJ/NX/NJ, Mitsubishi MELSEC-Q/L/iQ-R/iQ-F, Beckhoff TwinCAT 2/3, Schneider Modicon M340/M580/Premium/Quantum
- Read-only QTextEdit with HTML content

**Theme Manager:**
- Singleton pattern with `__new__` override
- `_initialized` flag to prevent re-initialization
- `current_theme` property returns active theme
- `colors` property returns current `ThemeColors` instance
- Auto theme detection (simplified - defaults to dark)

**Syntax Highlighting:**
- `_setup_formats()` creates `QTextCharFormat` objects from theme colors
- `_setup_rules()` defines regex patterns and formats (override in subclasses)
- `highlightBlock()` applies rules to text blocks
- `update_theme()` refreshes formats and re-highlights all text
- Keywords, types, functions, operators, strings, numbers, comments each have dedicated formats
- IEC 61131-3 keywords: PROGRAM, FUNCTION_BLOCK, VAR, IF, FOR, WHILE, etc.
- Standard functions: ABS, SQRT, ADD, SEL, TON, CTU, R_TRIG, etc.

**Device Monitor:**
- Columns: Tag, Value, Type, Address, Forcing, Trend
- Real-time PLC tag monitoring
- Uses `QHeaderView.ResizeMode.Stretch`

**Tabs:**
- Welcome tab shown by default
- Closable tabs with `tabCloseRequested` signal
- Dynamic tab creation for opened files
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `PyQt6>=6.5` - Core GUI framework (QMainWindow, QWidget, QSplitter, QSyntaxHighlighter, QTextCharFormat, QPalette, QColor, etc.)
- `plcforge.pal.unified_api` - DeviceFactory, UnifiedPLC, Vendor
- `plcforge.drivers.base` - PLCMode, DeviceInfo
- `plcforge.recovery.engine` - RecoveryEngine, RecoveryTarget, RecoveryConfig, RecoveryMethod, RecoveryProgress, RecoveryResult, RecoveryStatus
- `plcforge.security.audit_log` - get_logger()
- `plcforge.gui.themes` - ThemeManager, Theme, StructuredTextHighlighter
- `re` - Regex for syntax highlighting patterns (standard library)
<!-- END AUTO-MANAGED -->
