"""
Beckhoff TwinCAT ADS Protocol Driver

Supports TwinCAT 2 and TwinCAT 3 PLCs.
Uses pyads library for ADS communication.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import pyads
    from pyads import Connection, AdsSymbol
    PYADS_AVAILABLE = True
except ImportError:
    PYADS_AVAILABLE = False

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


class BeckhoffADSDriver(PLCDevice):
    """
    Beckhoff TwinCAT ADS driver.

    Supports:
    - TwinCAT 2 (CX series, BC series)
    - TwinCAT 3 (CX series, embedded PCs)
    - EtherCAT terminals

    Uses symbolic variable access for reading/writing.
    """

    # TwinCAT ADS ports
    PORT_PLC_RUNTIME_1 = 851
    PORT_PLC_RUNTIME_2 = 852
    PORT_NC = 500
    PORT_IO = 301

    def __init__(self):
        super().__init__()
        if not PYADS_AVAILABLE:
            raise ImportError(
                "pyads library not installed. Install with: pip install pyads"
            )
        self._plc: Optional[Connection] = None
        self._ams_net_id: Optional[str] = None
        self._ams_port: int = self.PORT_PLC_RUNTIME_1
        self._ip: Optional[str] = None

    @property
    def vendor(self) -> str:
        return "Beckhoff"

    def connect(
        self,
        ams_net_id: str,
        ip: Optional[str] = None,
        port: int = PORT_PLC_RUNTIME_1
    ) -> bool:
        """
        Connect to Beckhoff PLC via ADS.

        Args:
            ams_net_id: AMS Net ID (e.g., "192.168.1.10.1.1")
            ip: Optional IP address (uses route if not specified)
            port: ADS port (default 851 for PLC Runtime 1)
        """
        self._ams_net_id = ams_net_id
        self._ams_port = port
        self._ip = ip

        try:
            # Add route if IP specified
            if ip:
                pyads.add_route(ams_net_id, ip)

            self._plc = pyads.Connection(ams_net_id, port)
            self._plc.open()
            self._connected = True

            # Read device info
            self._device_info = self._read_device_info()

            return True
        except Exception as e:
            self._last_error = f"Connection failed: {e}"
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._plc:
            try:
                self._plc.close()
            except:
                pass
            self._plc = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device information via ADS."""
        try:
            if self._plc:
                info = self._plc.read_device_info()
                return DeviceInfo(
                    vendor="Beckhoff",
                    model=info.name,
                    firmware_version=f"{info.version.version}.{info.version.revision}.{info.version.build}",
                    serial_number="",
                    ip_address=self._ip or "",
                )
        except Exception:
            pass

        return DeviceInfo(
            vendor="Beckhoff",
            model="TwinCAT",
            firmware_version="",
            serial_number="",
            ip_address=self._ip or "",
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
        Read memory by index group/offset.

        For TwinCAT, use index groups:
        - 0x4020: %M area (markers)
        - 0x4021: %I area (inputs)
        - 0x4022: %Q area (outputs)
        """
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        index_groups = {
            MemoryArea.MEMORY: 0x4020,
            MemoryArea.INPUT: 0x4021,
            MemoryArea.OUTPUT: 0x4022,
        }

        ig = index_groups.get(area)
        if ig is None:
            raise ValueError(f"Unsupported memory area: {area}")

        return self._plc.read(ig, start, pyads.PLCTYPE_ARR_BYTE(length))

    def write_memory(self, area: MemoryArea, start: int, data: bytes) -> bool:
        """Write memory by index group/offset."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        index_groups = {
            MemoryArea.MEMORY: 0x4020,
            MemoryArea.INPUT: 0x4021,
            MemoryArea.OUTPUT: 0x4022,
        }

        ig = index_groups.get(area)
        if ig is None:
            raise ValueError(f"Unsupported memory area: {area}")

        try:
            self._plc.write(ig, start, data, pyads.PLCTYPE_ARR_BYTE(len(data)))
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tag(self, tag_name: str) -> TagValue:
        """Read variable by symbolic name."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        try:
            symbol = self._plc.get_symbol(tag_name)
            value = symbol.read()

            return TagValue(
                name=tag_name,
                value=value,
                data_type=str(symbol.plc_type),
                address=tag_name,
            )
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write variable by symbolic name."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        try:
            symbol = self._plc.get_symbol(tag_name)
            symbol.write(value)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_by_name(self, name: str, plc_type: Any) -> Any:
        """Read by name with explicit type."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        return self._plc.read_by_name(name, plc_type)

    def write_by_name(self, name: str, value: Any, plc_type: Any) -> None:
        """Write by name with explicit type."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        self._plc.write_by_name(name, value, plc_type)

    def get_symbol_info(self, name: str) -> Dict[str, Any]:
        """Get symbol information."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        symbol = self._plc.get_symbol(name)
        return {
            "name": symbol.name,
            "index_group": symbol.index_group,
            "index_offset": symbol.index_offset,
            "plc_type": str(symbol.plc_type),
            "symbol_type": symbol.symbol_type,
            "comment": symbol.comment,
        }

    def list_symbols(self) -> List[Dict[str, Any]]:
        """List all symbols in PLC."""
        if not self._plc or not self._connected:
            raise ConnectionError("Not connected")

        symbols = []
        for symbol in self._plc.get_all_symbols():
            symbols.append({
                "name": symbol.name,
                "plc_type": str(symbol.plc_type),
                "symbol_type": symbol.symbol_type,
            })
        return symbols

    def authenticate(self, password: str) -> bool:
        """Authenticate (not typically required for ADS)."""
        return True

    def list_blocks(self, block_type: Optional[BlockType] = None) -> List[BlockInfo]:
        """List program blocks."""
        # Could list POUs from symbol table
        return []

    def upload_block(self, block_type: BlockType, number: int) -> bytes:
        """Upload block."""
        return b''

    def download_block(self, block_type: BlockType, number: int, data: bytes) -> bool:
        """Download block."""
        return False

    def upload_program(self) -> PLCProgram:
        """Upload program."""
        return PLCProgram(vendor="Beckhoff", model="TwinCAT", blocks=[])

    def download_program(self, program: PLCProgram) -> bool:
        """Download program."""
        return False

    def get_mode(self) -> PLCMode:
        """Get PLC state."""
        if not self._plc or not self._connected:
            return PLCMode.UNKNOWN

        try:
            state = self._plc.read_state()
            state_map = {
                pyads.ADSSTATE_INVALID: PLCMode.UNKNOWN,
                pyads.ADSSTATE_IDLE: PLCMode.STOP,
                pyads.ADSSTATE_RESET: PLCMode.STOP,
                pyads.ADSSTATE_INIT: PLCMode.STOP,
                pyads.ADSSTATE_START: PLCMode.RUN,
                pyads.ADSSTATE_RUN: PLCMode.RUN,
                pyads.ADSSTATE_STOP: PLCMode.STOP,
                pyads.ADSSTATE_CONFIG: PLCMode.PROGRAM,
                pyads.ADSSTATE_ERROR: PLCMode.FAULT,
            }
            return state_map.get(state[0], PLCMode.UNKNOWN)
        except Exception:
            return PLCMode.UNKNOWN

    def set_mode(self, mode: PLCMode) -> bool:
        """Set PLC state."""
        if not self._plc or not self._connected:
            return False

        try:
            if mode == PLCMode.RUN:
                self._plc.write_control(pyads.ADSSTATE_RUN, 0, 0)
            elif mode == PLCMode.STOP:
                self._plc.write_control(pyads.ADSSTATE_STOP, 0, 0)
            return True
        except Exception as e:
            self._last_error = str(e)
            return False
