"""Unit tests for AI code generation module."""

import pytest
from unittest.mock import patch, MagicMock

from plcforge.drivers.base import CodeLanguage
from plcforge.pal.unified_api import Vendor


class TestAIModuleImports:
    """Tests for AI module imports."""

    def test_import_ai_module(self):
        """Test AI module can be imported."""
        from plcforge import ai
        assert ai is not None

    def test_import_code_generator(self):
        """Test AICodeGenerator can be imported."""
        from plcforge.ai.code_generator import AICodeGenerator
        assert AICodeGenerator is not None

    def test_import_code_target(self):
        """Test CodeTarget can be imported."""
        from plcforge.ai.code_generator import CodeTarget
        assert CodeTarget is not None

    def test_import_generated_code(self):
        """Test GeneratedCode can be imported."""
        from plcforge.ai.code_generator import GeneratedCode
        assert GeneratedCode is not None


class TestCodeTarget:
    """Tests for CodeTarget dataclass."""

    def test_create_code_target(self):
        """Test creating CodeTarget instance."""
        from plcforge.ai.code_generator import CodeTarget

        target = CodeTarget(
            vendor=Vendor.SIEMENS,
            model="S7-1500",
            language=CodeLanguage.STRUCTURED_TEXT,
        )

        assert target is not None
        assert target.vendor == Vendor.SIEMENS
        assert target.model == "S7-1500"
        assert target.language == CodeLanguage.STRUCTURED_TEXT


class TestGeneratedCode:
    """Tests for GeneratedCode dataclass."""

    def test_create_generated_code(self):
        """Test creating GeneratedCode instance."""
        from plcforge.ai.code_generator import GeneratedCode

        result = GeneratedCode(
            code="Motor := TRUE;",
            language=CodeLanguage.STRUCTURED_TEXT,
            vendor=Vendor.SIEMENS,
            explanation="Simple motor control",
        )

        assert result is not None
        assert result.code == "Motor := TRUE;"
        assert result.language == CodeLanguage.STRUCTURED_TEXT


class TestCodeLanguageValues:
    """Tests for CodeLanguage enum."""

    def test_language_values(self):
        """Test all language values exist."""
        assert CodeLanguage.LADDER is not None
        assert CodeLanguage.STRUCTURED_TEXT is not None
        assert CodeLanguage.FUNCTION_BLOCK is not None
        assert CodeLanguage.INSTRUCTION_LIST is not None
        assert CodeLanguage.SFC is not None

    def test_language_string_values(self):
        """Test language string values."""
        assert CodeLanguage.LADDER.value == "ladder"
        assert CodeLanguage.STRUCTURED_TEXT.value == "st"
        assert CodeLanguage.FUNCTION_BLOCK.value == "fbd"
        assert CodeLanguage.INSTRUCTION_LIST.value == "il"
