"""
Vulnerability Exploits for Password Recovery

Contains vendor-specific exploits for password bypass/recovery.
"""

from abc import ABC, abstractmethod
from typing import Any


class VulnerabilityExploit(ABC):
    """Base class for vulnerability exploits"""

    name: str = "Unknown Exploit"
    description: str = ""
    affected_vendors: list[str] = []
    affected_models: list[str] = []
    affected_firmware: list[str] = []
    cve: str | None = None

    @abstractmethod
    def check_applicable(self, target) -> bool:
        """Check if exploit is applicable to target"""
        pass

    @abstractmethod
    def execute(self, target) -> dict[str, Any]:
        """
        Execute the exploit.

        Returns dict with:
        - success: bool
        - password: Optional[str]
        - message: Optional[str]
        """
        pass


# Lazy imports to avoid circular dependencies
def _get_exploit_classes():
    from plcforge.recovery.vulnerabilities.siemens_s7_300 import S7_300_SDBExtract
    from plcforge.recovery.vulnerabilities.siemens_s7_400 import S7_400_SDBExtract
    from plcforge.recovery.vulnerabilities.siemens_s7_1200 import S7_1200_WeakHash

    return [
        S7_300_SDBExtract,
        S7_400_SDBExtract,
        S7_1200_WeakHash,
    ]


def get_exploits(vendor: str, model: str) -> list[VulnerabilityExploit]:
    """Get applicable exploits for a vendor/model combination"""
    applicable = []

    vendor_lower = vendor.lower()
    model_lower = model.lower()

    for exploit_class in _get_exploit_classes():
        # Check if vendor matches
        vendor_match = any(
            v.lower() in vendor_lower or vendor_lower in v.lower()
            for v in exploit_class.affected_vendors
        )

        # Check if model matches
        model_match = any(
            m.lower() in model_lower or model_lower in m.lower()
            for m in exploit_class.affected_models
        )

        if vendor_match and model_match:
            applicable.append(exploit_class())

    return applicable


def register_exploit(exploit_class: type[VulnerabilityExploit]):
    """Register a new exploit class - for plugin extensibility"""
    # Would need mutable registry for runtime extension
    pass


__all__ = [
    'VulnerabilityExploit',
    'get_exploits',
    'register_exploit',
]
