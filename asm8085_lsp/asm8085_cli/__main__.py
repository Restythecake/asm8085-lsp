"""Entry point for running asm8085_cli as a module.

This allows the package to be executed with:
    python -m asm8085_lsp.asm8085_cli [args]
"""

from .cli import main

if __name__ == "__main__":
    main()
