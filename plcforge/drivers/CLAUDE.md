# PLC Drivers Module

<!-- AUTO-MANAGED: module-description -->
Vendor-specific PLC communication drivers implementing a unified abstract interface. Each driver handles protocol-specific communication for different PLC manufacturers while presenting a consistent API through the Protocol Abstraction Layer.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
drivers/
├── base.py                  # Abstract PLCDevice interface, enums, dataclasses
├── siemens/
│   ├── __init__.py
│   ├── s7comm.py            # S7-300/400/1200/1500 via python-snap7
│   └── project_parser.py    # TIA Portal .ap13-.ap20 parser
├── allen_bradley/
│   ├── __init__.py
│   └── cip_driver.py        # CompactLogix/ControlLogix via pycomm3
├── delta/
│   ├── __init__.py
│   └── modbus_driver.py     # DVP series via pymodbus
├── omron/
│   ├── __init__.py
│   └── fins_driver.py       # CP/CJ/NX/NJ via pyfins
├── beckhoff/
│   ├── __init__.py
│   └── ads_driver.py        # TwinCAT 2/3 via pyads (ADS protocol)
├── mitsubishi/
│   ├── __init__.py
│   └── mc_protocol.py       # MELSEC-Q/L/iQ-R/iQ-F via MC Protocol/SLMP
└── schneider/
    ├── __init__.py
    └── modbus_driver.py     # Modicon M340/M580/Premium/Quantum via pymodbus
```
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Base Interface (`base.py`):**
- All drivers inherit from `PLCDevice` ABC
- Required methods: `connect()`, `disconnect()`, `is_connected()`, `get_device_info()`
- Error tracking via `_last_error` property
- Connection state in `_connected` boolean

**Enums (IEC 61131-3 aligned):**
- `MemoryArea`: INPUT, OUTPUT, MEMORY, DATA, TIMER, COUNTER, SPECIAL
- `PLCMode`: RUN, STOP, PROGRAM, FAULT, UNKNOWN
- `AccessLevel`: NONE, READ_ONLY, READ_WRITE, FULL
- `BlockType`: OB, FB, FC, DB, UDT, AOI, PROGRAM, TASK
- `CodeLanguage`: LADDER, STRUCTURED_TEXT, FUNCTION_BLOCK, INSTRUCTION_LIST, SFC, GRAPH

**Dataclasses:**
- `DeviceInfo`: vendor, model, firmware, serial, name, ip_address, rack, slot
- `ProtectionStatus`: cpu_protected, project_protected, access_level
- `BlockInfo`: block_type, number, name, language, size, protected
- `TagValue`: name, value, data_type, address, timestamp, quality
- `PLCProgram`: vendor, model, blocks, tags, configuration, metadata

**Driver-Specific:**
- Siemens (`SiemensS7Driver`): Uses `snap7.client.Client`, `MEMORY_AREA_MAP` conditionally defined (maps `MemoryArea` to snap7 `Areas` when `SNAP7_AVAILABLE=True`, empty dict otherwise), area mapping to snap7 `Areas` enum (PE/PA/MK/DB/TM/CT), rack/slot parameters with auto-adjust for 1200/1500, protection via `get_protection()` with sch_schal levels (1=none, 2=read, 3=read/write), address parsing via `_parse_address()` (supports DB1.DBW0, MW100 formats), `__init__` raises `ImportError` if snap7 not installed, device info extracted from CPU info (model name, firmware version, serial number, order code)
- Allen-Bradley (`AllenBradleyDriver`): Uses `pycomm3.LogixDriver`, path format `ip/slot`, tag-based addressing (not memory areas), supports arrays/structures/program-scoped tags, read/write return objects with `.value` and `.error` attributes
- Delta (`DeltaDVPDriver`): Uses `pymodbus.ModbusTcpClient`, port default 502, register-based addressing (holding registers, input registers, coils), response objects have `.isError()` method
- Omron (`OmronFINSDriver`): Uses `pyfins.FinsClient` for FINS protocol over UDP, memory area read/write methods, controller data read for device info
- Beckhoff (`BeckhoffADSDriver`): Uses `pyads.Connection`, requires AMS Net ID (e.g., "192.168.1.10.1.1") and AMS port (default 851 for PLC Runtime 1, 852 for Runtime 2, 500 for NC, 301 for I/O), supports symbolic variable access via tag names, index group/offset addressing for direct memory access (0x4020=%M markers, 0x4021=%I inputs, 0x4022=%Q outputs), `pyads.add_route()` for IP-based connections (route creation), device info from ADS device info (name, version), `read_tag()` uses symbolic variables, `read_memory()` uses index groups, `__init__` raises `ImportError` if pyads not installed
- Mitsubishi (`MitsubishiMCDriver`): Uses raw socket communication with MC Protocol 3E frame format (binary over TCP), default port 5000, device codes for memory types (X=0x9C inputs, Y=0x9D outputs, M=0x90 internal relays, D=0xA8 data registers, TN/CN for timers/counters), frame structure with subheader 0x5000, network number 0x00, PC number 0xFF, module I/O 0x03FF, monitoring timer (default 1s), `_build_frame()` constructs binary frames, `_parse_response()` validates end code, supports batch read (0x0401), batch write (0x1401), random read (0x0403), CPU model read (0x0101), device info from CPU model command
- Schneider (`SchneiderModbusDriver`): Uses `pymodbus.ModbusTcpClient` or `ModbusSerialClient`, supports both TCP (port 502) and RTU modes, Schneider-specific address ranges (%I=discrete inputs, %Q=coils/outputs, %M=coils/internal, %IW=input registers, %QW/%MW=holding registers, %MD=double words, %MF=floats), unit ID configuration (default 1), RTU mode uses even parity/19200 baud by default, `connect()` for TCP and `connect_rtu()` for serial (COM port or /dev/ttyUSB*), `_read_device_info()` queries Modbus device identification, `_parse_address()` maps Schneider address formats to Modbus functions, `__init__` raises `ImportError` if pymodbus not installed

**Testing Approach:**
- Mock vendor libraries at module level: `@patch("plcforge.drivers.siemens.s7comm.snap7")`, `@patch("plcforge.drivers.beckhoff.ads_driver.pyads")`
- Return mock clients from library constructors
- Set driver `._client` and `._connected` attributes directly in fixtures
- Mock utility functions: `snap7.util.get_int()`, `snap7.util.set_int()`
- Conditional test skipping: Import availability flags from driver modules (`SNAP7_AVAILABLE`, `PYCOMM3_AVAILABLE`, `PYMODBUS_AVAILABLE`, `PYADS_AVAILABLE`), use `pytest.skip()` when dependencies unavailable
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `python-snap7>=1.3` - Siemens S7comm (S7-300/400/1200/1500)
- `pycomm3>=1.2` - Allen-Bradley CIP/EtherNet-IP
- `pymodbus>=3.5` - Delta/Schneider Modbus TCP/RTU
- `pyfins>=1.0` - Omron FINS protocol
- `pyads>=3.3` - Beckhoff TwinCAT ADS protocol
- `socket`, `struct` - Mitsubishi MC Protocol (standard library)
<!-- END AUTO-MANAGED -->
