"""Unit tests for PLC drivers."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import asdict

from plcforge.drivers.base import (
    MemoryArea,
    PLCMode,
    AccessLevel,
    BlockType,
    CodeLanguage,
    DeviceInfo,
    ProtectionStatus,
)


class TestSiemensDriver:
    """Tests for Siemens S7 driver."""

    @pytest.fixture
    def siemens_driver(self, mock_snap7_client):
        """Create Siemens driver with mocked snap7."""
        with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
            mock_snap7.client.Client.return_value = mock_snap7_client
            mock_snap7.util.get_int.return_value = 100
            mock_snap7.util.set_int.return_value = None

            from plcforge.drivers.siemens.s7comm import SiemensS7Driver
            driver = SiemensS7Driver(
                ip="192.168.1.10",
                rack=0,
                slot=1,
            )
            driver._client = mock_snap7_client
            driver._connected = True
            return driver

    def test_connect(self, mock_snap7_client):
        """Test successful connection."""
        with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
            mock_snap7.client.Client.return_value = mock_snap7_client

            from plcforge.drivers.siemens.s7comm import SiemensS7Driver
            driver = SiemensS7Driver(ip="192.168.1.10", rack=0, slot=1)

            result = driver.connect()

            assert result is True
            mock_snap7_client.connect.assert_called_once()

    def test_disconnect(self, siemens_driver, mock_snap7_client):
        """Test disconnection."""
        siemens_driver.disconnect()

        mock_snap7_client.disconnect.assert_called_once()

    def test_get_device_info(self, siemens_driver):
        """Test getting device information."""
        info = siemens_driver.get_device_info()

        assert info is not None
        assert info.vendor == "Siemens"
        assert "CPU" in info.model or info.model is not None

    def test_read_memory_db(self, siemens_driver, mock_snap7_client):
        """Test reading from data block."""
        mock_snap7_client.db_read.return_value = bytearray([0x00, 0x64])

        result = siemens_driver.read_memory(MemoryArea.DATA_BLOCK, 0, 2)

        assert result is not None
        assert len(result) == 2

    def test_write_memory_db(self, siemens_driver, mock_snap7_client):
        """Test writing to data block."""
        result = siemens_driver.write_memory(
            MemoryArea.DATA_BLOCK,
            0,
            bytes([0x00, 0x64])
        )

        assert result is True

    def test_read_tag(self, siemens_driver, mock_snap7_client):
        """Test reading a tag by address."""
        mock_snap7_client.db_read.return_value = bytearray([0x00, 0x64])

        with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
            mock_snap7.util.get_int.return_value = 100
            result = siemens_driver.read_tag("DB1.DBW0")

        assert result is not None

    def test_get_mode(self, siemens_driver, mock_snap7_client):
        """Test getting PLC mode."""
        mock_snap7_client.get_cpu_state.return_value = "S7CpuStatusRun"

        mode = siemens_driver.get_mode()

        assert mode in [PLCMode.RUN, PLCMode.STOP, PLCMode.UNKNOWN]

    def test_address_parsing(self):
        """Test S7 address parsing."""
        from plcforge.drivers.siemens.s7comm import SiemensS7Driver

        # Test DB address parsing
        db, offset, bit = SiemensS7Driver._parse_address("DB1.DBW0")
        assert db == 1
        assert offset == 0

        # Test MW address
        db, offset, bit = SiemensS7Driver._parse_address("MW100")
        assert offset == 100


class TestAllenBradleyDriver:
    """Tests for Allen-Bradley CIP driver."""

    @pytest.fixture
    def ab_driver(self, mock_pycomm3_plc):
        """Create Allen-Bradley driver with mocked pycomm3."""
        with patch("plcforge.drivers.allen_bradley.cip_driver.LogixDriver") as mock_logix:
            mock_logix.return_value = mock_pycomm3_plc

            from plcforge.drivers.allen_bradley.cip_driver import AllenBradleyDriver
            driver = AllenBradleyDriver(ip="192.168.1.20", slot=0)
            driver._plc = mock_pycomm3_plc
            driver._connected = True
            return driver

    def test_connect(self, mock_pycomm3_plc):
        """Test successful connection."""
        with patch("plcforge.drivers.allen_bradley.cip_driver.LogixDriver") as mock_logix:
            mock_logix.return_value = mock_pycomm3_plc

            from plcforge.drivers.allen_bradley.cip_driver import AllenBradleyDriver
            driver = AllenBradleyDriver(ip="192.168.1.20", slot=0)

            result = driver.connect()

            assert result is True

    def test_read_tag(self, ab_driver, mock_pycomm3_plc):
        """Test reading a tag."""
        mock_pycomm3_plc.read.return_value = MagicMock(value=100, error=None)

        result = ab_driver.read_tag("Motor_Speed")

        assert result is not None
        assert result.value == 100

    def test_write_tag(self, ab_driver, mock_pycomm3_plc):
        """Test writing a tag."""
        mock_pycomm3_plc.write.return_value = MagicMock(error=None)

        result = ab_driver.write_tag("Motor_Speed", 1500)

        assert result is True
        mock_pycomm3_plc.write.assert_called()

    def test_get_device_info(self, ab_driver, mock_pycomm3_plc):
        """Test getting device information."""
        info = ab_driver.get_device_info()

        assert info is not None
        assert info.vendor == "Allen-Bradley"


class TestDeltaDriver:
    """Tests for Delta Modbus driver."""

    @pytest.fixture
    def delta_driver(self, mock_modbus_client):
        """Create Delta driver with mocked pymodbus."""
        with patch("plcforge.drivers.delta.modbus_driver.ModbusTcpClient") as mock_modbus:
            mock_modbus.return_value = mock_modbus_client

            from plcforge.drivers.delta.modbus_driver import DeltaDVPDriver
            driver = DeltaDVPDriver(ip="192.168.1.30", port=502)
            driver._client = mock_modbus_client
            driver._connected = True
            return driver

    def test_connect(self, mock_modbus_client):
        """Test successful connection."""
        with patch("plcforge.drivers.delta.modbus_driver.ModbusTcpClient") as mock_modbus:
            mock_modbus.return_value = mock_modbus_client

            from plcforge.drivers.delta.modbus_driver import DeltaDVPDriver
            driver = DeltaDVPDriver(ip="192.168.1.30", port=502)

            result = driver.connect()

            assert result is True

    def test_read_holding_register(self, delta_driver, mock_modbus_client):
        """Test reading holding register."""
        mock_modbus_client.read_holding_registers.return_value = MagicMock(
            registers=[100], isError=lambda: False
        )

        result = delta_driver.read_tag("D100")

        assert result is not None

    def test_write_holding_register(self, delta_driver, mock_modbus_client):
        """Test writing holding register."""
        mock_modbus_client.write_register.return_value = MagicMock(
            isError=lambda: False
        )

        result = delta_driver.write_tag("D100", 200)

        assert result is True


class TestOmronDriver:
    """Tests for Omron FINS driver."""

    @pytest.fixture
    def omron_driver(self, mock_fins_client):
        """Create Omron driver with mocked FINS client."""
        with patch("plcforge.drivers.omron.fins_driver.FinsClient") as mock_fins:
            mock_fins.return_value = mock_fins_client

            from plcforge.drivers.omron.fins_driver import OmronFINSDriver
            driver = OmronFINSDriver(ip="192.168.1.40")
            driver._client = mock_fins_client
            driver._connected = True
            return driver

    def test_connect(self, mock_fins_client):
        """Test successful connection."""
        with patch("plcforge.drivers.omron.fins_driver.FinsClient") as mock_fins:
            mock_fins.return_value = mock_fins_client

            from plcforge.drivers.omron.fins_driver import OmronFINSDriver
            driver = OmronFINSDriver(ip="192.168.1.40")

            result = driver.connect()

            assert result is True

    def test_read_dm_area(self, omron_driver, mock_fins_client):
        """Test reading DM area."""
        mock_fins_client.memory_area_read.return_value = [100]

        result = omron_driver.read_tag("D100")

        assert result is not None

    def test_write_dm_area(self, omron_driver, mock_fins_client):
        """Test writing DM area."""
        mock_fins_client.memory_area_write.return_value = True

        result = omron_driver.write_tag("D100", 200)

        assert result is True


class TestBaseDataclasses:
    """Tests for base dataclasses."""

    def test_device_info_creation(self, mock_device_info):
        """Test DeviceInfo dataclass creation."""
        assert mock_device_info.vendor == "Siemens"
        assert mock_device_info.model == "S7-1500"
        assert mock_device_info.rack == 0
        assert mock_device_info.slot == 1

    def test_protection_status_creation(self, mock_protection_status):
        """Test ProtectionStatus dataclass creation."""
        assert mock_protection_status.password_protected is True
        assert mock_protection_status.read_protected is False

    def test_block_info_creation(self, mock_block_info):
        """Test BlockInfo dataclass creation."""
        assert mock_block_info.block_type == BlockType.DATA_BLOCK
        assert mock_block_info.number == 1
        assert mock_block_info.name == "Motor_Data"

    def test_tag_value_creation(self, mock_tag_value):
        """Test TagValue dataclass creation."""
        assert mock_tag_value.name == "Motor_Speed"
        assert mock_tag_value.value == 1500
        assert mock_tag_value.data_type == "INT"


class TestEnums:
    """Tests for enum definitions."""

    def test_memory_area_values(self):
        """Test MemoryArea enum values."""
        assert MemoryArea.INPUT.value is not None
        assert MemoryArea.OUTPUT.value is not None
        assert MemoryArea.MARKER.value is not None
        assert MemoryArea.DATA_BLOCK.value is not None

    def test_plc_mode_values(self):
        """Test PLCMode enum values."""
        assert PLCMode.RUN.value is not None
        assert PLCMode.STOP.value is not None
        assert PLCMode.UNKNOWN.value is not None

    def test_block_type_values(self):
        """Test BlockType enum values."""
        assert BlockType.ORGANIZATION_BLOCK.value is not None
        assert BlockType.FUNCTION_BLOCK.value is not None
        assert BlockType.FUNCTION.value is not None
        assert BlockType.DATA_BLOCK.value is not None

    def test_code_language_values(self):
        """Test CodeLanguage enum values."""
        assert CodeLanguage.LADDER.value is not None
        assert CodeLanguage.STRUCTURED_TEXT.value is not None
        assert CodeLanguage.FUNCTION_BLOCK_DIAGRAM.value is not None
        assert CodeLanguage.INSTRUCTION_LIST.value is not None
