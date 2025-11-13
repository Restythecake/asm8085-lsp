"""Disassembly command for 8085 assembly programs."""

from ...shared.disasm import (
    disassemble_instruction,
    get_instruction_cycles,
    get_instruction_description,
)

__all__ = [
    "disassemble_instruction",
    "get_instruction_cycles",
    "get_instruction_description",
]
