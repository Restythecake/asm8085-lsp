#!/usr/bin/env python3
"""Generate the JSON version of the instruction metadata used by the LSP."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    lsp_dir = repo_root / "lsp"

    instruction_db_path = lsp_dir / "asm8085_cli" / "instruction_db.py"
    spec = spec_from_file_location("asm8085_cli.instruction_db", instruction_db_path)
    if spec is None or spec.loader is None:  # pragma: no cover - build-time script
        raise SystemExit(
            f"Unable to load instruction DB module from {instruction_db_path}"
        )

    instruction_db_module = module_from_spec(spec)
    sys.modules[spec.name] = instruction_db_module
    spec.loader.exec_module(instruction_db_module)
    try:
        INSTRUCTION_DB = instruction_db_module.INSTRUCTION_DB
    except AttributeError as exc:  # pragma: no cover - build-time script
        raise SystemExit(f"Instruction DB missing in module: {exc}") from exc

    output_path = lsp_dir / "asm8085_cli" / "instruction_db.json"
    output_path.write_text(
        json.dumps(INSTRUCTION_DB, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
