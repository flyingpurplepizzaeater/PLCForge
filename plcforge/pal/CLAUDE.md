# Protocol Abstraction Layer (PAL)

<!-- AUTO-MANAGED: module-description -->
Vendor-agnostic interface for PLC communication. Provides automatic vendor detection through protocol probing and a unified API that abstracts vendor-specific differences across Siemens, Allen-Bradley, Delta, and Omron PLCs.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
pal/
├── __init__.py
└── unified_api.py           # DeviceFactory, UnifiedPLC, vendor detection
```
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Device Creation:**
```python
# Auto-detect vendor
plc = DeviceFactory.create(ip="192.168.1.10")

# Explicit vendor
plc = DeviceFactory.create(ip="192.168.1.10", vendor="siemens", rack=0, slot=1)
plc = DeviceFactory.create(ip="192.168.1.10", vendor=Vendor.ALLEN_BRADLEY, slot=2)
```

**Vendor Auto-Detection:**
- Probes each vendor's protocol in sequence
- Siemens S7: COTP connection request on TCP port 102 (TPKT/COTP headers)
- Allen-Bradley: EtherNet/IP List Identity on TCP port 44818 (command 0x63)
- Omron: FINS probe on UDP port 9600 (FINS header 0x80)
- Delta: Modbus read on TCP port 502 (Modbus TCP frame)
- Returns `Vendor.UNKNOWN` if all probes fail
- Probe methods: `_probe_siemens()`, `_probe_allen_bradley()`, `_probe_omron()`, `_probe_delta()`

**Factory Pattern:**
- `DeviceFactory.register_driver(vendor, driver_class)` - Register new drivers
- `DeviceFactory.create()` - Create and connect to PLC
- Raises `ValueError` if vendor unsupported or detection fails
- Raises `ConnectionError` if connection fails with error details

**Vendor Enum:**
- `Vendor.SIEMENS` - Siemens S7 family
- `Vendor.ALLEN_BRADLEY` - CompactLogix/ControlLogix
- `Vendor.DELTA` - Delta DVP series
- `Vendor.OMRON` - Omron CP/CJ/NX/NJ
- `Vendor.UNKNOWN` - Detection failed

**Discovery:**
- `DiscoveredDevice` dataclass: ip, vendor, model, name, mac_address, additional_info
- Used by network scanning features
- `NetworkScanner` class for subnet scanning
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

Depends on all vendor-specific driver libraries:
- `python-snap7>=1.3` (Siemens)
- `pycomm3>=1.2` (Allen-Bradley)
- `pymodbus>=3.5` (Delta)
- `pyfins>=1.0` (Omron)
<!-- END AUTO-MANAGED -->
