# PLCForge

Multi-vendor PLC programming application with AI-assisted code generation and password recovery capabilities.

## Features

- **Multi-Vendor Support**: Siemens, Allen-Bradley, Delta, and Omron PLCs through a unified Protocol Abstraction Layer (PAL)
- **AI Code Generation**: Natural language to PLC code using GPT-4 or Claude
- **Password Recovery**: Recover forgotten passwords from project files or live PLCs
- **PyQt6 Desktop GUI**: Project explorer, code editor with syntax highlighting, device monitor
- **Network Scanning**: Auto-detect PLCs on your network

## Supported PLCs

| Vendor | Models | Protocol |
|--------|--------|----------|
| Siemens | S7-300, S7-400, S7-1200 (G1/G2), S7-1500 | S7comm/S7comm+ |
| Allen-Bradley | CompactLogix, ControlLogix | CIP/EtherNet-IP |
| Delta | DVP series | Modbus TCP/RTU |
| Omron | CP/CJ series, NX/NJ series | FINS |

### Siemens Details
- TIA Portal project files V13-V20 supported
- S7-1200 G2 firmware V1.x+ supported
- S7-300/400 legacy support

## Installation

```bash
# Clone the repository
git clone https://github.com/flyingpurplepizzaeater/PLCForge.git
cd PLCForge

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Dependencies

**Communication Libraries:**
- `python-snap7` - Siemens S7comm protocol
- `pycomm3` - Allen-Bradley CIP/EtherNet-IP
- `pymodbus` - Delta Modbus TCP/RTU
- `pyfins` - Omron FINS protocol

**Other:**
- `PyQt6` - Desktop GUI
- `openai` / `anthropic` - AI code generation
- `cryptography` - Password recovery

## Usage

### GUI Application

```bash
python -m plcforge.main
```

### CLI Commands

```bash
# Connect to a PLC
python -m plcforge.main connect 192.168.1.10 --vendor siemens --rack 0 --slot 1

# Read a tag/address
python -m plcforge.main read 192.168.1.10 DB1.DBW0 --vendor siemens

# Write a value
python -m plcforge.main write 192.168.1.10 DB1.DBW0 100 --vendor siemens

# Scan network for PLCs
python -m plcforge.main scan 192.168.1.0/24

# Password recovery (requires confirmation)
python -m plcforge.main recover backup.ap17 --vendor siemens --method file dictionary --confirm
```

### Python API

```python
from plcforge import connect, DeviceFactory

# Auto-detect vendor and connect
plc = connect("192.168.1.10")

# Or specify vendor explicitly
plc = DeviceFactory.create(
    ip="192.168.1.10",
    vendor="siemens",
    rack=0,
    slot=1
)

# Read/write operations
value = plc.read_tag("DB1.DBW0")
plc.write_tag("DB1.DBW0", 100)

# Get device info
info = plc.get_device_info()
print(f"Connected to: {info.model} ({info.firmware_version})")

plc.disconnect()
```

### AI Code Generation

```python
from plcforge.ai import AICodeGenerator, CodeTarget
from plcforge.drivers.base import Vendor, CodeLanguage

# Initialize with OpenAI
generator = AICodeGenerator(provider="openai", api_key="sk-...")

# Define target
target = CodeTarget(
    vendor=Vendor.SIEMENS,
    model="S7-1500",
    language=CodeLanguage.STRUCTURED_TEXT
)

# Generate code from natural language
result = generator.generate(
    prompt="Create a motor start/stop circuit with overload protection",
    target=target,
    safety_check=True
)

print(result.code)
print(f"Safety issues: {result.safety_issues}")
```

## Architecture

```
plcforge/
├── pal/                 # Protocol Abstraction Layer
│   └── unified_api.py   # Vendor-agnostic interface
├── drivers/             # Vendor-specific implementations
│   ├── siemens/         # S7comm driver + TIA Portal parser
│   ├── allen_bradley/   # CIP/EtherNet-IP driver
│   ├── delta/           # Modbus driver
│   └── omron/           # FINS driver
├── ai/                  # AI code generation
├── recovery/            # Password recovery engine
├── security/            # Audit logging
└── gui/                 # PyQt6 interface
```

## Password Recovery

PLCForge includes password recovery capabilities for authorized use cases:
- Recovering access to your own PLCs with forgotten passwords
- Security research and penetration testing (with authorization)
- Educational purposes

**Methods:**
- File parsing (TIA Portal .ap13-.ap20 files)
- Dictionary attacks
- Brute-force attacks
- Known vulnerability exploits

**Security:**
- All recovery attempts are logged with tamper-evident audit trail
- `--confirm` flag required for CLI operations
- GUI includes authorization confirmation dialog

## Security Notice

This tool includes password recovery features intended for legitimate purposes:
- Recovering access to equipment you own
- Authorized security testing
- Research and education

**Do not use this tool for unauthorized access to industrial control systems.**

All password recovery operations are logged for accountability.

## License

See [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! Please read the design document in `docs/plans/` before submitting PRs.

## Acknowledgments

- python-snap7 team for Siemens communication
- pycomm3 team for Allen-Bradley support
- PyQt team for the GUI framework
