#!/usr/bin/env python3
"""Simple command-line assembler and runner for 8085 assembly programs
Usage: asm [-d] <file.asm>
"""

import argparse
import os
import sys
import time

try:
    import readline
except ImportError:
    readline = None

from .commands import (
    InteractiveREPL,
    analyze_warnings,
    create_from_template,
    disassemble_instruction,
    explain_instruction,
    explain_instruction_detailed,
    explore_symbols,
    export_cheat_sheet,
    export_hex,
    get_instruction_cycles,
    get_instruction_description,
    interactive_template_selector,
    list_symbols_summary,
    list_templates,
    run_benchmark_mode,
    run_coverage_mode,
    run_debug_mode,
    run_diff_mode,
    run_profiler_mode,
    visualize_memory_map,
)
from .shared import (
    Colors,
    assemble_or_exit,
    decode_flags,
    emu8085,
    load_config,
    load_source_file,
    parse_address_value,
    print_full_help,
    print_short_help,
    resolve_step_limit,
)
from .shared.constants import DEFAULT_BENCHMARK_RUNS, PROFILER_DEFAULT_TOP_N


def expand_combined_flags(argv):
    """Expand combined short flags like -sr into -s -r"""
    expanded = []

    # Valid single-char flags that can be combined
    valid_flags = {"s", "t", "e", "w", "r", "b", "v", "d", "W", "S", "x", "h", "H"}

    for arg in argv:
        if arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
            # This is a combined flag like -sr
            flags = arg[1:]  # Remove the leading '-'

            # Check if all characters are valid flags
            if all(c in valid_flags for c in flags):
                # Expand into separate flags
                for flag in flags:
                    expanded.append(f"-{flag}")
            else:
                # Not all valid, keep as-is (might be -m, -u, -c with arguments)
                expanded.append(arg)
        else:
            expanded.append(arg)

    return expanded


def main():
    # Expand combined flags first (e.g., -sr -> -s -r)
    sys.argv = expand_combined_flags(sys.argv)

    # Load configuration files
    config = load_config()

    # Check for help flags first
    if "-h" in sys.argv or "--help" in sys.argv:
        if "--help-full" not in sys.argv:
            print_short_help()
            sys.exit(0)

    if "--help-full" in sys.argv:
        print_full_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="8085 assembler and simulator",
        add_help=False,  # We'll handle help manually
    )

    # Add manual help arguments
    parser.add_argument("-h", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--help", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--help-full", action="store_true", help=argparse.SUPPRESS)

    # Positional argument
    parser.add_argument("filename", nargs="?", help=argparse.SUPPRESS)

    # Execution modes
    parser.add_argument("-s", "--step", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-t", "--table", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-e", "--explain", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "-w",
        "--auto",
        "--watch-file",
        action="store_true",
        dest="watch_file",
        help=argparse.SUPPRESS,
    )

    # Debugging & Analysis
    parser.add_argument("--debug", metavar="FILE", help=argparse.SUPPRESS)
    parser.add_argument(
        "--diff", nargs=2, metavar=("FILE_A", "FILE_B"), help=argparse.SUPPRESS
    )
    parser.add_argument("--coverage", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "-W",
        "--warnings",
        action="store_const",
        const=True,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--symbols",
        action="store_true",
        dest="show_symbols",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--benchmark",
        nargs="+",
        metavar="FILE",
        dest="benchmark_files",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--bench-runs",
        type=int,
        default=DEFAULT_BENCHMARK_RUNS,
        metavar="N",
        dest="bench_runs",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        dest="profile",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--profile-top",
        type=int,
        default=PROFILER_DEFAULT_TOP_N,
        metavar="N",
        dest="profile_top",
        help=argparse.SUPPRESS,
    )

    # Display
    parser.add_argument(
        "-r",
        "--registers",
        action="store_const",
        const=True,
        default=None,
        dest="show_registers",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-H",
        "--highlight",
        action="store_const",
        const=True,
        default=None,
        dest="highlight_changes",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-b",
        "--binary",
        action="store_const",
        const=True,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--base", choices=["hex", "dec", "bin"], default="hex", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=True,
        default=None,
        help=argparse.SUPPRESS,
    )

    # Memory
    parser.add_argument(
        "-m", "--memory", type=str, metavar="RANGE", help=argparse.SUPPRESS
    )
    parser.add_argument("-S", "--stack", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--show-changes", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--watch", type=str, metavar="ADDRS", help=argparse.SUPPRESS)
    parser.add_argument("--memory-map", action="store_true", help=argparse.SUPPRESS)

    # Output
    parser.add_argument(
        "-d", "--disassemble", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "-x", "--export-hex", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--hex-format",
        choices=["raw", "intel", "c", "json"],
        default="raw",
        metavar="FMT",
        help=argparse.SUPPRESS,
    )

    # Learning
    parser.add_argument(
        "--explain-instr",
        type=str,
        metavar="INSTR",
        dest="explain_instruction",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--repl", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--cheat-sheet",
        nargs=2,
        metavar=("FORMAT", "OUTPUT"),
        dest="cheat_sheet",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        dest="list_templates",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--new-from-template",
        nargs="+",
        metavar=("TEMPLATE", "OUTPUT"),
        dest="new_template",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--template-wizard",
        action="store_true",
        dest="template_wizard",
        help=argparse.SUPPRESS,
    )

    # Advanced
    parser.add_argument(
        "-u",
        "--unsafe",
        nargs="?",
        const=-1,
        type=int,
        metavar="N",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-c", "--clock", type=float, metavar="MHZ", help=argparse.SUPPRESS
    )

    args = parser.parse_args()

    # Apply configuration file defaults (only for flags not explicitly set by user)
    config.apply_to_args(args)

    # Convert remaining None values to False for boolean flags (after config application)
    # Config may have set these to True or False, so only convert if still None
    if args.highlight_changes is None:
        args.highlight_changes = False
    if args.show_registers is None:
        args.show_registers = False
    if args.binary is None:
        args.binary = False
    if args.verbose is None:
        args.verbose = False
    if args.warnings is None:
        args.warnings = False

    args.memory_auto = False

    # Handle REPL mode
    if args.repl:
        from_repl = InteractiveREPL()
        from_repl.run()
        sys.exit(0)

    if args.debug:
        incompatible = []
        if args.filename:
            incompatible.append("positional filename")
        if args.step:
            incompatible.append("-s/--step")
        if args.table:
            incompatible.append("-t/--table")
        if args.explain:
            incompatible.append("-e/--explain")
        if args.disassemble:
            incompatible.append("-d/--disassemble")
        if args.warnings:
            incompatible.append("-W/--warnings")
        if args.stack:
            incompatible.append("-S/--stack")
        if args.memory:
            incompatible.append("-m/--memory")
        if args.show_changes:
            incompatible.append("--show-changes")
        if args.watch:
            incompatible.append("--watch")
        if args.watch_file:
            incompatible.append("--auto/--watch-file")
        if args.binary:
            incompatible.append("-b/--binary")
        if args.show_registers:
            incompatible.append("-r/--registers")
        if args.explain_instruction:
            incompatible.append("--explain-instr")
        if args.diff:
            incompatible.append("--diff")
        if args.coverage:
            incompatible.append("--coverage")

        if incompatible:
            print(
                f"{Colors.RED}Error:{Colors.RESET} --debug cannot be combined with: {', '.join(incompatible)}"
            )
            sys.exit(1)

        run_debug_mode(args.debug, args)
        return

    if args.diff:
        incompatible = []
        if args.filename:
            incompatible.append("positional filename")
        if args.step:
            incompatible.append("-s/--step")
        if args.table:
            incompatible.append("-t/--table")
        if args.explain:
            incompatible.append("-e/--explain")
        if args.disassemble:
            incompatible.append("-d/--disassemble")
        if args.warnings:
            incompatible.append("-W/--warnings")
        if args.stack:
            incompatible.append("-S/--stack")
        if args.memory:
            incompatible.append("-m/--memory")
        if args.show_changes:
            incompatible.append("--show-changes")
        if args.watch:
            incompatible.append("--watch")
        if args.watch_file:
            incompatible.append("--auto/--watch-file")
        if args.binary:
            incompatible.append("-b/--binary")
        if args.highlight_changes:
            incompatible.append("--highlight")
        if args.show_registers:
            incompatible.append("-r/--registers")
        if args.explain_instruction:
            incompatible.append("--explain-instr")
        if args.coverage:
            incompatible.append("--coverage")

        if incompatible:
            print(
                f"{Colors.RED}Error:{Colors.RESET} --diff cannot be combined with: {', '.join(incompatible)}"
            )
            sys.exit(1)

        run_diff_mode(args.diff[0], args.diff[1], args)
        return

    if args.coverage:
        incompatible = []
        if args.step:
            incompatible.append("-s/--step")
        if args.table:
            incompatible.append("-t/--table")
        if args.explain:
            incompatible.append("-e/--explain")
        if args.disassemble:
            incompatible.append("-d/--disassemble")
        if args.warnings:
            incompatible.append("-W/--warnings")
        if args.stack:
            incompatible.append("-S/--stack")
        if args.memory:
            incompatible.append("-m/--memory")
        if args.show_changes:
            incompatible.append("--show-changes")
        if args.watch:
            incompatible.append("--watch")
        if args.watch_file:
            incompatible.append("--auto/--watch-file")
        if args.binary:
            incompatible.append("-b/--binary")
        if args.highlight_changes:
            incompatible.append("--highlight")
        if args.show_registers:
            incompatible.append("-r/--registers")
        if args.explain_instruction:
            incompatible.append("--explain-instr")
        if args.diff:
            incompatible.append("--diff")
        if args.debug:
            incompatible.append("--debug")

        if incompatible:
            print(
                f"{Colors.RED}Error:{Colors.RESET} --coverage cannot be combined with: {', '.join(incompatible)}"
            )
            sys.exit(1)

        if not args.filename:
            print(f"{Colors.RED}Error:{Colors.RESET} --coverage requires a filename")
            sys.exit(1)

        run_coverage_mode(args)
        return

    # Handle --symbols mode
    if args.show_symbols:
        if not args.filename:
            print(f"{Colors.RED}Error:{Colors.RESET} --symbols requires a filename")
            sys.exit(1)
        explore_symbols(args.filename, args)
        return

    # Handle --benchmark mode
    if args.benchmark_files:
        run_benchmark_mode(args.benchmark_files, args, runs=args.bench_runs)
        return

    # Handle --memory-map mode
    if args.memory_map:
        if not args.filename:
            print(f"{Colors.RED}Error:{Colors.RESET} --memory-map requires a filename")
            sys.exit(1)
        visualize_memory_map(args.filename, args)
        return

    # Handle --profile mode
    if args.profile:
        if not args.filename:
            print(f"{Colors.RED}Error:{Colors.RESET} --profile requires a filename")
            sys.exit(1)
        run_profiler_mode(args.filename, args, top_n=args.profile_top)
        return

    # Validate mutually exclusive options
    mode_count = sum([args.step, args.table, args.explain])
    if mode_count > 1:
        print(
            f"{Colors.RED}Error:{Colors.RESET} Options -s, -t, and -e are mutually exclusive. Use only one."
        )
        sys.exit(1)

    # Handle --explain-instr mode
    if args.explain_instruction:
        explain_instruction_detailed(args.explain_instruction)
        sys.exit(0)

    # Handle --cheat-sheet mode
    if args.cheat_sheet:
        format_type, output_file = args.cheat_sheet
        export_cheat_sheet(format_type, output_file)
        sys.exit(0)

    # Handle --list-templates mode
    if args.list_templates:
        list_templates()
        sys.exit(0)

    # Handle --template-wizard mode
    if args.template_wizard:
        selected = interactive_template_selector()
        if selected:
            output = input("\nEnter output filename: ").strip()
            if output:
                author = input("Author name (optional): ").strip()
                desc = input("Description (optional): ").strip()
                create_from_template(selected, output, author, desc)
        sys.exit(0)

    # Handle --new-from-template mode
    if args.new_template:
        if len(args.new_template) < 2:
            print(
                f"{Colors.RED}Error:{Colors.RESET} --new-from-template requires TEMPLATE and OUTPUT arguments"
            )
            sys.exit(1)
        template_name = args.new_template[0]
        output_file = args.new_template[1]
        author = args.new_template[2] if len(args.new_template) > 2 else ""
        desc = args.new_template[3] if len(args.new_template) > 3 else ""
        if create_from_template(template_name, output_file, author, desc):
            sys.exit(0)
        else:
            sys.exit(1)

    # Back-compat: if -m accidentally consumed filename, recover gracefully
    if not args.filename and args.memory:
        candidate = args.memory
        if os.path.exists(candidate) or candidate.lower().endswith(".asm"):
            args.filename = candidate
            args.memory = None
            args.memory_auto = True

    # Ensure filename is provided for normal operations
    if not args.filename:
        print(f"{Colors.RED}Error:{Colors.RESET} No input file specified")
        print(f"{Colors.BOLD}Usage:{Colors.RESET} asm [OPTIONS] <file.asm>")
        print(f"Try 'asm --help' for more information")
        sys.exit(1)

    # Normalize base argument
    base_map = {"hex": 16, "dec": 10, "bin": 2}
    args.base_num = base_map[args.base]
    filename = args.filename

    if not os.path.exists(filename):
        print(f"{Colors.RED}Error:{Colors.RESET} File '{filename}' not found")
        sys.exit(1)

    # Watch mode: monitor file for changes and re-run
    if args.watch_file:
        print(f"{Colors.BLUE}{Colors.BOLD}Watch Mode Enabled{Colors.RESET}")
        print(f"Monitoring: {Colors.CYAN}{filename}{Colors.RESET}")
        print(f"Press {Colors.YELLOW}Ctrl+C{Colors.RESET} to exit\n")

        last_mtime = 0
        run_count = 0

        try:
            while True:
                current_mtime = os.path.getmtime(filename)

                # File changed or first run
                if current_mtime != last_mtime:
                    run_count += 1
                    last_mtime = current_mtime

                    # Clear screen for clean output
                    os.system("clear" if os.name == "posix" else "cls")

                    # Show header
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"{Colors.BLUE}{'═' * 70}{Colors.RESET}")
                    print(
                        f"{Colors.BLUE}{Colors.BOLD}Run #{run_count} at {timestamp}{Colors.RESET}"
                    )
                    print(f"{Colors.BLUE}File: {Colors.CYAN}{filename}{Colors.RESET}")
                    print(f"{Colors.BLUE}{'═' * 70}{Colors.RESET}\n")

                    # Run the program
                    try:
                        run_program_once(args)
                    except Exception as e:
                        print(f"\n{Colors.RED}Error:{Colors.RESET} {e}")

                    # Show footer
                    print(f"\n{Colors.DIM}{'─' * 70}{Colors.RESET}")
                    print(
                        f"{Colors.DIM}Watching for changes... (Ctrl+C to exit){Colors.RESET}"
                    )

                # Poll every 0.5 seconds
                time.sleep(0.5)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Watch mode stopped.{Colors.RESET}")
            sys.exit(0)
    else:
        # Normal mode: run once
        run_program_once(args)


def run_program_once(args):
    """Execute the assembly program once"""
    filename = args.filename

    clean_lines, original_lines = load_source_file(filename)
    asm = assemble_or_exit(filename, clean_lines, original_lines, args)

    print(
        f"{Colors.GREEN}✓ Assembly successful{Colors.RESET} for {Colors.BOLD}{filename}{Colors.RESET}"
    )
    load_addr = asm.ploadoff
    program_size = sum(asm.writtenaddresses)
    if getattr(args, "memory_auto", False) and not args.memory:
        end_addr = (load_addr + 0x1F) & 0xFFFF
        args.memory = f"{load_addr:04X}-{end_addr:04X}"

    # Check for warnings if enabled
    if args.warnings:
        warnings = analyze_warnings(clean_lines, asm)
        if warnings:
            severity_colors = {
                "error": Colors.RED,
                "warning": Colors.YELLOW,
                "info": Colors.BLUE,
                "hint": Colors.GREEN,
            }
            print(f"\n{Colors.YELLOW}{'─' * 60}{Colors.RESET}")
            print(
                f"{Colors.YELLOW}{Colors.BOLD}⚠ WARNINGS ({len(warnings)} found){Colors.RESET}"
            )
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

            for warning in warnings:
                line_num = (
                    warning.get("line") if isinstance(warning, dict) else warning[0]
                )
                message = (
                    warning.get("message") if isinstance(warning, dict) else warning[2]
                )
                severity = (
                    warning.get("severity") if isinstance(warning, dict) else None
                )
                severity = severity or "warning"
                color = severity_colors.get(severity, Colors.YELLOW)
                label = severity.upper()
                print(f"{color}Line {line_num} [{label}]:{Colors.RESET} {message}")

            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
            print(
                f"{Colors.DIM}Tip: These are suggestions to improve your code, not errors.{Colors.RESET}"
            )

    # Show assembled code with disassembly (if -d flag is used)
    if args.disassemble:
        print(f"\n{Colors.BLUE}{Colors.BOLD}Disassembly:{Colors.RESET}")
        print(
            f"{Colors.DIM}{'ADDR':<6} {'HEX':<12} {'INSTRUCTION':<20} {'CYCLES':<8} DESCRIPTION{Colors.RESET}"
        )
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

        addr = asm.ploadoff
        total_cycles = 0
        instruction_count = 0

        while addr < len(asm.writtenaddresses) and asm.writtenaddresses[addr]:
            # Get instruction
            instr, size = disassemble_instruction(asm.pmemory, addr)

            # Get hex bytes
            hex_bytes = " ".join(f"{asm.pmemory[addr + i]:02X}" for i in range(size))

            # Get cycle count
            cycles = get_instruction_cycles(asm.pmemory, addr)
            total_cycles += cycles

            # Get description
            description = get_instruction_description(instr)

            # Print line
            print(
                f"{Colors.CYAN}{addr:04X}:{Colors.RESET}  {hex_bytes:<12} {instr:<20} {Colors.DIM}{cycles:>2}T{Colors.RESET}     {Colors.DIM}{description}{Colors.RESET}"
            )
            addr += size
            instruction_count += 1

        # Print summary
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
        print(
            f"{Colors.BOLD}Total:{Colors.RESET} {instruction_count} instructions, {Colors.CYAN}{total_cycles}{Colors.RESET} T-states"
        )
        print()

    # Export hex code (if --export-hex flag is used)
    if args.export_hex:
        format_type = args.hex_format
        base_name = os.path.splitext(filename)[0]

        # Determine output filename based on format
        if format_type == "intel":
            output_file = f"{base_name}.hex"
        elif format_type == "c":
            output_file = f"{base_name}.h"
        elif format_type == "json":
            output_file = f"{base_name}.json"
        else:  # raw
            output_file = f"{base_name}.txt"

        try:
            export_hex(asm, output_file, format_type)
            format_names = {
                "raw": "Raw Hex",
                "intel": "Intel HEX",
                "c": "C Array",
                "json": "JSON",
            }
            print(
                f"{Colors.GREEN}✓ Machine code exported:{Colors.RESET} {output_file} ({format_names[format_type]} format)"
            )
            print()
        except Exception as e:
            print(f"{Colors.RED}Error:{Colors.RESET} Failed to export hex: {e}")
            sys.exit(1)

    # Create emulator and load the program
    cpu = emu8085()
    # Copy assembled memory to emulator (pmemory is int array, need to set c_ubyte values)
    for i, byte_val in enumerate(asm.pmemory):
        cpu.memory[i].value = byte_val
    cpu.PC.value = asm.ploadoff

    # Track initial memory state for change detection
    initial_memory = [cpu.memory[i].value for i in range(len(cpu.memory))]

    if args.step:
        print(f"{Colors.DIM}(Step trace mode enabled){Colors.RESET}\n")

    if args.explain:
        print(f"{Colors.DIM}(Mathematical explanation mode enabled){Colors.RESET}\n")

    if args.table:
        print(f"{Colors.DIM}(Table mode enabled){Colors.RESET}\n")
        # Print table header
        print(
            f"{Colors.BLUE}{Colors.BOLD}{'Step':<5} {'PC':<6} {'Instruction':<18} {'A':<3} {'B':<3} {'C':<3} {'D':<3} {'E':<3} {'H':<3} {'L':<3} {'SP':<6} {'Flags':<10} [T]{Colors.RESET}"
        )
        print(f"{Colors.DIM}{'─' * 90}{Colors.RESET}")

    # Determine step limit based on --unsafe flag
    max_steps, has_limit = resolve_step_limit(args)

    steps = 0
    total_cycles = 0

    # Track previous register values for highlighting changes
    prev_regs = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "H": 0, "L": 0, "F": 0}

    # Start real-time measurement
    start_time = time.time()

    # Run until halted or max_steps reached
    while not cpu.haulted and steps < max_steps:
        # Get cycles for current instruction before execution
        cycles = get_instruction_cycles(cpu.memory, cpu.PC.value)

        # Get current instruction for display
        instr, size = disassemble_instruction(cpu.memory, cpu.PC.value)
        current_pc = cpu.PC.value

        # Save CPU state before execution for explanation mode
        if args.explain:
            cpu_before = {
                "A": cpu.A.value,
                "B": cpu.B.value,
                "C": cpu.C.value,
                "D": cpu.D.value,
                "E": cpu.E.value,
                "H": cpu.H.value,
                "L": cpu.L.value,
                "F": cpu.F.value,
                "PC": cpu.PC.value,
                "SP": cpu.SP.value,
            }

        # Show step info if trace mode enabled
        if args.step:
            print(
                f"{Colors.CYAN}Step {steps + 1}:{Colors.RESET} {Colors.BOLD}{current_pc:04X}{Colors.RESET}  {instr}  {Colors.DIM}[{cycles}T]{Colors.RESET}"
            )

        # Save state before execution for highlighting
        if args.step and args.highlight_changes:
            pre_exec_regs = {
                "A": cpu.A.value,
                "B": cpu.B.value,
                "C": cpu.C.value,
                "D": cpu.D.value,
                "E": cpu.E.value,
                "H": cpu.H.value,
                "L": cpu.L.value,
                "F": cpu.F.value,
            }
            pre_exec_instr = disassemble_instruction(cpu.memory, cpu.PC.value)[0]

        cpu.runcrntins()
        steps += 1
        total_cycles += cycles

        # Show mathematical explanation if explain mode enabled
        if args.explain:
            cpu_after = {
                "A": cpu.A.value,
                "B": cpu.B.value,
                "C": cpu.C.value,
                "D": cpu.D.value,
                "E": cpu.E.value,
                "H": cpu.H.value,
                "L": cpu.L.value,
                "F": cpu.F.value,
                "PC": cpu.PC.value,
                "SP": cpu.SP.value,
            }
            explanation = explain_instruction(
                instr, cpu_before, cpu_after, cpu.memory, args.base_num
            )
            if explanation:
                print(
                    f"{Colors.CYAN}{steps:<4}{Colors.RESET} {Colors.BOLD}{current_pc:04X}{Colors.RESET}  {instr:<20} {Colors.DIM}→{Colors.RESET} {Colors.GREEN}{explanation}{Colors.RESET}"
                )

        # Show table row if table mode enabled
        if args.table:
            # Get current register values
            curr_regs = {
                "A": cpu.A.value,
                "B": cpu.B.value,
                "C": cpu.C.value,
                "D": cpu.D.value,
                "E": cpu.E.value,
                "H": cpu.H.value,
                "L": cpu.L.value,
                "F": cpu.F.value,
            }

            # Format flags
            flags = decode_flags(cpu.F.value)
            flags_str = f"{'S' if flags['S'] else '-'}{'Z' if flags['Z'] else '-'}{'-'}{'A' if flags['AC'] else '-'}{'-'}{'P' if flags['P'] else '-'}{'-'}{'C' if flags['CY'] else '-'}"

            # Format registers with optional highlighting
            if args.highlight_changes:
                # Format values first, then add color codes to maintain alignment
                def fmt_reg(val, old_val):
                    val_str = f"{val:02X}"
                    if val != old_val:
                        return f"{Colors.HIGHLIGHT}{val_str}{Colors.RESET}"
                    return val_str

                a_str = fmt_reg(curr_regs["A"], prev_regs["A"])
                b_str = fmt_reg(curr_regs["B"], prev_regs["B"])
                c_str = fmt_reg(curr_regs["C"], prev_regs["C"])
                d_str = fmt_reg(curr_regs["D"], prev_regs["D"])
                e_str = fmt_reg(curr_regs["E"], prev_regs["E"])
                h_str = fmt_reg(curr_regs["H"], prev_regs["H"])
                l_str = fmt_reg(curr_regs["L"], prev_regs["L"])

                # Highlight flags if changed
                flags_display = flags_str
                if curr_regs["F"] != prev_regs["F"]:
                    flags_display = f"{Colors.HIGHLIGHT}{flags_str}{Colors.RESET}"

                # Manual padding for flags to avoid color code alignment issues
                flags_padded = flags_display + " " * (10 - len(flags_str))

                print(
                    f"{steps:<5} {Colors.CYAN}{current_pc:04X}{Colors.RESET}  {instr:<18} {a_str}  {b_str}  {c_str}  {d_str}  {e_str}  {h_str}  {l_str}  {cpu.SP.value:04X}  {flags_padded}  {Colors.DIM}{cycles}{Colors.RESET}"
                )
            else:
                print(
                    f"{steps:<5} {Colors.CYAN}{current_pc:04X}{Colors.RESET}  {instr:<18} {curr_regs['A']:02X}  {curr_regs['B']:02X}  {curr_regs['C']:02X}  {curr_regs['D']:02X}  {curr_regs['E']:02X}  {curr_regs['H']:02X}  {curr_regs['L']:02X}  {cpu.SP.value:04X}  {flags_str:<10}  {Colors.DIM}{cycles}{Colors.RESET}"
                )

            # Update previous registers for next iteration
            prev_regs = curr_regs.copy()

        # Show registers after execution if trace mode enabled
        if args.step:
            # Get current register values
            curr_regs = {
                "A": cpu.A.value,
                "B": cpu.B.value,
                "C": cpu.C.value,
                "D": cpu.D.value,
                "E": cpu.E.value,
                "H": cpu.H.value,
                "L": cpu.L.value,
                "F": cpu.F.value,
            }

            flags = decode_flags(cpu.F.value)

            if args.binary:
                # Binary output with optional highlighting
                if args.highlight_changes:
                    # Format each register with highlight if changed
                    def fmt_reg_bin(name, val, changed):
                        if changed:
                            return f"{name}={Colors.HIGHLIGHT}{val:08b}{Colors.RESET}"
                        else:
                            return f"{name}={val:08b}"

                    a_str = fmt_reg_bin(
                        "A", curr_regs["A"], curr_regs["A"] != prev_regs["A"]
                    )
                    b_str = fmt_reg_bin(
                        "B", curr_regs["B"], curr_regs["B"] != prev_regs["B"]
                    )
                    c_str = fmt_reg_bin(
                        "C", curr_regs["C"], curr_regs["C"] != prev_regs["C"]
                    )
                    d_str = fmt_reg_bin(
                        "D", curr_regs["D"], curr_regs["D"] != prev_regs["D"]
                    )
                    e_str = fmt_reg_bin(
                        "E", curr_regs["E"], curr_regs["E"] != prev_regs["E"]
                    )
                    h_str = fmt_reg_bin(
                        "H", curr_regs["H"], curr_regs["H"] != prev_regs["H"]
                    )
                    l_str = fmt_reg_bin(
                        "L", curr_regs["L"], curr_regs["L"] != prev_regs["L"]
                    )

                    print(f"  {a_str} {b_str} {c_str} {d_str} {e_str} {h_str} {l_str}")
                else:
                    print(
                        f"  A={curr_regs['A']:08b} B={curr_regs['B']:08b} C={curr_regs['C']:08b} "
                        f"D={curr_regs['D']:08b} E={curr_regs['E']:08b} H={curr_regs['H']:08b} L={curr_regs['L']:08b}"
                    )
            else:
                # Hex output with optional highlighting
                if args.highlight_changes:
                    # Format each register with highlight if changed
                    def fmt_reg(name, val, changed):
                        if changed:
                            return f"{name}={Colors.HIGHLIGHT}{val:02X}{Colors.RESET}"
                        else:
                            return f"{name}={val:02X}"

                    a_str = fmt_reg(
                        "A", curr_regs["A"], curr_regs["A"] != prev_regs["A"]
                    )
                    b_str = fmt_reg(
                        "B", curr_regs["B"], curr_regs["B"] != prev_regs["B"]
                    )
                    c_str = fmt_reg(
                        "C", curr_regs["C"], curr_regs["C"] != prev_regs["C"]
                    )
                    d_str = fmt_reg(
                        "D", curr_regs["D"], curr_regs["D"] != prev_regs["D"]
                    )
                    e_str = fmt_reg(
                        "E", curr_regs["E"], curr_regs["E"] != prev_regs["E"]
                    )
                    h_str = fmt_reg(
                        "H", curr_regs["H"], curr_regs["H"] != prev_regs["H"]
                    )
                    l_str = fmt_reg(
                        "L", curr_regs["L"], curr_regs["L"] != prev_regs["L"]
                    )

                    f_changed = curr_regs["F"] != prev_regs["F"]
                    if f_changed:
                        flags_str = f"  {Colors.HIGHLIGHT}Flags: S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}{Colors.RESET}"
                    else:
                        flags_str = f"  Flags: S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"

                    print(
                        f"  {a_str} {b_str} {c_str} {d_str} {e_str} {h_str} {l_str}{flags_str}"
                    )
                else:
                    print(
                        f"  A={curr_regs['A']:02X} B={curr_regs['B']:02X} C={curr_regs['C']:02X} "
                        f"D={curr_regs['D']:02X} E={curr_regs['E']:02X} H={curr_regs['H']:02X} L={curr_regs['L']:02X}  "
                        f"Flags: S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"
                    )

            # Show what changed and why (if highlighting enabled)
            if args.highlight_changes:
                changes = []

                # Helper to get register value
                def get_reg_val(reg_name):
                    reg_map = {
                        "A": "A",
                        "B": "B",
                        "C": "C",
                        "D": "D",
                        "E": "E",
                        "H": "H",
                        "L": "L",
                    }
                    if reg_name in reg_map:
                        return pre_exec_regs[reg_map[reg_name]]
                    return 0

                # Check which registers changed and build explanation
                if curr_regs["A"] != prev_regs["A"]:
                    if "MVI A" in pre_exec_instr:
                        changes.append(f"A = immediate {curr_regs['A']:02X}H")
                    elif "MOV A," in pre_exec_instr:
                        src = pre_exec_instr.split(",")[1].strip()
                        changes.append(f"A = {src}({curr_regs['A']:02X}H)")
                    elif "ADD" in pre_exec_instr or "ADC" in pre_exec_instr:
                        op = (
                            pre_exec_instr.split()[1]
                            if len(pre_exec_instr.split()) > 1
                            else "M"
                        )
                        op_val = get_reg_val(op)
                        changes.append(
                            f"A = {prev_regs['A']:02X}H + {op}({op_val:02X}H) = {curr_regs['A']:02X}H"
                        )
                    elif "SUB" in pre_exec_instr or "SBB" in pre_exec_instr:
                        op = (
                            pre_exec_instr.split()[1]
                            if len(pre_exec_instr.split()) > 1
                            else "M"
                        )
                        op_val = get_reg_val(op)
                        changes.append(
                            f"A = {prev_regs['A']:02X}H - {op}({op_val:02X}H) = {curr_regs['A']:02X}H"
                        )
                    elif "ANA" in pre_exec_instr:
                        op = pre_exec_instr.split()[1]
                        op_val = get_reg_val(op)
                        changes.append(
                            f"A = {prev_regs['A']:02X}H AND {op}({op_val:02X}H) = {curr_regs['A']:02X}H"
                        )
                    elif "ORA" in pre_exec_instr:
                        op = pre_exec_instr.split()[1]
                        op_val = get_reg_val(op)
                        changes.append(
                            f"A = {prev_regs['A']:02X}H OR {op}({op_val:02X}H) = {curr_regs['A']:02X}H"
                        )
                    elif "XRA" in pre_exec_instr:
                        op = pre_exec_instr.split()[1]
                        op_val = get_reg_val(op)
                        changes.append(
                            f"A = {prev_regs['A']:02X}H XOR {op}({op_val:02X}H) = {curr_regs['A']:02X}H"
                        )
                    elif "INR A" in pre_exec_instr:
                        changes.append(
                            f"A = {prev_regs['A']:02X}H + 1 = {curr_regs['A']:02X}H"
                        )
                    elif "DCR A" in pre_exec_instr:
                        changes.append(
                            f"A = {prev_regs['A']:02X}H - 1 = {curr_regs['A']:02X}H"
                        )
                    elif "CMA" in pre_exec_instr:
                        changes.append(
                            f"A = NOT {prev_regs['A']:02X}H = {curr_regs['A']:02X}H"
                        )
                    elif (
                        "RLC" in pre_exec_instr
                        or "RRC" in pre_exec_instr
                        or "RAL" in pre_exec_instr
                        or "RAR" in pre_exec_instr
                    ):
                        changes.append(
                            f"A = rotated {prev_regs['A']:02X}H = {curr_regs['A']:02X}H"
                        )
                    else:
                        changes.append(f"A = {curr_regs['A']:02X}H")

                # Check other registers
                for reg_name in ["B", "C", "D", "E", "H", "L"]:
                    if curr_regs[reg_name] != prev_regs[reg_name]:
                        if f"MVI {reg_name}" in pre_exec_instr:
                            changes.append(
                                f"{reg_name} = immediate {curr_regs[reg_name]:02X}H"
                            )
                        elif f"MOV {reg_name}," in pre_exec_instr:
                            src = pre_exec_instr.split(",")[1].strip()
                            changes.append(
                                f"{reg_name} = {src}({curr_regs[reg_name]:02X}H)"
                            )
                        elif f"INR {reg_name}" in pre_exec_instr:
                            changes.append(
                                f"{reg_name} = {prev_regs[reg_name]:02X}H + 1 = {curr_regs[reg_name]:02X}H"
                            )
                        elif f"DCR {reg_name}" in pre_exec_instr:
                            changes.append(
                                f"{reg_name} = {prev_regs[reg_name]:02X}H - 1 = {curr_regs[reg_name]:02X}H"
                            )
                        else:
                            changes.append(f"{reg_name} = {curr_regs[reg_name]:02X}H")

                # Check flags
                if curr_regs["F"] != prev_regs["F"]:
                    old_flags = decode_flags(prev_regs["F"])
                    new_flags = decode_flags(curr_regs["F"])
                    flag_changes = []
                    for flag in ["S", "Z", "AC", "P", "CY"]:
                        if old_flags[flag] != new_flags[flag]:
                            flag_changes.append(
                                f"{flag}:{old_flags[flag]}→{new_flags[flag]}"
                            )
                    if flag_changes:
                        changes.append(f"Flags: {', '.join(flag_changes)}")

                if changes:
                    print(f"{Colors.DIM}     {', '.join(changes)}{Colors.RESET}")

            # Update previous registers for next iteration
            prev_regs = curr_regs.copy()
            print()

    # End real-time measurement
    end_time = time.time()
    execution_time = end_time - start_time

    # Print table footer if table mode was active
    if args.table:
        print(f"{Colors.DIM}{'─' * 90}{Colors.RESET}\n")

    # Format execution time
    def format_execution_time(seconds):
        if seconds < 0.001:
            return f"{seconds * 1_000_000:.2f} µs"
        elif seconds < 1:
            return f"{seconds * 1000:.2f} ms"
        elif seconds < 60:
            return f"{seconds:.2f} s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.2f}s"

    # Show execution summary
    exec_time_str = format_execution_time(execution_time)
    run_meta = (
        f"{Colors.DIM}[load {load_addr:04X}H · {program_size} bytes]{Colors.RESET}"
    )

    if cpu.haulted:
        if args.clock:

            def format_time(cycles, freq_mhz):
                """Format execution time with appropriate unit"""
                freq_hz = freq_mhz * 1_000_000
                time_us = (cycles / freq_hz) * 1_000_000
                if time_us < 1000:
                    return f"{time_us:.2f} µs"
                else:
                    time_ms = time_us / 1000
                    if time_ms < 1000:
                        return f"{time_ms:.2f} ms"
                    else:
                        time_s = time_ms / 1000
                        return f"{time_s:.2f} s"

            time_str = format_time(total_cycles, args.clock)
            print(
                f"{Colors.GREEN}✓ Program halted{Colors.RESET} after {steps} steps, {Colors.CYAN}{total_cycles}{Colors.RESET} Takte @ {args.clock} MHz: {Colors.CYAN}{time_str}{Colors.RESET} {Colors.DIM}(real: {exec_time_str}){Colors.RESET} {run_meta}\n"
            )
        else:
            print(
                f"{Colors.GREEN}✓ Program halted{Colors.RESET} after {steps} steps, {Colors.CYAN}{total_cycles}{Colors.RESET} Takte {Colors.DIM}(real: {exec_time_str}){Colors.RESET} {run_meta}\n"
            )
    else:
        # Show appropriate max_steps value
        limit_str = f"{int(max_steps)}" if max_steps != float("inf") else "∞"
        print(
            f"{Colors.RED}⚠ Program stopped{Colors.RESET} after {limit_str} steps (no HLT), {Colors.CYAN}{total_cycles}{Colors.RESET} Takte {Colors.DIM}(real: {exec_time_str}){Colors.RESET} {run_meta}"
        )
        if args.unsafe is None:
            print(
                f"{Colors.DIM}   Use -u or --unsafe to remove limit, or -u N for custom limit{Colors.RESET}\n"
            )
        else:
            print(
                f"{Colors.DIM}   Increase limit with --unsafe N or use --unsafe for unlimited{Colors.RESET}\n"
            )

    if args.show_registers:
        print(f"{Colors.BLUE}{Colors.BOLD}Final Register Values:{Colors.RESET}")
        if args.binary:
            print(f"  A = {Colors.CYAN}{cpu.A.value:08b}{Colors.RESET} ({cpu.A.value})")
            print(f"  B = {Colors.CYAN}{cpu.B.value:08b}{Colors.RESET} ({cpu.B.value})")
            print(f"  C = {Colors.CYAN}{cpu.C.value:08b}{Colors.RESET} ({cpu.C.value})")
            print(f"  D = {Colors.CYAN}{cpu.D.value:08b}{Colors.RESET} ({cpu.D.value})")
            print(f"  E = {Colors.CYAN}{cpu.E.value:08b}{Colors.RESET} ({cpu.E.value})")
            print(f"  H = {Colors.CYAN}{cpu.H.value:08b}{Colors.RESET} ({cpu.H.value})")
            print(f"  L = {Colors.CYAN}{cpu.L.value:08b}{Colors.RESET} ({cpu.L.value})")
            print(
                f"  {Colors.DIM}SP = {cpu.SP.value:016b}  PC = {cpu.PC.value:016b}{Colors.RESET}"
            )
        else:
            print(
                f"  A = {Colors.CYAN}0x{cpu.A.value:02X}{Colors.RESET} ({cpu.A.value})"
            )
            print(
                f"  B = {Colors.CYAN}0x{cpu.B.value:02X}{Colors.RESET} ({cpu.B.value})"
            )
            print(
                f"  C = {Colors.CYAN}0x{cpu.C.value:02X}{Colors.RESET} ({cpu.C.value})"
            )
            print(
                f"  D = {Colors.CYAN}0x{cpu.D.value:02X}{Colors.RESET} ({cpu.D.value})"
            )
            print(
                f"  E = {Colors.CYAN}0x{cpu.E.value:02X}{Colors.RESET} ({cpu.E.value})"
            )
            print(
                f"  H = {Colors.CYAN}0x{cpu.H.value:02X}{Colors.RESET} ({cpu.H.value})"
            )
            print(
                f"  L = {Colors.CYAN}0x{cpu.L.value:02X}{Colors.RESET} ({cpu.L.value})"
            )
            print(
                f"  {Colors.DIM}SP = 0x{cpu.SP.value:04X}  PC = 0x{cpu.PC.value:04X}{Colors.RESET}"
            )

        flags = decode_flags(cpu.F.value)
        flag_str = f"S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"
        print(f"\n{Colors.BLUE}{Colors.BOLD}Flags:{Colors.RESET} {flag_str}")

    # Show stack (only if -S flag is used)
    if args.stack:
        print(
            f"\n{Colors.BLUE}{Colors.BOLD}Stack (SP = {Colors.CYAN}0x{cpu.SP.value:04X}{Colors.RESET}{Colors.BLUE}{Colors.BOLD}):{Colors.RESET}"
        )
        sp_val = cpu.SP.value

        # Show stack contents (8 words = 16 bytes starting from SP)
        stack_entries = 8
        if sp_val < 0xFFFF - (stack_entries * 2):
            print(
                f"{Colors.DIM}{'Addr':<8} {'Word':<8} {'Lo Hi':<12} Description{Colors.RESET}"
            )
            print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")

            for i in range(stack_entries):
                addr = sp_val + (i * 2)
                if addr < 0xFFFF:
                    lo_byte = cpu.memory[addr].value
                    hi_byte = cpu.memory[addr + 1].value if addr + 1 < 0xFFFF else 0
                    word = (hi_byte << 8) | lo_byte

                    # Highlight SP position
                    if i == 0:
                        marker = f"{Colors.HIGHLIGHT}→ SP{Colors.RESET}"
                    else:
                        marker = f"  SP+{i * 2}"

                    # Check if this looks like a return address (within program range)
                    desc = ""
                    if (
                        asm.ploadoff
                        <= word
                        < (asm.ploadoff + sum(asm.writtenaddresses))
                    ):
                        desc = f"{Colors.GREEN}(possible return addr){Colors.RESET}"

                    print(
                        f"{marker:<8} {Colors.CYAN}{addr:04X}H{Colors.RESET}  {word:04X}H  {lo_byte:02X} {hi_byte:02X}    {desc}"
                    )
        else:
            print(f"{Colors.DIM}  Stack pointer at top of memory{Colors.RESET}")

    # Memory display options
    def parse_address(addr_str):
        """Parse address string (supports hex with 0x prefix or H suffix, or decimal)"""
        return parse_address_value(addr_str)

    # Option 1: Show memory range (-m)
    if args.memory:
        try:
            if "-" in args.memory:
                start_str, end_str = args.memory.split("-")
                start_addr = parse_address(start_str)
                end_addr = parse_address(end_str)
            else:
                start_addr = parse_address(args.memory)
                end_addr = start_addr

            print(
                f"\n{Colors.BLUE}{Colors.BOLD}Memory [{start_addr:04X}H - {end_addr:04X}H]:{Colors.RESET}"
            )
            for addr in range(start_addr, end_addr + 1):
                value = cpu.memory[addr].value
                changed = value != initial_memory[addr]
                if changed:
                    print(
                        f"  {Colors.CYAN}{addr:04X}H:{Colors.RESET} {Colors.HIGHLIGHT}{value:02X}H{Colors.RESET} (changed from {initial_memory[addr]:02X}H)"
                    )
                else:
                    print(f"  {Colors.CYAN}{addr:04X}H:{Colors.RESET} {value:02X}H")
        except Exception as e:
            print(f"{Colors.RED}Error parsing memory range:{Colors.RESET} {e}")

    # Option 2: Show all changes (--show-changes)
    if args.show_changes:
        changes = []
        for addr in range(len(cpu.memory)):
            if cpu.memory[addr].value != initial_memory[addr]:
                changes.append((addr, initial_memory[addr], cpu.memory[addr].value))

        if changes:
            print(f"\n{Colors.BLUE}{Colors.BOLD}Memory Changes:{Colors.RESET}")
            for addr, old_val, new_val in changes:
                print(
                    f"  {Colors.CYAN}{addr:04X}H:{Colors.RESET} {old_val:02X}H {Colors.DIM}→{Colors.RESET} {Colors.HIGHLIGHT}{new_val:02X}H{Colors.RESET}"
                )
        else:
            print(f"\n{Colors.DIM}No memory changes detected{Colors.RESET}")

    # Option 3: Watch specific addresses (--watch)
    if args.watch:
        try:
            watch_addrs = [
                parse_address(addr.strip()) for addr in args.watch.split(",")
            ]
            print(f"\n{Colors.BLUE}{Colors.BOLD}Watched Memory:{Colors.RESET}")
            for addr in watch_addrs:
                value = cpu.memory[addr].value
                changed = value != initial_memory[addr]
                if changed:
                    print(
                        f"  {Colors.CYAN}{addr:04X}H:{Colors.RESET} {initial_memory[addr]:02X}H {Colors.DIM}→{Colors.RESET} {Colors.HIGHLIGHT}{value:02X}H{Colors.RESET} {Colors.GREEN}(written){Colors.RESET}"
                    )
                else:
                    print(
                        f"  {Colors.CYAN}{addr:04X}H:{Colors.RESET} {value:02X}H {Colors.DIM}(unchanged){Colors.RESET}"
                    )
        except Exception as e:
            print(f"{Colors.RED}Error parsing watch addresses:{Colors.RESET} {e}")

    # Option 4: Comprehensive Memory Map (--memory-map)
    if args.memory_map:
        print(f"\n{Colors.BLUE}{Colors.BOLD}═══ Memory Map ═══{Colors.RESET}")

        # Find all non-zero memory regions
        regions = []
        in_region = False
        region_start = 0

        for addr in range(0x10000):
            has_data = cpu.memory[addr].value != 0
            if has_data and not in_region:
                region_start = addr
                in_region = True
            elif not has_data and in_region:
                regions.append((region_start, addr - 1))
                in_region = False
        if in_region:
            regions.append((region_start, 0xFFFF))

        # Calculate program region
        prog_start = asm.ploadoff
        prog_end = asm.ploadoff + sum(asm.writtenaddresses) - 1

        # Stack region (assume stack grows down from initial SP)
        stack_top = cpu.SP.value
        stack_bottom = 0xFFFF

        print(f"\n{Colors.CYAN}Program Region:{Colors.RESET}")
        print(
            f"  Start:  {Colors.HIGHLIGHT}{prog_start:04X}H{Colors.RESET} ({prog_start})"
        )
        print(f"  End:    {Colors.HIGHLIGHT}{prog_end:04X}H{Colors.RESET} ({prog_end})")
        print(f"  Size:   {prog_end - prog_start + 1} bytes")

        print(f"\n{Colors.CYAN}Stack Region:{Colors.RESET}")
        print(
            f"  SP:     {Colors.HIGHLIGHT}{cpu.SP.value:04X}H{Colors.RESET} ({cpu.SP.value})"
        )
        print(
            f"  Top:    {Colors.HIGHLIGHT}{stack_bottom:04X}H{Colors.RESET} (grows down)"
        )
        print(f"  Used:   {stack_bottom - stack_top + 1} bytes")

        # Show all memory regions with data
        print(f"\n{Colors.CYAN}Memory Regions (non-zero):{Colors.RESET}")
        if regions:
            print(
                f"{Colors.DIM}  {'Start':<8} {'End':<8} {'Size':<8} Type{Colors.RESET}"
            )
            print(f"{Colors.DIM}  {'─' * 42}{Colors.RESET}")

            for start, end in regions:
                size = end - start + 1
                # Determine region type
                if prog_start <= start <= prog_end or prog_start <= end <= prog_end:
                    region_type = f"{Colors.GREEN}CODE{Colors.RESET}"
                elif start >= stack_top:
                    region_type = f"{Colors.YELLOW}STACK{Colors.RESET}"
                else:
                    region_type = f"{Colors.BLUE}DATA{Colors.RESET}"

                print(f"  {start:04X}H    {end:04X}H    {size:<8} {region_type}")
        else:
            print(f"  {Colors.DIM}No non-zero memory regions{Colors.RESET}")

        # Show memory usage statistics
        total_used = sum(1 for addr in range(0x10000) if cpu.memory[addr].value != 0)
        total_changed = sum(
            1
            for addr in range(0x10000)
            if cpu.memory[addr].value != initial_memory[addr]
        )

        print(f"\n{Colors.CYAN}Memory Statistics:{Colors.RESET}")
        print(f"  Total:    {0x10000} bytes (64 KB)")
        print(f"  Used:     {total_used} bytes ({total_used / 0x10000 * 100:.2f}%)")
        print(
            f"  Changed:  {total_changed} bytes ({total_changed / 0x10000 * 100:.2f}%)"
        )
        print(f"  Free:     {0x10000 - total_used} bytes")

        # Show detailed hex dump of all non-zero regions
        print(f"\n{Colors.CYAN}Detailed Memory Contents:{Colors.RESET}")
        for start, end in regions:
            print(f"\n{Colors.DIM}Region {start:04X}H - {end:04X}H:{Colors.RESET}")

            # Limit display to reasonable size per region
            display_size = min(end - start + 1, 256)
            if display_size < end - start + 1:
                print(
                    f"{Colors.DIM}  (showing first 256 bytes of {end - start + 1}){Colors.RESET}"
                )

            addr = start
            bytes_shown = 0
            while addr <= end and bytes_shown < display_size:
                # Show 16 bytes per line
                line_bytes = []
                line_ascii = []
                line_start = addr

                for _ in range(16):
                    if addr <= end and bytes_shown < display_size:
                        val = cpu.memory[addr].value
                        changed = val != initial_memory[addr]

                        if changed:
                            line_bytes.append(
                                f"{Colors.HIGHLIGHT}{val:02X}{Colors.RESET}"
                            )
                        else:
                            line_bytes.append(f"{val:02X}")

                        # ASCII representation
                        if 32 <= val <= 126:
                            line_ascii.append(chr(val))
                        else:
                            line_ascii.append(".")

                        addr += 1
                        bytes_shown += 1
                    else:
                        line_bytes.append("  ")
                        line_ascii.append(" ")

                # Print line
                hex_part = " ".join(line_bytes[:8]) + "  " + " ".join(line_bytes[8:])
                ascii_part = "".join(line_ascii)
                print(
                    f"  {Colors.CYAN}{line_start:04X}{Colors.RESET}: {hex_part}  {Colors.DIM}|{ascii_part}|{Colors.RESET}"
                )


if __name__ == "__main__":
    main()
