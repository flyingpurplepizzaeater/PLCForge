"""
AI-Powered PLC Code Generation

Uses LLMs to generate PLC code from natural language descriptions.
Supports multiple output languages and vendors.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from plcforge.drivers.base import CodeLanguage


class Vendor(Enum):
    """Supported vendors for code generation"""
    SIEMENS = "siemens"
    ALLEN_BRADLEY = "allen_bradley"
    DELTA = "delta"
    OMRON = "omron"
    GENERIC = "generic"  # IEC 61131-3 compliant


@dataclass
class CodeTarget:
    """Target configuration for code generation"""
    vendor: Vendor
    model: str
    language: CodeLanguage
    iec_version: str = "IEC 61131-3"


@dataclass
class SafetyIssue:
    """A safety concern in generated code"""
    severity: Literal["critical", "warning", "info"]
    message: str
    line_number: int | None = None
    suggestion: str | None = None


@dataclass
class GeneratedCode:
    """Result of code generation"""
    code: str
    language: CodeLanguage
    vendor: Vendor
    explanation: str
    safety_issues: list[SafetyIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AICodeGenerator:
    """
    AI-powered PLC code generator.

    Uses LLMs (OpenAI GPT-4 or Anthropic Claude) to generate
    vendor-specific PLC code from natural language descriptions.
    """

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        api_key: str | None = None,
        model: str | None = None
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model or self._default_model()
        self._client = None

    def _default_model(self) -> str:
        """Get default model for provider"""
        if self.provider == "openai":
            return "gpt-4-turbo-preview"
        elif self.provider == "anthropic":
            return "claude-3-opus-20240229"
        return "gpt-4"

    def _get_client(self):
        """Get or create API client"""
        if self._client:
            return self._client

        if self.provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed")

        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed")

        return self._client

    def generate(
        self,
        prompt: str,
        target: CodeTarget,
        context: str | None = None,
        safety_check: bool = True
    ) -> GeneratedCode:
        """
        Generate PLC code from natural language description.

        Args:
            prompt: Natural language description of desired logic
            target: Target vendor/model/language configuration
            context: Additional context (existing code, requirements)
            safety_check: Whether to run safety analysis

        Returns:
            GeneratedCode with generated code and metadata
        """
        # Build system prompt
        system_prompt = self._build_system_prompt(target)

        # Build user prompt
        user_prompt = self._build_user_prompt(prompt, target, context)

        # Call LLM
        if self.provider == "openai":
            response = self._call_openai(system_prompt, user_prompt)
        elif self.provider == "anthropic":
            response = self._call_anthropic(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Parse response
        code = self._extract_code(response)
        explanation = self._extract_explanation(response)

        # Safety analysis
        safety_issues = []
        if safety_check:
            safety_issues = self._analyze_safety(code, target)

        return GeneratedCode(
            code=code,
            language=target.language,
            vendor=target.vendor,
            explanation=explanation,
            safety_issues=safety_issues,
            metadata={
                'prompt': prompt,
                'model': self.model,
                'provider': self.provider,
            }
        )

    def _build_system_prompt(self, target: CodeTarget) -> str:
        """Build system prompt for LLM"""
        vendor_info = self._get_vendor_info(target.vendor)
        language_info = self._get_language_info(target.language)

        return f"""You are an expert industrial PLC programmer specializing in {vendor_info['name']} PLCs.

You generate high-quality, safe, and efficient PLC code following these standards:
- IEC 61131-3 compliance where applicable
- {vendor_info['name']}-specific best practices
- Industrial safety standards (IEC 62443, machinery safety)

Target Platform:
- Vendor: {vendor_info['name']}
- Model: {target.model}
- Programming Language: {language_info['name']}

Code Requirements:
1. Always include proper initialization
2. Include emergency stop handling where appropriate
3. Use meaningful variable names
4. Add comments explaining logic
5. Handle edge cases and error conditions
6. Follow {vendor_info['name']} naming conventions

{vendor_info['specific_guidelines']}

{language_info['syntax_notes']}

Output Format:
1. First, provide a brief explanation of your approach
2. Then provide the complete code in a code block
3. Finally, note any safety considerations or recommendations
"""

    def _build_user_prompt(
        self,
        prompt: str,
        target: CodeTarget,
        context: str | None
    ) -> str:
        """Build user prompt"""
        user_prompt = f"Generate {target.language.value} code for the following requirement:\n\n{prompt}"

        if context:
            user_prompt += f"\n\nAdditional Context:\n{context}"

        return user_prompt

    def _get_vendor_info(self, vendor: Vendor) -> dict[str, str]:
        """Get vendor-specific information"""
        vendor_info = {
            Vendor.SIEMENS: {
                'name': 'Siemens',
                'specific_guidelines': """
Siemens-Specific Guidelines:
- Use DB (Data Blocks) for structured data storage
- Use FB (Function Blocks) for reusable logic with instance data
- Use FC (Functions) for stateless operations
- Follow TIA Portal naming conventions (e.g., "Motor_1", "Conveyor_Start")
- Use symbolic addressing when possible
- Implement proper OB organization (OB1 for main, OB100 for startup)
"""
            },
            Vendor.ALLEN_BRADLEY: {
                'name': 'Allen-Bradley',
                'specific_guidelines': """
Allen-Bradley-Specific Guidelines:
- Use Add-On Instructions (AOI) for reusable logic
- Follow Studio 5000 naming conventions (CamelCase)
- Use UDTs (User-Defined Types) for structured data
- Implement proper task organization
- Use program-scoped vs controller-scoped tags appropriately
- Follow Rockwell Automation best practices
"""
            },
            Vendor.DELTA: {
                'name': 'Delta',
                'specific_guidelines': """
Delta DVP-Specific Guidelines:
- Use D registers for data storage (D0-D9999)
- Use M relays for internal flags (M0-M4095)
- Follow ISPSoft conventions
- Use proper timer/counter ranges for DVP series
- X inputs and Y outputs use octal addressing
"""
            },
            Vendor.OMRON: {
                'name': 'Omron',
                'specific_guidelines': """
Omron-Specific Guidelines:
- Use DM (Data Memory) for data storage
- Use W (Work) area for internal flags
- Follow CX-Programmer or Sysmac conventions
- Use proper memory area designations (CIO, W, H, D)
- Implement function blocks for reusable code
"""
            },
            Vendor.GENERIC: {
                'name': 'Generic IEC 61131-3',
                'specific_guidelines': """
Generic IEC 61131-3 Guidelines:
- Follow standard data types (BOOL, INT, DINT, REAL, etc.)
- Use POUs (Program Organization Units) properly
- Implement proper variable scoping
- Follow standard function block conventions
"""
            },
        }
        return vendor_info.get(vendor, vendor_info[Vendor.GENERIC])

    def _get_language_info(self, language: CodeLanguage) -> dict[str, str]:
        """Get language-specific information"""
        language_info = {
            CodeLanguage.STRUCTURED_TEXT: {
                'name': 'Structured Text (ST)',
                'syntax_notes': """
Structured Text Syntax:
- Use := for assignment
- END_IF, END_FOR, END_WHILE for block terminators
- Use (* comments *) or // for line comments
- Case-insensitive keywords
- Standard operators: AND, OR, NOT, XOR
"""
            },
            CodeLanguage.LADDER: {
                'name': 'Ladder Diagram (LAD)',
                'syntax_notes': """
Ladder Diagram Notes:
- Provide code as pseudo-ladder or XML representation
- Include rung comments
- Use standard contact/coil notation
- Specify parallel and series connections clearly
"""
            },
            CodeLanguage.FUNCTION_BLOCK: {
                'name': 'Function Block Diagram (FBD)',
                'syntax_notes': """
Function Block Diagram Notes:
- Describe connections between blocks
- Specify input/output mappings
- Use standard function block types
"""
            },
            CodeLanguage.INSTRUCTION_LIST: {
                'name': 'Instruction List (IL)',
                'syntax_notes': """
Instruction List Syntax:
- Use standard IL mnemonics (LD, ST, AND, OR, etc.)
- One instruction per line
- Labels end with colon
- Use CAL for function calls
"""
            },
        }
        return language_info.get(language, language_info[CodeLanguage.STRUCTURED_TEXT])

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API"""
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4096,
            temperature=0.3,  # Lower temperature for more deterministic code
        )

        return response.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic API"""
        client = self._get_client()

        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.content[0].text

    def _extract_code(self, response: str) -> str:
        """Extract code block from response"""
        # Look for code blocks
        import re

        # Try to find fenced code block
        code_match = re.search(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Look for indented code block
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                code_lines.append(line)
                in_code = True
            elif in_code and line.strip() == '':
                code_lines.append(line)
            elif in_code:
                break

        if code_lines:
            return '\n'.join(code_lines).strip()

        # Return full response if no code block found
        return response

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation from response"""
        # Get text before code block
        import re

        code_start = re.search(r'```', response)
        if code_start:
            explanation = response[:code_start.start()].strip()
            return explanation

        return ""

    def _analyze_safety(self, code: str, target: CodeTarget) -> list[SafetyIssue]:
        """Analyze generated code for safety issues"""
        issues = []

        code_lower = code.lower()

        # Check for emergency stop handling
        estop_keywords = ['estop', 'e_stop', 'emergency', 'emergencystop', 'nothalt']
        has_estop = any(kw in code_lower for kw in estop_keywords)

        if not has_estop:
            issues.append(SafetyIssue(
                severity="warning",
                message="No emergency stop handling detected",
                suggestion="Consider adding emergency stop logic for safety-critical applications"
            ))

        # Check for infinite loops
        if 'while true' in code_lower and 'exit' not in code_lower:
            issues.append(SafetyIssue(
                severity="warning",
                message="Potential infinite loop detected",
                suggestion="Ensure loop has proper exit condition"
            ))

        # Check for hardcoded timers without safety margins
        import re
        timer_pattern = r't#(\d+)(ms|s|m)'
        timers = re.findall(timer_pattern, code_lower)
        for value, unit in timers:
            if unit == 's' and int(value) > 60:
                issues.append(SafetyIssue(
                    severity="info",
                    message=f"Long timer duration detected: {value}{unit}",
                    suggestion="Verify long timer is intentional and consider watchdog"
                ))

        # Check for missing initialization
        if target.language == CodeLanguage.STRUCTURED_TEXT:
            if 'var' in code_lower and ':=' not in code_lower:
                issues.append(SafetyIssue(
                    severity="info",
                    message="Variables declared without initialization",
                    suggestion="Consider initializing variables to known safe values"
                ))

        return issues

    def explain_code(self, code: str, target: CodeTarget) -> str:
        """Generate explanation for existing PLC code"""
        system_prompt = f"""You are an expert PLC programmer who explains code clearly.
Analyze the following {target.vendor.value} PLC code and provide:
1. A high-level summary of what the code does
2. Step-by-step explanation of the logic
3. Any potential issues or improvements
"""
        user_prompt = f"Explain this code:\n\n```\n{code}\n```"

        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        else:
            return self._call_anthropic(system_prompt, user_prompt)

    def optimize_code(self, code: str, target: CodeTarget) -> GeneratedCode:
        """Optimize existing PLC code"""
        system_prompt = self._build_system_prompt(target)
        user_prompt = f"""Optimize the following code for better performance and readability.
Maintain the same functionality but improve:
- Execution efficiency
- Memory usage
- Code clarity
- Best practices compliance

Original code:
```
{code}
```

Provide the optimized code with explanations of changes made."""

        if self.provider == "openai":
            response = self._call_openai(system_prompt, user_prompt)
        else:
            response = self._call_anthropic(system_prompt, user_prompt)

        optimized_code = self._extract_code(response)
        explanation = self._extract_explanation(response)

        return GeneratedCode(
            code=optimized_code,
            language=target.language,
            vendor=target.vendor,
            explanation=explanation,
            metadata={'original_code': code, 'operation': 'optimize'}
        )
