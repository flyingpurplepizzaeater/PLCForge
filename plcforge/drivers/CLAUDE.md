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
└── omron/
    ├── __init__.py
    └── fins_driver.py       # CP/CJ/NX/NJ via pyfins
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
- Siemens (`SiemensS7Driver`): Uses `snap7.client.Client`, area mapping to snap7 `Areas` enum (PE/PA/MK/DB/TM/CT), rack/slot parameters with auto-adjust for 1200/1500, protection via `get_protection()` with sch_schal levels, address parsing via `_parse_address()` (supports DB1.DBW0, MW100 formats)
- Allen-Bradley (`AllenBradleyDriver`): Uses `pycomm3.LogixDriver`, path format `ip/slot`, tag-based addressing (not memory areas), supports arrays/structures/program-scoped tags, read/write return objects with `.value` and `.error` attributes
- Delta (`DeltaDVPDriver`): Uses `pymodbus.ModbusTcpClient`, port default 502, register-based addressing (holding registers, input registers, coils), response objects have `.isError()` method
- Omron (`OmronFINSDriver`): Uses `pyfins.FinsClient` for FINS protocol over UDP, memory area read/write methods, controller data read for device info

**Testing Approach:**
- Mock vendor libraries at module level: `@patch("plcforge.drivers.siemens.s7comm.snap7")`
- Return mock clients from library constructors
- Set driver `._client` and `._connected` attributes directly in fixtures
- Mock utility functions: `snap7.util.get_int()`, `snap7.util.set_int()`
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `python-snap7>=1.3` - Siemens S7comm (S7-300/400/1200/1500)
- `pycomm3>=1.2` - Allen-Bradley CIP/EtherNet-IP
- `pymodbus>=3.5` - Delta Modbus TCP/RTU
- `pyfins>=1.0` - Omron FINS protocol
<!-- END AUTO-MANAGED -->
