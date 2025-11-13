"""CLI commands for 8085 assembler and emulator."""

from .benchmark.benchmark import run_benchmark_mode
from .coverage.coverage import run_coverage_mode
from .debug.debugger import run_debug_mode
from .diff.diffing import run_diff_mode
from .disassemble.disasm import (
    disassemble_instruction,
    get_instruction_cycles,
    get_instruction_description,
)
from .export.hex_export import export_hex
from .learning.cheat_sheet import export_cheat_sheet
from .learning.explain import explain_instruction, explain_instruction_detailed
from .learning.repl import InteractiveREPL
from .memory.memory_map import visualize_memory_map
from .profile.profiler import run_profiler_mode
from .symbols.symbols import explore_symbols, list_symbols_summary
from .templates.templates import (
    create_from_template,
    interactive_template_selector,
    list_templates,
)
from .warnings.analysis import analyze_warnings

__all__ = [
    "run_benchmark_mode",
    "run_coverage_mode",
    "run_debug_mode",
    "run_diff_mode",
    "disassemble_instruction",
    "get_instruction_cycles",
    "get_instruction_description",
    "export_hex",
    "export_cheat_sheet",
    "explain_instruction",
    "explain_instruction_detailed",
    "InteractiveREPL",
    "visualize_memory_map",
    "run_profiler_mode",
    "explore_symbols",
    "list_symbols_summary",
    "create_from_template",
    "interactive_template_selector",
    "list_templates",
    "analyze_warnings",
]
