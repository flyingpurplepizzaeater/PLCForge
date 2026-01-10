# PLCForge - Multi-Vendor PLC Programming Application

## Design Document
**Date:** 2026-01-10
**Version:** 1.0

---

## 1. Overview

PLCForge is a fully automated PLC programming desktop application supporting multiple vendors with integrated password recovery capabilities.

### Target Users
- Industrial technicians/engineers recovering lost passwords
- Security researchers conducting authorized testing
- System integrators supporting clients
- Educational/training environments

### Supported PLC Vendors

| Vendor | Models | Firmware | Protocol | Project Files |
|--------|--------|----------|----------|---------------|
| **Siemens** | S7-300, S7-400 | All | S7comm | .ap13-.ap20, STEP 7 |
| **Siemens** | S7-1200 G1 | V1.x-V4.x | S7comm/S7comm+ | .ap13-.ap20 |
| **Siemens** | S7-1200 G2 | V1.x+ | S7comm+ | .ap13-.ap20 |
| **Siemens** | S7-1500 | V1.x-V3.x+ | S7comm+ | .ap13-.ap20 |
| **Allen-Bradley** | CompactLogix | All | CIP/EtherNet-IP | .ACD, .L5X |
| **Allen-Bradley** | ControlLogix | All | CIP/EtherNet-IP | .ACD, .L5X |
| **Delta** | DVP series | All | Modbus TCP/RTU | .dvp |
| **Omron** | CP/CJ series | All | FINS | .cxp |
| **Omron** | NX/NJ series | All | FINS/CIP | .smc2 |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PLCForge Desktop App                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │   PyQt6     │  │  AI Engine   │  │     Security Module         │ │
│  │  Main GUI   │  │ (LLM + RAG)  │  │  (Audit, Auth, Compliance)  │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              Protocol Abstraction Layer (PAL)                   ││
│  │  Unified API for all vendors: connect, read, write, upload...   ││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────────┐│
│  │  Siemens  │ │Allen-Brad │ │   Delta   │ │        Omron          ││
│  │  Driver   │ │  Driver   │ │  Driver   │ │        Driver         ││
│  │snap7+custom│ │ pycomm3  │ │ pymodbus  │ │ pyFins+CIP            ││
│  └───────────┘ └───────────┘ └───────────┘ └───────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │           Project File Parsers (offline analysis)               ││
│  │   .ap13-.ap20 │ .ACD/.L5X │ .dvp  │ .cxp/.smc2                  ││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              Password Recovery Engine                            ││
│  │  Dictionary │ Brute-Force │ Vulnerability Exploits │ File Parse ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Core Dependencies
```
# Communication
python-snap7>=1.3       # Siemens S7comm
pycomm3>=1.2            # Allen-Bradley CIP/EtherNet/IP
pymodbus>=3.5           # Delta DVP (Modbus TCP/RTU)
pyfins>=1.0             # Omron FINS protocol

# GUI
PyQt6>=6.5              # Desktop interface
pyqtgraph>=0.13         # Real-time data visualization

# AI/Code Generation
openai>=1.0             # GPT-4 for code generation
anthropic>=0.20         # Claude as alternative
chromadb>=0.4           # Vector DB for RAG
langchain>=0.1          # LLM orchestration

# Security & Crypto
cryptography>=41.0      # Password recovery algorithms

# Project File Parsing
zipfile, xml.etree      # TIA Portal .ap files
olefile>=0.46           # Legacy project formats
```

---

## 4. Module Structure

```
plcforge/
├── __init__.py
├── main.py                    # Application entry point
├── gui/
│   ├── __init__.py
│   ├── main_window.py         # Main application window
│   ├── project_manager.py     # Project tree, file browser
│   ├── code_editor.py         # Ladder/ST/FBD editor
│   ├── live_monitor.py        # Online data monitoring
│   └── password_recovery.py   # Recovery wizard UI
├── drivers/
│   ├── __init__.py
│   ├── base.py                # Abstract driver interface
│   ├── siemens/
│   │   ├── __init__.py
│   │   ├── s7comm.py          # S7-300/400 communication
│   │   ├── s7comm_plus.py     # S7-1200/1500 communication
│   │   └── project_parser.py  # .ap13-.ap20 parsing
│   ├── allen_bradley/
│   │   ├── __init__.py
│   │   ├── cip_driver.py      # CIP/EtherNet/IP
│   │   └── project_parser.py  # .ACD/.L5X parsing
│   ├── delta/
│   │   ├── __init__.py
│   │   ├── modbus_driver.py   # Modbus TCP/RTU
│   │   └── project_parser.py  # .dvp parsing
│   └── omron/
│       ├── __init__.py
│       ├── fins_driver.py     # FINS for CP/CJ
│       ├── cip_driver.py      # CIP for NX/NJ
│       └── project_parser.py  # .cxp/.smc2 parsing
├── pal/
│   ├── __init__.py
│   ├── unified_api.py         # Vendor-agnostic interface
│   ├── device_factory.py      # Device creation/discovery
│   └── memory_mapping.py      # Cross-vendor memory abstraction
├── ai/
│   ├── __init__.py
│   ├── code_generator.py      # Natural language → PLC code
│   ├── code_analyzer.py       # Explain/optimize existing code
│   └── rag_engine.py          # Retrieval from PLC code examples
├── recovery/
│   ├── __init__.py
│   ├── engine.py              # Recovery orchestration
│   ├── dictionary.py          # Dictionary attack
│   ├── bruteforce.py          # Brute-force with acceleration
│   ├── vulnerabilities/
│   │   ├── __init__.py
│   │   ├── siemens_s7_300.py  # S7-300 specific exploits
│   │   ├── siemens_s7_400.py  # S7-400 specific exploits
│   │   ├── siemens_s7_1200.py # S7-1200 specific exploits
│   │   ├── allen_bradley.py   # AB specific exploits
│   │   ├── delta_dvp.py       # Delta specific exploits
│   │   └── omron.py           # Omron specific exploits
│   └── file_parsers/
│       ├── __init__.py
│       ├── tia_portal.py      # Extract from .ap files
│       ├── studio5000.py      # Extract from .ACD files
│       ├── ispsoft.py         # Extract from .dvp files
│       └── cx_programmer.py   # Extract from .cxp files
├── security/
│   ├── __init__.py
│   ├── audit_log.py           # Tamper-evident logging
│   ├── authorization.py       # User auth + access control
│   └── compliance.py          # IEC 62443 compliance checks
├── code/
│   ├── __init__.py
│   ├── ladder.py              # Ladder diagram representation
│   ├── structured_text.py     # ST code handling
│   ├── function_block.py      # FBD representation
│   └── compiler.py            # Cross-compile between formats
└── utils/
    ├── __init__.py
    ├── plc_data_types.py      # IEC 61131-3 type system
    ├── binary_utils.py        # Binary parsing helpers
    └── network_utils.py       # Network scanning utilities
```

---

## 5. Protocol Abstraction Layer (PAL)

### Base Interface

```python
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import List, Any, Optional

class MemoryArea(Enum):
    INPUT = "input"
    OUTPUT = "output"
    MEMORY = "memory"
    DATA = "data"
    TIMER = "timer"
    COUNTER = "counter"

class PLCMode(Enum):
    RUN = "run"
    STOP = "stop"
    PROGRAM = "program"
    FAULT = "fault"

class AccessLevel(Enum):
    NONE = 0
    READ = 1
    WRITE = 2
    FULL = 3

@dataclass
class DeviceInfo:
    vendor: str
    model: str
    firmware: str
    serial: str
    name: str

@dataclass
class ProtectionStatus:
    cpu_protected: bool
    project_protected: bool
    block_protected: bool
    access_level: AccessLevel

class PLCDevice(ABC):
    """Abstract base for all PLC drivers"""

    @abstractmethod
    def connect(self, ip: str, **kwargs) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        pass

    @abstractmethod
    def get_protection_status(self) -> ProtectionStatus:
        pass

    @abstractmethod
    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        pass

    @abstractmethod
    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        pass

    @abstractmethod
    def read_tag(self, tag_name: str) -> Any:
        pass

    @abstractmethod
    def write_tag(self, tag_name: str, value: Any) -> bool:
        pass

    @abstractmethod
    def upload_program(self) -> 'PLCProgram':
        pass

    @abstractmethod
    def download_program(self, program: 'PLCProgram') -> bool:
        pass

    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> bool:
        pass

    @abstractmethod
    def get_mode(self) -> PLCMode:
        pass

    @abstractmethod
    def authenticate(self, password: str) -> bool:
        pass
```

---

## 6. Password Recovery Engine

### Recovery Methods

| Method | Offline | Online | Speed | Success Rate |
|--------|---------|--------|-------|--------------|
| File Parse | Yes | No | Instant | High (older files) |
| Dictionary | Yes | Yes | Fast | Medium |
| Brute-force | Yes | Slow | Variable | Guaranteed (time) |
| Vulnerability | Partial | Yes | Fast | Model-dependent |

### Supported Vulnerabilities

#### Siemens
- S7-300/400: SDB extraction without auth (older firmware)
- S7-1200 G1 V1-V2: Weak password hash
- S7-1200 G2: Enhanced security (limited exploits)
- S7-1500 V1-V2: Hash weakness in early firmware

#### Allen-Bradley
- RSLogix 500: XOR-based password in .RSS files
- Studio 5000: Source key extraction from .ACD (older versions)

#### Delta
- DVP: Reversible password encoding in project files
- ISPSoft: Weak project file encryption

#### Omron
- CP/CJ: FINS plaintext password capture
- CX-Programmer: Weak .cxp encryption

### Safety Features
- Mandatory authorization acknowledgment
- Rate limiting on online attacks
- Automatic backup before modifications
- Kill switch for long operations
- Complete audit trail

---

## 7. AI Code Generation

### Supported Output Languages
- Ladder Diagram (LAD) - XML representation
- Structured Text (ST) - IEC 61131-3
- Function Block Diagram (FBD)
- Instruction List (IL)

### Generation Pipeline
1. User provides natural language description
2. RAG retrieves similar code examples
3. LLM generates vendor-specific code
4. Syntax validator checks output
5. Safety analyzer flags potential issues
6. Code presented with explanation

### Safety Analysis
- Missing E-stop detection
- Infinite loop warnings
- Unsafe output combination alerts
- Timer/counter overflow risks

---

## 8. Security & Compliance

### Authorization Workflow
1. User requests security-sensitive action
2. Legal disclaimer displayed
3. User acknowledges authorization checkboxes
4. Action logged with full details
5. Operation executed with progress tracking

### Audit Log Format
```json
{
  "timestamp": "ISO-8601",
  "user": "username",
  "machine_id": "unique-id",
  "action": "action_type",
  "target": {
    "type": "online_plc|backup_file",
    "identifier": "ip_or_path",
    "vendor": "vendor_name",
    "model": "model_name"
  },
  "method": "recovery_method",
  "result": "success|failure|aborted",
  "duration_ms": 12345
}
```

### Compliance
- IEC 62443 alignment
- Exportable audit reports
- Configurable password policies
- Automatic backup enforcement

---

## 9. GUI Design

### Main Window Layout
- Menu bar: File, Edit, View, PLC, Tools, AI, Help
- Toolbar: Connect, Upload, Download, Run, Stop, Unlock
- Left panel: Project explorer (multi-vendor tree)
- Center: Code editor with language tabs (LAD/ST/FBD/IL)
- Bottom: Device monitor with live tag values
- Right panel: AI assistant chat

### Password Recovery Wizard
- Step 1: Authorization confirmation
- Step 2: Target selection (online/offline)
- Step 3: Protection type selection
- Step 4: Recovery method configuration
- Progress display with abort option
- Result display with export option

---

## 10. Implementation Phases

### Phase 1: Core Infrastructure
- Project structure and build system
- Protocol Abstraction Layer base classes
- Security/audit module
- Basic PyQt6 window

### Phase 2: Vendor Drivers
- Siemens S7comm/S7comm+ driver
- Allen-Bradley CIP driver
- Delta Modbus driver
- Omron FINS driver

### Phase 3: Project File Parsers
- TIA Portal .ap13-.ap20 parser
- Studio 5000 .ACD/.L5X parser
- ISPSoft .dvp parser
- CX-Programmer .cxp parser
- Sysmac Studio .smc2 parser

### Phase 4: Password Recovery
- Recovery engine orchestration
- Dictionary attack implementation
- Brute-force with optimization
- Vendor-specific vulnerability exploits

### Phase 5: AI Integration
- LLM integration (OpenAI/Anthropic)
- RAG knowledge base
- Code generation pipeline
- Safety analyzer

### Phase 6: Full IDE Features
- Complete code editor
- Ladder diagram visual editor
- Live monitoring dashboard
- Cross-compilation between languages

---

## 11. Legal Considerations

This tool is designed for **authorized use only**:
- Equipment owners recovering lost passwords
- Authorized security testing with written permission
- System integrators with client authorization
- Educational environments

Unauthorized use may violate:
- Computer Fraud and Abuse Act (US)
- Computer Misuse Act (UK)
- Industrial espionage laws
- IEC 62443 compliance requirements

The application includes:
- Mandatory authorization acknowledgments
- Complete audit logging
- Legal disclaimers
- Terms of service acceptance
