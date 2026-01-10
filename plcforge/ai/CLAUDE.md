# AI Code Generation Module

<!-- AUTO-MANAGED: module-description -->
LLM-powered PLC code generation from natural language descriptions. Supports multiple vendors, programming languages (Ladder, ST, FBD, IL), and includes automated safety analysis for industrial applications.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
ai/
├── __init__.py              # Exports AICodeGenerator, CodeTarget, GeneratedCode
└── code_generator.py        # LLM integration and code generation logic
```
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Code Generation Flow:**
1. Create `CodeTarget(vendor, model, language, iec_version)`
2. Call `AICodeGenerator.generate(prompt, target, context, safety_check)`
3. Returns `GeneratedCode(code, language, vendor, explanation, safety_issues, metadata)`

**Supported Providers:**
- `"openai"` - Default model: `gpt-4-turbo-preview`
- `"anthropic"` - Default model: `claude-3-opus-20240229`

**Vendor Support:**
- `Vendor.SIEMENS` - Siemens-specific syntax and best practices
- `Vendor.ALLEN_BRADLEY` - Allen-Bradley conventions
- `Vendor.DELTA` - Delta DVP syntax
- `Vendor.OMRON` - Omron programming standards
- `Vendor.GENERIC` - IEC 61131-3 compliant code

**System Prompt Structure:**
- Vendor-specific best practices
- IEC 61131-3 compliance requirements
- Industrial safety standards (IEC 62443)
- Language syntax notes
- Output format: explanation → code block → safety considerations

**Safety Analysis:**
- Returns list of `SafetyIssue` objects (or dicts with severity, message, line_number, suggestion)
- Severity levels: "critical", "warning", "info"
- Includes line numbers and suggestions
- Checks for emergency stop handling, edge cases, error conditions

**Response Parsing:**
- Extract code from markdown code blocks in LLM responses
- Supports fence format: ```language\ncode\n```
- Parse explanation and safety sections from response text
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `openai>=1.0` - OpenAI GPT-4 API
- `anthropic>=0.20` - Anthropic Claude API
- `chromadb>=0.4` - Vector database for RAG
- `langchain>=0.1` - LLM orchestration framework
<!-- END AUTO-MANAGED -->
