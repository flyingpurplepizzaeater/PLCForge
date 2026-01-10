"""
Base PLC Driver Interface

Defines the abstract interface that all vendor-specific drivers must implement.
This enables the Protocol Abstraction Layer (PAL) to work uniformly across vendors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryArea(Enum):
    """Unified memory area types across all PLC vendors"""
    INPUT = "input"           # Digital inputs (X, I, CIO)
    OUTPUT = "output"         # Digital outputs (Y, Q, CIO)
    MEMORY = "memory"         # Internal memory/flags (M, HR, W)
    DATA = "data"             # Data registers (D, DB, DM)
    TIMER = "timer"           # Timer values
    COUNTER = "counter"       # Counter values
    SPECIAL = "special"       # Special registers (vendor-specific)


class PLCMode(Enum):
    """PLC operating modes"""
    RUN = "run"
    STOP = "stop"
    PROGRAM = "program"
    FAULT = "fault"
    UNKNOWN = "unknown"


class AccessLevel(Enum):
    """Access levels for PLC operations"""
    NONE = 0
    READ_ONLY = 1
    READ_WRITE = 2
    FULL = 3


class BlockType(Enum):
    """PLC program block types (IEC 61131-3 aligned)"""
    OB = "organization_block"      # Main program / cyclic tasks
    FB = "function_block"          # Function blocks with instance data
    FC = "function"                # Functions (no instance data)
    DB = "data_block"              # Data blocks
    UDT = "user_defined_type"      # User-defined data types
    AOI = "add_on_instruction"     # Allen-Bradley Add-On Instructions
    PROGRAM = "program"            # Program (Omron/Delta)
    TASK = "task"                  # Task configuration


class CodeLanguage(Enum):
    """PLC programming languages (IEC 61131-3)"""
    LADDER = "ladder"             # Ladder Diagram (LAD/LD)
    STRUCTURED_TEXT = "st"        # Structured Text (ST)
    FUNCTION_BLOCK = "fbd"        # Function Block Diagram (FBD)
    INSTRUCTION_LIST = "il"       # Instruction List (IL)
    SFC = "sfc"                   # Sequential Function Chart
    GRAPH = "graph"               # Siemens GRAPH


@dataclass
class DeviceInfo:
    """Information about a connected PLC device"""
    vendor: str
    model: str
    firmware: str
    serial: str
    name: str
    ip_address: str | None = None
    rack: int | None = None
    slot: int | None = None
    additional_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtectionStatus:
    """Protection/security status of the PLC"""
    cpu_protected: bool = False
    project_protected: bool = False
    block_protected: bool = False
    know_how_protected: bool = False
    access_level: AccessLevel = AccessLevel.FULL
    protection_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockInfo:
    """Information about a program block"""
    block_type: BlockType
    number: int
    name: str
    language: CodeLanguage
    size: int
    protected: bool = False
    timestamp: datetime | None = None
    author: str | None = None
    comment: str | None = None


@dataclass
class TagValue:
    """A tag/variable value from the PLC"""
    name: str
    value: Any
    data_type: str
    address: str | None = None
    timestamp: datetime | None = None
    quality: str = "good"


@dataclass
class PLCProgram:
    """Container for a complete PLC program"""
    vendor: str
    model: str
    blocks: list['Block'] = field(default_factory=list)
    tags: list[TagValue] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def save(self, path: str) -> None:
        """Save program to file"""
        # Implementation in subclasses or utility module
        raise NotImplementedError

    @classmethod
    def load(cls, path: str) -> 'PLCProgram':
        """Load program from file"""
        raise NotImplementedError


@dataclass
class Block:
    """A program block with code content"""
    info: BlockInfo
    source_code: str | None = None      # Human-readable source
    compiled_code: bytes | None = None  # Compiled/binary form
    interface: dict[str, Any] = field(default_factory=dict)  # I/O interface


class PLCDevice(ABC):
    """
    Abstract base class for all PLC drivers.

    Each vendor-specific driver (Siemens, Allen-Bradley, Delta, Omron)
    must implement this interface to enable unified access through the PAL.
    """

    def __init__(self):
        self._connected = False
        self._device_info: DeviceInfo | None = None
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        """Get the last error message"""
        return self._last_error

    # ===================
    # Connection Methods
    # ===================

    @abstractmethod
    def connect(self, ip: str, **kwargs) -> bool:
        """
        Connect to the PLC.

        Args:
            ip: IP address of the PLC
            **kwargs: Vendor-specific parameters (rack, slot, port, etc.)

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the PLC"""
        pass

    def is_connected(self) -> bool:
        """Check if connected to PLC"""
        return self._connected

    # ===================
    # Device Information
    # ===================

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """
        Get information about the connected PLC.

        Returns:
            DeviceInfo object with vendor, model, firmware, etc.
        """
        pass

    @abstractmethod
    def get_protection_status(self) -> ProtectionStatus:
        """
        Get the protection/security status of the PLC.

        Returns:
            ProtectionStatus indicating what protections are enabled
        """
        pass

    # ===================
    # Memory Operations
    # ===================

    @abstractmethod
    def read_memory(self, area: MemoryArea, address: int, count: int) -> bytes:
        """
        Read raw bytes from a memory area.

        Args:
            area: Memory area type (INPUT, OUTPUT, DATA, etc.)
            address: Starting address
            count: Number of bytes to read

        Returns:
            Raw bytes from PLC memory
        """
        pass

    @abstractmethod
    def write_memory(self, area: MemoryArea, address: int, data: bytes) -> bool:
        """
        Write raw bytes to a memory area.

        Args:
            area: Memory area type
            address: Starting address
            data: Bytes to write

        Returns:
            True if write successful
        """
        pass

    @abstractmethod
    def read_tag(self, tag_name: str) -> TagValue:
        """
        Read a named tag/variable.

        Args:
            tag_name: Name of the tag (may include path like "DB1.Temperature")

        Returns:
            TagValue with current value and metadata
        """
        pass

    @abstractmethod
    def write_tag(self, tag_name: str, value: Any) -> bool:
        """
        Write to a named tag/variable.

        Args:
            tag_name: Name of the tag
            value: Value to write (will be converted to appropriate type)

        Returns:
            True if write successful
        """
        pass

    def read_tags(self, tag_names: list[str]) -> list[TagValue]:
        """
        Read multiple tags at once (default: sequential reads).

        Override in driver for optimized batch reads.
        """
        return [self.read_tag(name) for name in tag_names]

    def write_tags(self, tags: dict[str, Any]) -> bool:
        """
        Write multiple tags at once (default: sequential writes).

        Override in driver for optimized batch writes.
        """
        return all(self.write_tag(name, value) for name, value in tags.items())

    # ===================
    # Program Operations
    # ===================

    @abstractmethod
    def upload_program(self) -> PLCProgram:
        """
        Upload the complete program from the PLC.

        Returns:
            PLCProgram containing all blocks and configuration
        """
        pass

    @abstractmethod
    def download_program(self, program: PLCProgram) -> bool:
        """
        Download a program to the PLC.

        Args:
            program: PLCProgram to download

        Returns:
            True if download successful
        """
        pass

    @abstractmethod
    def get_block_list(self) -> list[BlockInfo]:
        """
        Get list of all program blocks in the PLC.

        Returns:
            List of BlockInfo objects
        """
        pass

    @abstractmethod
    def get_block(self, block_type: BlockType, number: int) -> Block:
        """
        Get a specific program block.

        Args:
            block_type: Type of block (OB, FB, FC, DB)
            number: Block number

        Returns:
            Block with source code and metadata
        """
        pass

    # ===================
    # PLC Control
    # ===================

    @abstractmethod
    def start(self) -> bool:
        """
        Start the PLC (set to RUN mode).

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the PLC (set to STOP/PROGRAM mode).

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_mode(self) -> PLCMode:
        """
        Get current PLC operating mode.

        Returns:
            PLCMode enum value
        """
        pass

    # ===================
    # Authentication
    # ===================

    @abstractmethod
    def authenticate(self, password: str) -> bool:
        """
        Authenticate with PLC using password.

        Args:
            password: Password string

        Returns:
            True if authentication successful
        """
        pass

    def clear_authentication(self) -> bool:
        """
        Clear current authentication/session.

        Returns:
            True if successful
        """
        return True  # Default: no-op

    @abstractmethod
    def get_access_level(self) -> AccessLevel:
        """
        Get current access level after authentication.

        Returns:
            AccessLevel enum value
        """
        pass

    # ===================
    # Diagnostic Methods
    # ===================

    def get_diagnostics(self) -> dict[str, Any]:
        """
        Get diagnostic information from PLC.

        Override in driver for vendor-specific diagnostics.
        """
        return {}

    def get_cpu_state(self) -> dict[str, Any]:
        """
        Get CPU state information.

        Override in driver for vendor-specific state info.
        """
        return {"mode": self.get_mode().value}


class ProjectFileParser(ABC):
    """
    Abstract base class for project file parsers.

    Each vendor has different project file formats that need
    specialized parsers for offline analysis.
    """

    @abstractmethod
    def parse(self, file_path: str) -> PLCProgram:
        """
        Parse a project file and extract program content.

        Args:
            file_path: Path to project file

        Returns:
            PLCProgram extracted from file
        """
        pass

    @abstractmethod
    def get_protection_info(self, file_path: str) -> dict[str, Any]:
        """
        Extract password/protection information from project file.

        Args:
            file_path: Path to project file

        Returns:
            Dictionary with protection details (hashes, flags, etc.)
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of extensions like ['.ap16', '.ap17']
        """
        pass
