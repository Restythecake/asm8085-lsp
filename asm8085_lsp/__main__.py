#!/usr/bin/env python3
"""
Entry point for the 8085 Assembly Language Server.

This module allows the LSP to be run as a package:
    python -m asm8085_lsp
"""

from .server import main

if __name__ == "__main__":
    main()
