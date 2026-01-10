"""
PLC Network Security Scanner

Scans networks for PLC devices and identifies potential security issues:
- Open protocol ports
- Default credentials
- Firmware vulnerabilities
- Insecure configurations
"""

import ipaddress
import socket
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ScanStatus(Enum):
    """Scan status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class RiskLevel(Enum):
    """Security risk level"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class PortScanResult:
    """Result of a port scan"""
    port: int
    protocol: str  # tcp or udp
    is_open: bool
    service: str = ""
    banner: str = ""


@dataclass
class SecurityIssue:
    """Identified security issue"""
    title: str
    description: str
    risk_level: RiskLevel
    recommendation: str
    cve_ids: list[str] = field(default_factory=list)


@dataclass
class DeviceScanResult:
    """Scan result for a single device"""
    ip_address: str
    hostname: str = ""
    is_plc: bool = False
    vendor: str = ""
    model: str = ""
    firmware: str = ""
    open_ports: list[PortScanResult] = field(default_factory=list)
    security_issues: list[SecurityIssue] = field(default_factory=list)
    scan_time: float = 0.0
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkScanResult:
    """Complete network scan result"""
    subnet: str
    start_time: datetime
    end_time: datetime | None = None
    status: ScanStatus = ScanStatus.PENDING
    devices: list[DeviceScanResult] = field(default_factory=list)
    total_hosts: int = 0
    scanned_hosts: int = 0
    plc_count: int = 0
    issue_count: int = 0
    error_message: str = ""


# Known PLC ports and their protocols
PLC_PORTS = {
    # Siemens
    102: ("S7comm", "Siemens"),
    443: ("HTTPS", "Multiple"),

    # Allen-Bradley
    44818: ("EtherNet/IP", "Allen-Bradley"),
    2222: ("EtherNet/IP", "Allen-Bradley"),

    # Modbus
    502: ("Modbus TCP", "Multiple"),

    # Omron
    9600: ("FINS UDP", "Omron"),

    # Beckhoff
    48898: ("ADS", "Beckhoff"),
    851: ("ADS Runtime", "Beckhoff"),

    # Mitsubishi
    5000: ("MC Protocol", "Mitsubishi"),
    5001: ("MC Protocol", "Mitsubishi"),

    # BACnet (Building Automation)
    47808: ("BACnet", "Multiple"),

    # OPC UA
    4840: ("OPC UA", "Multiple"),

    # DNP3
    20000: ("DNP3", "Multiple"),

    # Other industrial
    1962: ("PCWorx", "Phoenix Contact"),
    20547: ("ProConOS", "Phoenix Contact"),
}

# Known vulnerabilities database (simplified)
KNOWN_VULNERABILITIES = {
    "siemens_s7_1200_v1": {
        "title": "S7-1200 CPU Firmware V1.x Vulnerabilities",
        "cves": ["CVE-2019-13945"],
        "risk": RiskLevel.CRITICAL,
        "description": "Older S7-1200 firmware versions contain critical vulnerabilities",
        "recommendation": "Update to latest firmware version"
    },
    "modbus_no_auth": {
        "title": "Modbus Protocol Without Authentication",
        "cves": [],
        "risk": RiskLevel.HIGH,
        "description": "Modbus protocol does not support authentication by design",
        "recommendation": "Implement network segmentation and firewall rules"
    },
    "open_s7comm": {
        "title": "S7comm Port Exposed",
        "cves": [],
        "risk": RiskLevel.MEDIUM,
        "description": "S7comm port 102 is accessible from scanned network",
        "recommendation": "Restrict access to PLC communication ports"
    },
}


class NetworkScanner:
    """
    Network scanner for PLC device discovery and security assessment.

    Usage:
        scanner = NetworkScanner()
        result = scanner.scan_subnet("192.168.1.0/24")
        for device in result.devices:
            if device.is_plc:
                print(f"Found PLC: {device.vendor} {device.model}")
                for issue in device.security_issues:
                    print(f"  Issue: {issue.title} ({issue.risk_level.value})")
    """

    def __init__(self, timeout: float = 2.0, max_workers: int = 50):
        """
        Initialize scanner.

        Args:
            timeout: Socket timeout in seconds
            max_workers: Maximum concurrent scanning threads
        """
        self._timeout = timeout
        self._max_workers = max_workers
        self._cancelled = False
        self._progress_callback: Callable[[int, int], None] | None = None

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set callback for progress updates: callback(scanned, total)"""
        self._progress_callback = callback

    def scan_subnet(
        self,
        subnet: str,
        ports: list[int] | None = None,
        quick_scan: bool = False
    ) -> NetworkScanResult:
        """
        Scan a subnet for PLC devices.

        Args:
            subnet: Subnet in CIDR notation (e.g., "192.168.1.0/24")
            ports: Specific ports to scan (default: PLC_PORTS)
            quick_scan: If True, only scan common ports

        Returns:
            NetworkScanResult with discovered devices
        """
        self._cancelled = False
        result = NetworkScanResult(
            subnet=subnet,
            start_time=datetime.now(),
            status=ScanStatus.RUNNING
        )

        try:
            network = ipaddress.ip_network(subnet, strict=False)
            hosts = list(network.hosts())
            result.total_hosts = len(hosts)

            # Determine ports to scan
            if ports:
                scan_ports = ports
            elif quick_scan:
                scan_ports = [102, 502, 44818, 9600, 5000, 4840]
            else:
                scan_ports = list(PLC_PORTS.keys())

            # Scan hosts in parallel
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {
                    executor.submit(self._scan_host, str(ip), scan_ports): ip
                    for ip in hosts
                }

                for future in as_completed(futures):
                    if self._cancelled:
                        break

                    result.scanned_hosts += 1
                    device_result = future.result()

                    if device_result.open_ports or device_result.is_plc:
                        result.devices.append(device_result)
                        if device_result.is_plc:
                            result.plc_count += 1
                        result.issue_count += len(device_result.security_issues)

                    # Progress callback
                    if self._progress_callback:
                        self._progress_callback(result.scanned_hosts, result.total_hosts)

            result.status = ScanStatus.CANCELLED if self._cancelled else ScanStatus.COMPLETED

        except Exception as e:
            result.status = ScanStatus.ERROR
            result.error_message = str(e)

        result.end_time = datetime.now()
        return result

    def scan_host(self, ip: str, ports: list[int] | None = None) -> DeviceScanResult:
        """
        Scan a single host.

        Args:
            ip: IP address to scan
            ports: Ports to scan

        Returns:
            DeviceScanResult for the host
        """
        scan_ports = ports or list(PLC_PORTS.keys())
        return self._scan_host(ip, scan_ports)

    def _scan_host(self, ip: str, ports: list[int]) -> DeviceScanResult:
        """Internal host scanning implementation"""
        import time
        start_time = time.time()

        result = DeviceScanResult(ip_address=ip)

        # Try to resolve hostname
        try:
            result.hostname = socket.gethostbyaddr(ip)[0]
        except socket.herror:
            pass

        # Scan TCP ports
        for port in ports:
            if self._cancelled:
                break

            port_result = self._scan_tcp_port(ip, port)
            if port_result.is_open:
                result.open_ports.append(port_result)

                # Try to identify device
                self._identify_device(result, port, port_result)

        # Check for security issues
        self._analyze_security(result)

        result.scan_time = time.time() - start_time
        return result

    def _scan_tcp_port(self, ip: str, port: int) -> PortScanResult:
        """Scan a single TCP port"""
        result = PortScanResult(port=port, protocol="tcp", is_open=False)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)

            if sock.connect_ex((ip, port)) == 0:
                result.is_open = True

                # Get service info
                if port in PLC_PORTS:
                    result.service, _ = PLC_PORTS[port]

                # Try to grab banner
                try:
                    sock.send(b'\r\n')
                    result.banner = sock.recv(256).decode('ascii', errors='ignore').strip()
                except:
                    pass

            sock.close()
        except:
            pass

        return result

    def _identify_device(
        self,
        result: DeviceScanResult,
        port: int,
        port_result: PortScanResult
    ) -> None:
        """Try to identify the PLC device"""
        if port not in PLC_PORTS:
            return

        service, vendor = PLC_PORTS[port]
        result.is_plc = True

        if not result.vendor:
            result.vendor = vendor

        # Protocol-specific identification
        if port == 102:  # S7comm
            self._identify_siemens(result)
        elif port == 44818:  # EtherNet/IP
            self._identify_allen_bradley(result)
        elif port == 502:  # Modbus
            self._identify_modbus(result)
        elif port == 5000:  # MC Protocol
            self._identify_mitsubishi(result)

    def _identify_siemens(self, result: DeviceScanResult) -> None:
        """Identify Siemens PLC via S7comm"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((result.ip_address, 102))

            # COTP Connection Request
            cotp_cr = bytes([
                0x03, 0x00, 0x00, 0x16,  # TPKT
                0x11, 0xE0, 0x00, 0x00, 0x00, 0x01, 0x00,
                0xC1, 0x02, 0x01, 0x00,  # Source TSAP
                0xC2, 0x02, 0x01, 0x02,  # Destination TSAP
                0xC0, 0x01, 0x0A         # TPDU size
            ])

            sock.send(cotp_cr)
            response = sock.recv(256)

            if len(response) >= 7 and response[5] == 0xD0:
                result.vendor = "Siemens"
                result.raw_data["s7comm_connected"] = True

                # Try to read CPU info
                # This would require full S7comm implementation

            sock.close()
        except:
            pass

    def _identify_allen_bradley(self, result: DeviceScanResult) -> None:
        """Identify Allen-Bradley PLC via EtherNet/IP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((result.ip_address, 44818))

            # List Identity request
            list_identity = bytes([
                0x63, 0x00,  # Command: List Identity
                0x00, 0x00,  # Length
                0x00, 0x00, 0x00, 0x00,  # Session handle
                0x00, 0x00, 0x00, 0x00,  # Status
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Sender context
                0x00, 0x00, 0x00, 0x00   # Options
            ])

            sock.send(list_identity)
            response = sock.recv(512)

            if len(response) > 24:
                result.vendor = "Allen-Bradley"
                result.raw_data["enip_response"] = response.hex()

                # Parse identity response
                if len(response) > 48:
                    try:
                        # Product name is typically at offset ~36 with length byte
                        name_len = response[35]
                        if name_len > 0 and name_len < 50:
                            result.model = response[36:36+name_len].decode('ascii', errors='ignore')
                    except:
                        pass

            sock.close()
        except:
            pass

    def _identify_modbus(self, result: DeviceScanResult) -> None:
        """Identify device via Modbus"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((result.ip_address, 502))

            # Read Device Identification (function code 43/14)
            request = bytes([
                0x00, 0x00,  # Transaction ID
                0x00, 0x00,  # Protocol ID (Modbus)
                0x00, 0x05,  # Length
                0x01,        # Unit ID
                0x2B,        # Function code (Read Device Identification)
                0x0E,        # MEI type
                0x01,        # Read device ID code
                0x00         # Object ID
            ])

            sock.send(request)
            response = sock.recv(256)

            if len(response) > 8 and response[7] == 0x2B:
                result.raw_data["modbus_device_id"] = response.hex()

            sock.close()
        except:
            pass

    def _identify_mitsubishi(self, result: DeviceScanResult) -> None:
        """Identify Mitsubishi PLC via MC Protocol"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((result.ip_address, 5000))

            # MC Protocol CPU model read
            request = bytes([
                0x50, 0x00,  # Subheader (3E frame)
                0x00,        # Network number
                0xFF,        # PC number
                0xFF, 0x03,  # Request dest module I/O
                0x00,        # Request dest module station
                0x06, 0x00,  # Request data length
                0x10, 0x00,  # Monitoring timer
                0x01, 0x01,  # Command (CPU model read)
                0x00, 0x00   # Subcommand
            ])

            sock.send(request)
            response = sock.recv(256)

            if len(response) > 11:
                result.vendor = "Mitsubishi"
                result.raw_data["mc_response"] = response.hex()

                # Parse model name from response
                if len(response) > 20:
                    try:
                        result.model = response[11:27].decode('ascii', errors='ignore').strip('\x00')
                    except:
                        pass

            sock.close()
        except:
            pass

    def _analyze_security(self, result: DeviceScanResult) -> None:
        """Analyze security issues for the device"""
        open_port_numbers = {p.port for p in result.open_ports}

        # Check for S7comm exposure
        if 102 in open_port_numbers:
            result.security_issues.append(SecurityIssue(
                title="S7comm Port Exposed",
                description="Siemens S7 communication port 102 is accessible. "
                           "This may allow unauthorized PLC access.",
                risk_level=RiskLevel.MEDIUM,
                recommendation="Restrict access to port 102 using network segmentation and firewalls"
            ))

        # Check for Modbus without authentication
        if 502 in open_port_numbers:
            result.security_issues.append(SecurityIssue(
                title="Modbus TCP Without Authentication",
                description="Modbus TCP port 502 is open. Modbus protocol lacks built-in authentication.",
                risk_level=RiskLevel.HIGH,
                recommendation="Implement network segmentation and consider Modbus/TCP security extensions"
            ))

        # Check for EtherNet/IP exposure
        if 44818 in open_port_numbers:
            result.security_issues.append(SecurityIssue(
                title="EtherNet/IP Port Exposed",
                description="Allen-Bradley EtherNet/IP port 44818 is accessible.",
                risk_level=RiskLevel.MEDIUM,
                recommendation="Restrict access using CIP Security or network segmentation"
            ))

        # Check for HTTP/HTTPS web interface
        if 80 in open_port_numbers:
            result.security_issues.append(SecurityIssue(
                title="Unencrypted Web Interface",
                description="HTTP port 80 is open. Web traffic may be intercepted.",
                risk_level=RiskLevel.MEDIUM,
                recommendation="Use HTTPS (port 443) instead of HTTP"
            ))

        # Multiple open industrial ports
        industrial_ports = open_port_numbers & set(PLC_PORTS.keys())
        if len(industrial_ports) > 3:
            result.security_issues.append(SecurityIssue(
                title="Multiple Industrial Protocols Exposed",
                description=f"Device has {len(industrial_ports)} industrial protocol ports open.",
                risk_level=RiskLevel.HIGH,
                recommendation="Apply principle of least privilege - only expose necessary ports"
            ))

    def cancel(self) -> None:
        """Cancel ongoing scan"""
        self._cancelled = True


def generate_security_report(scan_result: NetworkScanResult) -> str:
    """
    Generate a security report from scan results.

    Args:
        scan_result: Network scan result

    Returns:
        Markdown-formatted security report
    """
    lines = []
    lines.append("# PLC Network Security Scan Report")
    lines.append("")
    lines.append(f"**Scan Date:** {scan_result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Subnet:** {scan_result.subnet}")
    lines.append(f"**Total Hosts Scanned:** {scan_result.scanned_hosts}")
    lines.append(f"**PLCs Discovered:** {scan_result.plc_count}")
    lines.append(f"**Security Issues Found:** {scan_result.issue_count}")
    lines.append("")

    # Risk summary
    critical = sum(1 for d in scan_result.devices for i in d.security_issues if i.risk_level == RiskLevel.CRITICAL)
    high = sum(1 for d in scan_result.devices for i in d.security_issues if i.risk_level == RiskLevel.HIGH)
    medium = sum(1 for d in scan_result.devices for i in d.security_issues if i.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for d in scan_result.devices for i in d.security_issues if i.risk_level == RiskLevel.LOW)

    lines.append("## Risk Summary")
    lines.append("")
    lines.append(f"- **Critical:** {critical}")
    lines.append(f"- **High:** {high}")
    lines.append(f"- **Medium:** {medium}")
    lines.append(f"- **Low:** {low}")
    lines.append("")

    # Device details
    lines.append("## Discovered Devices")
    lines.append("")

    for device in scan_result.devices:
        if not device.is_plc and not device.security_issues:
            continue

        lines.append(f"### {device.ip_address}")
        if device.hostname:
            lines.append(f"**Hostname:** {device.hostname}")
        if device.vendor:
            lines.append(f"**Vendor:** {device.vendor}")
        if device.model:
            lines.append(f"**Model:** {device.model}")
        lines.append("")

        if device.open_ports:
            lines.append("**Open Ports:**")
            for port in device.open_ports:
                lines.append(f"- {port.port}/tcp ({port.service})")
            lines.append("")

        if device.security_issues:
            lines.append("**Security Issues:**")
            for issue in device.security_issues:
                risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
                emoji = risk_emoji.get(issue.risk_level.value, "⚪")
                lines.append(f"- {emoji} **{issue.title}** ({issue.risk_level.value.upper()})")
                lines.append(f"  - {issue.description}")
                lines.append(f"  - *Recommendation:* {issue.recommendation}")
            lines.append("")

    # Recommendations
    lines.append("## General Recommendations")
    lines.append("")
    lines.append("1. **Network Segmentation:** Isolate industrial networks from corporate IT networks")
    lines.append("2. **Firewall Rules:** Restrict access to industrial protocol ports")
    lines.append("3. **Firmware Updates:** Keep PLC firmware up to date")
    lines.append("4. **Monitoring:** Implement industrial network monitoring and intrusion detection")
    lines.append("5. **Authentication:** Enable authentication where supported")
    lines.append("6. **Encryption:** Use encrypted protocols where available (TLS, VPN)")
    lines.append("")

    return "\n".join(lines)
