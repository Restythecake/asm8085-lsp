"""Assembler helpers (file loading + assembly diagnostics)."""

import re
import sys

from . import assembler
from .colors import Colors
from .syntax import (
    VALID_DIRECTIVES,
    VALID_INSTRUCTIONS,
    build_syntax_suggestions,
    find_similar_words,
)


def load_source_file(filename):
    """Read source file and return cleaned lines plus originals."""
    with open(filename) as f:
        lines = f.readlines()

    clean_lines = []
    original_lines = []
    for i, line in enumerate(lines, 1):
        original_lines.append((i, line.rstrip()))
        clean_line = line
        if ";" in clean_line:
            clean_line = clean_line[: clean_line.index(";")]
        clean_lines.append(clean_line.strip())
    return clean_lines, original_lines


def assemble_or_exit(filename, clean_lines, original_lines, args):
    """Assemble the provided lines or exit with detailed diagnostics."""
    asm_obj = assembler()
    success, error = asm_obj.assemble(clean_lines)

    if success:
        return asm_obj

    if isinstance(error, str):
        error_message = error
    else:
        error_message = str(error)

    # Try to find the failing line by assembling incrementally
    error_line = None
    for i in range(1, len(clean_lines) + 1):
        test_asm = assembler()
        test_success, test_error = test_asm.assemble(clean_lines[:i])
        if not test_success:
            # Found the failing line (skip empty lines)
            for j in range(i - 1, -1, -1):
                if clean_lines[j].strip():
                    error_line = j + 1
                    break
            break

    print(f"\n{Colors.RED}{'═' * 60}{Colors.RESET}")
    print(f"{Colors.RED}{Colors.BOLD}✗ ASSEMBLY ERROR{Colors.RESET}")
    print(f"{Colors.RED}{'═' * 60}{Colors.RESET}\n")

    if error_line:
        print(
            f"{Colors.BOLD}Error on line {error_line}:{Colors.RESET} {error_message}\n"
        )
    else:
        print(f"{Colors.BOLD}Error:{Colors.RESET} {error_message}\n")

    # Try to provide helpful suggestions using fuzzy matching
    suggestions = []
    error_line_text = None

    # Get the problematic line if we found it
    if error_line and error_line <= len(clean_lines):
        error_line_text = clean_lines[error_line - 1].strip()
        words = error_line_text.split()

        # Check if it's an opcode error
        if "opcode" in error_message.lower() and words:
            # First word might be the invalid instruction
            first_word = words[0].rstrip(":").upper()

            # Skip if it looks like a label (ends with colon in original)
            if not error_line_text.strip().startswith(first_word + ":"):
                similar = find_similar_words(
                    first_word, VALID_INSTRUCTIONS + VALID_DIRECTIVES, n=3, cutoff=0.5
                )
                if similar:
                    suggestions.append(
                        f"  {Colors.CYAN}Found:{Colors.RESET} {first_word}"
                    )
                    suggestions.append(
                        f"  {Colors.GREEN}Did you mean:{Colors.RESET} {', '.join(similar)}"
                    )

        # Check for unresolved labels
        elif "unresolved labels" in error_message.lower():
            # Extract label names from error message
            label_match = re.search(r"\['([^']+)'\]", error_message)
            if label_match:
                missing_label = label_match.group(1)
                # Get all defined labels from the assembler
                if hasattr(asm_obj, "labeloff") and asm_obj.labeloff:
                    defined_labels = list(asm_obj.labeloff.keys())
                    similar = find_similar_words(
                        missing_label, defined_labels, n=3, cutoff=0.5
                    )
                    if similar:
                        suggestions.append(
                            f"  {Colors.CYAN}Missing label:{Colors.RESET} {missing_label}"
                        )
                        suggestions.append(
                            f"  {Colors.GREEN}Did you mean:{Colors.RESET} {', '.join(similar)}"
                        )
                    else:
                        suggestions.append(
                            f"  {Colors.CYAN}Available labels:{Colors.RESET} {', '.join(defined_labels[:5])}"
                        )
                        if len(defined_labels) > 5:
                            suggestions.append(
                                f"    {Colors.DIM}... and {len(defined_labels) - 5} more{Colors.RESET}"
                            )

    if error_line_text:
        syntax_suggestions = build_syntax_suggestions(
            error_message, error_line_text, suggestions
        )
        if syntax_suggestions:
            suggestions.extend(syntax_suggestions)

    if suggestions:
        for suggestion in suggestions:
            print(suggestion)
        print()

    # Show source code context only in verbose mode
    if args.verbose:
        # Try to provide context by showing the source code with line numbers
        print(f"{Colors.BOLD}Source code:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

        # Show only ±5 lines around the error
        context_range = 5
        if error_line:
            start_line = max(1, error_line - context_range)
            end_line = min(len(original_lines), error_line + context_range)
        else:
            # If we can't find error line, show all
            start_line = 1
            end_line = len(original_lines)

        # Show ellipsis if we're not starting at the beginning
        if start_line > 1:
            print(f"{Colors.DIM}    ⋮{Colors.RESET}")

        # Show source with line numbers, highlighting the error line
        for line_num, line_content in original_lines:
            # Only show lines in the context range
            if line_num < start_line or line_num > end_line:
                continue

            # Skip empty lines in display
            if line_content.strip():
                if error_line and line_num == error_line:
                    # Highlight the error line
                    print(
                        f"{Colors.RED}{Colors.BOLD}{line_num:3d}│ {line_content}{Colors.RESET} {Colors.RED}← ERROR{Colors.RESET}"
                    )
                else:
                    print(f"{Colors.DIM}{line_num:3d}│{Colors.RESET} {line_content}")

        # Show ellipsis if we're not at the end
        if end_line < len(original_lines):
            print(f"{Colors.DIM}    ⋮{Colors.RESET}")

        print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}\n")

    if not args.verbose:
        print(f"\n{Colors.DIM}Tip: Use -v to see source code context{Colors.RESET}")

    print()
    sys.exit(1)
