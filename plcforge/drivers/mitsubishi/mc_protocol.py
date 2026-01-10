"""
Mitsubishi MC Protocol Driver

Supports MELSEC-Q, MELSEC-L, iQ-R, and iQ-F series PLCs.
Uses SLMP (Seamless Message Protocol) over TCP/UDP.
"""

import socket
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from plcforge.drivers.base import (
    AccessLevel,
    Block,
    BlockInfo,
    BlockType,
    DeviceInfo,
    MemoryArea,
    PLCDevice,
    PLCMode,
    PLCProgram,
    ProtectionStatus,
    TagValue,
)


class MCDeviceCode(IntEnum):
    """Mitsubishi device codes for MC Protocol"""
    # Bit devices
    X = 0x9C    # Input
    Y = 0x9D    # Output
    M = 0x90    # Internal relay
    L = 0x92    # Latch relay
    F = 0x93    # Annunciator
    V = 0x94    # Edge relay
    B = 0xA0    # Link relay

    # Word devices
    D = 0xA8    # Data register
    W = 0xB4    # Link register
    R = 0xAF    # File register
    ZR = 0xB0   # File register (extended)

    # Timer/Counter
    TN = 0xC2   # Timer current value
    TS = 0xC1   # Timer contact
    TC = 0xC0   # Timer coil
    CN = 0xC5   # Counter current value
    CS = 0xC4   # Counter contact
    CC = 0xC3   # Counter coil


# Memory area to device code mapping
DEVICE_MAP = {
    MemoryArea.INPUT: MCDeviceCode.X,
    MemoryArea.OUTPUT: MCDeviceCode.Y,
    MemoryArea.MEMORY: MCDeviceCode.M,
    MemoryArea.DATA: MCDeviceCode.D,
    MemoryArea.TIMER: MCDeviceCode.TN,
    MemoryArea.COUNTER: MCDeviceCode.CN,
}


@dataclass
class MCFrame:
    """MC Protocol frame structure"""
    subheader: int
    network_no: int
    pc_no: int
    request_dest_module_io: int
    request_dest_module_station: int
    request_data_length: int
    monitoring_timer: int
    command: int
    subcommand: int
    data: bytes


class MitsubishiMCDriver(PLCDevice):
    """
    Mitsubishi MC Protocol driver.

    Supports:
    - MELSEC-Q series (QnU, QnUD, etc.)
    - MELSEC-L series
    - iQ-R series
    - iQ-F series

    Uses 3E frame format (binary) over TCP.
    """

    # MC Protocol constants
    SUBHEADER_3E = 0x5000
    NETWORK_NO = 0x00
    PC_NO = 0xFF
    MODULE_IO = 0x03FF
    MODULE_STATION = 0x00

    # Commands
    CMD_BATCH_READ = 0x0401
    CMD_BATCH_WRITE = 0x1401
    CMD_RANDOM_READ = 0x0403
    CMD_RANDOM_WRITE = 0x1402
    CMD_MONITOR = 0x0801
    CMD_CPU_MODEL_READ = 0x0101

    def __init__(self):
        super().__init__()
        self._socket: socket.socket | None = None
        self._ip: str | None = None
        self._port: int = 5000  # Default MC Protocol port
        self._timeout: float = 5.0
        self._frame_type: str = "3E"

    @property
    def vendor(self) -> str:
        return "Mitsubishi"

    def connect(self, ip: str, port: int = 5000, timeout: float = 5.0) -> bool:
        """Connect to Mitsubishi PLC via MC Protocol."""
        self._ip = ip
        self._port = port
        self._timeout = timeout

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            self._socket.connect((self._ip, self._port))
            self._connected = True

            # Read CPU model to verify connection
            self._device_info = self._read_cpu_model()

            return True
        except Exception as e:
            self._last_error = f"Connection failed: {e}"
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
        self._connected = False

    def _build_frame(self, command: int, subcommand: int, data: bytes) -> bytes:
        """Build MC Protocol 3E frame."""
        # Data length = monitoring timer(2) + command(2) + subcommand(2) + data
        data_length = 6 + len(data)

        frame = struct.pack('<H', self.SUBHEADER_3E)  # Subheader
        frame += struct.pack('<B', self.NETWORK_NO)   # Network number
        frame += struct.pack('<B', self.PC_NO)        # PC number
        frame += struct.pack('<H', self.MODULE_IO)    # Request dest module I/O
        frame += struct.pack('<B', self.MODULE_STATION)  # Request dest module station
        frame += struct.pack('<H', data_length)       # Request data length
        frame += struct.pack('<H', 0x0010)            # Monitoring timer (1.0s)
        frame += struct.pack('<H', command)           # Command
        frame += struct.pack('<H', subcommand)        # Subcommand
        frame += data                                 # Data

        return frame

    def _parse_response(self, response: bytes) -> tuple[int, bytes]:
        """Parse MC Protocol response."""
        if len(response) < 11:
            raise ValueError("Response too short")

        # Parse header
        struct.unpack('<H', response[0:2])[0]
        response[2]
        response[3]
        struct.unpack('<H', response[4:6])[0]
        response[6]
        data_length = struct.unpack('<H', response[7:9])[0]
        end_code = struct.unpack('<H', response[9:11])[0]

        if end_code != 0:
            raise ValueError(f"MC Protocol error: 0x{end_code:04X}")

        # Return data after header
        data = response[11:11 + data_length - 2]
        return end_code, data

    def _send_receive(self, command: int, subcommand: int, data: bytes) -> bytes:
        """Send command and receive response."""
        if not self._socket or not self._connected:
            raise ConnectionError("Not connected")

        frame = self._build_frame(command, subcommand, data)
        self._socket.send(frame)

        # Receive response
        response = self._socket.recv(4096)
        end_code, data = self._parse_response(response)

        return data

    def _read_cpu_model(self) -> DeviceInfo:
        """Read CPU model information."""
        try:
            data = self._send_receive(self.CMD_CPU_MODEL_READ, 0x0000, b'')

            # Parse CPU model response
            model_name = data[0:16].decode('ascii').strip('\x00')

            return DeviceInfo(
                vendor="Mitsubishi",
                model=model_name,
                firmware_version="",
                serial_number="",
                ip_address=self._ip or "",
            )
        except Exception:
            return DeviceInfo(
                vendor="Mitsubishi",
                model="Unknown",
                firmware_version="",
                serial_number="",
                ip_address=self._ip or "",
            )

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        if self._device_info:
            return self._device_info
        return self._read_cpu_model()

    def get_protection_status(self) -> ProtectionStatus:
        """Get protection status."""
        return ProtectionStatus(
            protection_level=0,
            password_protected=False,
        )

    def read_memory(self, area: MemoryArea, start: int, length: int) -> bytes:
        """Read memory area."""
        device_code = DEVICE_MAP.get(area)
        if device_code is None:
            raise ValueError(f"Unsupported memory area: {area}")

        # Build read request
        # Device code (1 byte) + address (3 bytes) + points (2 bytes)
        data = struct.pack('<B', device_code)
        data += struct.pack('<I', start)[:3]  # 3-byte address
        data += struct.pack('<H', length)

        response = self._send_receive(self.CMD_BATCH_READ, 0x0000, data)
        return response

    def write_memory(self, area: MemoryArea, start: int, data: bytes) -> bool:
        """Write to memory area."""
        device_code = DEVICE_MAP.get(area)
        if device_code is None:
            raise ValueError(f"Unsupported memory area: {area}")

        # Build write request
        points = len(data) // 2
        request = struct.pack('<B', device_code)
        request += struct.pack('<I', start)[:3]  # 3-byte address
        request += struct.pack('<H', points)
        request += data

        try:
            self._send_receive(self.CMD_BATCH_WRITE, 0x0000, request)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """Read tag by name (D100, M0, etc.)."""
        device, address = self._parse_tag(tag_name)
        device_code = self._get_device_code(device)

        # Build read request
        data = struct.pack('<B', device_code)
        data += struct.pack('<I', address)[:3]
        data += struct.pack('<H', 1)

        response = self._send_receive(self.CMD_BATCH_READ, 0x0000, data)

        if device in ['X', 'Y', 'M', 'L', 'B']:  # Bit devices
            value = response[0] & 0x01
        else:  # Word devices
            value = struct.unpack('<H', response[0:2])[0]

        return TagValue(
            name=tag_name,
            value=value,
            data_type="WORD" if device in ['D', 'W', 'R'] else "BOOL",
            address=tag_name,
        )

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write tag by name."""
        device, address = self._parse_tag(tag_name)
        device_code = self._get_device_code(device)

        if device in ['X', 'Y', 'M', 'L', 'B']:  # Bit devices
            # Use bit write
            data = struct.pack('<B', device_code)
            data += struct.pack('<I', address)[:3]
            data += struct.pack('<H', 1)
            data += struct.pack('<B', 1 if value else 0)
        else:  # Word devices
            data = struct.pack('<B', device_code)
            data += struct.pack('<I', address)[:3]
            data += struct.pack('<H', 1)
            data += struct.pack('<H', int(value))

        try:
            self._send_receive(self.CMD_BATCH_WRITE, 0x0000, data)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def _parse_tag(self, tag: str) -> tuple[str, int]:
        """Parse tag name into device and address."""
        # Examples: D100, M0, X0, Y10
        tag = tag.upper()

        # Find where numbers start
        for i, c in enumerate(tag):
            if c.isdigit():
                device = tag[:i]
                address = int(tag[i:])
                return device, address

        raise ValueError(f"Invalid tag format: {tag}")

    def _get_device_code(self, device: str) -> int:
        """Get device code from device letter."""
        device_codes = {
            'X': MCDeviceCode.X,
            'Y': MCDeviceCode.Y,
            'M': MCDeviceCode.M,
            'L': MCDeviceCode.L,
            'B': MCDeviceCode.B,
            'D': MCDeviceCode.D,
            'W': MCDeviceCode.W,
            'R': MCDeviceCode.R,
            'TN': MCDeviceCode.TN,
            'CN': MCDeviceCode.CN,
        }

        if device not in device_codes:
            raise ValueError(f"Unknown device: {device}")

        return device_codes[device]

    def authenticate(self, password: str) -> bool:
        """Authenticate with password (not typically required for MC Protocol)."""
        return True

    def list_blocks(self, block_type: BlockType | None = None) -> list[BlockInfo]:
        """List program blocks (not supported in MC Protocol)."""
        return []

    def upload_block(self, block_type: BlockType, number: int) -> bytes:
        """Upload block (not supported)."""
        return b''

    def download_block(self, block_type: BlockType, number: int, data: bytes) -> bool:
        """Download block (not supported)."""
        return False

    def upload_program(self) -> PLCProgram:
        """Upload program (not supported)."""
        return PLCProgram(vendor="Mitsubishi", model="", blocks=[])

    def download_program(self, program: PLCProgram) -> bool:
        """Download program (not supported)."""
        return False

    def get_mode(self) -> PLCMode:
        """Get PLC mode."""
        return PLCMode.RUN

    def set_mode(self, mode: PLCMode) -> bool:
        """Set PLC mode (not supported via MC Protocol)."""
        return False

    def start(self) -> bool:
        """Start PLC (not supported via MC Protocol)."""
        return False

    def stop(self) -> bool:
        """Stop PLC (not supported via MC Protocol)."""
        return False

    def get_access_level(self) -> AccessLevel:
        """Get current access level."""
        return AccessLevel.READ_WRITE

    def get_block(self, block_type: BlockType, number: int) -> Block | None:
        """Get block (not supported via MC Protocol)."""
        return None

    def get_block_list(self, block_type: BlockType | None = None) -> list[BlockInfo]:
        """Get list of blocks (not supported via MC Protocol)."""
        return []
