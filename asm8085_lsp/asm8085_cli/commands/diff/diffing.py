"""Program diffing utilities."""

import os
import sys

from ...shared import emu8085
from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors
from ...shared.executor import resolve_step_limit
from ...shared.registers import (
    compute_register_differences,
    format_register_summary,
    snapshot_registers,
)
from ..disassemble.disasm import disassemble_instruction, get_instruction_cycles


def simulate_program(filename, args):
    """Assemble and execute a program, capturing register state after each step."""
    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    cpu = emu8085()
    for i, byte_val in enumerate(asm_obj.pmemory):
        cpu.memory[i].value = byte_val
    cpu.PC.value = asm_obj.ploadoff

    max_steps, _ = resolve_step_limit(args)
    steps = []
    total_cycles = 0

    while not cpu.haulted and len(steps) < max_steps:
        current_pc = cpu.PC.value
        instr, _ = disassemble_instruction(cpu.memory, current_pc)
        cycles = get_instruction_cycles(cpu.memory, current_pc)
        cpu.runcrntins()
        total_cycles += cycles

        steps.append(
            {
                "pc": current_pc,
                "instr": instr,
                "cycles": cycles,
                "regs": snapshot_registers(cpu),
            }
        )

    reached_limit = (
        (not cpu.haulted) and (len(steps) >= max_steps) and (max_steps != float("inf"))
    )

    return {
        "steps": steps,
        "halted": cpu.haulted,
        "reached_limit": reached_limit,
        "total_cycles": total_cycles,
        "final_regs": snapshot_registers(cpu),
        "pload": asm_obj.ploadoff,
    }


def format_diff_step(label, step, is_different=False):
    """Return a formatted diff row for a specific program."""
    if not step:
        return f"{Colors.DIM}{label:<16}{Colors.RESET} {Colors.DIM}<< halted >>{Colors.RESET}"

    # Use different colors for different instructions
    indicator = "▸" if is_different else " "
    color = Colors.GREEN if is_different else Colors.RESET

    return (
        f"{color}{indicator} {Colors.BOLD}{label:<15}{Colors.RESET} "
        f"{Colors.CYAN}{step['pc']:04X}{Colors.RESET}  "
        f"{color}{step['instr']:<20}{Colors.RESET}  {format_register_summary(step['regs'])}"
    )


def format_table_row(step_num, step, width=42):
    """Format a single table row for diff mode.

    Args:
        step_num: Step number
        step: Step data dict or None
        width: Total width the row should occupy (default 42 to match header)
    """
    if not step:
        halted_msg = "<< halted >>"
        # Pad to exact width
        content = f"{step_num:<4} {halted_msg}"
        return f"{content:<{width}}"

    regs = step["regs"]
    # Decode flags from FLAGS byte value
    from .registers import decode_flags

    flags = decode_flags(regs["FLAGS"])
    flags_str = (
        f"{'S' if flags['S'] else '-'}"
        f"{'Z' if flags['Z'] else '-'}"
        f"{'A' if flags['AC'] else '-'}"
        f"{'P' if flags['P'] else '-'}"
        f"{'C' if flags['CY'] else '-'}"
    )

    # Format matching header: Step PC Instruction A B C Flags T
    # Without color codes, this should be exactly 42 chars
    row = (
        f"{step_num:<4} "
        f"{Colors.CYAN}{step['pc']:04X}{Colors.RESET} "
        f"{step['instr']:<14} "
        f"{regs['A']:02X} {regs['B']:02X} {regs['C']:02X} "
        f"{flags_str:<5} "
        f"{Colors.DIM}{step['cycles']:>2}{Colors.RESET}"
    )
    return row


def highlight_differences(step_a, step_b, row_a, row_b):
    """Add color highlighting for differences between two steps."""
    if not step_a or not step_b:
        return row_a, row_b

    # Check if instructions differ
    if step_a["instr"] != step_b["instr"]:
        # Highlight entire rows in yellow
        row_a = f"{Colors.YELLOW}{row_a}{Colors.RESET}"
        row_b = f"{Colors.YELLOW}{row_b}{Colors.RESET}"
        return row_a, row_b

    # Check for register differences
    regs_a = step_a["regs"]
    regs_b = step_b["regs"]

    has_diff = False
    for reg in ["A", "B", "C", "D", "E", "H", "L"]:
        if regs_a[reg] != regs_b[reg]:
            has_diff = True
            break

    if not has_diff and regs_a["FLAGS"] != regs_b["FLAGS"]:
        has_diff = True

    if has_diff:
        # Subtle highlight for register differences
        row_a = f"{Colors.GREEN}{row_a}{Colors.RESET}"
        row_b = f"{Colors.GREEN}{row_b}{Colors.RESET}"

    return row_a, row_b


def run_diff_mode(file_a, file_b, args):
    """Compare two programs using side-by-side tables (like -t mode)."""
    for path in (file_a, file_b):
        if not os.path.exists(path):
            print(f"{Colors.RED}✗ Error:{Colors.RESET} File '{path}' not found")
            sys.exit(1)

    label_a = os.path.basename(file_a)
    label_b = os.path.basename(file_b)

    # Simulate both programs
    trace_a = simulate_program(file_a, args)
    trace_b = simulate_program(file_b, args)

    steps_a = trace_a["steps"]
    steps_b = trace_b["steps"]
    max_steps = max(len(steps_a), len(steps_b))

    if max_steps == 0:
        print(f"{Colors.DIM}No instructions executed in either program.{Colors.RESET}")
        return

    # Print header
    divider = "│"
    # Calculate exact width from header format
    header = f"{'Step':<4} {'PC':<4} {'Instruction':<14} {'A':<2} {'B':<2} {'C':<2} {'Flags':<5} {'T':>2}"
    header_width = len(header)  # Should be 42

    print(
        f"\n{Colors.BLUE}{Colors.BOLD}{'─' * header_width} {divider} {'─' * header_width}{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD}{label_a:^{header_width}}{Colors.RESET} {divider} {Colors.BOLD}{label_b:^{header_width}}{Colors.RESET}"
    )
    print(
        f"{Colors.BLUE}{Colors.BOLD}{'─' * header_width} {divider} {'─' * header_width}{Colors.RESET}"
    )

    # Table headers
    print(
        f"{Colors.BOLD}{header}{Colors.RESET} {divider} {Colors.BOLD}{header}{Colors.RESET}"
    )
    print(
        f"{Colors.DIM}{'─' * header_width} {divider} {'─' * header_width}{Colors.RESET}"
    )

    # Print rows
    diff_count = 0
    for idx in range(max_steps):
        step_num = idx + 1
        step_a = steps_a[idx] if idx < len(steps_a) else None
        step_b = steps_b[idx] if idx < len(steps_b) else None

        row_a = format_table_row(step_num, step_a, header_width)
        row_b = format_table_row(step_num, step_b, header_width)

        # Highlight differences
        row_a, row_b = highlight_differences(step_a, step_b, row_a, row_b)

        # Track differences
        if step_a and step_b:
            if step_a["instr"] != step_b["instr"] or step_a["regs"] != step_b["regs"]:
                diff_count += 1

        print(f"{row_a} {divider} {row_b}")

    # Table footer
    print(
        f"{Colors.BLUE}{Colors.BOLD}{'─' * header_width} {divider} {'─' * header_width}{Colors.RESET}"
    )

    def summarize(label, trace):
        status_icon = "✓" if trace["halted"] else "⚠"
        status_color = Colors.GREEN if trace["halted"] else Colors.YELLOW
        status = "halted" if trace["halted"] else "not halted"
        if trace["reached_limit"]:
            status += " (hit step cap)"
            status_color = Colors.YELLOW
        return (
            f"  {status_color}{status_icon}{Colors.RESET} {Colors.BOLD}{label:<20}{Colors.RESET} "
            f"{Colors.CYAN}{len(trace['steps']):>4}{Colors.RESET} steps  "
            f"{Colors.CYAN}{trace['total_cycles']:>5}{Colors.RESET} T-states  "
            f"{Colors.DIM}{status}{Colors.RESET}"
        )

    # Summary section
    print(f"\n{Colors.BLUE}{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

    # Create summary table
    summary_line_a = summarize(label_a, trace_a)
    summary_line_b = summarize(label_b, trace_b)

    print(summary_line_a)
    print(summary_line_b)

    # Calculate deltas
    step_diff = len(trace_b["steps"]) - len(trace_a["steps"])
    cycle_diff = trace_b["total_cycles"] - trace_a["total_cycles"]

    # Show differences
    if diff_count > 0:
        print(f"\n{Colors.YELLOW}≠ {diff_count} step(s) with differences{Colors.RESET}")

    if step_diff != 0 or cycle_diff != 0:
        print(f"\n{Colors.BLUE}{Colors.BOLD}Performance Comparison:{Colors.RESET}")
        if step_diff != 0:
            sign = "+" if step_diff > 0 else ""
            color = Colors.RED if step_diff > 0 else Colors.GREEN
            print(f"  Steps:   {label_b} {color}{sign}{step_diff}{Colors.RESET}")
        if cycle_diff != 0:
            sign = "+" if cycle_diff > 0 else ""
            color = Colors.RED if cycle_diff > 0 else Colors.GREEN
            speedup = (
                abs(trace_a["total_cycles"] / trace_b["total_cycles"])
                if cycle_diff < 0
                else abs(trace_b["total_cycles"] / trace_a["total_cycles"])
            )
            print(
                f"  Cycles:  {label_b} {color}{sign}{cycle_diff}{Colors.RESET} "
                f"({speedup:.2f}x {'faster' if cycle_diff < 0 else 'slower'})"
            )

    final_diffs = compute_register_differences(
        trace_a["final_regs"], trace_b["final_regs"]
    )
    if final_diffs:
        print(
            f"\n{Colors.YELLOW}{Colors.BOLD}Final Register Differences:{Colors.RESET}"
        )
        for diff in final_diffs:
            print(f"  {diff}")
    else:
        print(f"\n{Colors.GREEN}✓ Final registers match{Colors.RESET}")

    if trace_a["reached_limit"] or trace_b["reached_limit"]:
        print(
            f"\n{Colors.DIM}Tip: Use --unsafe or --unsafe <N> to adjust the step limit for longer programs.{Colors.RESET}"
        )
