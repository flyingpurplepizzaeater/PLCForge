# PLCForge

<!-- AUTO-MANAGED: project-description -->
Multi-vendor PLC programming desktop application with AI-assisted code generation and password recovery capabilities. Supports Siemens S7-300/400/1200/1500, Allen-Bradley CompactLogix/ControlLogix, Delta DVP series, and Omron CP/CJ/NX/NJ series PLCs through a unified Protocol Abstraction Layer (PAL).
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: build-commands -->
## Build Commands

```bash
# Run GUI application
python -m plcforge.main

# CLI commands
python -m plcforge.main connect <ip> --vendor siemens --rack 0 --slot 1
python -m plcforge.main read <ip> <tag> --vendor siemens
python -m plcforge.main write <ip> <tag> <value> --vendor siemens
python -m plcforge.main recover <file> --vendor siemens --method file dictionary --confirm
python -m plcforge.main scan <subnet>
```
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
plcforge/
├── __init__.py              # Exports connect(), DeviceFactory, UnifiedPLC
├── main.py                  # Entry point with GUI and CLI modes
├── gui/
│   ├── __init__.py
│   └── main_window.py       # PyQt6 main window with project explorer, editor, monitor
├── pal/
│   ├── __init__.py
│   └── unified_api.py       # Vendor-agnostic interface, auto-detection
├── drivers/
│   ├── base.py              # Abstract PLCDevice interface
│   ├── siemens/
│   │   ├── __init__.py
│   │   ├── s7comm.py        # S7comm driver (python-snap7)
│   │   └── project_parser.py # TIA Portal .ap file parser
│   ├── allen_bradley/
│   │   ├── __init__.py
│   │   └── cip_driver.py    # CIP/EtherNet-IP driver (pycomm3)
│   ├── delta/
│   │   ├── __init__.py
│   │   └── modbus_driver.py # Modbus TCP/RTU driver
│   └── omron/
│       ├── __init__.py
│       └── fins_driver.py   # FINS protocol driver
├── ai/
│   ├── __init__.py
│   └── code_generator.py    # LLM-powered code generation (OpenAI/Anthropic)
├── recovery/
│   ├── __init__.py
│   ├── engine.py            # Recovery orchestration
│   ├── file_parsers/        # Extract passwords from project files
│   └── vulnerabilities/     # Vendor-specific exploits
├── security/
│   └── __init__.py          # Audit logging, authorization
├── code/
│   └── __init__.py          # PLC code representations
├── utils/
│   └── __init__.py          # Utility functions
└── tests/
    ├── __init__.py          # Test suite marker
    ├── conftest.py          # Pytest fixtures (mock devices, clients, sample data)
    ├── test_ai.py           # AI code generation tests
    ├── test_drivers.py      # Driver implementation tests
    ├── test_pal.py          # Protocol Abstraction Layer tests
    └── test_recovery.py     # Password recovery engine tests
```

**Design Layers:**
- **GUI Layer**: PyQt6 interface with project explorer, code editor, device monitor, AI assistant
- **PAL Layer**: Unified API with vendor auto-detection (probes ports: S7/102, EtherNet-IP/44818, FINS/9600, Modbus/502)
- **Driver Layer**: Vendor-specific implementations of abstract PLCDevice interface
- **AI Layer**: Natural language to PLC code (Ladder/ST/FBD/IL) with safety analysis
- **Recovery Layer**: Password recovery via file parsing, dictionary, brute-force, vulnerability exploits
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Module Exports:**
- Top-level package exports PAL components: `connect()`, `DeviceFactory`, `UnifiedPLC`
- Submodules export key classes through `__init__.py`

**Driver Interface:**
- All drivers inherit from `PLCDevice` abstract base class
- Implement: `connect()`, `disconnect()`, `get_device_info()`, `read()`, `write()`
- Use enums from base: `MemoryArea`, `PLCMode`, `AccessLevel`, `BlockType`, `CodeLanguage`
- Use dataclasses: `DeviceInfo`, `ProtectionStatus`, `BlockInfo`, `TagValue`, `PLCProgram`

**Vendor Auto-Detection:**
- Protocol-specific probes on standard ports
- Siemens: COTP connection request on TCP 102
- Allen-Bradley: List Identity on TCP 44818
- Omron: FINS probe on UDP 9600
- Delta: Modbus on TCP 502

**AI Code Generation:**
- `AICodeGenerator` supports providers: "openai", "anthropic"
- `CodeTarget` specifies vendor, model, language
- Returns `GeneratedCode` with code, explanation, safety_issues
- System prompts include vendor-specific guidelines and IEC 61131-3 compliance
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: patterns -->
## Patterns

**Error Handling:**
- Drivers store errors in `_last_error` property
- Connection failures raise descriptive `ConnectionError` with vendor context
- Import checks use try/except with vendor-specific flags (`SNAP7_AVAILABLE`, `PYCOMM3_AVAILABLE`)
- Missing libraries raise `ImportError` with installation instructions in driver `__init__`

**Factory Pattern:**
- `DeviceFactory.create()` with vendor auto-detection or explicit specification
- Driver registry: `DeviceFactory.register_driver(vendor, driver_class)`
- Converts string vendors to `Vendor` enum automatically

**Dataclass Usage:**
- Immutable configuration objects: `CodeTarget`, `DeviceInfo`
- Result objects with metadata: `GeneratedCode`, `TagValue`, `BlockInfo`
- Use `field(default_factory=dict)` for mutable defaults

**Protocol Probing:**
- Socket-based protocol detection with timeout
- Send vendor-specific handshake, validate response format
- Return boolean success/failure, catch all exceptions

**CLI Pattern:**
- Subparsers for each command (gui, connect, read, write, recover, scan)
- `--confirm` flag required for destructive operations (password recovery)
- Main entry delegates to `cli_main()` with argparse

**Application Setup:**
- `setup_environment()` creates `~/.plcforge` directories (audit, cache, projects)
- Called before launching GUI or CLI
- Ensures sys.path includes application directory

**Testing Patterns:**
- Pytest fixtures in `conftest.py` for all vendors (mock clients, device info, protection status)
- Mock vendor libraries: `mock_snap7_client`, `mock_pycomm3_plc`, `mock_modbus_client`, `mock_fins_client`
- Patch driver imports with `@patch("plcforge.drivers.vendor.module.Library")`
- `MockPLCDevice` class for testing PAL without real hardware
- Sample TIA Portal XML and temp project files via `tmp_path` fixture
- Test authorization with `patch.object(engine, "_confirm_authorization", return_value=True)`

**Version Control:**
- `.gitignore` excludes Python artifacts (`__pycache__/`, `*.pyc`, `*.egg-info/`)
- Virtual environments ignored (`venv/`, `.venv/`, `ENV/`)
- IDE files excluded (`.idea/`, `.vscode/`)
- User data directory `~/.plcforge/` and log files ignored
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

**Communication Libraries:**
- `python-snap7>=1.3` - Siemens S7comm protocol
- `pycomm3>=1.2` - Allen-Bradley CIP/EtherNet-IP
- `pymodbus>=3.5` - Delta Modbus TCP/RTU
- `pyfins>=1.0` - Omron FINS protocol

**GUI Framework:**
- `PyQt6>=6.5` - Desktop interface
- `pyqtgraph>=0.13` - Real-time data visualization

**AI/LLM:**
- `openai>=1.0` - GPT-4 for code generation
- `anthropic>=0.20` - Claude as alternative
- `chromadb>=0.4` - Vector DB for RAG
- `langchain>=0.1` - LLM orchestration

**Security:**
- `cryptography>=41.0` - Password recovery algorithms

**File Parsing:**
- `zipfile`, `xml.etree` - TIA Portal .ap files
- `olefile>=0.46` - Legacy project formats

**Testing:**
- `pytest>=7.0` - Test framework
- `unittest.mock` - Mocking (standard library)
<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Manual Notes

Add project-specific notes here that should not be auto-updated.
<!-- END MANUAL -->
