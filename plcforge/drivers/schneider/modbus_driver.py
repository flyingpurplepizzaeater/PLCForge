"""
Schneider Electric Modbus Protocol Driver

Supports Modicon M340, M580, Premium, Quantum, and Micro series PLCs.
Uses pymodbus library for Modbus TCP/RTU communication.
"""

import struct
from enum import IntEnum
from typing import Any

try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False

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


class SchneiderMemoryType(IntEnum):
    """Schneider Electric memory types mapped to Modbus addresses"""
    # Discrete inputs (%I)
    DISCRETE_INPUT = 0
    # Coils (%Q, %M)
    COIL = 1
    # Input registers (%IW)
    INPUT_REGISTER = 2
    # Holding registers (%MW, %MD)
    HOLDING_REGISTER = 3


# Schneider address ranges (Unity Pro / EcoStruxure conventions)
ADDRESS_RANGES = {
    '%I': (0, 0xFFFF, SchneiderMemoryType.DISCRETE_INPUT),      # Digital inputs
    '%Q': (0, 0xFFFF, SchneiderMemoryType.COIL),                # Digital outputs
    '%M': (0, 0xFFFF, SchneiderMemoryType.COIL),                # Internal bits
    '%IW': (0, 0x7FFF, SchneiderMemoryType.INPUT_REGISTER),     # Input words
    '%QW': (0, 0x7FFF, SchneiderMemoryType.HOLDING_REGISTER),   # Output words
    '%MW': (0, 0x7FFF, SchneiderMemoryType.HOLDING_REGISTER),   # Internal words
    '%MD': (0, 0x3FFF, SchneiderMemoryType.HOLDING_REGISTER),   # Internal double words
    '%MF': (0, 0x3FFF, SchneiderMemoryType.HOLDING_REGISTER),   # Internal floats
}


class SchneiderModbusDriver(PLCDevice):
    """
    Schneider Electric Modbus driver.

    Supports:
    - Modicon M340 (BMX P34)
    - Modicon M580 (BME P58)
    - Premium (TSX P57)
    - Quantum (140 CPU)
    - Micro (BMX NOE 01x0)

    Uses standard Modbus TCP/RTU with Schneider-specific addressing.
    """

    # Default ports
    DEFAULT_TCP_PORT = 502
    DEFAULT_UNIT_ID = 1

    def __init__(self):
        super().__init__()
        if not PYMODBUS_AVAILABLE:
            raise ImportError(
                "pymodbus library not installed. Install with: pip install pymodbus"
            )
        self._client: ModbusTcpClient | None = None
        self._ip: str | None = None
        self._port: int = self.DEFAULT_TCP_PORT
        self._unit_id: int = self.DEFAULT_UNIT_ID
        self._timeout: float = 5.0
        self._use_rtu: bool = False
        self._serial_port: str | None = None

    @property
    def vendor(self) -> str:
        return "Schneider Electric"

    def connect(
        self,
        ip: str,
        port: int = DEFAULT_TCP_PORT,
        unit_id: int = DEFAULT_UNIT_ID,
        timeout: float = 5.0
    ) -> bool:
        """
        Connect to Schneider PLC via Modbus TCP.

        Args:
            ip: IP address of the PLC
            port: TCP port (default 502)
            unit_id: Modbus unit ID (default 1)
            timeout: Connection timeout in seconds
        """
        self._ip = ip
        self._port = port
        self._unit_id = unit_id
        self._timeout = timeout

        try:
            self._client = ModbusTcpClient(
                host=ip,
                port=port,
                timeout=timeout
            )

            if not self._client.connect():
                self._last_error = "Failed to establish TCP connection"
                return False

            self._connected = True

            # Read device identification
            self._device_info = self._read_device_info()

            return True
        except Exception as e:
            self._last_error = f"Connection failed: {e}"
            self._connected = False
            return False

    def connect_rtu(
        self,
        port: str,
        baudrate: int = 19200,
        unit_id: int = DEFAULT_UNIT_ID,
        timeout: float = 5.0
    ) -> bool:
        """
        Connect to Schneider PLC via Modbus RTU (serial).

        Args:
            port: Serial port (e.g., "COM1" or "/dev/ttyUSB0")
            baudrate: Baud rate (default 19200)
            unit_id: Modbus unit ID (default 1)
            timeout: Communication timeout in seconds
        """
        self._serial_port = port
        self._unit_id = unit_id
        self._timeout = timeout
        self._use_rtu = True

        try:
            self._client = ModbusSerialClient(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                parity='E',  # Even parity (Schneider default)
                stopbits=1,
                bytesize=8
            )

            if not self._client.connect():
                self._last_error = "Failed to establish serial connection"
                return False

            self._connected = True
            self._device_info = self._read_device_info()

            return True
        except Exception as e:
            self._last_error = f"RTU connection failed: {e}"
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device identification via Modbus Device Information."""
        model = "Modicon"
        firmware = ""

        try:
            if self._client:
                # Try to read device identification (function code 43/14)
                # Object ID 0x00 = Vendor Name
                # Object ID 0x01 = Product Code
                # Object ID 0x02 = Major/Minor Revision
                response = self._client.read_device_information(
                    slave=self._unit_id
                )
                if response and not response.isError():
                    info = response.information
                    if 0x01 in info:
                        model = info[0x01].decode('ascii', errors='ignore')
                    if 0x02 in info:
                        firmware = info[0x02].decode('ascii', errors='ignore')
        except Exception:
            pass

        return DeviceInfo(
            vendor="Schneider Electric",
            model=model,
            firmware_version=firmware,
            serial_number="",
            ip_address=self._ip or self._serial_port or "",
        )

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        if self._device_info:
            return self._device_info
        return self._read_device_info()

    def get_protection_status(self) -> ProtectionStatus:
        """Get protection status."""
        return ProtectionStatus(
            protection_level=0,
            password_protected=False,
        )

    def read_memory(self, area: MemoryArea, start: int, length: int) -> bytes:
        """
        Read memory area.

        Maps generic memory areas to Schneider-specific addresses.
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        # Map memory areas to Modbus function codes
        if area == MemoryArea.INPUT:
            # Read discrete inputs
            response = self._client.read_discrete_inputs(
                address=start,
                count=length * 8,
                slave=self._unit_id
            )
            if response.isError():
                raise ValueError(f"Read error: {response}")
            # Pack bits into bytes
            bits = response.bits[:length * 8]
            return bytes([
                sum(bits[i*8:(i+1)*8][j] << j for j in range(8))
                for i in range(length)
            ])

        elif area == MemoryArea.OUTPUT:
            # Read coils
            response = self._client.read_coils(
                address=start,
                count=length * 8,
                slave=self._unit_id
            )
            if response.isError():
                raise ValueError(f"Read error: {response}")
            bits = response.bits[:length * 8]
            return bytes([
                sum(bits[i*8:(i+1)*8][j] << j for j in range(8))
                for i in range(length)
            ])

        elif area in (MemoryArea.MEMORY, MemoryArea.DATA):
            # Read holding registers
            # Length is in bytes, convert to registers (2 bytes each)
            reg_count = (length + 1) // 2
            response = self._client.read_holding_registers(
                address=start,
                count=reg_count,
                slave=self._unit_id
            )
            if response.isError():
                raise ValueError(f"Read error: {response}")
            # Convert registers to bytes
            result = b''
            for reg in response.registers:
                result += struct.pack('>H', reg)
            return result[:length]

        else:
            raise ValueError(f"Unsupported memory area: {area}")

    def write_memory(self, area: MemoryArea, start: int, data: bytes) -> bool:
        """Write to memory area."""
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        try:
            if area == MemoryArea.OUTPUT:
                # Write coils
                bits = []
                for byte in data:
                    for i in range(8):
                        bits.append(bool(byte & (1 << i)))
                response = self._client.write_coils(
                    address=start,
                    values=bits,
                    slave=self._unit_id
                )
                return not response.isError()

            elif area in (MemoryArea.MEMORY, MemoryArea.DATA):
                # Write holding registers
                registers = []
                for i in range(0, len(data), 2):
                    if i + 1 < len(data):
                        reg = struct.unpack('>H', data[i:i+2])[0]
                    else:
                        reg = data[i] << 8
                    registers.append(reg)
                response = self._client.write_registers(
                    address=start,
                    values=registers,
                    slave=self._unit_id
                )
                return not response.isError()

            else:
                raise ValueError(f"Unsupported memory area for write: {area}")

        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read tag by Schneider address format.

        Supports:
        - %MW100 (memory word)
        - %MD50 (memory double word)
        - %MF10 (memory float)
        - %I0.5 (input bit)
        - %Q1.2 (output bit)
        - %M100 (internal bit)
        """
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        address_type, address, bit = self._parse_address(tag_name)
        value: Any = None
        data_type = "WORD"

        try:
            if address_type in ('%I',):
                # Read discrete input
                response = self._client.read_discrete_inputs(
                    address=address * 8 + (bit or 0),
                    count=1,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                value = response.bits[0]
                data_type = "BOOL"

            elif address_type in ('%Q', '%M'):
                # Read coil
                response = self._client.read_coils(
                    address=address * 8 + (bit or 0) if bit is not None else address,
                    count=1,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                value = response.bits[0]
                data_type = "BOOL"

            elif address_type in ('%IW',):
                # Read input register
                response = self._client.read_input_registers(
                    address=address,
                    count=1,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                value = response.registers[0]
                data_type = "WORD"

            elif address_type in ('%MW', '%QW'):
                # Read holding register (word)
                response = self._client.read_holding_registers(
                    address=address,
                    count=1,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                value = response.registers[0]
                data_type = "WORD"

            elif address_type == '%MD':
                # Read holding registers (double word)
                response = self._client.read_holding_registers(
                    address=address * 2,
                    count=2,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                decoder = BinaryPayloadDecoder.fromRegisters(
                    response.registers,
                    byteorder=Endian.BIG,
                    wordorder=Endian.BIG
                )
                value = decoder.decode_32bit_int()
                data_type = "DINT"

            elif address_type == '%MF':
                # Read holding registers (float)
                response = self._client.read_holding_registers(
                    address=address * 2,
                    count=2,
                    slave=self._unit_id
                )
                if response.isError():
                    raise ValueError(f"Read error: {response}")
                decoder = BinaryPayloadDecoder.fromRegisters(
                    response.registers,
                    byteorder=Endian.BIG,
                    wordorder=Endian.BIG
                )
                value = decoder.decode_32bit_float()
                data_type = "REAL"

            else:
                raise ValueError(f"Unknown address type: {address_type}")

            return TagValue(
                name=tag_name,
                value=value,
                data_type=data_type,
                address=tag_name,
            )

        except Exception as e:
            self._last_error = str(e)
            raise

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write tag by Schneider address format."""
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        address_type, address, bit = self._parse_address(tag_name)

        try:
            if address_type in ('%Q', '%M'):
                # Write single coil
                addr = address * 8 + (bit or 0) if bit is not None else address
                response = self._client.write_coil(
                    address=addr,
                    value=bool(value),
                    slave=self._unit_id
                )
                return not response.isError()

            elif address_type in ('%MW', '%QW'):
                # Write single register
                response = self._client.write_register(
                    address=address,
                    value=int(value),
                    slave=self._unit_id
                )
                return not response.isError()

            elif address_type == '%MD':
                # Write double word (2 registers)
                builder = BinaryPayloadBuilder(
                    byteorder=Endian.BIG,
                    wordorder=Endian.BIG
                )
                builder.add_32bit_int(int(value))
                payload = builder.to_registers()
                response = self._client.write_registers(
                    address=address * 2,
                    values=payload,
                    slave=self._unit_id
                )
                return not response.isError()

            elif address_type == '%MF':
                # Write float (2 registers)
                builder = BinaryPayloadBuilder(
                    byteorder=Endian.BIG,
                    wordorder=Endian.BIG
                )
                builder.add_32bit_float(float(value))
                payload = builder.to_registers()
                response = self._client.write_registers(
                    address=address * 2,
                    values=payload,
                    slave=self._unit_id
                )
                return not response.isError()

            else:
                raise ValueError(f"Cannot write to address type: {address_type}")

        except Exception as e:
            self._last_error = str(e)
            return False

    def _parse_address(self, address: str) -> tuple[str, int, int | None]:
        """
        Parse Schneider address format.

        Returns: (address_type, address_number, bit_number)

        Examples:
        - "%MW100" -> ("%MW", 100, None)
        - "%M10.5" -> ("%M", 10, 5)
        - "%I0.3" -> ("%I", 0, 3)
        """
        address = address.upper().strip()

        # Extract address type prefix
        for prefix in sorted(ADDRESS_RANGES.keys(), key=len, reverse=True):
            if address.startswith(prefix):
                rest = address[len(prefix):]

                # Check for bit address (X.Y format)
                if '.' in rest:
                    parts = rest.split('.')
                    return prefix, int(parts[0]), int(parts[1])
                else:
                    return prefix, int(rest), None

        raise ValueError(f"Invalid Schneider address format: {address}")

    def read_multiple_registers(
        self,
        start_address: int,
        count: int,
        register_type: str = "holding"
    ) -> list[int]:
        """Read multiple registers efficiently."""
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        if register_type == "holding":
            response = self._client.read_holding_registers(
                address=start_address,
                count=count,
                slave=self._unit_id
            )
        elif register_type == "input":
            response = self._client.read_input_registers(
                address=start_address,
                count=count,
                slave=self._unit_id
            )
        else:
            raise ValueError(f"Unknown register type: {register_type}")

        if response.isError():
            raise ValueError(f"Read error: {response}")

        return response.registers

    def write_multiple_registers(
        self,
        start_address: int,
        values: list[int]
    ) -> bool:
        """Write multiple registers efficiently."""
        if not self._client or not self._connected:
            raise ConnectionError("Not connected")

        try:
            response = self._client.write_registers(
                address=start_address,
                values=values,
                slave=self._unit_id
            )
            return not response.isError()
        except Exception as e:
            self._last_error = str(e)
            return False

    def authenticate(self, password: str) -> bool:
        """Authenticate (Modbus has no standard authentication)."""
        return True

    def list_blocks(self, block_type: BlockType | None = None) -> list[BlockInfo]:
        """List program blocks (not supported via Modbus)."""
        return []

    def upload_block(self, block_type: BlockType, number: int) -> bytes:
        """Upload block (not supported)."""
        return b''

    def download_block(self, block_type: BlockType, number: int, data: bytes) -> bool:
        """Download block (not supported)."""
        return False

    def upload_program(self) -> PLCProgram:
        """Upload program (not supported)."""
        return PLCProgram(vendor="Schneider Electric", model="Modicon", blocks=[])

    def download_program(self, program: PLCProgram) -> bool:
        """Download program (not supported)."""
        return False

    def get_mode(self) -> PLCMode:
        """Get PLC mode (limited support via Modbus)."""
        return PLCMode.RUN

    def set_mode(self, mode: PLCMode) -> bool:
        """Set PLC mode (not supported via standard Modbus)."""
        return False

    def start(self) -> bool:
        """Start PLC (not supported via Modbus)."""
        return False

    def stop(self) -> bool:
        """Stop PLC (not supported via Modbus)."""
        return False

    def get_access_level(self) -> AccessLevel:
        """Get current access level."""
        return AccessLevel.READ_WRITE

    def get_block(self, block_type: BlockType, number: int) -> Block | None:
        """Get block (not supported via Modbus)."""
        return None

    def get_block_list(self, block_type: BlockType | None = None) -> list[BlockInfo]:
        """Get list of blocks (not supported via Modbus)."""
        return []
