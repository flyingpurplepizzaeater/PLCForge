"""
Siemens S7comm Protocol Driver

Supports S7-300, S7-400, and S7-1200/1500 in compatibility mode.
Uses python-snap7 library for low-level communication.
"""

import struct
from datetime import datetime
from enum import IntEnum
from typing import Any

try:
    import snap7
    from snap7.client import Client
    from snap7.types import Areas, WordLen
    from snap7.util import get_bool, get_int, get_real, set_bool, set_int, set_real
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False

from plcforge.drivers.base import (
    AccessLevel,
    Block,
    BlockInfo,
    BlockType,
    CodeLanguage,
    DeviceInfo,
    MemoryArea,
    PLCDevice,
    PLCMode,
    PLCProgram,
    ProtectionStatus,
    TagValue,
)


class S7Area(IntEnum):
    """S7 memory area codes"""
    PE = 0x81   # Process inputs
    PA = 0x82   # Process outputs
    MK = 0x83   # Merkers (flags)
    DB = 0x84   # Data blocks
    CT = 0x1C   # Counters
    TM = 0x1D   # Timers


class S7BlockType(IntEnum):
    """S7 block type codes"""
    OB = 0x38
    DB = 0x41
    SDB = 0x42
    FC = 0x43
    SFC = 0x44
    FB = 0x45
    SFB = 0x46


# Memory area mapping (only if snap7 available)
if SNAP7_AVAILABLE:
    MEMORY_AREA_MAP = {
        MemoryArea.INPUT: Areas.PE,
        MemoryArea.OUTPUT: Areas.PA,
        MemoryArea.MEMORY: Areas.MK,
        MemoryArea.DATA: Areas.DB,
        MemoryArea.TIMER: Areas.TM,
        MemoryArea.COUNTER: Areas.CT,
    }
else:
    MEMORY_AREA_MAP = {}


class SiemensS7Driver(PLCDevice):
    """
    Siemens S7 driver using S7comm protocol.

    Supports:
    - S7-300 (all firmware versions)
    - S7-400 (all firmware versions)
    - S7-1200 G1 (V1.x-V4.x in compatibility mode)
    - S7-1200 G2 (V1.x+ in compatibility mode)
    - S7-1500 (V1.x+ in compatibility mode)
    """

    def __init__(self):
        super().__init__()
        if not SNAP7_AVAILABLE:
            raise ImportError("python-snap7 library not installed. Install with: pip install python-snap7")

        self._client: Client | None = None
        self._ip: str | None = None
        self._rack: int = 0
        self._slot: int = 1
        self._model: str | None = None

    def connect(self, ip: str, **kwargs) -> bool:
        """
        Connect to Siemens PLC.

        Args:
            ip: IP address
            rack: Rack number (default 0)
            slot: Slot number (default 1 for S7-300, 0 for S7-1200/1500)
            model: Model hint for optimization

        Returns:
            True if connected successfully
        """
        self._ip = ip
        self._rack = kwargs.get('rack', 0)
        self._slot = kwargs.get('slot', 1)
        self._model = kwargs.get('model')

        # Auto-adjust slot for newer PLCs
        if self._model and ('1200' in self._model or '1500' in self._model):
            self._slot = kwargs.get('slot', 0)

        try:
            self._client = Client()
            self._client.connect(ip, self._rack, self._slot)
            self._connected = self._client.get_connected()

            if self._connected:
                # Cache device info
                self._device_info = self._read_device_info()

            return self._connected
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from PLC"""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device information from PLC"""
        try:
            cpu_info = self._client.get_cpu_info()
            order_code = self._client.get_order_code()

            return DeviceInfo(
                vendor="Siemens",
                model=cpu_info.ModuleTypeName.decode('utf-8').strip(),
                firmware=f"V{cpu_info.ASName.decode('utf-8').strip()}",
                serial=cpu_info.SerialNumber.decode('utf-8').strip(),
                name=cpu_info.ModuleName.decode('utf-8').strip(),
                ip_address=self._ip,
                rack=self._rack,
                slot=self._slot,
                additional_info={
                    'order_code': order_code.OrderCode.decode('utf-8').strip(),
                }
            )
        except Exception:
            return DeviceInfo(
                vendor="Siemens",
                model=self._model or "Unknown S7",
                firmware="Unknown",
                serial="Unknown",
                name="Unknown",
                ip_address=self._ip,
            )

    def get_device_info(self) -> DeviceInfo:
        """Get cached device information"""
        if not self._device_info:
            self._device_info = self._read_device_info()
        return self._device_info

    def get_protection_status(self) -> ProtectionStatus:
        """Get PLC protection status"""
        try:
            protection = self._client.get_protection()
            # Protection levels: 1=no protection, 2=read protection, 3=read/write protection

            cpu_protected = protection.sch_schal > 1
            access_level = AccessLevel.FULL

            if protection.sch_schal == 2:
                access_level = AccessLevel.READ_ONLY
            elif protection.sch_schal >= 3:
                access_level = AccessLevel.NONE

            return ProtectionStatus(
                cpu_protected=cpu_protected,
                project_protected=False,  # Determined from project file
                block_protected=False,    # Check individual blocks
                access_level=access_level,
                protection_details={
                    'sch_schal': protection.sch_schal,
                    'sch_par': protection.sch_par,
                    'sch_rel': protection.sch_rel,
                    'bart_sch': protection.bart_sch,
                    'anl_sch': protection.anl_sch,
                }
            )
        except Exception as e:
            self._last_error = str(e)
            return ProtectionStatus()

    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        """Read raw bytes from memory area"""
        try:
            if area == MemoryArea.DATA:
                # For DB area, address format is DB number
                # Assume DB1 if just address given
                return self._client.db_read(1, address, count)

            snap7_area = MEMORY_AREA_MAP.get(area)
            if snap7_area is None:
                raise ValueError(f"Unsupported memory area: {area}")

            return bytes(self._client.read_area(snap7_area, 0, address, count))
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        """Write raw bytes to memory area"""
        try:
            if area == MemoryArea.DATA:
                self._client.db_write(1, address, bytearray(data))
                return True

            snap7_area = MEMORY_AREA_MAP.get(area)
            if snap7_area is None:
                raise ValueError(f"Unsupported memory area: {area}")

            self._client.write_area(snap7_area, 0, address, bytearray(data))
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read a tag by name or address.

        Supports formats:
        - "DB1.DBD0" - Data block double word
        - "DB1.DBW10" - Data block word
        - "DB1.DBX0.0" - Data block bit
        - "M0.0" - Merker bit
        - "MW10" - Merker word
        - "I0.0" - Input bit
        - "Q0.0" - Output bit
        """
        try:
            address_info = self._parse_address(tag_name)
            value = self._read_by_address(address_info)

            return TagValue(
                name=tag_name,
                value=value,
                data_type=address_info['type'],
                address=tag_name,
                timestamp=datetime.now(),
            )
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write to a tag by name or address"""
        try:
            address_info = self._parse_address(tag_name)
            return self._write_by_address(address_info, value)
        except Exception as e:
            self._last_error = str(e)
            return False

    def _parse_address(self, address: str) -> dict[str, Any]:
        """
        Parse S7 address string into components.

        Returns dict with: area, db_number, offset, bit, type, size
        """
        address = address.upper().strip()
        result = {
            'area': None,
            'db_number': None,
            'offset': 0,
            'bit': None,
            'type': 'BYTE',
            'size': 1,
        }

        # Data block address: DB1.DBX0.0, DB1.DBW10, DB1.DBD20
        if address.startswith('DB'):
            parts = address.split('.')
            result['area'] = 'DB'
            result['db_number'] = int(parts[0][2:])

            if len(parts) > 1:
                addr_part = parts[1]
                if addr_part.startswith('DBX'):
                    # Bit address: DBX0.0
                    result['offset'] = int(addr_part[3:])
                    result['bit'] = int(parts[2]) if len(parts) > 2 else 0
                    result['type'] = 'BOOL'
                    result['size'] = 1
                elif addr_part.startswith('DBB'):
                    result['offset'] = int(addr_part[3:])
                    result['type'] = 'BYTE'
                    result['size'] = 1
                elif addr_part.startswith('DBW'):
                    result['offset'] = int(addr_part[3:])
                    result['type'] = 'WORD'
                    result['size'] = 2
                elif addr_part.startswith('DBD'):
                    result['offset'] = int(addr_part[3:])
                    result['type'] = 'DWORD'
                    result['size'] = 4

        # Merker address: M0.0, MB0, MW0, MD0
        elif address.startswith('M'):
            result['area'] = 'M'
            if '.' in address:
                # Bit address
                parts = address[1:].split('.')
                result['offset'] = int(parts[0])
                result['bit'] = int(parts[1])
                result['type'] = 'BOOL'
            elif address[1] == 'B':
                result['offset'] = int(address[2:])
                result['type'] = 'BYTE'
            elif address[1] == 'W':
                result['offset'] = int(address[2:])
                result['type'] = 'WORD'
                result['size'] = 2
            elif address[1] == 'D':
                result['offset'] = int(address[2:])
                result['type'] = 'DWORD'
                result['size'] = 4
            else:
                # Just M0 = MB0
                result['offset'] = int(address[1:])
                result['type'] = 'BYTE'

        # Input address: I0.0, IB0, IW0
        elif address.startswith('I') or address.startswith('E'):
            result['area'] = 'I'
            addr = address[1:]
            if '.' in addr:
                parts = addr.split('.')
                result['offset'] = int(parts[0])
                result['bit'] = int(parts[1])
                result['type'] = 'BOOL'
            elif addr[0] == 'B':
                result['offset'] = int(addr[1:])
                result['type'] = 'BYTE'
            elif addr[0] == 'W':
                result['offset'] = int(addr[1:])
                result['type'] = 'WORD'
                result['size'] = 2
            else:
                result['offset'] = int(addr)
                result['type'] = 'BYTE'

        # Output address: Q0.0, QB0, QW0
        elif address.startswith('Q') or address.startswith('A'):
            result['area'] = 'Q'
            addr = address[1:]
            if '.' in addr:
                parts = addr.split('.')
                result['offset'] = int(parts[0])
                result['bit'] = int(parts[1])
                result['type'] = 'BOOL'
            elif addr[0] == 'B':
                result['offset'] = int(addr[1:])
                result['type'] = 'BYTE'
            elif addr[0] == 'W':
                result['offset'] = int(addr[1:])
                result['type'] = 'WORD'
                result['size'] = 2
            else:
                result['offset'] = int(addr)
                result['type'] = 'BYTE'

        return result

    def _read_by_address(self, addr_info: dict[str, Any]) -> Any:
        """Read value using parsed address info"""
        area = addr_info['area']
        offset = addr_info['offset']
        size = addr_info['size']
        data_type = addr_info['type']

        # Read raw bytes
        if area == 'DB':
            data = self._client.db_read(addr_info['db_number'], offset, size)
        elif area == 'M':
            data = self._client.read_area(Areas.MK, 0, offset, size)
        elif area == 'I':
            data = self._client.read_area(Areas.PE, 0, offset, size)
        elif area == 'Q':
            data = self._client.read_area(Areas.PA, 0, offset, size)
        else:
            raise ValueError(f"Unknown area: {area}")

        # Convert to appropriate type
        if data_type == 'BOOL':
            bit = addr_info.get('bit', 0)
            return get_bool(data, 0, bit)
        elif data_type == 'BYTE':
            return data[0]
        elif data_type == 'WORD':
            return struct.unpack('>H', bytes(data))[0]
        elif data_type == 'DWORD':
            return struct.unpack('>I', bytes(data))[0]
        elif data_type == 'INT':
            return struct.unpack('>h', bytes(data))[0]
        elif data_type == 'DINT':
            return struct.unpack('>i', bytes(data))[0]
        elif data_type == 'REAL':
            return struct.unpack('>f', bytes(data))[0]
        else:
            return bytes(data)

    def _write_by_address(self, addr_info: dict[str, Any], value: Any) -> bool:
        """Write value using parsed address info"""
        area = addr_info['area']
        offset = addr_info['offset']
        addr_info['size']
        data_type = addr_info['type']

        # Convert value to bytes
        if data_type == 'BOOL':
            # For bit writes, read-modify-write
            if area == 'DB':
                data = bytearray(self._client.db_read(addr_info['db_number'], offset, 1))
            elif area == 'M':
                data = bytearray(self._client.read_area(Areas.MK, 0, offset, 1))
            elif area == 'I':
                data = bytearray(self._client.read_area(Areas.PE, 0, offset, 1))
            elif area == 'Q':
                data = bytearray(self._client.read_area(Areas.PA, 0, offset, 1))

            bit = addr_info.get('bit', 0)
            set_bool(data, 0, bit, bool(value))
        elif data_type == 'BYTE':
            data = bytearray([int(value) & 0xFF])
        elif data_type == 'WORD':
            data = bytearray(struct.pack('>H', int(value)))
        elif data_type == 'DWORD':
            data = bytearray(struct.pack('>I', int(value)))
        elif data_type == 'INT':
            data = bytearray(struct.pack('>h', int(value)))
        elif data_type == 'DINT':
            data = bytearray(struct.pack('>i', int(value)))
        elif data_type == 'REAL':
            data = bytearray(struct.pack('>f', float(value)))
        else:
            data = bytearray(value)

        # Write to PLC
        try:
            if area == 'DB':
                self._client.db_write(addr_info['db_number'], offset, data)
            elif area == 'M':
                self._client.write_area(Areas.MK, 0, offset, data)
            elif area == 'I':
                self._client.write_area(Areas.PE, 0, offset, data)
            elif area == 'Q':
                self._client.write_area(Areas.PA, 0, offset, data)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def upload_program(self) -> PLCProgram:
        """Upload complete program from PLC"""
        program = PLCProgram(
            vendor="Siemens",
            model=self.get_device_info().model,
        )

        # Get list of blocks and upload each
        block_list = self.get_block_list()
        for block_info in block_list:
            try:
                block = self.get_block(block_info.block_type, block_info.number)
                program.blocks.append(block)
            except Exception:
                # Log error but continue with other blocks
                pass

        return program

    def download_program(self, program: PLCProgram) -> bool:
        """Download program to PLC"""
        # This requires PLC to be in STOP mode
        if self.get_mode() == PLCMode.RUN:
            self._last_error = "PLC must be in STOP mode for program download"
            return False

        try:
            for block in program.blocks:
                if block.compiled_code:
                    # Download compiled block
                    self._download_block(block)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def _download_block(self, block: Block) -> bool:
        """Download a single block to PLC"""
        # Implementation would use snap7 block download functions
        # This is a placeholder for the actual implementation
        raise NotImplementedError("Block download not yet implemented")

    def get_block_list(self) -> list[BlockInfo]:
        """Get list of all program blocks"""
        blocks = []

        try:
            # Get list of each block type
            block_types = [
                (snap7.types.Block.OB, BlockType.OB),
                (snap7.types.Block.FB, BlockType.FB),
                (snap7.types.Block.FC, BlockType.FC),
                (snap7.types.Block.DB, BlockType.DB),
            ]

            for snap7_type, block_type in block_types:
                try:
                    block_list = self._client.list_blocks_of_type(snap7_type, 1000)
                    for block_num in block_list:
                        if block_num > 0:
                            try:
                                info = self._client.get_block_info(snap7_type, block_num)
                                blocks.append(BlockInfo(
                                    block_type=block_type,
                                    number=block_num,
                                    name=f"{block_type.name}{block_num}",
                                    language=CodeLanguage.LADDER,  # Default
                                    size=info.mc7_size,
                                    protected=info.family != b'',
                                ))
                            except Exception:
                                blocks.append(BlockInfo(
                                    block_type=block_type,
                                    number=block_num,
                                    name=f"{block_type.name}{block_num}",
                                    language=CodeLanguage.LADDER,
                                    size=0,
                                ))
                except Exception:
                    pass

        except Exception as e:
            self._last_error = str(e)

        return blocks

    def get_block(self, block_type: BlockType, number: int) -> Block:
        """Get a specific program block"""
        # Map to snap7 block type
        type_map = {
            BlockType.OB: snap7.types.Block.OB,
            BlockType.FB: snap7.types.Block.FB,
            BlockType.FC: snap7.types.Block.FC,
            BlockType.DB: snap7.types.Block.DB,
        }

        snap7_type = type_map.get(block_type)
        if not snap7_type:
            raise ValueError(f"Unsupported block type: {block_type}")

        # Get block info
        self._client.get_block_info(snap7_type, number)

        # Upload block data
        data = self._client.full_upload(snap7_type, number)

        block_info = BlockInfo(
            block_type=block_type,
            number=number,
            name=f"{block_type.name}{number}",
            language=CodeLanguage.LADDER,
            size=len(data),
        )

        return Block(
            info=block_info,
            compiled_code=bytes(data),
        )

    def start(self) -> bool:
        """Start PLC (set to RUN)"""
        try:
            self._client.plc_hot_start()
            return True
        except Exception:
            try:
                self._client.plc_cold_start()
                return True
            except Exception as e2:
                self._last_error = str(e2)
                return False

    def stop(self) -> bool:
        """Stop PLC"""
        try:
            self._client.plc_stop()
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_mode(self) -> PLCMode:
        """Get current PLC mode"""
        try:
            state = self._client.get_cpu_state()
            if state == 'S7CpuStatusRun':
                return PLCMode.RUN
            elif state == 'S7CpuStatusStop':
                return PLCMode.STOP
            else:
                return PLCMode.UNKNOWN
        except Exception:
            return PLCMode.UNKNOWN

    def authenticate(self, password: str) -> bool:
        """Authenticate with PLC password"""
        try:
            self._client.set_session_password(password)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def clear_authentication(self) -> bool:
        """Clear session authentication"""
        try:
            self._client.clear_session_password()
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_access_level(self) -> AccessLevel:
        """Get current access level"""
        protection = self.get_protection_status()
        return protection.access_level

    def get_diagnostics(self) -> dict[str, Any]:
        """Get diagnostic information"""
        try:
            return {
                'cpu_state': self._client.get_cpu_state(),
                'protection': self.get_protection_status().protection_details,
                'connected': self._connected,
            }
        except Exception as e:
            return {'error': str(e)}
