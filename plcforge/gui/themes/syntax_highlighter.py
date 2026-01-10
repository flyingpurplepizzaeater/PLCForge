"""
Syntax Highlighters for IEC 61131-3 Languages

Provides syntax highlighting for:
- Structured Text (ST)
- Ladder Diagram (LD) - textual representation
- Instruction List (IL)
- Function Block Diagram (FBD) - textual representation
"""

import re
from typing import List, Tuple, Optional, Pattern

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QTextDocument,
    QColor, QFont, QBrush
)
from PyQt6.QtCore import Qt

from plcforge.gui.themes.theme_manager import ThemeManager


class BasePLCHighlighter(QSyntaxHighlighter):
    """Base class for PLC language syntax highlighters."""

    def __init__(self, parent: QTextDocument = None):
        super().__init__(parent)
        self._theme_manager = ThemeManager()
        self._rules: List[Tuple[Pattern, QTextCharFormat]] = []
        self._setup_formats()
        self._setup_rules()

    def _setup_formats(self) -> None:
        """Set up text formats based on current theme."""
        colors = self._theme_manager.colors

        # Keyword format
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(colors.syntax_keyword))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # Type format
        self.type_format = QTextCharFormat()
        self.type_format.setForeground(QColor(colors.syntax_type))

        # String format
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(colors.syntax_string))

        # Number format
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(colors.syntax_number))

        # Comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(colors.syntax_comment))
        self.comment_format.setFontItalic(True)

        # Function format
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor(colors.syntax_function))

        # Operator format
        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor(colors.syntax_operator))
        self.operator_format.setFontWeight(QFont.Weight.Bold)

        # Variable format
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor(colors.syntax_variable))

    def _setup_rules(self) -> None:
        """Set up highlighting rules. Override in subclasses."""
        pass

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to a block of text."""
        for pattern, format in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)

    def update_theme(self) -> None:
        """Update formats when theme changes."""
        self._setup_formats()
        self._setup_rules()
        self.rehighlight()


class StructuredTextHighlighter(BasePLCHighlighter):
    """
    Syntax highlighter for IEC 61131-3 Structured Text (ST).

    Highlights:
    - Keywords (IF, THEN, ELSE, FOR, WHILE, etc.)
    - Data types (BOOL, INT, REAL, STRING, etc.)
    - Operators (:=, AND, OR, NOT, etc.)
    - Comments (// and (* *))
    - Strings
    - Numbers
    - Function/FB calls
    """

    def _setup_rules(self) -> None:
        """Set up Structured Text highlighting rules."""
        self._rules = []

        # Keywords
        keywords = [
            'PROGRAM', 'END_PROGRAM', 'FUNCTION', 'END_FUNCTION',
            'FUNCTION_BLOCK', 'END_FUNCTION_BLOCK', 'VAR', 'VAR_INPUT',
            'VAR_OUTPUT', 'VAR_IN_OUT', 'VAR_TEMP', 'VAR_GLOBAL',
            'VAR_EXTERNAL', 'END_VAR', 'CONSTANT', 'RETAIN', 'NON_RETAIN',
            'IF', 'THEN', 'ELSIF', 'ELSE', 'END_IF',
            'CASE', 'OF', 'END_CASE',
            'FOR', 'TO', 'BY', 'DO', 'END_FOR',
            'WHILE', 'END_WHILE',
            'REPEAT', 'UNTIL', 'END_REPEAT',
            'EXIT', 'RETURN', 'CONTINUE',
            'AND', 'OR', 'NOT', 'XOR', 'MOD',
            'TRUE', 'FALSE',
            'TYPE', 'END_TYPE', 'STRUCT', 'END_STRUCT', 'ARRAY',
            'AT', 'CONFIGURATION', 'END_CONFIGURATION',
            'RESOURCE', 'END_RESOURCE', 'TASK', 'END_TASK',
            'WITH', 'READ_ONLY', 'READ_WRITE',
        ]
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.keyword_format))

        # Data types
        types = [
            'BOOL', 'BYTE', 'WORD', 'DWORD', 'LWORD',
            'SINT', 'INT', 'DINT', 'LINT',
            'USINT', 'UINT', 'UDINT', 'ULINT',
            'REAL', 'LREAL',
            'TIME', 'DATE', 'TIME_OF_DAY', 'DATE_AND_TIME', 'TOD', 'DT',
            'STRING', 'WSTRING',
            'POINTER', 'REFERENCE',
            'ANY', 'ANY_INT', 'ANY_REAL', 'ANY_NUM', 'ANY_BIT',
        ]
        pattern = r'\b(' + '|'.join(types) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.type_format))

        # Standard functions
        functions = [
            'ABS', 'SQRT', 'LN', 'LOG', 'EXP', 'EXPT',
            'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN', 'ATAN2',
            'ADD', 'SUB', 'MUL', 'DIV',
            'GT', 'GE', 'EQ', 'LE', 'LT', 'NE',
            'SEL', 'MAX', 'MIN', 'LIMIT', 'MUX',
            'SHL', 'SHR', 'ROL', 'ROR',
            'AND', 'OR', 'XOR', 'NOT',
            'LEN', 'LEFT', 'RIGHT', 'MID', 'CONCAT', 'INSERT', 'DELETE', 'REPLACE', 'FIND',
            'ADR', 'SIZEOF', 'TRUNC', 'MOVE',
            'TO_BOOL', 'TO_INT', 'TO_DINT', 'TO_REAL', 'TO_STRING',
            'INT_TO_REAL', 'REAL_TO_INT', 'BOOL_TO_INT', 'INT_TO_BOOL',
        ]
        pattern = r'\b(' + '|'.join(functions) + r')\s*\('
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.function_format))

        # Timer/Counter function blocks
        fb_types = [
            'TON', 'TOF', 'TP', 'RTC',
            'CTU', 'CTD', 'CTUD',
            'R_TRIG', 'F_TRIG',
            'SR', 'RS',
        ]
        pattern = r'\b(' + '|'.join(fb_types) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.function_format))

        # Operators
        self._rules.append((re.compile(r':=|=>'), self.operator_format))
        self._rules.append((re.compile(r'[+\-*/=<>:;,\.\(\)\[\]]'), self.operator_format))

        # Numbers (including typed literals)
        self._rules.append((re.compile(r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b'), self.number_format))
        self._rules.append((re.compile(r'\b(16#[0-9A-Fa-f]+|2#[01]+|8#[0-7]+)\b'), self.number_format))
        self._rules.append((re.compile(r'\bT#[\d_]+[dhms]+\b', re.IGNORECASE), self.number_format))

        # Strings
        self._rules.append((re.compile(r"'[^']*'"), self.string_format))
        self._rules.append((re.compile(r'"[^"]*"'), self.string_format))

        # Single-line comments
        self._rules.append((re.compile(r'//.*$'), self.comment_format))

    def highlightBlock(self, text: str) -> None:
        """Apply highlighting with multi-line comment support."""
        # Apply single-line rules
        super().highlightBlock(text)

        # Handle multi-line comments (* ... *)
        self._highlight_multiline_comment(text, r'\(\*', r'\*\)', 1)

    def _highlight_multiline_comment(
        self, text: str, start_pattern: str, end_pattern: str, state: int
    ) -> None:
        """Handle multi-line comment highlighting."""
        start_re = re.compile(start_pattern)
        end_re = re.compile(end_pattern)

        start_index = 0
        if self.previousBlockState() != state:
            # Not in a comment, look for start
            match = start_re.search(text)
            if match:
                start_index = match.start()
            else:
                return

        while start_index >= 0:
            end_match = end_re.search(text, start_index + 2)
            if end_match:
                # Comment ends in this block
                length = end_match.end() - start_index
                self.setFormat(start_index, length, self.comment_format)
                # Look for another comment start
                match = start_re.search(text, end_match.end())
                if match:
                    start_index = match.start()
                else:
                    break
            else:
                # Comment continues to next block
                self.setCurrentBlockState(state)
                length = len(text) - start_index
                self.setFormat(start_index, length, self.comment_format)
                break


class LadderHighlighter(BasePLCHighlighter):
    """
    Syntax highlighter for Ladder Diagram textual representation.

    Highlights ladder logic instructions and elements.
    """

    def _setup_rules(self) -> None:
        """Set up Ladder highlighting rules."""
        self._rules = []

        # Rung elements
        elements = [
            'XIC', 'XIO', 'OTE', 'OTL', 'OTU', 'ONS',
            'TON', 'TOF', 'RTO', 'CTU', 'CTD', 'RES',
            'ADD', 'SUB', 'MUL', 'DIV', 'MOV', 'COP', 'FLL',
            'EQU', 'NEQ', 'LES', 'LEQ', 'GRT', 'GEQ',
            'JSR', 'RET', 'SBR', 'JMP', 'LBL',
            'MCR', 'END', 'AFI',
            'BST', 'NXB', 'BND',  # Branch instructions
        ]
        pattern = r'\b(' + '|'.join(elements) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.keyword_format))

        # Tag names (alphanumeric with underscores)
        self._rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\b'), self.variable_format))

        # Numbers
        self._rules.append((re.compile(r'\b\d+(\.\d+)?\b'), self.number_format))

        # Rung markers
        self._rules.append((re.compile(r'\|--.*--\|'), self.operator_format))
        self._rules.append((re.compile(r'[\|\-\+\[\]\(\)]'), self.operator_format))

        # Comments
        self._rules.append((re.compile(r';.*$'), self.comment_format))


class InstructionListHighlighter(BasePLCHighlighter):
    """
    Syntax highlighter for IEC 61131-3 Instruction List (IL).

    Highlights IL mnemonics and operands.
    """

    def _setup_rules(self) -> None:
        """Set up Instruction List highlighting rules."""
        self._rules = []

        # IL operators/mnemonics
        operators = [
            'LD', 'LDN', 'ST', 'STN', 'S', 'R',
            'AND', 'ANDN', 'OR', 'ORN', 'XOR', 'XORN',
            'NOT', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD',
            'GT', 'GE', 'EQ', 'NE', 'LE', 'LT',
            'JMP', 'JMPC', 'JMPCN',
            'CAL', 'CALC', 'CALCN',
            'RET', 'RETC', 'RETCN',
        ]
        pattern = r'^\s*(' + '|'.join(operators) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE | re.MULTILINE), self.keyword_format))

        # Labels
        self._rules.append((re.compile(r'^[A-Za-z_][A-Za-z0-9_]*:'), self.function_format))

        # Variables/operands
        self._rules.append((re.compile(r'%[IQMXBWD]\d+(\.\d+)?'), self.variable_format))
        self._rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\b'), self.variable_format))

        # Numbers
        self._rules.append((re.compile(r'\b\d+(\.\d+)?\b'), self.number_format))
        self._rules.append((re.compile(r'\bTRUE\b|\bFALSE\b', re.IGNORECASE), self.number_format))

        # Comments (parentheses style)
        self._rules.append((re.compile(r'\(.*\)'), self.comment_format))


class FunctionBlockHighlighter(BasePLCHighlighter):
    """
    Syntax highlighter for Function Block Diagram textual representation.

    Highlights FBD elements in textual format.
    """

    def _setup_rules(self) -> None:
        """Set up FBD highlighting rules."""
        self._rules = []

        # Block types
        blocks = [
            'AND', 'OR', 'NOT', 'XOR', 'NAND', 'NOR',
            'ADD', 'SUB', 'MUL', 'DIV', 'MOD',
            'GT', 'GE', 'EQ', 'NE', 'LE', 'LT',
            'SEL', 'MUX', 'LIMIT', 'MAX', 'MIN',
            'TON', 'TOF', 'TP', 'CTU', 'CTD', 'CTUD',
            'SR', 'RS', 'R_TRIG', 'F_TRIG',
            'MOVE', 'ABS', 'SQRT', 'SIN', 'COS', 'TAN',
        ]
        pattern = r'\b(' + '|'.join(blocks) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.function_format))

        # Connection keywords
        keywords = ['EN', 'ENO', 'IN', 'IN1', 'IN2', 'OUT', 'Q', 'PT', 'ET', 'PV', 'CV']
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.keyword_format))

        # Data types
        types = ['BOOL', 'INT', 'DINT', 'REAL', 'TIME', 'STRING']
        pattern = r'\b(' + '|'.join(types) + r')\b'
        self._rules.append((re.compile(pattern, re.IGNORECASE), self.type_format))

        # Variables
        self._rules.append((re.compile(r'%[IQMXBWD]\d+(\.\d+)?'), self.variable_format))
        self._rules.append((re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\b'), self.variable_format))

        # Numbers
        self._rules.append((re.compile(r'\b\d+(\.\d+)?\b'), self.number_format))

        # Connection lines
        self._rules.append((re.compile(r'[=\-\+\|]'), self.operator_format))

        # Comments
        self._rules.append((re.compile(r'//.*$'), self.comment_format))


def apply_highlighter(editor: QTextEdit, language: str) -> Optional[BasePLCHighlighter]:
    """
    Apply appropriate syntax highlighter to an editor.

    Args:
        editor: QTextEdit to apply highlighting to
        language: Language name (structured_text, ladder, instruction_list, function_block)

    Returns:
        The applied highlighter or None if language not supported
    """
    highlighter_map = {
        'structured_text': StructuredTextHighlighter,
        'st': StructuredTextHighlighter,
        'ladder': LadderHighlighter,
        'ld': LadderHighlighter,
        'instruction_list': InstructionListHighlighter,
        'il': InstructionListHighlighter,
        'function_block': FunctionBlockHighlighter,
        'fbd': FunctionBlockHighlighter,
    }

    highlighter_class = highlighter_map.get(language.lower())
    if highlighter_class:
        return highlighter_class(editor.document())
    return None
