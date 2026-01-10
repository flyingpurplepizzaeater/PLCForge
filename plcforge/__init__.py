"""
PLCForge - Multi-Vendor PLC Programming Application

A comprehensive PLC programming tool supporting:
- Siemens S7-300/400/1200/1500
- Allen-Bradley CompactLogix/ControlLogix
- Delta DVP Series
- Omron CP/CJ/NX/NJ Series

Features:
- Multi-vendor PLC communication
- Project file management
- AI-assisted code generation
- Password recovery
- Security audit logging
"""

__version__ = "1.0.0"
__author__ = "PLCForge Team"

from plcforge.pal.unified_api import DeviceFactory, UnifiedPLC, connect

__all__ = [
    'connect',
    'DeviceFactory',
    'UnifiedPLC',
]
