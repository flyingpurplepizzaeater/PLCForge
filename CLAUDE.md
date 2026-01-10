# PLCForge

<!-- AUTO-MANAGED: project-description -->
Multi-vendor PLC programming desktop application with AI-assisted code generation, password recovery, and security scanning capabilities. Supports Siemens S7-300/400/1200/1500, Allen-Bradley CompactLogix/ControlLogix, Delta DVP series, Omron CP/CJ/NX/NJ series, Beckhoff TwinCAT 2/3, Mitsubishi MELSEC-Q/L/iQ-R/iQ-F, and Schneider Modicon M340/M580/Premium/Quantum PLCs through a unified Protocol Abstraction Layer (PAL). Includes network scanning, real-time trend logging, and syntax highlighting for IEC 61131-3 languages.
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
.github/
└── workflows/
    ├── ci.yml               # CI pipeline (test matrix: Ubuntu/Windows, Python 3.10-3.12, pytest+coverage, linting)
    └── release.yml          # PyPI publishing on GitHub releases

plcforge/
├── __init__.py              # Exports connect(), DeviceFactory, UnifiedPLC
├── main.py                  # Entry point with GUI and CLI modes
├── gui/
│   ├── __init__.py
│   ├── main_window.py       # PyQt6 main window with project explorer, editor, monitor
│   └── themes/
│       ├── __init__.py
│       ├── theme_manager.py # Light/dark theme support
│       └── syntax_highlighter.py # IEC 61131-3 syntax highlighting
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
│   ├── omron/
│   │   ├── __init__.py
│   │   └── fins_driver.py   # FINS protocol driver
│   ├── beckhoff/
│   │   ├── __init__.py
│   │   └── ads_driver.py    # TwinCAT ADS driver (pyads)
│   ├── mitsubishi/
│   │   ├── __init__.py
│   │   └── mc_protocol.py   # MC Protocol/SLMP driver
│   └── schneider/
│       ├── __init__.py
│       └── modbus_driver.py # Modicon Modbus TCP/RTU driver
├── ai/
│   ├── __init__.py
│   └── code_generator.py    # LLM-powered code generation (OpenAI/Anthropic)
├── recovery/
│   ├── __init__.py
│   ├── engine.py            # Recovery orchestration
│   ├── file_parsers/        # Extract passwords from project files
│   └── vulnerabilities/     # Vendor-specific exploits
├── security/
│   ├── __init__.py          # Audit logging, authorization
│   ├── audit_log.py         # AuditLogger, AuditEntry
│   └── network_scanner.py   # PLC network discovery, security scanning
├── code/
│   └── __init__.py          # PLC code representations
├── utils/
│   ├── __init__.py
│   └── trend_logger.py      # Real-time data logging (CSV/JSON/SQLite)
└── tests/
    ├── __init__.py          # Test suite marker
    ├── conftest.py          # Pytest fixtures (mock devices, clients, sample data)
    ├── test_ai.py           # AI code generation tests
    ├── test_drivers.py      # Driver implementation tests
    ├── test_pal.py          # Protocol Abstraction Layer tests
    ├── test_recovery.py     # Password recovery engine tests
    └── test_new_features.py # v1.1.0 feature tests (new drivers, themes, highlighters, scanner, trend logger)
```

**Design Layers:**
- **GUI Layer**: PyQt6 interface with project explorer, code editor, device monitor, AI assistant, theme system (light/dark modes), syntax highlighting (ST/LD/IL/FBD)
- **PAL Layer**: Unified API with vendor auto-detection (probes ports: S7/102, EtherNet-IP/44818, FINS/9600, Modbus/502, ADS/851, MC Protocol/5000)
- **Driver Layer**: Vendor-specific implementations of abstract PLCDevice interface (7 vendors: Siemens, Allen-Bradley, Delta, Omron, Beckhoff, Mitsubishi, Schneider)
- **AI Layer**: Natural language to PLC code (Ladder/ST/FBD/IL) with safety analysis
- **Recovery Layer**: Password recovery via file parsing, dictionary, brute-force, vulnerability exploits
- **Security Layer**: Network scanning with subnet discovery, PLC detection, vulnerability assessment (CVE tracking), audit logging
- **Utils Layer**: Real-time trend logging (CSV/JSON/SQLite export), data export, helper functions
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
- Delta/Schneider: Modbus on TCP 502
- Beckhoff: ADS on TCP 851/48898
- Mitsubishi: MC Protocol on TCP 5000

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
- Import checks use try/except with vendor-specific flags (`SNAP7_AVAILABLE`, `PYCOMM3_AVAILABLE`, `PYMODBUS_AVAILABLE`, `PYADS_AVAILABLE`)
- Missing libraries raise `ImportError` with installation instructions in driver `__init__`
- Conditional module-level constants: `MEMORY_AREA_MAP` only populated when dependency available (empty dict fallback)

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
- Pytest fixtures in `tests/conftest.py` for all vendors (mock clients, device info, protection status)
- `temp_project_file` fixture: Creates temporary TIA Portal project file (.ap17) with sample XML structure using zipfile, contains minimal project with CPU 1516-3 PN/DP device
- Mock vendor libraries: `mock_snap7_client`, `mock_pycomm3_plc`, `mock_modbus_client`, `mock_fins_client`, `mock_pyads_connection`
- Patch driver imports with `@patch("plcforge.drivers.vendor.module.Library")`
- `MockPLCDevice` class for testing PAL without real hardware
- Sample TIA Portal XML structure: `<?xml version="1.0"?><Document><Engineering version="V17"><Project><Device><DeviceItem></DeviceItem></Device></Project></Engineering></Document>`
- Test authorization with `patch.object(engine, "_confirm_authorization", return_value=True)`
- Conditional test skipping: Check availability flags (`SNAP7_AVAILABLE`, `PYCOMM3_AVAILABLE`, `PYMODBUS_AVAILABLE`, `PYADS_AVAILABLE`) before instantiating drivers, use `pytest.skip()` when dependencies missing

**Theme/UI Patterns:**
- Singleton pattern for `ThemeManager` with `__new__` override
- Dataclasses for theme colors (`ThemeColors`) with syntax highlighting palette
- `BasePLCHighlighter` abstract class for all language highlighters
- Multi-line comment handling in `highlightBlock()` with state tracking
- Theme updates trigger `rehighlight()` on all active highlighters

**Security Patterns:**
- Thread-safe scanning with `ThreadPoolExecutor` and progress callbacks
- Dataclasses for scan results (`DeviceScanResult`, `NetworkScanResult`, `SecurityIssue`)
- Risk level enum (`RiskLevel.CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`)
- Known vulnerability database with CVE tracking
- Port scanning with protocol detection (PLC_PORTS dict maps port to vendor/protocol)

**Data Logging Patterns:**
- Thread-safe circular buffer (`TrendBuffer`) with `deque` and `threading.Lock`
- Dataclasses for configuration (`TrendConfig`) and data points (`TrendDataPoint`)
- Export formats enum (`ExportFormat.CSV`, `JSON`, `SQLITE`)
- Background thread for continuous sampling with configurable intervals
- Optional SQLite persistence with indexed queries

**CI/CD Patterns:**
- GitHub Actions workflows in `.github/workflows/`
- CI workflow (`ci.yml`): Three jobs (test, lint, build)
  - Test job: Matrix strategy with Ubuntu/Windows, Python 3.10/3.11/3.12, runs pytest with coverage, uploads coverage.xml to Codecov (ubuntu-latest + 3.12 only)
  - Lint job: Runs ruff (ignores E501 line length) and mypy (with `--ignore-missing-imports`, allows failures with `|| true`)
  - Build job: Depends on test and lint, builds package with `python -m build`, validates with `twine check dist/*`, uploads dist artifacts
- Release workflow (`release.yml`): Triggered on GitHub release published, builds and publishes to PyPI using trusted publisher (requires id-token: write permission)
- Actions versions: `actions/checkout@v4`, `actions/setup-python@v5`, `codecov/codecov-action@v4`, `actions/upload-artifact@v4`, `pypa/gh-action-pypi-publish@release/v1`

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
- `pymodbus>=3.5` - Delta/Schneider Modbus TCP/RTU
- `pyfins>=1.0` - Omron FINS protocol
- `pyads>=3.3` - Beckhoff TwinCAT ADS protocol

**GUI Framework:**
- `PyQt6>=6.5` - Desktop interface (QMainWindow, QSplitter, QSyntaxHighlighter, QPalette)
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

**Data Logging/Scanning:**
- `sqlite3` - Persistent trend storage (standard library)
- `ipaddress` - Network scanning (standard library)
- `threading` - Background tasks (standard library)

**Testing:**
- `pytest>=7.0` - Test framework
- `unittest.mock` - Mocking (standard library)
<!-- END AUTO-MANAGED -->

<!-- MANUAL -->
## Manual Notes

Add project-specific notes here that should not be auto-updated.
<!-- END MANUAL -->
