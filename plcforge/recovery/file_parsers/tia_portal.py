"""
TIA Portal Project File Password Parser

Extracts password information from TIA Portal project files (.ap13-.ap20).
"""

import hashlib
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


class TIAPortalPasswordParser:
    """
    Parser for TIA Portal project file passwords.

    Supports extraction from:
    - Project protection
    - CPU protection
    - Know-how protection (block-level)
    """

    supported_extensions = [
        '.ap13', '.ap14', '.ap15', '.ap16', '.ap17', '.ap18', '.ap19', '.ap20',
        '.zap13', '.zap14', '.zap15', '.zap16', '.zap17', '.zap18', '.zap19', '.zap20',
    ]
    vendor = "Siemens"

    def extract_password(self, file_path: str, protection_type: str) -> dict[str, Any]:
        """
        Extract password information from TIA Portal project.

        TIA Portal uses different protection mechanisms:
        - Project protection: Prevents opening without password
        - CPU protection: Access levels for online PLC
        - Know-how protection: Individual block encryption
        """
        result = {
            'password': None,
            'hash': None,
            'algorithm': None,
            'salt': None,
            'protected': False,
            'details': {},
        }

        path = Path(file_path)
        if not path.exists():
            return result

        try:
            # Handle archived projects
            if path.suffix.lower().startswith('.zap'):
                file_path = self._extract_archived(file_path)
                if not file_path:
                    return result

            with zipfile.ZipFile(file_path, 'r') as zf:
                if protection_type == "project":
                    return self._extract_project_password(zf)
                elif protection_type == "cpu":
                    return self._extract_cpu_password(zf)
                elif protection_type == "block":
                    return self._extract_block_passwords(zf)
                else:
                    # Try all
                    proj_result = self._extract_project_password(zf)
                    if proj_result.get('protected'):
                        return proj_result
                    return result

        except zipfile.BadZipFile:
            result['details']['error'] = "Invalid or corrupted project file"
        except Exception as e:
            result['details']['error'] = str(e)

        return result

    def _extract_archived(self, file_path: str) -> str | None:
        """Extract .zap archive to temp location"""
        import gzip
        import tempfile

        try:
            with gzip.open(file_path, 'rb') as gz:
                with tempfile.NamedTemporaryFile(suffix='.ap', delete=False) as tmp:
                    tmp.write(gz.read())
                    return tmp.name
        except Exception:
            return None

    def _extract_project_password(self, zf: zipfile.ZipFile) -> dict[str, Any]:
        """Extract project-level password"""
        result = {
            'password': None,
            'hash': None,
            'algorithm': None,
            'salt': None,
            'protected': False,
            'details': {},
        }

        # Look for protection-related files
        for name in zf.namelist():
            name_lower = name.lower()

            # Check for protection configuration
            if 'protection' in name_lower or 'security' in name_lower:
                if name.endswith('.xml'):
                    try:
                        content = zf.read(name)
                        protection_info = self._parse_protection_xml(content)
                        if protection_info:
                            result.update(protection_info)
                    except Exception:
                        pass

            # Look for password in binary files
            if name.endswith('.plf') or name.endswith('.dat'):
                try:
                    content = zf.read(name)
                    hash_info = self._extract_hash_from_binary(content)
                    if hash_info:
                        result['hash'] = hash_info['hash']
                        result['algorithm'] = hash_info.get('algorithm')
                        result['salt'] = hash_info.get('salt')
                        result['protected'] = True
                except Exception:
                    pass

        return result

    def _extract_cpu_password(self, zf: zipfile.ZipFile) -> dict[str, Any]:
        """Extract CPU protection password settings"""
        result = {
            'password': None,
            'hash': None,
            'algorithm': None,
            'protected': False,
            'details': {'access_levels': []},
        }

        for name in zf.namelist():
            # Look for PLC configuration files
            if 'PLC_' in name or 'Device' in name:
                if name.endswith('.xml'):
                    try:
                        content = zf.read(name)
                        root = ET.fromstring(content)

                        # Look for protection settings
                        protection_elem = root.find('.//{*}Protection')
                        if protection_elem is not None:
                            result['protected'] = True

                            # Extract access level info
                            for level in protection_elem.findall('.//{*}AccessLevel'):
                                level_info = {
                                    'name': level.get('Name', 'Unknown'),
                                    'password_set': level.find('.//{*}Password') is not None
                                }
                                result['details']['access_levels'].append(level_info)

                    except Exception:
                        pass

        return result

    def _extract_block_passwords(self, zf: zipfile.ZipFile) -> dict[str, Any]:
        """Extract know-how protected block information"""
        result = {
            'password': None,
            'hash': None,
            'protected': False,
            'details': {'protected_blocks': []},
        }

        for name in zf.namelist():
            if 'ProgramBlocks' in name and name.endswith('.xml'):
                try:
                    content = zf.read(name)
                    root = ET.fromstring(content)

                    # Check for know-how protection
                    kh_elem = root.find('.//{*}KnowHowProtection')
                    if kh_elem is not None:
                        result['protected'] = True

                        # Get block name
                        block_name = root.find('.//{*}Name')
                        if block_name is not None:
                            result['details']['protected_blocks'].append({
                                'name': block_name.text,
                                'file': name,
                            })

                except Exception:
                    pass

        return result

    def _parse_protection_xml(self, content: bytes) -> dict[str, Any]:
        """Parse protection XML file"""
        result = {}

        try:
            root = ET.fromstring(content)

            # Look for password hash elements
            pwd_elem = root.find('.//{*}PasswordHash')
            if pwd_elem is not None and pwd_elem.text:
                result['hash'] = bytes.fromhex(pwd_elem.text)
                result['protected'] = True

            # Check algorithm
            algo_elem = root.find('.//{*}Algorithm')
            if algo_elem is not None:
                result['algorithm'] = algo_elem.text

            # Check salt
            salt_elem = root.find('.//{*}Salt')
            if salt_elem is not None and salt_elem.text:
                result['salt'] = bytes.fromhex(salt_elem.text)

        except ET.ParseError:
            pass

        return result

    def _extract_hash_from_binary(self, content: bytes) -> dict[str, Any] | None:
        """
        Extract password hash from binary file content.

        TIA Portal stores password hashes in various binary formats
        depending on version.
        """
        # Look for hash patterns in the binary data

        # V15+ uses 32-byte SHA256 hashes with 16-byte salt
        for i in range(len(content) - 48):
            potential_salt = content[i:i+16]
            potential_hash = content[i+16:i+48]

            if self._looks_like_hash(potential_hash):
                return {
                    'hash': potential_hash,
                    'salt': potential_salt,
                    'algorithm': 'SHA256_SALTED',
                    'offset': i,
                }

        # Older versions use 8-byte CRC-based hash
        for i in range(len(content) - 8):
            potential_hash = content[i:i+8]

            if self._looks_like_short_hash(potential_hash):
                return {
                    'hash': potential_hash,
                    'salt': None,
                    'algorithm': 'CRC_MODIFIED',
                    'offset': i,
                }

        return None

    def _looks_like_hash(self, data: bytes) -> bool:
        """Heuristic check if bytes look like a hash"""
        if len(data) < 16:
            return False

        # Check for reasonable entropy
        unique_bytes = len(set(data))
        if unique_bytes < 8:
            return False

        # Check no long runs of same byte
        max_run = 1
        current_run = 1
        for i in range(1, len(data)):
            if data[i] == data[i-1]:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1

        return max_run <= 4

    def _looks_like_short_hash(self, data: bytes) -> bool:
        """Check if 8 bytes look like a hash"""
        if data == b'\x00' * 8 or data == b'\xff' * 8:
            return False
        return len(set(data)) >= 4

    def verify_password(
        self,
        file_path: str,
        password: str,
        protection_type: str
    ) -> bool:
        """Verify if password is correct"""
        # Extract hash info
        info = self.extract_password(file_path, protection_type)

        if not info.get('hash'):
            return False

        # Compute hash with same algorithm
        algorithm = info.get('algorithm', 'SHA256_SALTED')
        salt = info.get('salt', b'')

        if algorithm == 'SHA256_SALTED':
            computed = hashlib.sha256(salt + password.encode('utf-8')).digest()
            return computed == info['hash']

        elif algorithm == 'CRC_MODIFIED':
            # Implement CRC-based verification
            # This would need the actual TIA Portal algorithm
            computed = self._compute_tia_crc(password, salt)
            return computed == info['hash']

        return False

    def _compute_tia_crc(self, password: str, salt: bytes) -> bytes:
        """
        Compute TIA Portal CRC-based password hash.

        Note: This is a placeholder - actual algorithm is proprietary.
        """
        # Simplified placeholder
        pwd_bytes = password.encode('utf-8')
        combined = salt + pwd_bytes if salt else pwd_bytes

        # Use CRC32 as approximation (NOT actual TIA algorithm)
        import zlib
        crc = zlib.crc32(combined)
        return struct.pack('>Q', crc)[:8]
