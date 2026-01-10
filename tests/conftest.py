"""Pytest configuration and fixtures for PLCForge tests."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional

from plcforge.drivers.base import (
    PLCDevice,
    DeviceInfo,
    ProtectionStatus,
    BlockInfo,
    TagValue,
    PLCProgram,
    MemoryArea,
    PLCMode,
    AccessLevel,
    BlockType,
    CodeLanguage,
)


@pytest.fixture
def mock_device_info():
    """Create a mock DeviceInfo object."""
    return DeviceInfo(
        vendor="Siemens",
        model="S7-1500",
        firmware_version="V2.9.4",
        serial_number="S C-XXXX-XXXX-XXXX",
        ip_address="192.168.1.10",
        mac_address="00:1A:2B:3C:4D:5E",
        rack=0,
        slot=1,
        cpu_type="CPU 1516-3 PN/DP",
        memory_size=4194304,
    )


@pytest.fixture
def mock_protection_status():
    """Create a mock ProtectionStatus object."""
    return ProtectionStatus(
        protection_level=1,
        password_protected=True,
        read_protected=False,
        write_protected=True,
        copy_protected=False,
    )


@pytest.fixture
def mock_block_info():
    """Create a mock BlockInfo object."""
    return BlockInfo(
        block_type=BlockType.DATA_BLOCK,
        number=1,
        name="Motor_Data",
        language=CodeLanguage.STRUCTURED_TEXT,
        size=256,
        load_memory_size=512,
        work_memory_size=256,
        author="Engineer",
        family="Motors",
        version="1.0",
    )


@pytest.fixture
def mock_tag_value():
    """Create a mock TagValue object."""
    return TagValue(
        name="Motor_Speed",
        value=1500,
        data_type="INT",
        address="DB1.DBW0",
        quality="Good",
        timestamp=None,
    )


@pytest.fixture
def mock_snap7_client():
    """Create a mock snap7 client."""
    client = MagicMock()
    client.connect.return_value = None
    client.disconnect.return_value = None
    client.get_connected.return_value = True
    client.get_cpu_info.return_value = MagicMock(
        ModuleTypeName=b"CPU 1516-3 PN/DP",
        SerialNumber=b"S C-XXXX-XXXX-XXXX",
        ASName=b"S7-1500",
        ModuleName=b"PLC_1",
    )
    client.db_read.return_value = bytearray([0x00, 0x64])  # 100 as INT
    client.db_write.return_value = None
    client.get_order_code.return_value = MagicMock(
        OrderCode=b"6ES7 516-3AN02-0AB0"
    )
    return client


@pytest.fixture
def mock_pycomm3_plc():
    """Create a mock pycomm3 LogixDriver."""
    plc = MagicMock()
    plc.open.return_value = True
    plc.close.return_value = None
    plc.connected = True
    plc.read.return_value = MagicMock(value=100, error=None)
    plc.write.return_value = MagicMock(error=None)
    plc.get_plc_info.return_value = {
        "vendor": "Rockwell Automation",
        "product_type": "Programmable Logic Controller",
        "product_name": "1769-L33ER CompactLogix",
        "serial_number": "12345678",
        "revision": "32.11",
    }
    return plc


@pytest.fixture
def mock_modbus_client():
    """Create a mock pymodbus client."""
    client = MagicMock()
    client.connect.return_value = True
    client.close.return_value = None
    client.connected = True
    client.read_holding_registers.return_value = MagicMock(
        registers=[100], isError=lambda: False
    )
    client.write_register.return_value = MagicMock(isError=lambda: False)
    return client


@pytest.fixture
def mock_fins_client():
    """Create a mock FINS client."""
    client = MagicMock()
    client.connect.return_value = True
    client.close.return_value = None
    client.memory_area_read.return_value = [100]
    client.memory_area_write.return_value = True
    client.controller_data_read.return_value = {
        "model": "NJ501-1500",
        "version": "1.40",
    }
    return client


@pytest.fixture
def sample_tia_project_xml():
    """Sample TIA Portal project XML structure."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="V17">
    <Project Name="TestProject">
      <Device Name="PLC_1" TypeIdentifier="OrderNumber:6ES7 516-3AN02-0AB0/V2.9">
        <DeviceItem Name="CPU 1516-3 PN/DP">
          <AttributeList>
            <Password>encrypted_password_data</Password>
          </AttributeList>
        </DeviceItem>
      </Device>
    </Project>
  </Engineering>
</Document>"""


@pytest.fixture
def temp_project_file(tmp_path, sample_tia_project_xml):
    """Create a temporary TIA Portal project file."""
    import zipfile

    project_path = tmp_path / "test_project.ap17"

    with zipfile.ZipFile(project_path, 'w') as zf:
        zf.writestr("project.xml", sample_tia_project_xml)

    return project_path


class MockPLCDevice(PLCDevice):
    """Mock PLC device for testing."""

    def __init__(self, ip: str = "192.168.1.10"):
        self._ip = ip
        self._connected = False
        self._last_error: Optional[str] = None

    @property
    def vendor(self) -> str:
        return "Mock"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            vendor="Mock",
            model="MockPLC",
            firmware_version="1.0.0",
            serial_number="MOCK-001",
            ip_address=self._ip,
        )

    def get_protection_status(self) -> ProtectionStatus:
        return ProtectionStatus(
            protection_level=0,
            password_protected=False,
        )

    def authenticate(self, password: str) -> bool:
        return password == "correct_password"

    def read_memory(self, area: MemoryArea, start: int, length: int) -> bytes:
        return bytes(length)

    def write_memory(self, area: MemoryArea, start: int, data: bytes) -> bool:
        return True

    def read_tag(self, tag_name: str) -> TagValue:
        return TagValue(name=tag_name, value=100, data_type="INT")

    def write_tag(self, tag_name: str, value) -> bool:
        return True

    def list_blocks(self, block_type: Optional[BlockType] = None) -> list:
        return []

    def upload_block(self, block_type: BlockType, number: int) -> bytes:
        return b""

    def download_block(self, block_type: BlockType, number: int, data: bytes) -> bool:
        return True

    def upload_program(self) -> PLCProgram:
        return PLCProgram(vendor="Mock", model="MockPLC", blocks=[])

    def download_program(self, program: PLCProgram) -> bool:
        return True

    def get_mode(self) -> PLCMode:
        return PLCMode.RUN

    def set_mode(self, mode: PLCMode) -> bool:
        return True


@pytest.fixture
def mock_plc_device():
    """Create a mock PLC device."""
    return MockPLCDevice()
