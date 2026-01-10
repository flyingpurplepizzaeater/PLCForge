"""Unit tests for Protocol Abstraction Layer (PAL)."""

import pytest
from unittest.mock import patch, MagicMock

from plcforge.pal.unified_api import (
    DeviceFactory,
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

    def test_vendor_string_values(self):
        """Test vendor string values."""
        assert Vendor.SIEMENS.value == "siemens"
        assert Vendor.ALLEN_BRADLEY.value == "allen_bradley"
        assert Vendor.DELTA.value == "delta"
        assert Vendor.OMRON.value == "omron"


class TestDeviceFactory:
    """Tests for DeviceFactory."""

    def test_factory_exists(self):
        """Test DeviceFactory class exists."""
        assert DeviceFactory is not None

    def test_factory_has_create_method(self):
        """Test DeviceFactory has create method."""
        assert hasattr(DeviceFactory, 'create')
        assert callable(DeviceFactory.create)


class TestPALImports:
    """Tests for PAL module imports."""

    def test_import_pal_module(self):
        """Test PAL module can be imported."""
        from plcforge import pal
        assert pal is not None

    def test_import_unified_api(self):
        """Test unified_api module can be imported."""
        from plcforge.pal import unified_api
        assert unified_api is not None

    def test_import_connect_function(self):
        """Test connect function can be imported."""
        from plcforge.pal.unified_api import connect
        assert connect is not None
        assert callable(connect)


class TestConnectFunction:
    """Tests for connect convenience function."""

    def test_connect_function_exists(self):
        """Test connect function is exported."""
        from plcforge import connect
        assert connect is not None
        assert callable(connect)
