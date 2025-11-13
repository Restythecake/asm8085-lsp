# asm8085-lsp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Language Server Protocol (LSP) implementation for Intel 8085 assembly language.

## Overview

`asm8085-lsp` provides comprehensive IDE features for 8085 assembly programming, including:

- **Real-time diagnostics** - Syntax errors, undefined labels, and assembly issues
- **Code completion** - Instructions, registers, labels, and directives
- **Hover documentation** - Detailed instruction information with examples
- **Go to definition** - Jump to label definitions
- **Document symbols** - Outline view of all labels in your code
- **Signature help** - Instruction syntax hints as you type

## Features

### Intelligent Diagnostics

The LSP provides immediate feedback on:
- Invalid opcodes and syntax errors
- Undefined or duplicate labels
- Invalid instruction arguments
- Directive usage issues

### Smart Completion

Context-aware completions for:
- All 8085 instructions (MOV, MVI, ADD, JMP, etc.)
- Register names (A, B, C, D, E, H, L, M)
- Register pairs (BC, DE, HL, SP, PSW)
- Labels defined in your code
- Assembler directives (ORG, DB, DS)

### Rich Documentation

Hover over any instruction to see:
- Full instruction name and description
- Opcode and instruction size
- Cycle count (T-states)
- Flags affected
- Syntax and usage examples
- Related instructions

## Installation

### Quick Start

```bash
# Install from source
git clone https://github.com/Restythecake/asm8085-lsp.git
cd asm8085-lsp
pip install .
```

### For Development

```bash
# Clone the repository
git clone https://github.com/Restythecake/asm8085-lsp.git
cd asm8085-lsp

# Install in development mode
pip install -e .

# Install development dependencies (optional)
pip install -r requirements.txt
```

### As a Standalone Binary

Build with PyInstaller for distribution:

```bash
# Install PyInstaller
pip install pyinstaller

# Build standalone executable
pyinstaller --onefile --name asm8085-lsp asm8085-lsp

# Binary will be in dist/asm8085-lsp (or dist/asm8085-lsp.exe on Windows)
```

## Usage

### Standalone

Run the language server directly:

```bash
asm8085-lsp
```

The server communicates via stdin/stdout using the Language Server Protocol.

### With Zed Editor

This LSP is designed to work seamlessly with the [zed-8085-asm](../zed-8085-asm) extension. The extension automatically discovers and launches the language server.

### With Other Editors

Configure your editor to use `asm8085-lsp` as the language server for `.asm`, `.a85`, and `.8085` files.

#### VS Code Example

```json
{
  "languageServerExample.trace.server": "verbose",
  "asm8085.languageServer": {
    "command": "asm8085-lsp",
    "args": []
  }
}
```

#### Neovim Example (with nvim-lspconfig)

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

configs.asm8085_lsp = {
  default_config = {
    cmd = {'asm8085-lsp'},
    filetypes = {'asm', 'a85', '8085'},
    root_dir = lspconfig.util.root_pattern('.git'),
  }
}

lspconfig.asm8085_lsp.setup{}
```

## Architecture

The LSP server consists of several components:

- **`server.py`** - Main LSP server implementation with JSON-RPC message handling
- **`asm8085_cli/`** - 8085 assembler and emulator (embedded)
- **`handlers/`** - Individual LSP feature handlers (completion, hover, etc.)
- **`instruction_docs.py`** - 8085 instruction metadata and documentation

### Design Principles

1. **Zero external dependencies** - Uses only Python standard library
2. **Fast response times** - Asynchronous diagnostics with token-based cancellation
3. **Robust error handling** - Graceful degradation on parse errors
4. **Educational focus** - Rich documentation to help learners

## Development

### Project Structure

```
asm8085-lsp/
├── asm8085_lsp/           # Main package
│   ├── __init__.py        # Package initialization
│   ├── __main__.py        # Entry point for `python -m asm8085_lsp`
│   ├── server.py          # LSP server implementation
│   ├── instruction_docs.py # Instruction metadata
│   ├── handlers/          # LSP feature handlers
│   │   ├── completion.py
│   │   ├── hover.py
│   │   ├── definition.py
│   │   ├── document_symbol.py
│   │   └── signature_help.py
│   ├── asm8085_cli/       # Embedded assembler
│   │   ├── assembler.py
│   │   ├── emulator.py
│   │   └── syntax.py
│   └── new_core/          # Core assembler logic
├── asm8085-lsp            # Standalone launcher script
├── setup.py               # Package setup (legacy)
├── pyproject.toml         # Modern Python packaging
└── README.md              # This file
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests (if available)
pytest

# Type checking
mypy asm8085_lsp/
```

### Building Binary

```bash
# Install build dependencies
pip install pyinstaller

# Build binary
./scripts/build.sh

# Test the binary
./dist/asm8085-lsp --version
```

### Debugging

Enable verbose logging:

```bash
export ASM8085_LSP_LOG_LEVEL=DEBUG
asm8085-lsp
```

The server sends log messages to the LSP client via `window/logMessage` notifications.

## 8085 Assembly Support

### Supported Instructions

All standard 8085 instructions are supported:

- **Data Transfer**: MOV, MVI, LXI, LDA, STA, LDAX, STAX, LHLD, SHLD, XCHG, etc.
- **Arithmetic**: ADD, ADI, ADC, SUB, SUI, SBB, INR, DCR, INX, DCX, DAD, DAA
- **Logical**: ANA, ANI, ORA, ORI, XRA, XRI, CMP, CPI, RLC, RRC, RAL, RAR, CMA, CMC, STC
- **Branch**: JMP, JZ, JNZ, JC, JNC, JP, JM, JPE, JPO, CALL, RET, RST, PCHL
- **Stack**: PUSH, POP
- **I/O & Control**: IN, OUT, EI, DI, HLT, NOP

### Assembler Directives

- `ORG address` - Set program origin
- `DB value` - Define byte
- `DS count` - Reserve space

### Syntax

```asm
; Comments start with semicolon
ORG 8000H          ; Optional origin directive

START:             ; Labels end with colon
    MVI A, 05H     ; Load immediate value
    MOV B, A       ; Register to register
    ADD B          ; Accumulator operation
    HLT            ; Halt execution

DATA: DB 10H       ; Data definition
```

## Integration with Zed Extension

This LSP server is designed to be embedded in the [zed-8085-asm](../zed-8085-asm) Zed extension. The extension:

1. Compiles this LSP into a standalone binary using PyInstaller
2. Bundles the binary in its `bin/` directory
3. Launches the LSP when opening 8085 assembly files

The separation allows:
- Independent development and testing of the LSP
- Easy updates without rebuilding the extension
- Potential reuse in other editors

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Examples

Check out the [examples](examples/) directory for sample 8085 assembly programs that demonstrate LSP features.

## Related Projects

- [zed-8085-asm](../zed-8085-asm) - Zed editor extension for 8085 assembly (if available)

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [SETUP.md](SETUP.md) - Publishing and setup instructions
- [examples/](examples/) - Example assembly programs

## Support

For issues, questions, or suggestions:
- [Open an issue](https://github.com/Restythecake/asm8085-lsp/issues) on GitHub
- Check the [CONTRIBUTING.md](CONTRIBUTING.md) guide
- Review existing [issues and discussions](https://github.com/Restythecake/asm8085-lsp/issues)
