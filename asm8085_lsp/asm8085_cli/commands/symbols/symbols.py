"""Symbol and label explorer for 8085 assembly programs."""

import sys

from ...shared.assembly import assemble_or_exit, load_source_file
from ...shared.colors import Colors


def explore_symbols(filename, args):
    """Explore all symbols/labels in an assembly program.

    Args:
        filename: Path to assembly file
        args: Command line arguments
    """
    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    # Extract labels from assembler
    labels = getattr(asm_obj, "labeloff", {})

    if not labels:
        print(f"{Colors.YELLOW}No labels found in {filename}{Colors.RESET}")
        return

    # Build cross-reference map
    label_references = build_cross_references(clean_lines, labels)

    # Display results
    print(f"\n{Colors.BLUE}{Colors.BOLD}Symbol Table for {filename}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}\n")

    # Sort labels by address
    sorted_labels = sorted(labels.items(), key=lambda x: x[1])

    print(f"{Colors.BOLD}{'Label':<20} {'Address':<10} {'References'}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")

    for label, address in sorted_labels:
        refs = label_references.get(label.upper(), [])
        ref_count = len(refs)

        # Format address
        addr_str = f"{Colors.CYAN}{address:04X}H{Colors.RESET}"

        # Format reference count
        if ref_count == 0:
            ref_str = f"{Colors.DIM}(unused){Colors.RESET}"
        elif ref_count == 1:
            ref_str = f"{Colors.GREEN}1 reference{Colors.RESET}"
        else:
            ref_str = f"{Colors.GREEN}{ref_count} references{Colors.RESET}"

        print(f"{label:<20} {addr_str:<20} {ref_str}")

        # Show where it's referenced (if verbose)
        if args.verbose and ref_count > 0:
            for ref_line in refs[:5]:  # Show first 5 references
                line_text = (
                    clean_lines[ref_line - 1] if ref_line <= len(clean_lines) else ""
                )
                print(
                    f"  {Colors.DIM}Line {ref_line:3d}: {line_text[:50]}{Colors.RESET}"
                )
            if ref_count > 5:
                print(f"  {Colors.DIM}... and {ref_count - 5} more{Colors.RESET}")

    print(f"\n{Colors.DIM}{'─' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Total labels: {len(labels)}")

    unused = [l for l, refs in label_references.items() if not refs]
    if unused:
        print(f"  {Colors.YELLOW}Unused labels: {len(unused)}{Colors.RESET}")

    print()


def build_cross_references(clean_lines, labels):
    """Build cross-reference map showing where labels are used.

    Args:
        clean_lines: Cleaned assembly source lines
        labels: Dictionary of label -> address

    Returns:
        Dictionary of label -> list of line numbers where it's referenced
    """
    # Instructions that reference labels
    label_instructions = [
        "JMP",
        "JZ",
        "JNZ",
        "JC",
        "JNC",
        "JP",
        "JM",
        "JPE",
        "JPO",
        "CALL",
        "CC",
        "CNC",
        "CZ",
        "CNZ",
        "CP",
        "CM",
        "CPE",
        "CPO",
    ]

    references = {label.upper(): [] for label in labels.keys()}

    for line_num, line in enumerate(clean_lines, 1):
        line_upper = line.upper().strip()

        # Skip label definitions (they have : at the end or start of line)
        if ":" in line_upper:
            continue

        # Check each instruction
        for instr in label_instructions:
            if line_upper.startswith(instr + " "):
                # Extract the operand (label name)
                parts = line_upper.split()
                if len(parts) >= 2:
                    operand = parts[1].strip().rstrip(",")
                    if operand in references:
                        references[operand].append(line_num)

    return references


def list_symbols_summary(filename, args):
    """Show quick summary of symbols.

    Args:
        filename: Path to assembly file
        args: Command line arguments
    """
    clean_lines, original_lines = load_source_file(filename)
    asm_obj = assemble_or_exit(filename, clean_lines, original_lines, args)

    labels = getattr(asm_obj, "labeloff", {})

    if not labels:
        print(f"{Colors.YELLOW}No labels found{Colors.RESET}")
        return

    # Group by address range
    code_labels = []
    data_labels = []

    # Heuristic: labels at higher addresses are likely data
    # (this is a simple heuristic, not always accurate)
    load_addr = asm_obj.ploadoff
    program_size = sum(asm_obj.writtenaddresses)
    program_end = load_addr + program_size

    for label, address in labels.items():
        if address < program_end:
            code_labels.append((label, address))
        else:
            data_labels.append((label, address))

    print(f"\n{Colors.BOLD}Labels Summary:{Colors.RESET}")
    print(f"  Code labels: {Colors.GREEN}{len(code_labels)}{Colors.RESET}")
    print(f"  Data labels: {Colors.CYAN}{len(data_labels)}{Colors.RESET}")
    print(f"  Total: {len(labels)}")

    if code_labels:
        print(f"\n{Colors.BOLD}Code Labels:{Colors.RESET}")
        for label, addr in sorted(code_labels, key=lambda x: x[1])[:10]:
            print(f"  {label:<20} {Colors.CYAN}{addr:04X}H{Colors.RESET}")
        if len(code_labels) > 10:
            print(f"  {Colors.DIM}... and {len(code_labels) - 10} more{Colors.RESET}")

    if data_labels:
        print(f"\n{Colors.BOLD}Data Labels:{Colors.RESET}")
        for label, addr in sorted(data_labels, key=lambda x: x[1])[:10]:
            print(f"  {label:<20} {Colors.CYAN}{addr:04X}H{Colors.RESET}")
        if len(data_labels) > 10:
            print(f"  {Colors.DIM}... and {len(data_labels) - 10} more{Colors.RESET}")

    print()
