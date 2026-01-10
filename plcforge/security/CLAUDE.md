# Security Module

<!-- AUTO-MANAGED: module-description -->
Security and audit logging components for PLCForge, including network scanning for PLC device discovery, vulnerability assessment, and security audit logging.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
security/
├── __init__.py              # Exports NetworkScanner, SecurityIssue, RiskLevel, get_logger
├── audit_log.py             # AuditLogger, AuditEntry for security event tracking
└── network_scanner.py       # PLC network discovery and security scanning
```

**Network Scanner:**
- `NetworkScanner` class for subnet scanning and PLC discovery
- Thread-safe scanning with `ThreadPoolExecutor` (default 50 workers)
- Progress callbacks for UI integration
- Known PLC port detection (S7/102, EIP/44818, Modbus/502, ADS/851, MC/5000, FINS/9600, OPC UA/4840)
- Vendor identification based on open ports

**Security Assessment:**
- `SecurityIssue` dataclass: title, description, risk_level, recommendation, cve_ids
- `RiskLevel` enum: CRITICAL, HIGH, MEDIUM, LOW, INFO
- Known vulnerability database with CVE tracking
- Automatic issue detection (open protocols, default credentials, firmware vulnerabilities)

**Scan Results:**
- `DeviceScanResult`: IP, hostname, vendor, model, firmware, open ports, security issues
- `NetworkScanResult`: Subnet, devices, statistics, status (PENDING, RUNNING, COMPLETED, CANCELLED, ERROR)
- `PortScanResult`: Port, protocol, service, banner
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Scanner Usage:**
```python
scanner = NetworkScanner(timeout=2.0, max_workers=50)
scanner.set_progress_callback(lambda scanned, total: print(f"{scanned}/{total}"))
result = scanner.scan_subnet("192.168.1.0/24", quick_scan=True)

for device in result.devices:
    if device.is_plc:
        print(f"Found PLC: {device.vendor} {device.model} at {device.ip_address}")
        for issue in device.security_issues:
            print(f"  {issue.risk_level.value}: {issue.title}")
```

**Port Detection:**
- PLC_PORTS dict maps port numbers to (protocol, vendor) tuples
- Standard ports: 102 (S7comm/Siemens), 44818 (EIP/AB), 502 (Modbus/Multiple), 851 (ADS/Beckhoff), 5000 (MC/Mitsubishi), 9600 (FINS/Omron)
- Industrial protocols: 4840 (OPC UA), 47808 (BACnet), 20000 (DNP3)

**Vulnerability Database:**
- KNOWN_VULNERABILITIES dict with vulnerability definitions
- Keys: vulnerability identifier strings
- Values: title, cves (list), risk, description, recommendation
- Examples: "siemens_s7_1200_v1", "modbus_no_auth", "open_s7comm"

**Thread Safety:**
- Scanner uses `ThreadPoolExecutor` for concurrent host scanning
- `_cancelled` flag for scan cancellation
- Progress callback invoked with (scanned_count, total_hosts)

**Dataclass Patterns:**
- Use `field(default_factory=list)` for mutable defaults (open_ports, security_issues, cve_ids)
- Timestamp fields use `datetime` objects
- Status tracking via enums (ScanStatus, RiskLevel)
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `socket` - TCP port scanning (standard library)
- `struct` - Binary protocol parsing (standard library)
- `threading` - Thread-safe scanning (standard library)
- `ipaddress` - Subnet parsing and IP address handling (standard library)
- `concurrent.futures.ThreadPoolExecutor` - Parallel scanning (standard library)
- `dataclasses` - Result objects (standard library)
- `enum.Enum` - Status and risk enums (standard library)
<!-- END AUTO-MANAGED -->
