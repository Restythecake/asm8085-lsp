"""
8085 Assembly Language Server Protocol (LSP) implementation.

This package provides a complete LSP server for 8085 assembly language
with support for:
- Real-time diagnostics (syntax errors, undefined labels)
- Code completion (instructions, registers, labels)
- Hover documentation (detailed instruction information)
- Go-to-definition (jump to label definitions)
- Document symbols (outline view of labels)
- Signature help (parameter hints)

The server is designed to work with any LSP-compatible editor.
"""

__version__ = "0.2.1"
__author__ = "Resty"

from .server import LSPServer, main

__all__ = [
    "LSPServer",
    "main",
    "__version__",
]
