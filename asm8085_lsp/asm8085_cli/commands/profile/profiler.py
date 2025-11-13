"""Performance profiler for 8085 programs."""

import sys
from collections import defaultdict

from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors
from ...shared.constants import (
    HOTSPOT_CRITICAL,
    HOTSPOT_HIGH,
    HOTSPOT_MEDIUM,
    PROFILER_DEFAULT_TOP_N,
)
from ...shared.executor import ProgramExecutor, resolve_step_limit


class PerformanceProfiler:
    """Track performance metrics during program execution."""

    def __init__(self, asm_obj, original_lines):
        """Initialize profiler.

        Args:
            asm_obj: Assembled program object
            original_lines: List of (line_num, line_text) tuples
        """
        self.asm_obj = asm_obj
        self.original_lines = dict(original_lines)

        # Build address to line mapping
        self.addr_to_line = {}
        for idx, line in enumerate(self.original_lines.values()):
            if idx < len(asm_obj.plsize):
                size = asm_obj.plsize[idx]
                if size > 0 and idx < len(asm_obj.poffset):
                    start_addr = asm_obj.poffset[idx]
                    for disp in range(size):
                        self.addr_to_line[start_addr + disp] = idx + 1

        # Performance tracking
        self.line_exec_count = defaultdict(int)  # Line -> execution count
        self.line_cycle_total = defaultdict(int)  # Line -> total cycles
        self.instruction_count = defaultdict(int)  # Mnemonic -> count
        self.total_steps = 0
        self.total_cycles = 0

    def record(self, step_result):
        """Record a step execution.

        Args:
            step_result: Dictionary with pc, cycles, instr, etc.
        """
        pc = step_result.get("pc")
        cycles = step_result.get("cycles", 0)
        instruction = step_result.get("instr", "")

        self.total_steps += 1
        self.total_cycles += cycles

        # Map PC to source line
        line_num = self.addr_to_line.get(pc)
        if line_num:
            self.line_exec_count[line_num] += 1
            self.line_cycle_total[line_num] += cycles

        # Track instruction frequency
        if instruction:
            mnemonic = instruction.split()[0].upper()
            self.instruction_count[mnemonic] += 1

    def report(self, top_n=10):
        """Print performance report.

        Args:
            top_n: Number of top items to show in each category
        """
        print(f"\n{Colors.BLUE}{Colors.BOLD}Performance Profile{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}\n")

        # Overall stats
        print(f"{Colors.BOLD}Execution Summary:{Colors.RESET}")
        print(f"  Total steps:  {self.total_steps:,}")
        print(f"  Total cycles: {self.total_cycles:,}")
        if self.total_steps > 0:
            avg_cycles = self.total_cycles / self.total_steps
            print(f"  Avg cycles/step: {avg_cycles:.2f}")

        # Hotspot lines (by total cycles)
        print(
            f"\n{Colors.BOLD}Top {top_n} Hotspot Lines (by total cycles):{Colors.RESET}"
        )
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

        hotspots = sorted(
            self.line_cycle_total.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        if hotspots:
            print(
                f"{Colors.BOLD}{'Line':<6} {'Executions':>12} {'Cycles':>12} {'% Total':>10} "
                f"{'Source'}{Colors.RESET}"
            )
            print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

            for line_num, total_cycles in hotspots:
                exec_count = self.line_exec_count[line_num]
                pct = (
                    (total_cycles / self.total_cycles * 100)
                    if self.total_cycles > 0
                    else 0
                )
                source = self.original_lines.get(line_num, "").strip()[:40]

                color = ""
                if pct > HOTSPOT_CRITICAL:
                    color = Colors.RED
                elif pct > HOTSPOT_HIGH:
                    color = Colors.YELLOW
                elif pct > HOTSPOT_MEDIUM:
                    color = Colors.CYAN

                print(
                    f"{color}{line_num:<6} {exec_count:>12,} {total_cycles:>12,} {pct:>9.1f}% "
                    f"{Colors.RESET}{source}"
                )
        else:
            print("  No data")

        # Most executed lines
        print(f"\n{Colors.BOLD}Top {top_n} Most Executed Lines:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

        most_exec = sorted(
            self.line_exec_count.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        if most_exec:
            print(
                f"{Colors.BOLD}{'Line':<6} {'Executions':>12} {'Avg Cycles':>12} "
                f"{'Source'}{Colors.RESET}"
            )
            print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

            for line_num, exec_count in most_exec:
                total_cycles = self.line_cycle_total[line_num]
                avg_cycles = total_cycles / exec_count if exec_count > 0 else 0
                source = self.original_lines.get(line_num, "").strip()[:40]

                print(
                    f"{line_num:<6} {exec_count:>12,} {avg_cycles:>12.1f} "
                    f"{Colors.DIM}{source}{Colors.RESET}"
                )
        else:
            print("  No data")

        # Instruction frequency
        print(f"\n{Colors.BOLD}Top {top_n} Most Used Instructions:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

        top_instructions = sorted(
            self.instruction_count.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        if top_instructions:
            print(
                f"{Colors.BOLD}{'Instruction':<15} {'Count':>12} {'% Total':>10}{Colors.RESET}"
            )
            print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

            for instr, count in top_instructions:
                pct = (count / self.total_steps * 100) if self.total_steps > 0 else 0
                print(
                    f"{Colors.CYAN}{instr:<15}{Colors.RESET} {count:>12,} {pct:>9.1f}%"
                )
        else:
            print("  No data")

        # Optimization suggestions
        self._print_optimization_hints()

        print()

    def _print_optimization_hints(self):
        """Print optimization suggestions based on profile data."""
        hints = []

        # Check for loops with high cycle counts
        loops = []
        for line_num, exec_count in self.line_exec_count.items():
            if exec_count > 100:  # Likely a loop
                cycles = self.line_cycle_total[line_num]
                loops.append((line_num, exec_count, cycles))

        if loops:
            hints.append(
                f"Found {len(loops)} potential loop(s) - consider optimizing high-cycle "
                "instructions inside loops"
            )

        # Check for inefficient instructions
        if "MVI" in self.instruction_count and "XRA" not in self.instruction_count:
            mvi_count = self.instruction_count["MVI"]
            if mvi_count > 5:
                hints.append(
                    "Consider using XRA A instead of MVI A, 00H for zeroing (saves 3 cycles)"
                )

        # Check for excessive memory operations
        memory_ops = sum(
            self.instruction_count.get(op, 0)
            for op in ["LDA", "STA", "LDAX", "STAX", "LHLD", "SHLD"]
        )
        if memory_ops > self.total_steps * 0.3:
            hints.append(
                "30%+ of instructions are memory operations - consider using registers more"
            )

        if hints:
            print(
                f"\n{Colors.YELLOW}{Colors.BOLD}Optimization Suggestions:{Colors.RESET}"
            )
            for i, hint in enumerate(hints, 1):
                print(f"  {i}. {hint}")


def run_profiler_mode(filename, args, top_n=PROFILER_DEFAULT_TOP_N):
    """Run performance profiler on a program.

    Args:
        filename: Path to assembly file
        args: Command line arguments
        top_n: Number of top items to show
    """
    print(f"\n{Colors.CYAN}Profiling: {filename}{Colors.RESET}")

    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    # Create profiler
    profiler = PerformanceProfiler(asm_obj, original_lines)

    # Execute program with profiling
    executor = ProgramExecutor(filename, args)
    limit, has_limit = resolve_step_limit(args)
    steps = 0

    while not executor.cpu.haulted and (steps < limit):
        result = executor.step_instruction()
        profiler.record(result)
        steps += 1

    if has_limit and (not executor.cpu.haulted) and steps >= limit:
        print(
            f"{Colors.YELLOW}Warning:{Colors.RESET} Program did not halt before step limit. "
            "Profile may be incomplete."
        )

    # Show report
    profiler.report(top_n=top_n)
