"""Shared helpers for formatting 8085 instruction documentation."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

INCLUDE_HOVER_EXAMPLES = os.getenv("ASM8085_HOVER_EXAMPLES", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@lru_cache(maxsize=1)
def load_instruction_metadata() -> Dict[str, Dict[str, Any]]:
    """Load the detailed instruction database with a JSON-to-Python fallback."""

    db_path = Path(__file__).parent / "asm8085_cli" / "instruction_db.json"
    if db_path.exists():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logging.info(
                "Instruction metadata loaded from JSON DB (%d entries)", len(data)
            )
            return data
        except Exception as exc:
            logging.warning(
                "Failed to parse %s (%s); falling back to Python module",
                db_path.name,
                exc,
            )

    try:
        from asm8085_cli import INSTRUCTION_DB

        logging.info(
            "Instruction metadata loaded from Python module (%d entries)",
            len(INSTRUCTION_DB),
        )
        return INSTRUCTION_DB
    except Exception as exc:
        logging.error("Failed to load instruction metadata: %s", exc, exc_info=True)
        return {}


def format_instruction_doc(opcode: str, info: Dict[str, Any]) -> str:
    """Format instruction metadata into a Markdown hover tooltip."""
    lines = [f"**{info.get('name', opcode)}**"]

    summary = []
    size = info.get("size")
    if size:
        summary.append(f"Size {size} byte{'s' if str(size) != '1' else ''}")

    cycles_text = format_cycle_text(info.get("cycles"))
    if cycles_text:
        summary.append(f"Cycles {cycles_text}")

    flags = info.get("flags")
    if flags and flags.lower() != "none":
        summary.append(f"Flags {flags}")

    opcode_base = info.get("opcode_base")
    if opcode_base:
        summary.append(f"Opcode {opcode_base}")

    if summary:
        lines.append(" • ".join(summary))

    description = info.get("description")
    if description:
        lines.append(description)

    syntax = info.get("syntax")
    if syntax:
        lines.append(f"**Syntax:** `{syntax}`")

    example = info.get("example")
    if INCLUDE_HOVER_EXAMPLES and example:
        lines.append("**Example:**")
        lines.append(f"```asm\n{example}\n```")

    notes = info.get("notes")
    if notes:
        lines.append(f"> {notes}")

    related = info.get("related")
    if related:
        lines.append(f"**Related:** {', '.join(related)}")

    return "\n\n".join(lines)


def format_cycle_text(cycles: Any) -> Optional[str]:
    """Return a human-friendly description of cycle timings."""
    if not cycles:
        return None

    if isinstance(cycles, dict):
        parts = []
        for key, value in cycles.items():
            label = key.replace("_", " ")
            parts.append(f"{label}: {value}")
        return ", ".join(parts)

    return str(cycles)
