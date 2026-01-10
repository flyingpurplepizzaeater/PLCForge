# GUI Module

<!-- AUTO-MANAGED: module-description -->
PyQt6-based desktop interface with project explorer, code editor tabs, real-time device monitor, and AI assistant dock. Provides multi-vendor PLC programming environment with integrated password recovery wizard.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
gui/
├── __init__.py
└── main_window.py           # Main application window with all UI components
```

**UI Layout:**
- Left panel: Project explorer (QTreeWidget)
- Center top: Code editor tabs (QTabWidget)
- Center bottom: Device monitor table (QTableWidget)
- Right dock: AI assistant with input/output (QDockWidget)
- Top: Menu bar and toolbar
- Bottom: Status bar
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
- Vendor selector: Siemens, Allen-Bradley, Delta, Omron, Generic IEC
- Language selector: Structured Text, Ladder, Function Block, Instruction List
- Input/output text areas for prompts and generated code
- "Generate Code" button triggers AI generation

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

- `PyQt6>=6.5` - Core GUI framework (QMainWindow, QWidget, QSplitter, etc.)
- `plcforge.pal.unified_api` - DeviceFactory, UnifiedPLC, Vendor
- `plcforge.drivers.base` - PLCMode, DeviceInfo
- `plcforge.recovery.engine` - RecoveryEngine, RecoveryTarget, RecoveryConfig, RecoveryMethod, RecoveryProgress, RecoveryResult, RecoveryStatus
- `plcforge.security.audit_log` - get_logger()
<!-- END AUTO-MANAGED -->
