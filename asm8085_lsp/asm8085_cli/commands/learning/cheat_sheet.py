"""Cheat sheet generator for 8085 instruction set reference."""

import sys
from datetime import datetime
from pathlib import Path

from ...shared.instruction_db import INSTRUCTION_DB

instruction_db = INSTRUCTION_DB


def _format_opcode(info: dict) -> str:
    pattern = info.get("opcode_base") or info.get("opcode") or "varies"
    example = info.get("example_opcode")
    return f"{pattern} ({example})" if example else pattern


def _format_cycles(value) -> str:
    if isinstance(value, dict):
        parts = [f"{k}: {v}T" for k, v in value.items()]
        return ", ".join(parts)
    return str(value) if value else "varies"


def generate_markdown_cheat_sheet() -> str:
    """Generate Markdown format cheat sheet.

    Returns:
        Markdown-formatted instruction reference
    """
    lines = []

    # Header
    lines.append("# 8085 Instruction Set Reference")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of contents by category
    categories = {}
    for opcode, info in instruction_db.items():
        cat = info.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(opcode)

    lines.append("## Categories")
    lines.append("")
    for cat in sorted(categories.keys()):
        lines.append(f"- [{cat}](#{cat.lower().replace(' ', '-')})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Instructions by category
    for cat in sorted(categories.keys()):
        lines.append(f"## {cat}")
        lines.append("")

        for opcode in sorted(categories[cat]):
            info = instruction_db[opcode]
            lines.append(f"### {opcode} - {info['name']}")
            lines.append("")
            lines.append(f"**Opcode**: `{_format_opcode(info)}`  ")
            lines.append(f"**Size**: {info['size']} bytes  ")
            lines.append(f"**Cycles**: {_format_cycles(info.get('cycles'))}  ")
            lines.append(f"**Flags**: {info['flags']}  ")
            lines.append("")
            lines.append(f"**Description**: {info['description']}")
            lines.append("")
            lines.append(f"**Syntax**: `{info['syntax']}`")
            lines.append("")
            lines.append("**Example**:")
            lines.append("```asm")
            lines.append(info["example"])
            lines.append("```")
            lines.append("")
            if info.get("notes"):
                lines.append(f"*Note: {info['notes']}*")
                lines.append("")
            related = info.get("related") or []
            lines.append(f"**Related**: {', '.join(related)}")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def generate_html_cheat_sheet() -> str:
    """Generate HTML format cheat sheet with styling.

    Returns:
        HTML-formatted instruction reference
    """
    lines = []

    # HTML header with CSS
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="en">')
    lines.append("<head>")
    lines.append('  <meta charset="UTF-8">')
    lines.append(
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    )
    lines.append("  <title>8085 Instruction Set Reference</title>")
    lines.append("  <style>")
    lines.append("""
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
      color: #333;
    }
    header {
      background: #2c3e50;
      color: white;
      padding: 30px;
      border-radius: 8px;
      margin-bottom: 30px;
    }
    h1 {
      margin: 0;
      font-size: 2.5em;
    }
    .timestamp {
      opacity: 0.7;
      margin-top: 10px;
    }
    .toc {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 30px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .toc h2 {
      margin-top: 0;
    }
    .toc ul {
      list-style: none;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }
    .toc a {
      color: #3498db;
      text-decoration: none;
      padding: 8px 12px;
      border-radius: 4px;
      display: block;
      transition: background 0.2s;
    }
    .toc a:hover {
      background: #ecf0f1;
    }
    .category {
      margin-bottom: 40px;
    }
    .category h2 {
      background: #34495e;
      color: white;
      padding: 15px 20px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    .instruction {
      background: white;
      padding: 20px;
      margin-bottom: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .instruction h3 {
      margin-top: 0;
      color: #2c3e50;
      border-bottom: 2px solid #3498db;
      padding-bottom: 10px;
    }
    .meta {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin: 15px 0;
      padding: 15px;
      background: #ecf0f1;
      border-radius: 4px;
    }
    .meta-item {
      display: flex;
      flex-direction: column;
    }
    .meta-label {
      font-weight: bold;
      color: #7f8c8d;
      font-size: 0.9em;
      text-transform: uppercase;
    }
    .meta-value {
      color: #2c3e50;
      font-family: 'Courier New', monospace;
    }
    .description {
      margin: 15px 0;
      line-height: 1.6;
    }
    .syntax {
      background: #2c3e50;
      color: #2ecc71;
      padding: 10px 15px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      margin: 15px 0;
    }
    .example {
      background: #2c3e50;
      color: #ecf0f1;
      padding: 15px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      margin: 15px 0;
      white-space: pre;
      overflow-x: auto;
    }
    .note {
      background: #fff3cd;
      border-left: 4px solid #ffc107;
      padding: 10px 15px;
      margin: 15px 0;
      border-radius: 4px;
    }
    .related {
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid #ecf0f1;
      color: #7f8c8d;
      font-size: 0.9em;
    }
    @media print {
      body { background: white; }
      .instruction { break-inside: avoid; }
    }
    """)
    lines.append("  </style>")
    lines.append("</head>")
    lines.append("<body>")

    # Header
    lines.append("  <header>")
    lines.append("    <h1>8085 Instruction Set Reference</h1>")
    lines.append(
        f'    <div class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>'
    )
    lines.append("  </header>")

    # Table of contents
    categories = {}
    for opcode, info in instruction_db.items():
        cat = info.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(opcode)

    lines.append('  <div class="toc">')
    lines.append("    <h2>Categories</h2>")
    lines.append("    <ul>")
    for cat in sorted(categories.keys()):
        cat_id = cat.lower().replace(" ", "-")
        lines.append(f'      <li><a href="#{cat_id}">{cat}</a></li>')
    lines.append("    </ul>")
    lines.append("  </div>")

    # Instructions by category
    for cat in sorted(categories.keys()):
        cat_id = cat.lower().replace(" ", "-")
        lines.append(f'  <div class="category" id="{cat_id}">')
        lines.append(f"    <h2>{cat}</h2>")

        for opcode in sorted(categories[cat]):
            info = instruction_db[opcode]
            lines.append('    <div class="instruction">')
            lines.append(f"      <h3>{opcode} - {info['name']}</h3>")

            # Metadata
            lines.append('      <div class="meta">')
            lines.append('        <div class="meta-item">')
            lines.append('          <span class="meta-label">Opcode</span>')
            lines.append(
                f'          <span class="meta-value">{_format_opcode(info)}</span>'
            )
            lines.append("        </div>")
            lines.append('        <div class="meta-item">')
            lines.append('          <span class="meta-label">Size</span>')
            lines.append(
                f'          <span class="meta-value">{info["size"]} bytes</span>'
            )
            lines.append("        </div>")
            lines.append('        <div class="meta-item">')
            lines.append('          <span class="meta-label">Cycles</span>')
            lines.append(
                f'          <span class="meta-value">{_format_cycles(info.get("cycles"))}</span>'
            )
            lines.append("        </div>")
            lines.append('        <div class="meta-item">')
            lines.append('          <span class="meta-label">Flags</span>')
            lines.append(f'          <span class="meta-value">{info["flags"]}</span>')
            lines.append("        </div>")
            lines.append("      </div>")

            # Description
            lines.append(f'      <div class="description">{info["description"]}</div>')

            # Syntax
            lines.append(f'      <div class="syntax">{info["syntax"]}</div>')

            # Example
            lines.append(f'      <div class="example">{info["example"]}</div>')

            # Note
            if info.get("notes"):
                lines.append(f'      <div class="note">💡 {info["notes"]}</div>')

            # Related
            related = ", ".join(info.get("related") or [])
            lines.append(f'      <div class="related">Related: {related}</div>')

            lines.append("    </div>")

        lines.append("  </div>")

    # Footer
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def export_cheat_sheet(format_type: str, output_file: str):
    """Export instruction set cheat sheet to file.

    Args:
        format_type: Output format ('markdown' or 'html')
        output_file: Path to output file
    """
    output_path = Path(output_file)

    if format_type == "markdown":
        content = generate_markdown_cheat_sheet()
        if not output_path.suffix:
            output_path = output_path.with_suffix(".md")
    elif format_type == "html":
        content = generate_html_cheat_sheet()
        if not output_path.suffix:
            output_path = output_path.with_suffix(".html")
    else:
        print(f"Error: Unknown format '{format_type}'. Use 'markdown' or 'html'.")
        sys.exit(1)

    # Write to file
    try:
        output_path.write_text(content, encoding="utf-8")
        print(f"✓ Cheat sheet exported to: {output_path}")
        print(f"  Format: {format_type.upper()}")
        print(f"  Instructions: {len(instruction_db)}")
    except Exception as e:
        print(f"✗ Error writing file: {e}")
        sys.exit(1)
