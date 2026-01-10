"""
PLCForge Protocol Abstraction Layer (PAL)

Provides unified API for all PLC vendors.
"""

from plcforge.pal.unified_api import (
    DeviceFactory,
    NetworkScanner,
    UnifiedPLC,
    Vendor,
    connect,
)

__all__ = [
    'DeviceFactory',
    'UnifiedPLC',
    'NetworkScanner',
    'Vendor',
    'connect',
]
