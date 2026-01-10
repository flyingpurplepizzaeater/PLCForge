"""Unit tests for password recovery module."""

import pytest
from pathlib import Path


class TestRecoveryModuleImports:
    """Tests for recovery module imports."""

    def test_import_recovery_module(self):
        """Test recovery module can be imported."""
        from plcforge import recovery
        assert recovery is not None

    def test_import_recovery_engine(self):
        """Test RecoveryEngine can be imported."""
        from plcforge.recovery.engine import RecoveryEngine
        assert RecoveryEngine is not None

    def test_import_recovery_target(self):
        """Test RecoveryTarget can be imported."""
        from plcforge.recovery.engine import RecoveryTarget
        assert RecoveryTarget is not None

    def test_import_recovery_config(self):
        """Test RecoveryConfig can be imported."""
        from plcforge.recovery.engine import RecoveryConfig
        assert RecoveryConfig is not None


class TestRecoveryEngineInstantiation:
    """Tests for RecoveryEngine instantiation."""

    def test_create_engine(self):
        """Test creating RecoveryEngine instance."""
        from plcforge.recovery.engine import RecoveryEngine
        engine = RecoveryEngine()
        assert engine is not None


class TestVulnerabilityExploitsImport:
    """Tests for vulnerability exploit imports."""

    def test_import_s7_300_exploit(self):
        """Test S7-300 exploit can be imported."""
        from plcforge.recovery.vulnerabilities.siemens_s7_300 import S7_300_SDBExtract
        assert S7_300_SDBExtract is not None

    def test_import_s7_400_exploit(self):
        """Test S7-400 exploit can be imported."""
        from plcforge.recovery.vulnerabilities.siemens_s7_400 import S7_400_SDBExtract
        assert S7_400_SDBExtract is not None

    def test_import_s7_1200_exploit(self):
        """Test S7-1200 exploit can be imported."""
        from plcforge.recovery.vulnerabilities.siemens_s7_1200 import S7_1200_WeakHash
        assert S7_1200_WeakHash is not None


class TestFileParserImport:
    """Tests for file parser imports."""

    def test_import_tia_parser(self):
        """Test TIA Portal parser can be imported."""
        from plcforge.recovery.file_parsers.tia_portal import TIAPortalPasswordParser
        assert TIAPortalPasswordParser is not None

    def test_create_tia_parser(self):
        """Test creating TIA Portal parser instance."""
        from plcforge.recovery.file_parsers.tia_portal import TIAPortalPasswordParser
        parser = TIAPortalPasswordParser()
        assert parser is not None
