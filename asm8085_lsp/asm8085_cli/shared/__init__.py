"""Shared utilities and core components for 8085 assembler and emulator."""

from .assembly import assemble_or_exit, load_source_file
from .colors import Colors
from .config import load_config
from .constants import *
from .disasm import (
    disassemble_instruction,
    get_instruction_cycles,
    get_instruction_description,
)
from .emu import emu8085
from .executor import resolve_step_limit
from .helptext import print_full_help, print_short_help
from .parsing import parse_address_value
from .registers import decode_flags

__all__ = [
    "emu8085",
    "Colors",
    "decode_flags",
    "assemble_or_exit",
    "load_source_file",
    "resolve_step_limit",
    "parse_address_value",
    "print_full_help",
    "print_short_help",
    "load_config",
    "disassemble_instruction",
    "get_instruction_cycles",
    "get_instruction_description",
]
