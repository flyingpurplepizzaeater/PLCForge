"""
Integration tests for PAL tag monitoring feature.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock
from plcforge.drivers.base import TagValue, PLCDevice, DeviceInfo, PLCMode, ProtectionStatus, AccessLevel


class MockMonitorDevice(PLCDevice):
    """Mock PLC device for testing monitoring"""

    def __init__(self):
        super().__init__()
        self._tag_values = {
            "Tag1": 100,
            "Tag2": 200,
            "Tag3": 300,
        }
        self._read_count = 0

    def connect(self, ip: str, **kwargs) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            vendor="Mock",
            model="Test",
            firmware="1.0",
            serial="12345",
            name="MockPLC"
        )

    def get_protection_status(self) -> ProtectionStatus:
        return ProtectionStatus()

    def read_memory(self, area, address, count):
        return b'\x00' * count

    def write_memory(self, area, address, data):
        return True

    def read_tag(self, tag_name: str) -> TagValue:
        """Read tag and simulate value changes"""
        self._read_count += 1

        # Simulate value change every 3 reads
        if self._read_count % 3 == 0:
            self._tag_values[tag_name] = self._tag_values.get(tag_name, 0) + 10

        return TagValue(
            name=tag_name,
            value=self._tag_values.get(tag_name, 0),
            data_type="INT"
        )

    def write_tag(self, tag_name: str, value) -> bool:
        self._tag_values[tag_name] = value
        return True

    def upload_program(self):
        from plcforge.drivers.base import PLCProgram
        return PLCProgram(vendor="Mock", model="Test")

    def download_program(self, program):
        return True

    def get_block_list(self):
        return []

    def get_block(self, block_type, number):
        from plcforge.drivers.base import Block, BlockInfo, BlockType, CodeLanguage
        return Block(info=BlockInfo(
            block_type=BlockType.OB,
            number=1,
            name="Test",
            language=CodeLanguage.LADDER,
            size=100
        ))

    def start(self):
        return True

    def stop(self):
        return True

    def get_mode(self):
        return PLCMode.RUN

    def authenticate(self, password):
        return True

    def get_access_level(self):
        return AccessLevel.FULL


class TestTagMonitoring:
    """Test tag monitoring functionality"""

    def test_monitor_creates_thread(self):
        """Test that monitoring starts a background thread"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        plc = UnifiedPLC(mock_device)

        callback_data = []

        def callback(tag, value):
            callback_data.append((tag, value.value))

        # Start monitoring
        stop = plc.monitor(["Tag1"], callback, interval_ms=10)

        # Let it run briefly
        time.sleep(0.05)

        # Stop monitoring
        stop()

        # Verify callback was called
        assert len(callback_data) > 0

    def test_monitor_detects_value_changes(self):
        """Test that monitoring detects when values change"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        plc = UnifiedPLC(mock_device)

        callback_data = []
        change_detected = threading.Event()

        def callback(tag, value):
            callback_data.append((tag, value.value))
            # Detect if we got multiple different values
            if len(callback_data) > 1:
                values = [v for _, v in callback_data]
                if len(set(values)) > 1:  # Multiple unique values
                    change_detected.set()

        # Start monitoring
        stop = plc.monitor(["Tag1"], callback, interval_ms=10)

        # Wait for changes (mock device changes every 3 reads)
        change_detected.wait(timeout=1.0)

        # Stop monitoring
        stop()

        # Verify we detected changes
        assert change_detected.is_set(), "Should have detected value changes"

    def test_monitor_multiple_tags(self):
        """Test monitoring multiple tags simultaneously"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        plc = UnifiedPLC(mock_device)

        callback_data = {}

        def callback(tag, value):
            if tag not in callback_data:
                callback_data[tag] = []
            callback_data[tag].append(value.value)

        # Monitor multiple tags
        stop = plc.monitor(["Tag1", "Tag2", "Tag3"], callback, interval_ms=10)

        # Let it run
        time.sleep(0.1)

        # Stop monitoring
        stop()

        # Verify all tags were monitored
        assert "Tag1" in callback_data
        assert "Tag2" in callback_data
        assert "Tag3" in callback_data

    def test_monitor_handles_read_errors(self):
        """Test that monitoring continues even if individual reads fail"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        # Make read_tag raise exception for one tag
        original_read = mock_device.read_tag

        def failing_read(tag_name):
            if tag_name == "Tag2":
                raise Exception("Simulated read error")
            return original_read(tag_name)

        mock_device.read_tag = failing_read

        plc = UnifiedPLC(mock_device)

        callback_data = {}

        def callback(tag, value):
            if tag not in callback_data:
                callback_data[tag] = []
            callback_data[tag].append(value.value)

        # Monitor multiple tags including one that fails
        stop = plc.monitor(["Tag1", "Tag2", "Tag3"], callback, interval_ms=10)

        # Let it run
        time.sleep(0.1)

        # Stop monitoring
        stop()

        # Tag1 and Tag3 should have data, Tag2 should not
        assert "Tag1" in callback_data
        assert "Tag3" in callback_data
        # Tag2 may or may not be in data depending on error handling

    def test_monitor_stops_cleanly(self):
        """Test that monitoring stops when requested"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        plc = UnifiedPLC(mock_device)

        callback_count = [0]

        def callback(tag, value):
            callback_count[0] += 1

        # Start monitoring
        stop = plc.monitor(["Tag1"], callback, interval_ms=10)

        # Let it run and count callbacks
        time.sleep(0.05)
        count_before_stop = callback_count[0]

        # Stop monitoring
        stop()

        # Wait a bit more
        time.sleep(0.05)
        count_after_stop = callback_count[0]

        # Count should not increase significantly after stop
        # (allow for a few in-flight callbacks)
        assert count_after_stop - count_before_stop < 5

    def test_monitor_interval_setting(self):
        """Test that monitoring respects interval setting"""
        from plcforge.pal.unified_api import UnifiedPLC

        mock_device = MockMonitorDevice()
        mock_device.connect("192.168.1.1")

        plc = UnifiedPLC(mock_device)

        callback_times = []

        def callback(tag, value):
            callback_times.append(time.time())

        # Start monitoring with 100ms interval
        stop = plc.monitor(["Tag1"], callback, interval_ms=100)

        # Let it run for a few intervals
        time.sleep(0.5)

        # Stop monitoring
        stop()

        # Verify monitoring ran and captured multiple callbacks
        assert len(callback_times) >= 2, "Should have multiple callbacks"

        # Verify callbacks happened over time (not all at once)
        time_span = callback_times[-1] - callback_times[0]
        assert time_span > 0.1, "Callbacks should be spread over time"
