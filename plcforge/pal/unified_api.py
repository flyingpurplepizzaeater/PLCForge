"""
Protocol Abstraction Layer (PAL) - Unified API

Provides a vendor-agnostic interface to interact with any supported PLC.
Automatically handles vendor detection and driver selection.
"""

import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any

from plcforge.drivers.base import (
    DeviceInfo,
    PLCDevice,
    PLCMode,
    PLCProgram,
    ProtectionStatus,
    TagValue,
)


class Vendor(Enum):
    """Supported PLC vendors"""
    SIEMENS = "siemens"
    ALLEN_BRADLEY = "allen_bradley"
    DELTA = "delta"
    OMRON = "omron"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredDevice:
    """A device discovered on the network"""
    ip: str
    vendor: Vendor
    model: str
    name: str | None = None
    mac_address: str | None = None
    additional_info: dict[str, Any] = None


class DeviceFactory:
    """
    Factory for creating PLC device connections.

    Supports automatic vendor detection or explicit specification.
    """

    # Registry of vendor drivers
    _drivers: dict[Vendor, type[PLCDevice]] = {}

    @classmethod
    def register_driver(cls, vendor: Vendor, driver_class: type[PLCDevice]) -> None:
        """
        Register a driver class for a vendor.

        Args:
            vendor: Vendor enum value
            driver_class: PLCDevice subclass for this vendor
        """
        cls._drivers[vendor] = driver_class

    @classmethod
    def create(
        cls,
        ip: str,
        vendor: Vendor | str | None = None,
        model: str | None = None,
        **kwargs
    ) -> PLCDevice:
        """
        Create a PLC device connection.

        Args:
            ip: IP address of the PLC
            vendor: Vendor name or enum (auto-detect if None)
            model: Specific model (for driver optimization)
            **kwargs: Additional connection parameters

        Returns:
            Connected PLCDevice instance

        Raises:
            ValueError: If vendor not supported or detection failed
        """
        # Convert string vendor to enum
        if isinstance(vendor, str):
            vendor = Vendor(vendor.lower())

        # Auto-detect vendor if not specified
        if vendor is None:
            vendor = cls._detect_vendor(ip)
            if vendor == Vendor.UNKNOWN:
                raise ValueError(f"Could not detect PLC vendor at {ip}")

        # Get driver class
        if vendor not in cls._drivers:
            raise ValueError(f"No driver registered for vendor: {vendor}")

        driver_class = cls._drivers[vendor]

        # Create driver instance
        driver = driver_class()

        # Connect with appropriate parameters
        connect_kwargs = kwargs.copy()
        if model:
            connect_kwargs['model'] = model

        if not driver.connect(ip, **connect_kwargs):
            raise ConnectionError(
                f"Failed to connect to {vendor.value} PLC at {ip}: {driver.last_error}"
            )

        return driver

    @classmethod
    def _detect_vendor(cls, ip: str, timeout: float = 2.0) -> Vendor:
        """
        Attempt to detect the vendor of a PLC at the given IP.

        Uses protocol-specific probes to identify the vendor.
        """
        # Try each vendor's protocol in parallel or sequence

        # 1. Try Siemens S7 (TCP port 102)
        if cls._probe_siemens(ip, timeout):
            return Vendor.SIEMENS

        # 2. Try Allen-Bradley EtherNet/IP (TCP port 44818)
        if cls._probe_allen_bradley(ip, timeout):
            return Vendor.ALLEN_BRADLEY

        # 3. Try Omron FINS (UDP port 9600)
        if cls._probe_omron(ip, timeout):
            return Vendor.OMRON

        # 4. Try Delta Modbus (TCP port 502)
        if cls._probe_delta(ip, timeout):
            return Vendor.DELTA

        return Vendor.UNKNOWN

    @classmethod
    def _probe_siemens(cls, ip: str, timeout: float) -> bool:
        """Probe for Siemens S7 protocol on TCP 102"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 102))

            # Send COTP connection request (ISO-on-TCP)
            cotp_cr = bytes([
                0x03, 0x00, 0x00, 0x16,  # TPKT header
                0x11, 0xe0, 0x00, 0x00,  # COTP CR
                0x00, 0x01, 0x00, 0xc0,  # Source ref, class
                0x01, 0x0a, 0xc1, 0x02,  # TSAP calling
                0x01, 0x00, 0xc2, 0x02,  # TSAP called
                0x01, 0x02              # Additional params
            ])
            sock.send(cotp_cr)

            response = sock.recv(1024)
            sock.close()

            # Check for valid COTP CC response
            return len(response) >= 4 and response[0:2] == b'\x03\x00'
        except Exception:
            return False

    @classmethod
    def _probe_allen_bradley(cls, ip: str, timeout: float) -> bool:
        """Probe for Allen-Bradley EtherNet/IP on TCP 44818"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 44818))

            # Send EtherNet/IP List Identity request
            list_identity = bytes([
                0x63, 0x00,              # Command: List Identity
                0x00, 0x00,              # Length
                0x00, 0x00, 0x00, 0x00,  # Session handle
                0x00, 0x00, 0x00, 0x00,  # Status
                0x00, 0x00, 0x00, 0x00,  # Sender context
                0x00, 0x00, 0x00, 0x00,  #
                0x00, 0x00, 0x00, 0x00,  # Options
            ])
            sock.send(list_identity)

            response = sock.recv(1024)
            sock.close()

            # Check for valid EtherNet/IP response
            return len(response) >= 24 and response[0] == 0x63
        except Exception:
            return False

    @classmethod
    def _probe_omron(cls, ip: str, timeout: float) -> bool:
        """Probe for Omron FINS on UDP 9600"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)

            # FINS node address request
            fins_request = bytes([
                0x46, 0x49, 0x4e, 0x53,  # "FINS"
                0x00, 0x00, 0x00, 0x0c,  # Length
                0x00, 0x00, 0x00, 0x00,  # Command
                0x00, 0x00, 0x00, 0x00,  # Error code
                0x00, 0x00, 0x00, 0x00,  # Client node (request assignment)
            ])
            sock.sendto(fins_request, (ip, 9600))

            response, _ = sock.recvfrom(1024)
            sock.close()

            # Check for valid FINS response
            return len(response) >= 16 and response[0:4] == b'FINS'
        except Exception:
            return False

    @classmethod
    def _probe_delta(cls, ip: str, timeout: float) -> bool:
        """Probe for Delta/Modbus on TCP 502"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 502))

            # Modbus TCP Read Device ID request
            modbus_request = bytes([
                0x00, 0x01,              # Transaction ID
                0x00, 0x00,              # Protocol ID (Modbus)
                0x00, 0x05,              # Length
                0x01,                    # Unit ID
                0x2b,                    # Function code: Read Device ID
                0x0e,                    # MEI type
                0x01,                    # Read Device ID code
                0x00,                    # Object ID
            ])
            sock.send(modbus_request)

            response = sock.recv(1024)
            sock.close()

            # Check for any Modbus response (even error response indicates Modbus device)
            return len(response) >= 8 and response[2:4] == b'\x00\x00'
        except Exception:
            return False


class NetworkScanner:
    """
    Scan network for PLC devices.
    """

    @staticmethod
    def scan_subnet(
        subnet: str,
        timeout: float = 1.0,
        vendors: list[Vendor] | None = None
    ) -> list[DiscoveredDevice]:
        """
        Scan a subnet for PLC devices.

        Args:
            subnet: Subnet in CIDR notation (e.g., "192.168.1.0/24")
            timeout: Timeout per host in seconds
            vendors: Specific vendors to scan for (all if None)

        Returns:
            List of discovered devices
        """
        # Parse subnet
        import ipaddress
        network = ipaddress.ip_network(subnet, strict=False)

        discovered = []
        for ip in network.hosts():
            ip_str = str(ip)

            # Detect vendor
            vendor = DeviceFactory._detect_vendor(ip_str, timeout)

            if vendor != Vendor.UNKNOWN:
                if vendors is None or vendor in vendors:
                    discovered.append(DiscoveredDevice(
                        ip=ip_str,
                        vendor=vendor,
                        model="Unknown",  # Would need connection to get details
                    ))

        return discovered

    @staticmethod
    def scan_ip_range(
        start_ip: str,
        end_ip: str,
        timeout: float = 1.0
    ) -> list[DiscoveredDevice]:
        """
        Scan a range of IP addresses for PLC devices.

        Args:
            start_ip: Starting IP address
            end_ip: Ending IP address
            timeout: Timeout per host

        Returns:
            List of discovered devices
        """
        import ipaddress
        start = int(ipaddress.ip_address(start_ip))
        end = int(ipaddress.ip_address(end_ip))

        discovered = []
        for ip_int in range(start, end + 1):
            ip_str = str(ipaddress.ip_address(ip_int))
            vendor = DeviceFactory._detect_vendor(ip_str, timeout)

            if vendor != Vendor.UNKNOWN:
                discovered.append(DiscoveredDevice(
                    ip=ip_str,
                    vendor=vendor,
                    model="Unknown",
                ))

        return discovered


class UnifiedPLC:
    """
    High-level unified PLC interface.

    Wraps a PLCDevice with additional convenience methods
    and cross-vendor compatibility features.
    """

    def __init__(self, device: PLCDevice):
        self._device = device
        self._cache_enabled = False
        self._tag_cache: dict[str, TagValue] = {}

    @property
    def device(self) -> PLCDevice:
        """Access underlying device driver"""
        return self._device

    @property
    def info(self) -> DeviceInfo:
        """Get device information"""
        return self._device.get_device_info()

    @property
    def mode(self) -> PLCMode:
        """Get current operating mode"""
        return self._device.get_mode()

    @property
    def is_running(self) -> bool:
        """Check if PLC is in RUN mode"""
        return self._device.get_mode() == PLCMode.RUN

    @property
    def protection(self) -> ProtectionStatus:
        """Get protection status"""
        return self._device.get_protection_status()

    # Convenience methods

    def read(self, tag_or_address: str) -> Any:
        """
        Read a value by tag name or address.

        Supports both symbolic tags ("Motor1.Speed") and
        direct addresses ("DB1.DBD0", "D100", "DM100").
        """
        tag_value = self._device.read_tag(tag_or_address)
        return tag_value.value

    def write(self, tag_or_address: str, value: Any) -> bool:
        """Write a value to tag or address"""
        return self._device.write_tag(tag_or_address, value)

    def read_multiple(self, tags: list[str]) -> dict[str, Any]:
        """Read multiple tags, return as dictionary"""
        results = self._device.read_tags(tags)
        return {tv.name: tv.value for tv in results}

    def write_multiple(self, values: dict[str, Any]) -> bool:
        """Write multiple tag values"""
        return self._device.write_tags(values)

    def start(self) -> bool:
        """Start the PLC"""
        return self._device.start()

    def stop(self) -> bool:
        """Stop the PLC"""
        return self._device.stop()

    def backup(self, path: str) -> PLCProgram:
        """
        Create a backup of the PLC program.

        Args:
            path: File path to save backup

        Returns:
            PLCProgram object
        """
        program = self._device.upload_program()
        program.save(path)
        return program

    def restore(self, path_or_program: str | PLCProgram) -> bool:
        """
        Restore a program to the PLC.

        Args:
            path_or_program: File path or PLCProgram object

        Returns:
            True if successful
        """
        if isinstance(path_or_program, str):
            program = PLCProgram.load(path_or_program)
        else:
            program = path_or_program

        return self._device.download_program(program)

    def unlock(self, password: str) -> bool:
        """
        Authenticate with PLC using password.

        Returns:
            True if authentication successful
        """
        return self._device.authenticate(password)

    def get_all_tags(self) -> list[TagValue]:
        """Get list of all available tags"""
        # Implementation depends on driver capability
        return []

    def monitor(
        self,
        tags: list[str],
        callback,
        interval_ms: int = 100
    ):
        """
        Start monitoring tags with callback on changes.

        Args:
            tags: List of tag names to monitor
            callback: Function to call when values change. 
                     Signature: callback(tag_name: str, value: TagValue)
            interval_ms: Polling interval in milliseconds (default 100ms)

        Returns:
            Callable to stop monitoring

        Example:
            >>> def on_change(tag, value):
            ...     print(f"{tag} = {value.value}")
            >>> stop = plc.monitor(["Motor1.Speed"], on_change)
            >>> # ... later ...
            >>> stop()
        """
        import threading
        import time

        self._monitoring_active = True
        self._monitoring_thread = None
        last_values = {}

        def monitor_loop():
            """Background thread for tag monitoring"""
            while self._monitoring_active:
                try:
                    # Read all tags
                    for tag in tags:
                        try:
                            current = self.read(tag)
                            # Check if value changed
                            if tag not in last_values or last_values[tag].value != current.value:
                                last_values[tag] = current
                                callback(tag, current)
                        except Exception as e:
                            # Continue monitoring other tags on error
                            pass
                    
                    # Sleep for interval
                    time.sleep(interval_ms / 1000.0)
                except Exception:
                    # Continue monitoring even if errors occur
                    pass

        # Start monitoring thread
        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()

        # Return stop function
        def stop_monitoring():
            self._monitoring_active = False
            if self._monitoring_thread:
                self._monitoring_thread.join(timeout=1.0)

        return stop_monitoring

    def disconnect(self) -> None:
        """Disconnect from PLC"""
        self._device.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Convenience function for quick connections
def connect(ip: str, vendor: str | None = None, **kwargs) -> UnifiedPLC:
    """
    Quick connect to a PLC.

    Args:
        ip: IP address
        vendor: Optional vendor name
        **kwargs: Additional connection parameters

    Returns:
        UnifiedPLC wrapper

    Example:
        >>> plc = connect("192.168.1.10")
        >>> print(plc.info)
        >>> value = plc.read("Motor1.Speed")
    """
    device = DeviceFactory.create(ip, vendor=vendor, **kwargs)
    return UnifiedPLC(device)
