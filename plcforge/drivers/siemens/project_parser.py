"""
TIA Portal Project File Parser

Parses Siemens TIA Portal project files (.ap13 through .ap20)
for offline analysis and password recovery.
"""

import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plcforge.drivers.base import (
    Block,
    BlockInfo,
    BlockType,
    CodeLanguage,
    PLCProgram,
    ProjectFileParser,
)


@dataclass
class TIAProjectInfo:
    """Information extracted from TIA Portal project"""
    version: str
    name: str
    author: str | None
    created: str | None
    modified: str | None
    devices: list[dict[str, Any]]
    protected: bool
    password_hash: bytes | None


class TIAPortalParser(ProjectFileParser):
    """
    Parser for TIA Portal project files (.ap13 - .ap20).

    TIA Portal projects are ZIP archives containing XML metadata
    and binary block data.
    """

    SUPPORTED_VERSIONS = {
        '.ap13': 'V13',
        '.ap14': 'V14',
        '.ap15': 'V15',
        '.ap15_1': 'V15.1',
        '.ap16': 'V16',
        '.ap17': 'V17',
        '.ap18': 'V18',
        '.ap19': 'V19',
        '.ap20': 'V20',
        '.zap13': 'V13 (archived)',
        '.zap14': 'V14 (archived)',
        '.zap15': 'V15 (archived)',
        '.zap16': 'V16 (archived)',
        '.zap17': 'V17 (archived)',
        '.zap18': 'V18 (archived)',
        '.zap19': 'V19 (archived)',
        '.zap20': 'V20 (archived)',
    }

    def supported_extensions(self) -> list[str]:
        return list(self.SUPPORTED_VERSIONS.keys())

    def parse(self, file_path: str) -> PLCProgram:
        """
        Parse TIA Portal project file.

        Args:
            file_path: Path to .ap or .zap file

        Returns:
            PLCProgram with extracted content
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Project file not found: {file_path}")

        ext = ''.join(path.suffixes).lower()
        if ext not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        # Handle archived projects (.zap files)
        if ext.startswith('.zap'):
            return self._parse_archived(file_path)

        return self._parse_project(file_path)

    def _parse_project(self, file_path: str) -> PLCProgram:
        """Parse unarchived .ap project file"""
        program = PLCProgram(
            vendor="Siemens",
            model="TIA Portal Project",
            metadata={'source_file': file_path}
        )

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Get project info
                project_info = self._extract_project_info(zf)
                program.metadata.update({
                    'tia_version': project_info.version,
                    'project_name': project_info.name,
                    'author': project_info.author,
                    'protected': project_info.protected,
                })

                # Extract program blocks
                program.blocks = self._extract_blocks(zf)

                # Extract configuration
                program.configuration = self._extract_configuration(zf)

        except zipfile.BadZipFile:
            raise ValueError(f"Invalid or corrupted project file: {file_path}")

        return program

    def _parse_archived(self, file_path: str) -> PLCProgram:
        """Parse archived .zap project file"""
        import gzip
        import tempfile

        # .zap files are gzip-compressed .ap files
        with tempfile.NamedTemporaryFile(suffix='.ap', delete=False) as tmp:
            try:
                with gzip.open(file_path, 'rb') as gz:
                    tmp.write(gz.read())
                tmp_path = tmp.name

                return self._parse_project(tmp_path)
            finally:
                os.unlink(tmp_path)

    def _extract_project_info(self, zf: zipfile.ZipFile) -> TIAProjectInfo:
        """Extract basic project information"""
        info = TIAProjectInfo(
            version="Unknown",
            name="Unknown",
            author=None,
            created=None,
            modified=None,
            devices=[],
            protected=False,
            password_hash=None,
        )

        # Look for project metadata files
        for name in zf.namelist():
            if 'System' in name and name.endswith('.xml'):
                try:
                    content = zf.read(name)
                    root = ET.fromstring(content)

                    # Extract project name
                    name_elem = root.find('.//{*}Name')
                    if name_elem is not None:
                        info.name = name_elem.text

                    # Check for protection
                    protection_elem = root.find('.//{*}Protection')
                    if protection_elem is not None:
                        info.protected = True

                except ET.ParseError:
                    pass

        # Detect version from file structure
        for name in zf.namelist():
            if 'ProjectVersion' in name:
                try:
                    content = zf.read(name).decode('utf-8')
                    if 'V20' in content:
                        info.version = 'V20'
                    elif 'V19' in content:
                        info.version = 'V19'
                    elif 'V18' in content:
                        info.version = 'V18'
                    elif 'V17' in content:
                        info.version = 'V17'
                    elif 'V16' in content:
                        info.version = 'V16'
                except Exception:
                    pass

        return info

    def _extract_blocks(self, zf: zipfile.ZipFile) -> list[Block]:
        """Extract program blocks from project"""
        blocks = []

        for name in zf.namelist():
            # Look for program block files
            if 'ProgramBlocks' in name or 'PLC_' in name:
                if name.endswith('.xml'):
                    try:
                        content = zf.read(name)
                        block = self._parse_block_xml(content, name)
                        if block:
                            blocks.append(block)
                    except Exception:
                        pass

        return blocks

    def _parse_block_xml(self, content: bytes, filename: str) -> Block | None:
        """Parse a block XML file"""
        try:
            root = ET.fromstring(content)

            # Determine block type from filename or content
            block_type = BlockType.FB  # Default
            block_number = 1

            if 'OB' in filename:
                block_type = BlockType.OB
            elif 'FB' in filename:
                block_type = BlockType.FB
            elif 'FC' in filename:
                block_type = BlockType.FC
            elif 'DB' in filename:
                block_type = BlockType.DB

            # Extract number from filename
            import re
            match = re.search(r'(\d+)', filename)
            if match:
                block_number = int(match.group(1))

            # Get block name
            name_elem = root.find('.//{*}Name')
            block_name = name_elem.text if name_elem is not None else f"{block_type.name}{block_number}"

            # Determine programming language
            lang = CodeLanguage.LADDER
            lang_elem = root.find('.//{*}ProgrammingLanguage')
            if lang_elem is not None:
                lang_text = lang_elem.text.upper()
                if 'LAD' in lang_text:
                    lang = CodeLanguage.LADDER
                elif 'SCL' in lang_text or 'ST' in lang_text:
                    lang = CodeLanguage.STRUCTURED_TEXT
                elif 'FBD' in lang_text:
                    lang = CodeLanguage.FUNCTION_BLOCK
                elif 'STL' in lang_text or 'IL' in lang_text:
                    lang = CodeLanguage.INSTRUCTION_LIST
                elif 'GRAPH' in lang_text:
                    lang = CodeLanguage.GRAPH

            block_info = BlockInfo(
                block_type=block_type,
                number=block_number,
                name=block_name,
                language=lang,
                size=len(content),
                protected=False,
            )

            # Check for know-how protection
            protect_elem = root.find('.//{*}KnowHowProtection')
            if protect_elem is not None:
                block_info.protected = True

            return Block(
                info=block_info,
                source_code=content.decode('utf-8', errors='ignore'),
            )

        except ET.ParseError:
            return None

    def _extract_configuration(self, zf: zipfile.ZipFile) -> dict[str, Any]:
        """Extract hardware configuration"""
        config = {}

        for name in zf.namelist():
            if 'HWConfig' in name or 'Hardware' in name:
                if name.endswith('.xml'):
                    try:
                        content = zf.read(name)
                        ET.fromstring(content)
                        # Extract relevant configuration
                        config['hardware_file'] = name
                    except Exception:
                        pass

        return config

    def get_protection_info(self, file_path: str) -> dict[str, Any]:
        """
        Extract password and protection information from project file.

        This is used by the password recovery engine.
        """
        info = {
            'protected': False,
            'protection_type': None,
            'password_hash': None,
            'hash_algorithm': None,
            'salt': None,
            'know_how_protected_blocks': [],
            'encryption_version': None,
        }

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Search for protection-related files
                for name in zf.namelist():
                    # Project-level protection
                    if 'Protection' in name or 'Security' in name:
                        try:
                            content = zf.read(name)
                            protection_data = self._parse_protection_data(content)
                            info.update(protection_data)
                        except Exception:
                            pass

                    # Know-how protection
                    if 'KnowHow' in name:
                        try:
                            content = zf.read(name)
                            kh_info = self._parse_knowhow_protection(content)
                            info['know_how_protected_blocks'].extend(kh_info)
                        except Exception:
                            pass

                    # Look for password hashes in binary files
                    if name.endswith('.plf') or name.endswith('.dat'):
                        try:
                            content = zf.read(name)
                            hash_data = self._extract_password_hash(content)
                            if hash_data:
                                info['password_hash'] = hash_data['hash']
                                info['hash_algorithm'] = hash_data['algorithm']
                                info['salt'] = hash_data.get('salt')
                                info['protected'] = True
                        except Exception:
                            pass

        except zipfile.BadZipFile:
            pass

        return info

    def _parse_protection_data(self, content: bytes) -> dict[str, Any]:
        """Parse protection configuration data"""
        result = {}

        try:
            # Try XML parsing
            root = ET.fromstring(content)

            protection_elem = root.find('.//{*}ProjectProtection')
            if protection_elem is not None:
                result['protected'] = True
                result['protection_type'] = 'project'

            access_elem = root.find('.//{*}AccessProtection')
            if access_elem is not None:
                result['protection_type'] = 'access'

        except ET.ParseError:
            # Binary format - try to extract hash directly
            if len(content) >= 32:
                # Look for hash patterns
                result['raw_protection_data'] = content[:256].hex()

        return result

    def _parse_knowhow_protection(self, content: bytes) -> list[dict[str, Any]]:
        """Parse know-how protection information"""
        protected_blocks = []

        try:
            root = ET.fromstring(content)

            for block_elem in root.findall('.//{*}ProtectedBlock'):
                block_info = {
                    'name': block_elem.get('Name', 'Unknown'),
                    'type': block_elem.get('Type', 'Unknown'),
                }
                protected_blocks.append(block_info)

        except ET.ParseError:
            pass

        return protected_blocks

    def _extract_password_hash(self, content: bytes) -> dict[str, Any] | None:
        """
        Attempt to extract password hash from binary content.

        TIA Portal uses different hash formats depending on version:
        - V13-V14: Modified CRC-based hash
        - V15+: SHA-256 based with salt
        """
        result = None

        # Look for known hash signatures
        # V15+ SHA-256 pattern: 32 bytes preceded by salt
        for i in range(len(content) - 64):
            # Check for potential salt+hash structure
            potential_salt = content[i:i+16]
            potential_hash = content[i+16:i+48]

            # Heuristic: check if it looks like a hash
            # (high entropy, no null bytes in middle)
            if self._looks_like_hash(potential_hash):
                result = {
                    'hash': potential_hash,
                    'salt': potential_salt,
                    'algorithm': 'SHA256_SALTED',
                    'offset': i,
                }
                break

        # Look for older CRC-based hashes (8 bytes)
        if result is None:
            for i in range(len(content) - 8):
                # V13-V14 used 8-byte hash
                potential_hash = content[i:i+8]
                if self._looks_like_short_hash(potential_hash):
                    result = {
                        'hash': potential_hash,
                        'salt': None,
                        'algorithm': 'CRC_MODIFIED',
                        'offset': i,
                    }
                    break

        return result

    def _looks_like_hash(self, data: bytes) -> bool:
        """Heuristic to check if bytes look like a hash"""
        if len(data) < 16:
            return False

        # Check for reasonable entropy
        unique_bytes = len(set(data))
        if unique_bytes < 8:  # Too few unique bytes
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

        if max_run > 4:  # Too repetitive
            return False

        return True

    def _looks_like_short_hash(self, data: bytes) -> bool:
        """Check if 8 bytes look like an older-style hash"""
        if data == b'\x00' * 8 or data == b'\xff' * 8:
            return False

        unique_bytes = len(set(data))
        return unique_bytes >= 4
