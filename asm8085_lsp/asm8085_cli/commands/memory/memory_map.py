"""Memory map visualization for 8085 programs."""

"""Memory map visualization helpers."""

import sys

from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors
from ...shared.executor import ProgramExecutor, resolve_step_limit


def visualize_memory_map(filename, args):
    """Visualize memory layout after program execution.

    Shows:
    - Code section (program instructions)
    - Data section (modified memory)
    - Stack region
    - Unused memory
    """
    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    # Run program to collect memory changes
    executor = ProgramExecutor(filename, args)
    limit, has_limit = resolve_step_limit(args)
    steps = 0

    while not executor.cpu.haulted and (steps < limit):
        executor.step_instruction()
        steps += 1

    if has_limit and (not executor.cpu.haulted) and steps >= limit:
        print(
            f"{Colors.YELLOW}Warning:{Colors.RESET} Program did not halt before step limit. "
            "Memory map may be incomplete."
        )

    # Collect memory regions
    load_addr = asm_obj.ploadoff
    program_size = sum(asm_obj.writtenaddresses)
    code_end = load_addr + program_size

    # Get stack pointer
    stack_ptr = executor.cpu.SP.value

    # Find all modified memory addresses
    modified_addresses = set()
    for addr in range(0x10000):
        # Check if memory was modified (not zero or in code section)
        if addr < load_addr or addr >= code_end:
            if executor.cpu.memory[addr].value != 0:
                modified_addresses.add(addr)

    # Build memory regions
    regions = []

    # Code region
    regions.append(
        {
            "name": "Code",
            "start": load_addr,
            "end": code_end - 1,
            "size": program_size,
            "color": Colors.GREEN,
            "type": "code",
        }
    )

    # Data region (modified memory outside code)
    if modified_addresses:
        data_addrs = sorted(modified_addresses)
        data_start = min(data_addrs)
        data_end = max(data_addrs)
        data_size = len(data_addrs)

        regions.append(
            {
                "name": "Data",
                "start": data_start,
                "end": data_end,
                "size": data_size,
                "color": Colors.CYAN,
                "type": "data",
            }
        )

    # Stack region (if SP has moved from initial position)
    # Standard 8085 stack starts at top of memory and grows down
    initial_sp = 0xFFFF
    if stack_ptr < initial_sp:
        stack_size = initial_sp - stack_ptr
        regions.append(
            {
                "name": "Stack",
                "start": stack_ptr + 1,
                "end": initial_sp,
                "size": stack_size,
                "color": Colors.YELLOW,
                "type": "stack",
            }
        )

    # Display memory map
    print(f"\n{Colors.BLUE}{Colors.BOLD}Memory Map: {filename}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}\n")

    # Sort regions by address
    regions.sort(key=lambda r: r["start"])

    # Display regions
    print(
        f"{Colors.BOLD}{'Region':<12} {'Start':<10} {'End':<10} {'Size':<10}{Colors.RESET}"
    )
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")

    for region in regions:
        name = f"{region['color']}{region['name']}{Colors.RESET}"
        start_str = f"{region['start']:04X}H"
        end_str = f"{region['end']:04X}H"
        size_str = f"{region['size']} bytes"

        print(f"{name:<22} {start_str:<10} {end_str:<10} {size_str}")

    # Visual bar representation
    print(f"\n{Colors.BOLD}Memory Layout:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")

    # Scale to 64KB address space
    bar_width = 60
    total_memory = 0x10000  # 64KB

    # Calculate bar positions
    memory_bar = [" "] * bar_width

    for region in regions:
        start_pos = int((region["start"] / total_memory) * bar_width)
        end_pos = int((region["end"] / total_memory) * bar_width)

        # Mark region on bar
        for i in range(start_pos, min(end_pos + 1, bar_width)):
            if region["type"] == "code":
                memory_bar[i] = "█"
            elif region["type"] == "data":
                memory_bar[i] = "▓"
            elif region["type"] == "stack":
                memory_bar[i] = "▒"

    # Display bar
    print(f"0000H [{Colors.DIM}{''.join(memory_bar)}{Colors.RESET}] FFFFH")

    # Legend
    print(f"\n{Colors.GREEN}█{Colors.RESET} Code   ", end="")
    print(f"{Colors.CYAN}▓{Colors.RESET} Data   ", end="")
    print(f"{Colors.YELLOW}▒{Colors.RESET} Stack")

    # Detailed breakdown
    print(f"\n{Colors.BOLD}Memory Usage:{Colors.RESET}")
    total_used = sum(r["size"] for r in regions)
    total_free = total_memory - total_used
    usage_pct = (total_used / total_memory) * 100

    print(f"  Used:  {total_used:6d} bytes ({usage_pct:.2f}%)")
    print(f"  Free:  {total_free:6d} bytes ({100 - usage_pct:.2f}%)")
    print(f"  Total: {total_memory:6d} bytes")

    # Address ranges summary
    if len(regions) > 0:
        lowest_addr = min(r["start"] for r in regions)
        highest_addr = max(r["end"] for r in regions)
        print(f"\n{Colors.BOLD}Address Range:{Colors.RESET}")
        print(f"  Lowest:  {lowest_addr:04X}H")
        print(f"  Highest: {highest_addr:04X}H")
        print(f"  Span:    {highest_addr - lowest_addr + 1} bytes")

    # Warnings
    warnings = []

    # Check for overlapping regions
    for i, r1 in enumerate(regions):
        for r2 in regions[i + 1 :]:
            if r1["end"] >= r2["start"] and r1["start"] <= r2["end"]:
                warnings.append(
                    f"⚠ Overlapping regions: {r1['name']} and {r2['name']} "
                    f"at {max(r1['start'], r2['start']):04X}H"
                )

    # Check for fragmentation
    gaps = []
    for i in range(len(regions) - 1):
        gap_size = regions[i + 1]["start"] - regions[i]["end"] - 1
        if gap_size > 0:
            gaps.append(gap_size)

    if len(gaps) > 2:
        warnings.append(f"⚠ Memory fragmentation detected ({len(gaps)} gaps)")

    if warnings:
        print(f"\n{Colors.YELLOW}Warnings:{Colors.RESET}")
        for warning in warnings:
            print(f"  {warning}")

    print()


def show_memory_regions(filename, args):
    """Quick summary of memory regions without execution."""
    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    load_addr = asm_obj.ploadoff
    program_size = sum(asm_obj.writtenaddresses)
    code_end = load_addr + program_size

    print(f"\n{Colors.BOLD}Memory Regions (Static Analysis):{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.GREEN}Code Section:{Colors.RESET}")
    print(f"  Start:  {load_addr:04X}H")
    print(f"  End:    {code_end - 1:04X}H")
    print(f"  Size:   {program_size} bytes")

    # Try to find data section from labels
    labels = getattr(asm_obj, "labeloff", {})
    data_labels = []
    for label, addr in labels.items():
        if addr >= code_end:
            data_labels.append((label, addr))

    if data_labels:
        print(f"\n{Colors.CYAN}Potential Data Section:{Colors.RESET}")
        for label, addr in sorted(data_labels, key=lambda x: x[1]):
            print(f"  {label:<20} @ {addr:04X}H")

    print()
