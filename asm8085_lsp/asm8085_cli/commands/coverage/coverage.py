"""Coverage reporting utilities."""

import contextlib
import os
import sys

from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors
from ...shared.executor import ProgramExecutor, resolve_step_limit
from ...shared.progress import spinner
from ...shared.syntax import CONDITIONAL_BRANCHES, strip_label_prefix


def is_conditional_line(line_text):
    stripped = strip_label_prefix(line_text).strip().upper()
    if not stripped:
        return False
    mnemonic = stripped.split()[0]
    return mnemonic in CONDITIONAL_BRANCHES


def build_line_coverage_maps(asm_obj, clean_lines):
    addr_to_line = {}
    executable_lines = set()
    conditional_lines = set()
    for idx, line in enumerate(clean_lines):
        line_num = idx + 1
        size = asm_obj.plsize[idx] if idx < len(asm_obj.plsize) else 0
        if size <= 0:
            continue
        if idx >= len(asm_obj.poffset):
            continue
        start_addr = asm_obj.poffset[idx]
        executable_lines.add(line_num)
        for disp in range(size):
            addr_to_line[start_addr + disp] = line_num
        if is_conditional_line(line):
            conditional_lines.add(line_num)
    return addr_to_line, executable_lines, conditional_lines


def group_line_ranges(lines):
    if not lines:
        return []
    lines = sorted(lines)
    ranges = []
    start = prev = lines[0]
    for line in lines[1:]:
        if line == prev + 1:
            prev = line
            continue
        ranges.append((start, prev))
        start = prev = line
    ranges.append((start, prev))
    return ranges


class CoverageTracker:
    def __init__(
        self, addr_to_line, executable_lines, conditional_lines, line_text_map
    ):
        self.addr_to_line = addr_to_line
        self.executable_lines = set(executable_lines)
        self.conditional_lines = set(conditional_lines)
        self.line_text_map = line_text_map
        self.lines_hit = set()
        self.branch_outcomes = {
            line: {"taken": False, "not_taken": False}
            for line in self.conditional_lines
        }

    def record(self, step_result):
        line = self.addr_to_line.get(step_result["pc"])
        if line:
            self.lines_hit.add(line)
            if line in self.branch_outcomes:
                if step_result["branch_taken"]:
                    self.branch_outcomes[line]["taken"] = True
                else:
                    self.branch_outcomes[line]["not_taken"] = True

    def stats(self):
        total_lines = len(self.executable_lines)
        hit_lines = len(self.lines_hit)
        line_pct = (hit_lines / total_lines * 100) if total_lines else 100

        total_branch_outcomes = len(self.branch_outcomes) * 2
        covered_outcomes = 0
        for flags in self.branch_outcomes.values():
            covered_outcomes += int(flags["taken"])
            covered_outcomes += int(flags["not_taken"])
        branch_pct = (
            covered_outcomes / total_branch_outcomes * 100
            if total_branch_outcomes
            else 100
        )

        uncovered_lines = sorted(self.executable_lines - self.lines_hit)
        incomplete_branches = [
            (line, flags)
            for line, flags in sorted(self.branch_outcomes.items())
            if not (flags["taken"] and flags["not_taken"])
        ]

        return {
            "line_total": total_lines,
            "line_hit": hit_lines,
            "line_pct": line_pct,
            "branch_total": total_branch_outcomes,
            "branch_hit": covered_outcomes,
            "branch_pct": branch_pct,
            "uncovered_lines": uncovered_lines,
            "incomplete_branches": incomplete_branches,
        }

    def report(self):
        stats = self.stats()
        print(f"{Colors.BLUE}{Colors.BOLD}Coverage Report{Colors.RESET}")
        if stats["line_total"]:
            print(
                f"  Lines executed: {stats['line_hit']}/{stats['line_total']} "
                f"({stats['line_pct']:.1f}%)"
            )
        else:
            print("  Lines executed: n/a (no executable lines)")

        if stats["branch_total"]:
            print(
                f"  Branch outcomes: {stats['branch_hit']}/{stats['branch_total']} "
                f"({stats['branch_pct']:.1f}%)"
            )
        else:
            print("  Branch outcomes: n/a (no conditional branches)")

        uncovered = stats["uncovered_lines"]
        print("\nUncovered code:")
        if not uncovered:
            print("  (all executable lines covered)")
        else:
            for start, end in group_line_ranges(uncovered):
                label = f"Line {start}" if start == end else f"Line {start}-{end}"
                text = self.line_text_map.get(start, "").strip()
                preview = f": {text}" if text else ""
                print(f"  {label}{preview}")

        missing = stats["incomplete_branches"]
        if missing:
            print("\nBranches missing outcomes:")
            for line, flags in missing:
                outcomes = []
                if not flags["taken"]:
                    outcomes.append("taken")
                if not flags["not_taken"]:
                    outcomes.append("not taken")
                text = self.line_text_map.get(line, "").strip()
                preview = f" ({text})" if text else ""
                print(
                    f"  Line {line}: missing {', '.join(outcomes)} outcome(s){preview}"
                )

    def export_html(self, filename, source_filename):
        """Export coverage report as HTML with syntax highlighting"""
        stats = self.stats()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>8085 Coverage Report - {source_filename}</title>
    <style>
        body {{
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            margin: 0;
        }}
        .header {{
            background: #252526;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #4fc3f7;
        }}
        .stats {{
            font-size: 14px;
            color: #a0a0a0;
        }}
        .stats-bar {{
            background: #333;
            height: 30px;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .stats-fill {{
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        pre {{
            background: #252526;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 0;
            line-height: 1.5;
        }}
        .line {{
            display: block;
            padding: 2px 8px;
            border-left: 3px solid transparent;
        }}
        .line-num {{
            display: inline-block;
            width: 50px;
            color: #858585;
            text-align: right;
            margin-right: 15px;
            user-select: none;
        }}
        .covered {{
            background: rgba(76, 175, 80, 0.15);
            border-left-color: #4caf50;
        }}
        .uncovered {{
            background: rgba(244, 67, 54, 0.15);
            border-left-color: #f44336;
        }}
        .non-executable {{
            color: #666;
        }}
        .partial {{
            background: rgba(255, 193, 7, 0.15);
            border-left-color: #ffc107;
        }}
        .legend {{
            margin: 20px 0;
            padding: 15px;
            background: #252526;
            border-radius: 8px;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>8085 Coverage Report</h1>
        <div class="stats">
            <strong>File:</strong> {source_filename}<br>
            <strong>Line Coverage:</strong> {stats["line_hit"]}/{stats["line_total"]} ({stats["line_pct"]:.1f}%)<br>
            <strong>Branch Coverage:</strong> {stats["branch_hit"]}/{stats["branch_total"]} ({stats["branch_pct"]:.1f}%)
        </div>
        <div class="stats-bar">
            <div class="stats-fill" style="width: {stats["line_pct"]}%">
                {stats["line_pct"]:.1f}%
            </div>
        </div>
    </div>

    <div class="legend">
        <span class="legend-item covered">✓ Covered</span>
        <span class="legend-item uncovered">✗ Not Covered</span>
        <span class="legend-item partial">~ Partially Covered (Branch)</span>
        <span class="legend-item non-executable">◦ Non-Executable</span>
    </div>

    <pre><code>"""

        # Get all lines from source
        all_lines = sorted(
            set(self.line_text_map.keys())
            | self.executable_lines
            | set(self.branch_outcomes.keys())
        )

        for line_num in all_lines:
            text = self.line_text_map.get(line_num, "").rstrip()

            # Determine coverage status
            if line_num not in self.executable_lines:
                css_class = "non-executable"
                marker = "◦"
            elif line_num in self.lines_hit:
                # Check if it's a branch with incomplete coverage
                if line_num in self.branch_outcomes:
                    flags = self.branch_outcomes[line_num]
                    if flags["taken"] and flags["not_taken"]:
                        css_class = "covered"
                        marker = "✓"
                    else:
                        css_class = "partial"
                        marker = "~"
                else:
                    css_class = "covered"
                    marker = "✓"
            else:
                css_class = "uncovered"
                marker = "✗"

            # HTML escape the text
            text_escaped = (
                text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )

            html += f'<span class="line {css_class}">'
            html += f'<span class="line-num">{marker} {line_num:4d}</span>'
            html += text_escaped
            html += "</span>\n"

        html += """</code></pre>
</body>
</html>"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)


def run_coverage_mode(args):
    filename = args.filename
    if not filename:
        raise ValueError("Coverage mode requires a filename.")
    if not os.path.exists(filename):
        print(f"{Colors.RED}✗ Error:{Colors.RESET} File '{filename}' not found")
        sys.exit(1)

    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)
    addr_map, executable_lines, conditional_lines = build_line_coverage_maps(
        asm_obj, clean_lines
    )
    line_text_map = dict(original_lines)

    tracker = CoverageTracker(
        addr_map, executable_lines, conditional_lines, line_text_map
    )
    executor = ProgramExecutor(filename, args)
    limit, has_limit = resolve_step_limit(args)
    steps = 0

    # Show progress for long-running programs
    show_progress = has_limit and limit > 1000
    if show_progress:
        print(f"{Colors.CYAN}Running coverage analysis...{Colors.RESET}")

    with (
        spinner("Analyzing coverage", color=True)
        if show_progress
        else contextlib.nullcontext()
    ):
        while not executor.cpu.haulted and (steps < limit):
            result = executor.step_instruction()
            tracker.record(result)
            steps += 1

    if has_limit and (not executor.cpu.haulted) and steps >= limit:
        print(
            f"{Colors.YELLOW}Warning:{Colors.RESET} Program did not halt before step limit "
            f"({int(limit)}). Coverage may be incomplete."
        )

    tracker.report()

    # Export HTML coverage report
    html_filename = f"{os.path.splitext(filename)[0]}_coverage.html"
    tracker.export_html(html_filename, os.path.basename(filename))
    print(
        f"\n{Colors.GREEN}✓ HTML coverage report saved:{Colors.RESET} {html_filename}"
    )
