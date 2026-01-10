"""
Delta DVP Series Modbus Driver

Supports Delta DVP PLCs using Modbus TCP/RTU protocol.
Uses pymodbus library for communication.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import struct

try:
    from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    from pymodbus.exceptions import ModbusException
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False

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


class DeltaDVPDriver(PLCDevice):
    """
    Delta DVP Series PLC driver using Modbus protocol.

    Supported models:
    - DVP-ES/ES2 series
    - DVP-EX/EX2 series
    - DVP-EC series
    - DVP-SS/SS2 series
    - DVP-SA/SA2 series
    - DVP-SE series
    - DVP-SV series

    Memory mapping (Modbus addresses):
    - X (inputs): 0x0000-0x00FF (coils, read-only)
    - Y (outputs): 0x0500-0x05FF (coils)
    - M (aux relays): 0x0800-0x1FFF (coils)
    - S (step relays): 0x0000-0x03FF (in discrete input range)
    - T (timers): Contacts at 0x0600, Values at 0x0600 (holding)
    - C (counters): Contacts at 0x0E00, Values at 0x0E00 (holding)
    - D (data regs): 0x1000-0x9FFF (holding registers)
    """

    # Delta DVP Modbus address mapping
    COIL_X_BASE = 0x0000      # X inputs (read-only)
    COIL_Y_BASE = 0x0500      # Y outputs
    COIL_M_BASE = 0x0800      # M auxiliary relays
    COIL_S_BASE = 0x0000      # S step relays (discrete inputs)

    HOLDING_D_BASE = 0x1000   # D data registers
    HOLDING_T_BASE = 0x0600   # T timer values
    HOLDING_C_BASE = 0x0E00   # C counter values

    def __init__(self):
        super().__init__()
        if not PYMODBUS_AVAILABLE:
            raise ImportError(
                "pymodbus library not installed. Install with: pip install pymodbus"
            )

        self._client: Optional[ModbusTcpClient] = None
        self._ip: Optional[str] = None
        self._port: int = 502
        self._unit_id: int = 1
        self._connection_type: str = "tcp"

    def connect(self, ip: str, **kwargs) -> bool:
        """
        Connect to Delta PLC.

        Args:
            ip: IP address (for TCP) or COM port (for RTU)
            port: TCP port (default 502)
            unit_id: Modbus unit ID (default 1)
            connection_type: "tcp" or "rtu"

        Returns:
            True if connected
        """
        self._ip = ip
        self._port = kwargs.get('port', 502)
        self._unit_id = kwargs.get('unit_id', 1)
        self._connection_type = kwargs.get('connection_type', 'tcp')

        try:
            if self._connection_type == 'tcp':
                self._client = ModbusTcpClient(
                    host=ip,
                    port=self._port,
                    timeout=5
                )
            else:
                # Serial/RTU connection
                baudrate = kwargs.get('baudrate', 9600)
                self._client = ModbusSerialClient(
                    port=ip,
                    baudrate=baudrate,
                    parity='N',
                    stopbits=1,
                    bytesize=8,
                    timeout=3
                )

            self._connected = self._client.connect()

            if self._connected:
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
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device information"""
        # Delta PLCs don't have standard device ID via Modbus
        # Return generic info
        return DeviceInfo(
            vendor="Delta",
            model="DVP Series",
            firmware="Unknown",
            serial="Unknown",
            name="Delta PLC",
            ip_address=self._ip,
            additional_info={
                'unit_id': self._unit_id,
                'connection_type': self._connection_type,
            }
        )

    def get_device_info(self) -> DeviceInfo:
        """Get device info"""
        if not self._device_info:
            self._device_info = self._read_device_info()
        return self._device_info

    def get_protection_status(self) -> ProtectionStatus:
        """Get protection status"""
        # Delta PLCs manage protection through ISPSoft
        return ProtectionStatus(
            cpu_protected=False,
            project_protected=False,
            block_protected=False,
            access_level=AccessLevel.FULL,
        )

    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        """Read raw memory"""
        try:
            if area == MemoryArea.DATA:
                # D registers (holding registers)
                result = self._client.read_holding_registers(
                    self.HOLDING_D_BASE + address,
                    count,
                    slave=self._unit_id
                )
                if result.isError():
                    raise Exception(str(result))
                # Convert registers to bytes
                data = b''
                for reg in result.registers:
                    data += struct.pack('>H', reg)
                return data

            elif area == MemoryArea.INPUT:
                # X inputs (coils)
                result = self._client.read_coils(
                    self.COIL_X_BASE + address,
                    count * 8,  # count in bits
                    slave=self._unit_id
                )
                if result.isError():
                    raise Exception(str(result))
                return bytes(result.bits[:count])

            elif area == MemoryArea.OUTPUT:
                # Y outputs (coils)
                result = self._client.read_coils(
                    self.COIL_Y_BASE + address,
                    count * 8,
                    slave=self._unit_id
                )
                if result.isError():
                    raise Exception(str(result))
                return bytes(result.bits[:count])

            elif area == MemoryArea.MEMORY:
                # M auxiliary relays (coils)
                result = self._client.read_coils(
                    self.COIL_M_BASE + address,
                    count * 8,
                    slave=self._unit_id
                )
                if result.isError():
                    raise Exception(str(result))
                return bytes(result.bits[:count])

            else:
                raise ValueError(f"Unsupported memory area: {area}")

        except Exception as e:
            self._last_error = str(e)
            raise

    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        """Write raw memory"""
        try:
            if area == MemoryArea.DATA:
                # D registers
                # Convert bytes to registers
                registers = []
                for i in range(0, len(data), 2):
                    if i + 1 < len(data):
                        registers.append(struct.unpack('>H', data[i:i+2])[0])
                    else:
                        registers.append(data[i])

                result = self._client.write_registers(
                    self.HOLDING_D_BASE + address,
                    registers,
                    slave=self._unit_id
                )
                return not result.isError()

            elif area == MemoryArea.OUTPUT:
                # Y outputs
                bits = [bool(b) for b in data]
                result = self._client.write_coils(
                    self.COIL_Y_BASE + address,
                    bits,
                    slave=self._unit_id
                )
                return not result.isError()

            elif area == MemoryArea.MEMORY:
                # M relays
                bits = [bool(b) for b in data]
                result = self._client.write_coils(
                    self.COIL_M_BASE + address,
                    bits,
                    slave=self._unit_id
                )
                return not result.isError()

            else:
                self._last_error = f"Cannot write to area: {area}"
                return False

        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read by Delta address format.

        Supports:
        - D0, D100, D1000 (data registers)
        - M0, M100 (auxiliary relays)
        - X0, X10 (inputs, octal)
        - Y0, Y10 (outputs, octal)
        - T0, T100 (timers)
        - C0, C100 (counters)
        """
        try:
            addr_info = self._parse_address(tag_name)
            value = self._read_by_type(addr_info)

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
        """Write by Delta address format"""
        try:
            addr_info = self._parse_address(tag_name)
            return self._write_by_type(addr_info, value)
        except Exception as e:
            self._last_error = str(e)
            return False

    def _parse_address(self, address: str) -> Dict[str, Any]:
        """Parse Delta address format"""
        address = address.upper().strip()
        result = {
            'area': None,
            'address': 0,
            'type': 'WORD',
            'modbus_addr': 0,
            'is_bit': False,
        }

        if address.startswith('D'):
            # Data register
            result['area'] = 'D'
            result['address'] = int(address[1:])
            result['modbus_addr'] = self.HOLDING_D_BASE + result['address']
            result['type'] = 'WORD'

        elif address.startswith('M'):
            # Auxiliary relay
            result['area'] = 'M'
            result['address'] = int(address[1:])
            result['modbus_addr'] = self.COIL_M_BASE + result['address']
            result['type'] = 'BOOL'
            result['is_bit'] = True

        elif address.startswith('X'):
            # Input (octal addressing)
            result['area'] = 'X'
            # Convert octal to decimal
            addr_str = address[1:]
            if addr_str:
                result['address'] = int(addr_str, 8)
            result['modbus_addr'] = self.COIL_X_BASE + result['address']
            result['type'] = 'BOOL'
            result['is_bit'] = True

        elif address.startswith('Y'):
            # Output (octal addressing)
            result['area'] = 'Y'
            addr_str = address[1:]
            if addr_str:
                result['address'] = int(addr_str, 8)
            result['modbus_addr'] = self.COIL_Y_BASE + result['address']
            result['type'] = 'BOOL'
            result['is_bit'] = True

        elif address.startswith('T'):
            # Timer
            result['area'] = 'T'
            result['address'] = int(address[1:])
            result['modbus_addr'] = self.HOLDING_T_BASE + result['address']
            result['type'] = 'WORD'

        elif address.startswith('C'):
            # Counter
            result['area'] = 'C'
            result['address'] = int(address[1:])
            result['modbus_addr'] = self.HOLDING_C_BASE + result['address']
            result['type'] = 'WORD'

        elif address.startswith('S'):
            # Step relay
            result['area'] = 'S'
            result['address'] = int(address[1:])
            result['modbus_addr'] = self.COIL_S_BASE + result['address']
            result['type'] = 'BOOL'
            result['is_bit'] = True

        else:
            raise ValueError(f"Unknown address format: {address}")

        return result

    def _read_by_type(self, addr_info: Dict[str, Any]) -> Any:
        """Read value based on address type"""
        if addr_info['is_bit']:
            # Read coil
            result = self._client.read_coils(
                addr_info['modbus_addr'],
                1,
                slave=self._unit_id
            )
            if result.isError():
                raise Exception(str(result))
            return result.bits[0]
        else:
            # Read holding register
            result = self._client.read_holding_registers(
                addr_info['modbus_addr'],
                1,
                slave=self._unit_id
            )
            if result.isError():
                raise Exception(str(result))
            return result.registers[0]

    def _write_by_type(self, addr_info: Dict[str, Any], value: Any) -> bool:
        """Write value based on address type"""
        try:
            if addr_info['is_bit']:
                # Write coil
                result = self._client.write_coil(
                    addr_info['modbus_addr'],
                    bool(value),
                    slave=self._unit_id
                )
            else:
                # Write holding register
                result = self._client.write_register(
                    addr_info['modbus_addr'],
                    int(value),
                    slave=self._unit_id
                )

            return not result.isError()
        except Exception as e:
            self._last_error = str(e)
            return False

    def upload_program(self) -> PLCProgram:
        """Upload program - not supported via Modbus"""
        self._last_error = "Program upload requires ISPSoft"
        return PLCProgram(vendor="Delta", model="DVP Series")

    def download_program(self, program: PLCProgram) -> bool:
        """Download program - not supported via Modbus"""
        self._last_error = "Program download requires ISPSoft"
        return False

    def get_block_list(self) -> List[BlockInfo]:
        """Get block list - not available via Modbus"""
        return []

    def get_block(self, block_type: BlockType, number: int) -> Block:
        """Get block - not available via Modbus"""
        raise NotImplementedError("Block access requires ISPSoft")

    def start(self) -> bool:
        """Start PLC - limited support"""
        # Some Delta PLCs support run/stop via special registers
        try:
            # D9046 is often used for remote run/stop
            result = self._client.write_register(
                0x1000 + 9046,
                1,  # 1 = RUN
                slave=self._unit_id
            )
            return not result.isError()
        except Exception as e:
            self._last_error = str(e)
            return False

    def stop(self) -> bool:
        """Stop PLC"""
        try:
            result = self._client.write_register(
                0x1000 + 9046,
                0,  # 0 = STOP
                slave=self._unit_id
            )
            return not result.isError()
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_mode(self) -> PLCMode:
        """Get PLC mode"""
        try:
            # Read status register
            result = self._client.read_holding_registers(
                0x1000 + 9046,
                1,
                slave=self._unit_id
            )
            if not result.isError():
                if result.registers[0] == 1:
                    return PLCMode.RUN
                else:
                    return PLCMode.STOP
        except Exception:
            pass
        return PLCMode.UNKNOWN

    def authenticate(self, password: str) -> bool:
        """Authenticate - Delta uses ISPSoft for password management"""
        self._last_error = "Password authentication requires ISPSoft"
        return False

    def get_access_level(self) -> AccessLevel:
        """Get access level"""
        return AccessLevel.FULL  # No runtime protection via Modbus

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostics"""
        return {
            'connected': self._connected,
            'unit_id': self._unit_id,
            'mode': self.get_mode().value,
        }
