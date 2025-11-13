"""Benchmark mode for comparing program performance."""

import sys
import time
from pathlib import Path

from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors
from ...shared.executor import ProgramExecutor, resolve_step_limit
from ...shared.progress import format_duration


def benchmark_program(filename, args, runs=1):
    """Benchmark a single program.

    Args:
        filename: Path to assembly file
        args: Command line arguments
        runs: Number of runs to average

    Returns:
        Dictionary with benchmark results
    """
    results = {
        "filename": filename,
        "runs": runs,
        "steps": [],
        "cycles": [],
        "wall_times": [],
        "success": [],
    }

    for run in range(runs):
        executor = ProgramExecutor(filename, args)
        limit, has_limit = resolve_step_limit(args)

        steps = 0
        total_cycles = 0
        start_time = time.time()

        while not executor.cpu.haulted and (steps < limit):
            result = executor.step_instruction()
            total_cycles += result.get("cycles", 0)
            steps += 1

        end_time = time.time()
        wall_time = end_time - start_time

        results["steps"].append(steps)
        results["cycles"].append(total_cycles)
        results["wall_times"].append(wall_time)
        results["success"].append(executor.cpu.haulted)

    return results


def compare_programs(files, args, runs=3):
    """Compare multiple programs.

    Args:
        files: List of assembly file paths
        args: Command line arguments
        runs: Number of runs per program
    """
    print(f"\n{Colors.BLUE}{Colors.BOLD}Benchmark Mode{Colors.RESET}")
    print(f"{Colors.DIM}Running each program {runs} times...{Colors.RESET}\n")

    all_results = []

    for filename in files:
        if not Path(filename).exists():
            print(f"{Colors.RED}✗ File not found:{Colors.RESET} {filename}")
            continue

        print(f"{Colors.CYAN}Benchmarking:{Colors.RESET} {filename}")

        try:
            results = benchmark_program(filename, args, runs)
            all_results.append(results)

            # Show quick stats
            avg_cycles = sum(results["cycles"]) / len(results["cycles"])
            avg_time = sum(results["wall_times"]) / len(results["wall_times"])
            print(
                f"  {Colors.GREEN}✓{Colors.RESET} Avg: {int(avg_cycles)} cycles, {format_duration(avg_time)}"
            )
        except Exception as e:
            print(f"  {Colors.RED}✗ Error:{Colors.RESET} {e}")

    if len(all_results) < 2:
        print(f"\n{Colors.YELLOW}Need at least 2 programs to compare{Colors.RESET}")
        return

    print(f"\n{Colors.BLUE}{Colors.BOLD}Comparison Results{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}\n")

    # Find best/worst
    best_cycles_idx = min(
        range(len(all_results)), key=lambda i: sum(all_results[i]["cycles"])
    )
    best_time_idx = min(
        range(len(all_results)), key=lambda i: sum(all_results[i]["wall_times"])
    )

    print(
        f"{Colors.BOLD}{'Program':<30} {'Cycles':>12} {'Time':>12} {'Speedup':>10}{Colors.RESET}"
    )
    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

    baseline_cycles = sum(all_results[0]["cycles"]) / len(all_results[0]["cycles"])

    for idx, results in enumerate(all_results):
        avg_cycles = sum(results["cycles"]) / len(results["cycles"])
        avg_time = sum(results["wall_times"]) / len(results["wall_times"])

        # Calculate speedup relative to first program
        if baseline_cycles > 0:
            speedup = baseline_cycles / avg_cycles
        else:
            speedup = 1.0

        # Highlight best
        if idx == best_cycles_idx:
            prefix = f"{Colors.GREEN}★{Colors.RESET}"
        else:
            prefix = " "

        filename_short = Path(results["filename"]).name
        speedup_str = f"{speedup:>6.2f}x" if speedup != 1.0 else "baseline"

        print(
            f"{prefix} {filename_short:<28} {int(avg_cycles):>12} {format_duration(avg_time):>12} {speedup_str:>10}"
        )

    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

    # Summary
    best_name = Path(all_results[best_cycles_idx]["filename"]).name
    best_cycles = sum(all_results[best_cycles_idx]["cycles"]) / len(
        all_results[best_cycles_idx]["cycles"]
    )
    worst_cycles = max(sum(r["cycles"]) / len(r["cycles"]) for r in all_results)

    if worst_cycles > 0 and best_cycles > 0:
        improvement = ((worst_cycles - best_cycles) / worst_cycles) * 100
        print(
            f"\n{Colors.BOLD}Winner:{Colors.RESET} {Colors.GREEN}{best_name}{Colors.RESET}"
        )
        print(f"  {improvement:.1f}% faster than slowest")

    print()


def run_benchmark_mode(files, args, runs=3):
    """Main entry point for benchmark mode.

    Args:
        files: List of files to benchmark
        args: Command line arguments
        runs: Number of runs per program
    """
    if len(files) < 1:
        print(f"{Colors.RED}Error:{Colors.RESET} Benchmark requires at least 1 file")
        sys.exit(1)

    if len(files) == 1:
        # Single file benchmark
        print(f"\n{Colors.BLUE}{Colors.BOLD}Benchmark: {files[0]}{Colors.RESET}")
        print(f"{Colors.DIM}Running {runs} times...{Colors.RESET}\n")

        results = benchmark_program(files[0], args, runs)

        # Calculate statistics
        avg_cycles = sum(results["cycles"]) / len(results["cycles"])
        min_cycles = min(results["cycles"])
        max_cycles = max(results["cycles"])

        avg_time = sum(results["wall_times"]) / len(results["wall_times"])
        min_time = min(results["wall_times"])
        max_time = max(results["wall_times"])

        print(f"{Colors.BOLD}Cycles (T-states):{Colors.RESET}")
        print(f"  Average: {Colors.CYAN}{int(avg_cycles)}{Colors.RESET}")
        print(f"  Min:     {int(min_cycles)}")
        print(f"  Max:     {int(max_cycles)}")

        print(f"\n{Colors.BOLD}Wall Time:{Colors.RESET}")
        print(f"  Average: {Colors.CYAN}{format_duration(avg_time)}{Colors.RESET}")
        print(f"  Min:     {format_duration(min_time)}")
        print(f"  Max:     {format_duration(max_time)}")

        if args.clock:
            # Calculate real execution time at specified clock speed
            freq_hz = args.clock * 1_000_000
            real_time = avg_cycles / freq_hz
            print(f"\n{Colors.BOLD}Simulated Time @ {args.clock} MHz:{Colors.RESET}")
            print(f"  {Colors.CYAN}{format_duration(real_time)}{Colors.RESET}")

        print()
    else:
        # Compare multiple programs
        compare_programs(files, args, runs)
