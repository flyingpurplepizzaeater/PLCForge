"""
File Parsers for Password Extraction

Parse vendor-specific project files to extract password information.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PasswordFileParser(ABC):
    """Base class for file-based password extraction"""

    supported_extensions: list[str] = []
    vendor: str = "Unknown"

    @abstractmethod
    def extract_password(self, file_path: str, protection_type: str) -> dict[str, Any]:
        """
        Extract password or password hash from file.

        Args:
            file_path: Path to project file
            protection_type: Type of protection ("project", "cpu", "block")

        Returns:
            Dict with:
            - password: Optional[str] - cleartext password if recoverable
            - hash: Optional[bytes] - password hash if not directly recoverable
            - algorithm: Optional[str] - hash algorithm used
            - salt: Optional[bytes] - salt if applicable
            - protected: bool - whether file is protected
        """
        pass

    @abstractmethod
    def verify_password(
        self,
        file_path: str,
        password: str,
        protection_type: str
    ) -> bool:
        """Verify if a password is correct for the file"""
        pass


# Registry of parsers
_PARSERS: dict[str, type[PasswordFileParser]] = {}


def register_parser(parser_class: type[PasswordFileParser]):
    """Register a parser class"""
    for ext in parser_class.supported_extensions:
        _PARSERS[ext.lower()] = parser_class


def get_parser(vendor: str, file_path: str) -> PasswordFileParser | None:
    """
    Get appropriate parser for a file.

    Args:
        vendor: Vendor name (for disambiguation)
        file_path: Path to file

    Returns:
        Parser instance or None if no parser available
    """
    path = Path(file_path)
    ext = ''.join(path.suffixes).lower()

    # Try exact extension match
    if ext in _PARSERS:
        return _PARSERS[ext]()

    # Try just the last extension
    last_ext = path.suffix.lower()
    if last_ext in _PARSERS:
        return _PARSERS[last_ext]()

    # Try vendor-specific lookup
    vendor_lower = vendor.lower()
    for _registered_ext, parser_class in _PARSERS.items():
        if vendor_lower in parser_class.vendor.lower():
            if last_ext in parser_class.supported_extensions:
                return parser_class()

    return None


# Import and register parsers
try:
    from plcforge.recovery.file_parsers.tia_portal import TIAPortalPasswordParser
    register_parser(TIAPortalPasswordParser)
except ImportError:
    pass


__all__ = [
    'PasswordFileParser',
    'get_parser',
    'register_parser',
]
