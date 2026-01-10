"""
Omron FINS Protocol Driver

Supports Omron CP/CJ/CS series PLCs using FINS protocol.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import socket
import struct

from plcforge.drivers.base import (
    PLCDevice,
    DeviceInfo,
    ProtectionStatus,
    MemoryArea,
    PLCMode,
    AccessLevel,
    BlockType,
    BlockInfo,
    Block,
    PLCProgram,
    TagValue,
    CodeLanguage,
)


class FINSClient:
    """Low-level FINS protocol client"""

    # FINS command codes
    CMD_MEMORY_AREA_READ = 0x0101
    CMD_MEMORY_AREA_WRITE = 0x0102
    CMD_CONTROLLER_DATA_READ = 0x0501
    CMD_CONTROLLER_STATUS_READ = 0x0601
    CMD_RUN = 0x0401
    CMD_STOP = 0x0402
    CMD_ACCESS_RIGHT_ACQUIRE = 0x0620
    CMD_ACCESS_RIGHT_RELEASE = 0x0621

    # Memory area codes
    AREA_CIO = 0xB0      # CIO (I/O) area - word
    AREA_WR = 0xB1       # Work area - word
    AREA_HR = 0xB2       # Holding area - word
    AREA_AR = 0xB3       # Auxiliary area - word
    AREA_DM = 0x82       # Data Memory - word
    AREA_EM = 0xA0       # Extended Memory (bank 0) - word
    AREA_TIM = 0x89      # Timer PV
    AREA_CNT = 0x89      # Counter PV (same as timer, different address range)
    AREA_CIO_BIT = 0x30  # CIO bit
    AREA_WR_BIT = 0x31   # Work area bit
    AREA_HR_BIT = 0x32   # Holding area bit

    def __init__(self, host: str, port: int = 9600):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.local_node = 0
        self.remote_node = 0
        self.sid = 0

    def connect(self) -> bool:
        """Connect to PLC via FINS/TCP"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5.0)

            # For FINS/UDP, send node address request
            self._request_node_address()

            return True
        except Exception:
            return False

    def _request_node_address(self):
        """Request node address assignment (FINS/TCP only)"""
        # For UDP, we use a fixed node address
        self.local_node = 1
        self.remote_node = 1

    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def _build_header(self, command: int, data: bytes) -> bytes:
        """Build FINS header"""
        self.sid = (self.sid + 1) & 0xFF

        header = bytes([
            0x80,           # ICF: Command, response required
            0x00,           # RSV: Reserved
            0x02,           # GCT: Gateway count
            0x00,           # DNA: Destination network (local)
            self.remote_node,  # DA1: Destination node
            0x00,           # DA2: Destination unit (CPU)
            0x00,           # SNA: Source network
            self.local_node,   # SA1: Source node
            0x00,           # SA2: Source unit
            self.sid,       # SID: Service ID
        ])

        # Add command code
        cmd_bytes = struct.pack('>H', command)

        return header + cmd_bytes + data

    def _send_command(self, command: int, data: bytes = b'') -> Tuple[int, bytes]:
        """Send FINS command and receive response"""
        packet = self._build_header(command, data)

        self.sock.sendto(packet, (self.host, self.port))

        response, _ = self.sock.recvfrom(4096)

        # Parse response
        if len(response) < 14:
            raise Exception("Response too short")

        # Check response code
        end_code = struct.unpack('>H', response[12:14])[0]
        response_data = response[14:]

        return end_code, response_data

    def memory_area_read(self, area: int, address: int, count: int) -> bytes:
        """Read from memory area"""
        # Build data: Area code, Address (3 bytes), Bit position, Count
        data = bytes([
            area,
            (address >> 8) & 0xFF,
            address & 0xFF,
            0x00,  # Bit position (for word access)
        ]) + struct.pack('>H', count)

        end_code, response = self._send_command(self.CMD_MEMORY_AREA_READ, data)

        if end_code != 0:
            raise Exception(f"FINS error: {end_code:04X}")

        return response

    def memory_area_write(self, area: int, address: int, data: bytes) -> bool:
        """Write to memory area"""
        count = len(data) // 2  # Word count

        # Build command data
        cmd_data = bytes([
            area,
            (address >> 8) & 0xFF,
            address & 0xFF,
            0x00,  # Bit position
        ]) + struct.pack('>H', count) + data

        end_code, _ = self._send_command(self.CMD_MEMORY_AREA_WRITE, cmd_data)

        return end_code == 0

    def controller_data_read(self) -> Dict[str, Any]:
        """Read controller data"""
        end_code, response = self._send_command(self.CMD_CONTROLLER_DATA_READ, b'')

        if end_code != 0 or len(response) < 64:
            return {}

        return {
            'model': response[0:20].decode('ascii', errors='ignore').strip(),
            'version': response[20:40].decode('ascii', errors='ignore').strip(),
        }

    def controller_status_read(self) -> Dict[str, Any]:
        """Read controller status"""
        end_code, response = self._send_command(self.CMD_CONTROLLER_STATUS_READ, b'')

        if end_code != 0 or len(response) < 2:
            return {'mode': 'unknown'}

        status = response[0]
        if status & 0x01:
            mode = 'run'
        elif status & 0x02:
            mode = 'program'
        else:
            mode = 'stop'

        return {
            'mode': mode,
            'fatal_error': bool(status & 0x40),
            'non_fatal_error': bool(status & 0x80),
        }

    def run(self) -> bool:
        """Set PLC to RUN mode"""
        end_code, _ = self._send_command(self.CMD_RUN, bytes([0x04, 0x01]))
        return end_code == 0

    def stop(self) -> bool:
        """Set PLC to STOP mode"""
        end_code, _ = self._send_command(self.CMD_STOP, b'')
        return end_code == 0

    def authenticate(self, password: str) -> bool:
        """Authenticate with password"""
        # Password is ASCII, padded to 8 bytes
        pwd_bytes = password.encode('ascii')[:8].ljust(8, b'\x00')

        end_code, _ = self._send_command(self.CMD_ACCESS_RIGHT_ACQUIRE, pwd_bytes)
        return end_code == 0


class OmronFINSDriver(PLCDevice):
    """
    Omron FINS protocol driver.

    Supports:
    - CP1L/CP1H/CP1E series
    - CJ1M/CJ2M series
    - CS1G/CS1H series

    Memory mapping:
    - CIO: I/O area (0000-6143)
    - W: Work area (000-511)
    - H: Holding area (000-511)
    - A: Auxiliary area (000-959)
    - D: Data Memory (0000-32767)
    - T: Timers (0000-4095)
    - C: Counters (0000-4095)
    """

    # Memory area mapping
    AREA_MAP = {
        MemoryArea.INPUT: FINSClient.AREA_CIO,
        MemoryArea.OUTPUT: FINSClient.AREA_CIO,
        MemoryArea.MEMORY: FINSClient.AREA_WR,
        MemoryArea.DATA: FINSClient.AREA_DM,
        MemoryArea.TIMER: FINSClient.AREA_TIM,
        MemoryArea.COUNTER: FINSClient.AREA_CNT,
    }

    def __init__(self):
        super().__init__()
        self._client: Optional[FINSClient] = None
        self._ip: Optional[str] = None
        self._port: int = 9600

    def connect(self, ip: str, **kwargs) -> bool:
        """Connect to Omron PLC via FINS"""
        self._ip = ip
        self._port = kwargs.get('port', 9600)

        try:
            self._client = FINSClient(ip, self._port)
            self._connected = self._client.connect()

            if self._connected:
                self._device_info = self._read_device_info()

            return self._connected
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect"""
        if self._client:
            self._client.close()
            self._client = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device info"""
        try:
            info = self._client.controller_data_read()
            return DeviceInfo(
                vendor="Omron",
                model=info.get('model', 'Unknown'),
                firmware=info.get('version', 'Unknown'),
                serial="Unknown",
                name="Omron PLC",
                ip_address=self._ip,
            )
        except Exception:
            return DeviceInfo(
                vendor="Omron",
                model="Unknown",
                firmware="Unknown",
                serial="Unknown",
                name="Omron PLC",
                ip_address=self._ip,
            )

    def get_device_info(self) -> DeviceInfo:
        """Get device info"""
        if not self._device_info:
            self._device_info = self._read_device_info()
        return self._device_info

    def get_protection_status(self) -> ProtectionStatus:
        """Get protection status"""
        return ProtectionStatus(
            cpu_protected=False,
            project_protected=False,
            block_protected=False,
            access_level=AccessLevel.FULL,
        )

    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        """Read memory"""
        fins_area = self.AREA_MAP.get(area)
        if fins_area is None:
            raise ValueError(f"Unsupported area: {area}")

        try:
            return self._client.memory_area_read(fins_area, address, count)
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        """Write memory"""
        fins_area = self.AREA_MAP.get(area)
        if fins_area is None:
            self._last_error = f"Unsupported area: {area}"
            return False

        try:
            return self._client.memory_area_write(fins_area, address, data)
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read by Omron address format.

        Supports:
        - D0, D100 (data memory)
        - W0, W100 (work area)
        - H0, H100 (holding area)
        - A0, A100 (auxiliary area)
        - CIO0, CIO100 (I/O area)
        - T0, C0 (timers/counters)
        """
        try:
            addr_info = self._parse_address(tag_name)
            value = self._read_by_address(addr_info)

            return TagValue(
                name=tag_name,
                value=value,
                data_type=addr_info['type'],
                address=tag_name,
                timestamp=datetime.now(),
            )
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write by Omron address format"""
        try:
            addr_info = self._parse_address(tag_name)
            return self._write_by_address(addr_info, value)
        except Exception as e:
            self._last_error = str(e)
            return False

    def _parse_address(self, address: str) -> Dict[str, Any]:
        """Parse Omron address format"""
        address = address.upper().strip()
        result = {
            'area': None,
            'fins_area': None,
            'address': 0,
            'bit': None,
            'type': 'WORD',
        }

        # Check for bit address (e.g., D0.00)
        if '.' in address:
            parts = address.split('.')
            address = parts[0]
            result['bit'] = int(parts[1])
            result['type'] = 'BOOL'

        if address.startswith('D'):
            result['area'] = 'D'
            result['fins_area'] = FINSClient.AREA_DM
            result['address'] = int(address[1:])

        elif address.startswith('W'):
            result['area'] = 'W'
            result['fins_area'] = FINSClient.AREA_WR
            result['address'] = int(address[1:])

        elif address.startswith('H'):
            result['area'] = 'H'
            result['fins_area'] = FINSClient.AREA_HR
            result['address'] = int(address[1:])

        elif address.startswith('A'):
            result['area'] = 'A'
            result['fins_area'] = FINSClient.AREA_AR
            result['address'] = int(address[1:])

        elif address.startswith('CIO'):
            result['area'] = 'CIO'
            result['fins_area'] = FINSClient.AREA_CIO
            result['address'] = int(address[3:])

        elif address.startswith('T'):
            result['area'] = 'T'
            result['fins_area'] = FINSClient.AREA_TIM
            result['address'] = int(address[1:])

        elif address.startswith('C'):
            result['area'] = 'C'
            result['fins_area'] = FINSClient.AREA_CNT
            result['address'] = int(address[1:])

        else:
            raise ValueError(f"Unknown address format: {address}")

        return result

    def _read_by_address(self, addr_info: Dict[str, Any]) -> Any:
        """Read value by parsed address"""
        data = self._client.memory_area_read(
            addr_info['fins_area'],
            addr_info['address'],
            1
        )

        word_value = struct.unpack('>H', data[:2])[0]

        if addr_info['bit'] is not None:
            return bool(word_value & (1 << addr_info['bit']))

        return word_value

    def _write_by_address(self, addr_info: Dict[str, Any], value: Any) -> bool:
        """Write value by parsed address"""
        if addr_info['bit'] is not None:
            # Read-modify-write for bit access
            data = self._client.memory_area_read(
                addr_info['fins_area'],
                addr_info['address'],
                1
            )
            word_value = struct.unpack('>H', data[:2])[0]

            if value:
                word_value |= (1 << addr_info['bit'])
            else:
                word_value &= ~(1 << addr_info['bit'])

            data = struct.pack('>H', word_value)
        else:
            data = struct.pack('>H', int(value))

        return self._client.memory_area_write(
            addr_info['fins_area'],
            addr_info['address'],
            data
        )

    def upload_program(self) -> PLCProgram:
        """Upload program - limited support via FINS"""
        self._last_error = "Full program upload requires CX-Programmer"
        return PLCProgram(vendor="Omron", model=self.get_device_info().model)

    def download_program(self, program: PLCProgram) -> bool:
        """Download program - requires CX-Programmer"""
        self._last_error = "Program download requires CX-Programmer"
        return False

    def get_block_list(self) -> List[BlockInfo]:
        """Get block list - not available via FINS"""
        return []

    def get_block(self, block_type: BlockType, number: int) -> Block:
        """Get block - not available via FINS"""
        raise NotImplementedError("Block access requires CX-Programmer")

    def start(self) -> bool:
        """Start PLC"""
        try:
            return self._client.run()
        except Exception as e:
            self._last_error = str(e)
            return False

    def stop(self) -> bool:
        """Stop PLC"""
        try:
            return self._client.stop()
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_mode(self) -> PLCMode:
        """Get PLC mode"""
        try:
            status = self._client.controller_status_read()
            mode_str = status.get('mode', 'unknown')

            if mode_str == 'run':
                return PLCMode.RUN
            elif mode_str == 'program':
                return PLCMode.PROGRAM
            elif mode_str == 'stop':
                return PLCMode.STOP
            else:
                return PLCMode.UNKNOWN
        except Exception:
            return PLCMode.UNKNOWN

    def authenticate(self, password: str) -> bool:
        """Authenticate with password"""
        try:
            return self._client.authenticate(password)
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_access_level(self) -> AccessLevel:
        """Get access level"""
        return AccessLevel.FULL

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostics"""
        try:
            status = self._client.controller_status_read()
            return {
                'connected': self._connected,
                'status': status,
            }
        except Exception as e:
            return {'error': str(e)}
