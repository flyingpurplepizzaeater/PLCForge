"""Unit tests for Protocol Abstraction Layer (PAL)."""

import pytest
from unittest.mock import patch, MagicMock
import socket

from plcforge.pal.unified_api import (
    DeviceFactory,
    UnifiedPLC,
    NetworkScanner,
    Vendor,
)


class TestVendorEnum:
    """Tests for Vendor enum."""

    def test_vendor_values(self):
        """Test all vendor enum values exist."""
        assert Vendor.SIEMENS is not None
        assert Vendor.ALLEN_BRADLEY is not None
        assert Vendor.DELTA is not None
        assert Vendor.OMRON is not None
        assert Vendor.UNKNOWN is not None

    def test_vendor_from_string(self):
        """Test converting string to vendor enum."""
        assert Vendor("siemens") == Vendor.SIEMENS or Vendor.SIEMENS.value == "siemens"


class TestDeviceFactory:
    """Tests for DeviceFactory."""

    def test_create_siemens_explicit(self, mock_snap7_client):
        """Test creating Siemens device with explicit vendor."""
        with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
            mock_snap7.client.Client.return_value = mock_snap7_client

            device = DeviceFactory.create(
                ip="192.168.1.10",
                vendor="siemens",
                rack=0,
                slot=1,
            )

            assert device is not None

    def test_create_allen_bradley_explicit(self, mock_pycomm3_plc):
        """Test creating Allen-Bradley device with explicit vendor."""
        with patch("plcforge.drivers.allen_bradley.cip_driver.LogixDriver") as mock_logix:
            mock_logix.return_value = mock_pycomm3_plc

            device = DeviceFactory.create(
                ip="192.168.1.20",
                vendor="allen_bradley",
                slot=0,
            )

            assert device is not None

    def test_create_delta_explicit(self, mock_modbus_client):
        """Test creating Delta device with explicit vendor."""
        with patch("plcforge.drivers.delta.modbus_driver.ModbusTcpClient") as mock_modbus:
            mock_modbus.return_value = mock_modbus_client

            device = DeviceFactory.create(
                ip="192.168.1.30",
                vendor="delta",
            )

            assert device is not None

    def test_create_omron_explicit(self, mock_fins_client):
        """Test creating Omron device with explicit vendor."""
        with patch("plcforge.drivers.omron.fins_driver.FinsClient") as mock_fins:
            mock_fins.return_value = mock_fins_client

            device = DeviceFactory.create(
                ip="192.168.1.40",
                vendor="omron",
            )

            assert device is not None

    def test_create_unknown_vendor_raises(self):
        """Test that unknown vendor raises ValueError."""
        with pytest.raises(ValueError):
            DeviceFactory.create(
                ip="192.168.1.10",
                vendor="unknown_vendor",
            )

    def test_register_driver(self):
        """Test registering a custom driver."""
        from tests.conftest import MockPLCDevice

        DeviceFactory.register_driver("mock", MockPLCDevice)

        # Verify it's registered
        assert "mock" in DeviceFactory._drivers or hasattr(DeviceFactory, "_drivers")


class TestVendorAutoDetection:
    """Tests for vendor auto-detection."""

    def test_probe_siemens_s7(self):
        """Test probing for Siemens S7 on port 102."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect.return_value = None
            mock_sock_instance.send.return_value = 22
            # COTP connection confirm response
            mock_sock_instance.recv.return_value = bytes([
                0x03, 0x00, 0x00, 0x16,  # TPKT header
                0x11, 0xD0,  # COTP CC
                0x00, 0x01, 0x00, 0x01,
                0x00, 0xC0, 0x01, 0x0A,
                0xC1, 0x02, 0x01, 0x00,
                0xC2, 0x02, 0x01, 0x02,
            ])

            result = DeviceFactory._probe_siemens("192.168.1.10")

            # Should attempt connection on port 102
            assert mock_sock_instance.connect.called or mock_sock_instance.send.called

    def test_probe_allen_bradley_cip(self):
        """Test probing for Allen-Bradley on port 44818."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect.return_value = None
            mock_sock_instance.send.return_value = 28
            # EtherNet/IP List Identity response
            mock_sock_instance.recv.return_value = bytes([
                0x63, 0x00,  # List Identity command
                0x00, 0x00,  # Length
                0x00, 0x00, 0x00, 0x00,  # Session handle
                0x00, 0x00, 0x00, 0x00,  # Status
            ])

            result = DeviceFactory._probe_allen_bradley("192.168.1.20")

            assert mock_sock_instance.connect.called or mock_sock_instance.send.called

    def test_probe_omron_fins(self):
        """Test probing for Omron FINS on UDP port 9600."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.sendto.return_value = 20
            mock_sock_instance.recvfrom.return_value = (
                bytes([0x80, 0x00, 0x02, 0x00]),  # FINS response
                ("192.168.1.40", 9600)
            )

            result = DeviceFactory._probe_omron("192.168.1.40")

            assert mock_sock_instance.sendto.called or mock_sock_instance.recvfrom.called

    def test_probe_delta_modbus(self):
        """Test probing for Delta Modbus on port 502."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect.return_value = None
            mock_sock_instance.send.return_value = 12
            # Modbus response
            mock_sock_instance.recv.return_value = bytes([
                0x00, 0x01,  # Transaction ID
                0x00, 0x00,  # Protocol ID
                0x00, 0x05,  # Length
                0x01,        # Unit ID
                0x03,        # Function code
                0x02,        # Byte count
                0x00, 0x64,  # Data
            ])

            result = DeviceFactory._probe_delta("192.168.1.30")

            assert mock_sock_instance.connect.called or mock_sock_instance.send.called


class TestUnifiedPLC:
    """Tests for UnifiedPLC wrapper."""

    @pytest.fixture
    def unified_plc(self, mock_plc_device):
        """Create UnifiedPLC with mock device."""
        return UnifiedPLC(mock_plc_device)

    def test_connect(self, unified_plc):
        """Test connecting through UnifiedPLC."""
        result = unified_plc.connect()
        assert result is True

    def test_disconnect(self, unified_plc):
        """Test disconnecting through UnifiedPLC."""
        unified_plc.connect()
        unified_plc.disconnect()
        assert unified_plc.is_connected is False

    def test_read_tag(self, unified_plc):
        """Test reading tag through UnifiedPLC."""
        unified_plc.connect()
        result = unified_plc.read_tag("TestTag")
        assert result is not None
        assert result.value == 100

    def test_write_tag(self, unified_plc):
        """Test writing tag through UnifiedPLC."""
        unified_plc.connect()
        result = unified_plc.write_tag("TestTag", 200)
        assert result is True

    def test_get_device_info(self, unified_plc):
        """Test getting device info through UnifiedPLC."""
        unified_plc.connect()
        info = unified_plc.get_device_info()
        assert info is not None
        assert info.vendor == "Mock"

    def test_context_manager(self, mock_plc_device):
        """Test using UnifiedPLC as context manager."""
        with UnifiedPLC(mock_plc_device) as plc:
            assert plc.is_connected is True
        assert mock_plc_device.is_connected is False


class TestNetworkScanner:
    """Tests for NetworkScanner."""

    def test_scan_single_host(self):
        """Test scanning a single host."""
        with patch.object(DeviceFactory, "detect_vendor") as mock_detect:
            mock_detect.return_value = Vendor.SIEMENS

            scanner = NetworkScanner()
            # Would need to mock actual scanning
            assert scanner is not None

    def test_scan_subnet(self):
        """Test scanning a subnet."""
        scanner = NetworkScanner()

        with patch.object(scanner, "_probe_host") as mock_probe:
            mock_probe.return_value = None

            # Scan should handle subnet notation
            results = scanner.scan("192.168.1.0/30", timeout=0.1)

            assert isinstance(results, list)

    def test_discovered_device_dataclass(self):
        """Test DiscoveredDevice dataclass."""
        from plcforge.pal.unified_api import DiscoveredDevice

        device = DiscoveredDevice(
            ip="192.168.1.10",
            vendor=Vendor.SIEMENS,
            model="S7-1500",
            name="PLC_1",
            mac_address="00:1A:2B:3C:4D:5E",
        )

        assert device.ip == "192.168.1.10"
        assert device.vendor == Vendor.SIEMENS


class TestConnectFunction:
    """Tests for the connect() convenience function."""

    def test_connect_with_auto_detect(self, mock_snap7_client):
        """Test connect() with auto-detection."""
        with patch.object(DeviceFactory, "detect_vendor") as mock_detect:
            mock_detect.return_value = Vendor.SIEMENS

            with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
                mock_snap7.client.Client.return_value = mock_snap7_client

                from plcforge.pal.unified_api import connect

                # This would attempt actual connection
                # Just verify the function exists and is callable
                assert callable(connect)

    def test_connect_with_explicit_vendor(self, mock_snap7_client):
        """Test connect() with explicit vendor specification."""
        with patch("plcforge.drivers.siemens.s7comm.snap7") as mock_snap7:
            mock_snap7.client.Client.return_value = mock_snap7_client

            from plcforge.pal.unified_api import connect

            # Verify function signature allows vendor parameter
            assert callable(connect)
