"""asm8085 CLI package initialization.

This package contains the assembler and emulator for 8085 assembly programs.
The emu module is included as part of this package for self-contained distribution.
"""

from .shared.emu import assembler, emu8085
from .shared.instruction_db import (
    INSTRUCTION_DB,  # Ensure metadata ships with the LSP bundle
)

__all__ = ["assembler", "emu8085", "INSTRUCTION_DB"]
__version__ = "0.2.0"
