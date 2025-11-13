# ASM8085 CLI Structure

This document describes the reorganized structure of the 8085 assembler and emulator CLI.

## Directory Structure

```
asm8085_cli/
├── __init__.py
├── __main__.py
├── cli.py                          # Main CLI entry point (argument parsing & routing)
│
├── shared/                         # Shared/core code used by multiple commands
│   ├── __init__.py
│   ├── assembler.py                # Core assembler
│   ├── assembly.py                 # Assembly utilities (load_source_file, assemble_or_exit)
│   ├── colors.py                   # Terminal color constants
│   ├── config.py                   # Configuration file handling
│   ├── constants.py                # Global constants (DEFAULT_BENCHMARK_RUNS, etc.)
│   ├── emu.py                      # Core 8085 emulator (emu8085 class)
│   ├── executor.py                 # Execution utilities (resolve_step_limit)
│   ├── helptext.py                 # Help text (print_short_help, print_full_help)
│   ├── instruction_db.json         # Instruction database (JSON)
│   ├── instruction_db.py           # Instruction database utilities
│   ├── instructions.py             # Instruction definitions
│   ├── parsing.py                  # Parsing utilities (parse_address_value)
│   ├── progress.py                 # Progress indicators
│   ├── registers.py                # Register utilities (decode_flags)
│   ├── syntax.py                   # Syntax highlighting
│   └── table.py                    # Table formatting utilities
│
├── commands/                       # Command implementations
│   ├── __init__.py
│   │
│   ├── benchmark/                  # --benchmark
│   │   ├── __init__.py
│   │   └── benchmark.py            # run_benchmark_mode()
│   │
│   ├── coverage/                   # --coverage
│   │   ├── __init__.py
│   │   └── coverage.py             # run_coverage_mode()
│   │
│   ├── debug/                      # --debug
│   │   ├── __init__.py
│   │   └── debugger.py             # run_debug_mode()
│   │
│   ├── diff/                       # --diff
│   │   ├── __init__.py
│   │   └── diffing.py              # run_diff_mode()
│   │
│   ├── disassemble/                # -d, --disassemble
│   │   ├── __init__.py
│   │   └── disasm.py               # disassemble_instruction(), get_instruction_cycles()
│   │
│   ├── export/                     # -x, --export-hex, --hex-format
│   │   ├── __init__.py
│   │   └── hex_export.py           # export_hex()
│   │
│   ├── learning/                   # Learning & documentation commands
│   │   ├── __init__.py
│   │   ├── cheat_sheet.py          # --cheat-sheet - export_cheat_sheet()
│   │   ├── explain.py              # --explain-instr, -e - explain_instruction()
│   │   └── repl.py                 # --repl - InteractiveREPL class
│   │
│   ├── memory/                     # Memory inspection commands
│   │   ├── __init__.py
│   │   └── memory_map.py           # --memory-map - visualize_memory_map()
│   │
│   ├── profile/                    # --profile
│   │   ├── __init__.py
│   │   └── profiler.py             # run_profiler_mode()
│   │
│   ├── symbols/                    # --symbols
│   │   ├── __init__.py
│   │   └── symbols.py              # explore_symbols(), list_symbols_summary()
│   │
│   ├── templates/                  # Template management
│   │   ├── __init__.py
│   │   └── templates.py            # --list-templates, --new-from-template, --template-wizard
│   │
│   └── warnings/                   # -W, --warnings
│       ├── __init__.py
│       └── analysis.py             # analyze_warnings()
│
└── tests/                          # Test files
    └── ...
```

## Command Categories

### Execution Modes (handled inline in `cli.py`)
- `-s, --step` - Step-by-step trace
- `-t, --table` - Table format output
- `-e, --explain` - Mathematical explanations
- `-w, --auto, --watch-file` - Auto-reload/watch mode

### Display Options (handled inline in `cli.py`)
- `-r, --registers` - Show final register state
- `-H, --highlight` - Highlight register changes
- `-b, --binary` - Binary display format
- `-v, --verbose` - Verbose error output
- `--base` - Number format (hex/dec/bin)

### Memory Inspection (handled inline in `cli.py`)
- `-m, --memory RANGE` - Display memory range
- `-S, --stack` - Display stack contents
- `--show-changes` - List memory changes
- `--watch ADDRS` - Watch specific addresses
- `--memory-map` - Visual memory map (uses `commands/memory/memory_map.py`)

### Advanced Options (handled inline in `cli.py`)
- `-u, --unsafe` - Remove/adjust step limit
- `-c, --clock` - CPU clock speed simulation

### Standalone Commands (in `commands/` directories)
Each standalone command has its own directory with:
- `__init__.py` - Exports the command's public API
- Implementation file(s) - Contains the command logic

## Import Structure

### From CLI Code

```python
# Import shared utilities
from .shared import (
    Colors,
    assemble_or_exit,
    decode_flags,
    emu8085,
    load_config,
    load_source_file,
    parse_address_value,
    print_full_help,
    print_short_help,
    resolve_step_limit,
)
from .shared.constants import DEFAULT_BENCHMARK_RUNS, PROFILER_DEFAULT_TOP_N

# Import commands
from .commands import (
    InteractiveREPL,
    analyze_warnings,
    create_from_template,
    disassemble_instruction,
    explain_instruction,
    explain_instruction_detailed,
    explore_symbols,
    export_cheat_sheet,
    export_hex,
    get_instruction_cycles,
    get_instruction_description,
    interactive_template_selector,
    list_symbols_summary,
    list_templates,
    run_benchmark_mode,
    run_coverage_mode,
    run_debug_mode,
    run_diff_mode,
    run_profiler_mode,
    visualize_memory_map,
)
```

### From Command Modules

Commands can import from shared:

```python
from ..shared import Colors, emu8085, assemble_or_exit
from ..shared.constants import SOME_CONSTANT
```

## Design Principles

1. **Separation of Concerns**: Each command has its own directory and is self-contained
2. **Shared Core**: Common utilities (assembler, emulator, colors, parsing) are in `shared/`
3. **Clean Imports**: All commands export through `__init__.py` for clean imports in `cli.py`
4. **Inline Display Logic**: Simple display flags (-r, -b, -H, etc.) remain in `cli.py` to avoid over-engineering
5. **Standalone Commands**: Complex commands with significant logic get their own directory

## Adding New Commands

To add a new command:

1. Create directory: `commands/mycommand/`
2. Add `__init__.py` that exports the command's public API
3. Implement command in `commands/mycommand/mycommand.py`
4. Update `commands/__init__.py` to export from your new command
5. Import and use in `cli.py`

Example:

```python
# commands/mycommand/__init__.py
from .mycommand import run_my_command
__all__ = ["run_my_command"]

# commands/__init__.py
from .mycommand import run_my_command
# Add to __all__

# cli.py
from .commands import run_my_command
# Use in main()
```

## Migration Notes

The structure was reorganized from a flat directory to a hierarchical one:

- **Old**: All files in `asm8085_cli/` root
- **New**: Organized into `shared/` and `commands/` subdirectories

All imports have been updated to reflect the new structure. The old files remain in place for now but should be removed once testing confirms the new structure works.