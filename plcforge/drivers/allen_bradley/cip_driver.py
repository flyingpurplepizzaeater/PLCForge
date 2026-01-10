"""
Allen-Bradley CIP/EtherNet-IP Driver

Supports CompactLogix and ControlLogix PLCs using
the pycomm3 library for CIP protocol communication.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from pycomm3 import LogixDriver, CIPDriver
    from pycomm3.exceptions import CommError, RequestError
    PYCOMM3_AVAILABLE = True
except ImportError:
    PYCOMM3_AVAILABLE = False

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


class AllenBradleyDriver(PLCDevice):
    """
    Allen-Bradley CompactLogix/ControlLogix driver.

    Uses pycomm3 for CIP/EtherNet-IP communication.

    Supported models:
    - CompactLogix 5370 series
    - CompactLogix 5380 series
    - CompactLogix 5480 series
    - ControlLogix 5570 series
    - ControlLogix 5580 series
    """

    def __init__(self):
        super().__init__()
        if not PYCOMM3_AVAILABLE:
            raise ImportError(
                "pycomm3 library not installed. Install with: pip install pycomm3"
            )

        self._plc: Optional[LogixDriver] = None
        self._ip: Optional[str] = None
        self._slot: int = 0

    def connect(self, ip: str, **kwargs) -> bool:
        """
        Connect to Allen-Bradley PLC.

        Args:
            ip: IP address (can include slot like "192.168.1.10/2")
            slot: Slot number (default 0)

        Returns:
            True if connected
        """
        self._ip = ip
        self._slot = kwargs.get('slot', 0)

        # Build path with slot if not in IP
        if '/' not in ip:
            path = f"{ip}/{self._slot}"
        else:
            path = ip

        try:
            self._plc = LogixDriver(path)
            self._plc.open()
            self._connected = True

            # Get device info
            self._device_info = self._read_device_info()

            return True
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from PLC"""
        if self._plc:
            try:
                self._plc.close()
            except Exception:
                pass
            self._plc = None
        self._connected = False

    def _read_device_info(self) -> DeviceInfo:
        """Read device information"""
        try:
            info = self._plc.get_plc_info()
            return DeviceInfo(
                vendor="Allen-Bradley",
                model=info.get('product_name', 'Unknown'),
                firmware=f"{info.get('major_revision', 0)}.{info.get('minor_revision', 0)}",
                serial=info.get('serial_number', 'Unknown'),
                name=info.get('name', 'Unknown'),
                ip_address=self._ip,
                slot=self._slot,
                additional_info={
                    'product_type': info.get('product_type'),
                    'product_code': info.get('product_code'),
                    'vendor_id': info.get('vendor_id'),
                    'device_type': info.get('device_type'),
                }
            )
        except Exception as e:
            return DeviceInfo(
                vendor="Allen-Bradley",
                model="Unknown Logix",
                firmware="Unknown",
                serial="Unknown",
                name="Unknown",
                ip_address=self._ip,
            )

    def get_device_info(self) -> DeviceInfo:
        """Get cached device info"""
        if not self._device_info:
            self._device_info = self._read_device_info()
        return self._device_info

    def get_protection_status(self) -> ProtectionStatus:
        """Get PLC protection status"""
        # Allen-Bradley protection is managed through Studio 5000
        # and enforced at runtime
        return ProtectionStatus(
            cpu_protected=False,  # Would need to query security settings
            project_protected=False,
            block_protected=False,
            access_level=AccessLevel.FULL,
        )

    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        """
        Read raw memory.

        Note: Logix PLCs use tag-based addressing, not memory areas.
        This method is provided for compatibility but has limited use.
        """
        # For compatibility, map to file access
        # N7:0 style for integer files
        if area == MemoryArea.DATA:
            tag = f"N7:{address}"
        elif area == MemoryArea.INPUT:
            tag = f"I:{address}"
        elif area == MemoryArea.OUTPUT:
            tag = f"O:{address}"
        else:
            raise ValueError("Logix PLCs use tag-based addressing. Use read_tag instead.")

        try:
            result = self._plc.read(tag)
            if result.error:
                raise Exception(result.error)
            # Convert to bytes
            import struct
            return struct.pack('>i', result.value)
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        """Write raw memory - limited support on Logix"""
        raise NotImplementedError(
            "Logix PLCs use tag-based addressing. Use write_tag instead."
        )

    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read a tag by name.

        Supports:
        - Simple tags: "MyTag"
        - Array elements: "MyArray[0]"
        - Structure members: "MyUDT.Member"
        - Program-scoped: "Program:MainProgram.LocalTag"
        """
        try:
            result = self._plc.read(tag_name)

            if result.error:
                raise Exception(f"Read error: {result.error}")

            return TagValue(
                name=tag_name,
                value=result.value,
                data_type=result.type or "Unknown",
                address=tag_name,
                timestamp=datetime.now(),
            )
        except Exception as e:
            self._last_error = str(e)
            raise

    def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write to a tag by name"""
        try:
            result = self._plc.write(tag_name, value)

            if result.error:
                self._last_error = str(result.error)
                return False

            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def read_tags(self, tag_names: List[str]) -> List[TagValue]:
        """Read multiple tags in one request (optimized)"""
        try:
            results = self._plc.read(*tag_names)

            tag_values = []
            # Handle single vs multiple results
            if not isinstance(results, list):
                results = [results]

            for i, result in enumerate(results):
                tag_values.append(TagValue(
                    name=tag_names[i] if i < len(tag_names) else f"Tag{i}",
                    value=result.value if not result.error else None,
                    data_type=result.type or "Unknown",
                    timestamp=datetime.now(),
                    quality="good" if not result.error else "bad",
                ))

            return tag_values
        except Exception as e:
            self._last_error = str(e)
            return [TagValue(name=n, value=None, data_type="Unknown", quality="bad")
                    for n in tag_names]

    def write_tags(self, tags: Dict[str, Any]) -> bool:
        """Write multiple tags in one request (optimized)"""
        try:
            # Build list of (tag, value) tuples
            writes = [(name, value) for name, value in tags.items()]
            results = self._plc.write(*writes)

            # Check all results
            if not isinstance(results, list):
                results = [results]

            return all(not r.error for r in results)
        except Exception as e:
            self._last_error = str(e)
            return False

    def get_tag_list(self) -> List[Dict[str, Any]]:
        """Get list of all tags in the PLC"""
        try:
            tags = self._plc.get_tag_list()
            return [
                {
                    'name': tag.get('tag_name'),
                    'type': tag.get('data_type'),
                    'dim': tag.get('dim', 0),
                    'value': tag.get('value'),
                }
                for tag in tags
            ]
        except Exception as e:
            self._last_error = str(e)
            return []

    def upload_program(self) -> PLCProgram:
        """
        Upload program from PLC.

        Note: Full program upload requires Studio 5000.
        This returns tag information and structure only.
        """
        program = PLCProgram(
            vendor="Allen-Bradley",
            model=self.get_device_info().model,
        )

        # Get all tags
        try:
            tags = self.get_tag_list()
            for tag in tags:
                program.tags.append(TagValue(
                    name=tag['name'],
                    value=tag.get('value'),
                    data_type=tag.get('type', 'Unknown'),
                ))
        except Exception:
            pass

        # Get program names
        try:
            programs = self._plc.get_program_tag_list()
            program.metadata['programs'] = list(programs.keys())
        except Exception:
            pass

        return program

    def download_program(self, program: PLCProgram) -> bool:
        """
        Download program to PLC.

        Note: Full program download requires Studio 5000.
        """
        self._last_error = "Full program download requires Studio 5000"
        return False

    def get_block_list(self) -> List[BlockInfo]:
        """
        Get list of program blocks.

        In Logix, these are Programs and Routines.
        """
        blocks = []

        try:
            # Get programs
            programs = self._plc.get_program_tag_list()

            for prog_name in programs.keys():
                blocks.append(BlockInfo(
                    block_type=BlockType.PROGRAM,
                    number=len(blocks),
                    name=prog_name,
                    language=CodeLanguage.LADDER,
                    size=0,
                ))
        except Exception as e:
            self._last_error = str(e)

        return blocks

    def get_block(self, block_type: BlockType, number: int) -> Block:
        """Get a specific block - limited support"""
        blocks = self.get_block_list()
        if number < len(blocks):
            return Block(info=blocks[number])
        raise ValueError(f"Block {number} not found")

    def start(self) -> bool:
        """
        Set PLC to Run mode.

        Note: Requires appropriate permissions.
        """
        try:
            # Use generic CIP message to set mode
            # This is controller-specific and may not work on all models
            self._last_error = "Remote mode change not supported via pycomm3"
            return False
        except Exception as e:
            self._last_error = str(e)
            return False

    def stop(self) -> bool:
        """Set PLC to Program mode"""
        self._last_error = "Remote mode change not supported via pycomm3"
        return False

    def get_mode(self) -> PLCMode:
        """Get current PLC mode"""
        try:
            info = self._plc.get_plc_info()
            # Mode is in the info but format varies
            mode_str = str(info.get('status', '')).upper()

            if 'RUN' in mode_str:
                return PLCMode.RUN
            elif 'PROGRAM' in mode_str or 'PROG' in mode_str:
                return PLCMode.PROGRAM
            elif 'FAULT' in mode_str:
                return PLCMode.FAULT
            else:
                return PLCMode.UNKNOWN
        except Exception:
            return PLCMode.UNKNOWN

    def authenticate(self, password: str) -> bool:
        """
        Authenticate with PLC.

        Allen-Bradley uses FactoryTalk security for authentication.
        """
        self._last_error = "FactoryTalk authentication not supported"
        return False

    def get_access_level(self) -> AccessLevel:
        """Get current access level"""
        return AccessLevel.FULL  # Assuming no restrictions without FT security

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information"""
        try:
            info = self._plc.get_plc_info()
            return {
                'plc_info': info,
                'connected': self._connected,
                'tag_count': len(self.get_tag_list()),
            }
        except Exception as e:
            return {'error': str(e)}
