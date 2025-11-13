"""Static analysis helpers (warnings & heuristics)."""

import re

from ...shared.disasm import get_instruction_cycles
from ...shared.syntax import (
    BRANCH_OPS,
    CALL_OPS,
    VALID_INSTRUCTIONS,
    strip_label_prefix,
)

TRACKED_REGISTERS = {"B", "C", "D", "E"}
REGISTER_PAIR_COMPONENTS = {
    "B": ("B", "C"),
    "D": ("D", "E"),
    "H": ("H", "L"),
}
STACK_OPS = {"PUSH", "POP", "XTHL"}
RETURN_OPS = {"RET", "RC", "RNC", "RZ", "RNZ", "RP", "RM", "RPE", "RPO"}

WARN_SEVERITIES = {"error": 1, "warning": 2, "info": 3, "hint": 4}
FLAG_PROGRESS_OPS = {
    "INR",
    "DCR",
    "INX",
    "DCX",
    "DAD",
    "ADI",
    "ACI",
    "SUI",
    "SBI",
    "ADD",
    "ADC",
    "SUB",
    "SBB",
    "ANA",
    "ANI",
    "ORA",
    "ORI",
    "XRA",
    "XRI",
    "CMP",
    "CPI",
    "CMA",
    "MVI",
}


def make_warning(line, category, message, severity="warning"):
    severity_key = severity if severity in WARN_SEVERITIES else "warning"
    return {
        "line": line,
        "type": category,
        "severity": severity_key,
        "message": message,
    }


def parse_immediate_value(token):
    """Convert an immediate operand token (e.g., 05H or 10) into an integer."""
    if not token:
        return None
    token = token.strip().upper()
    try:
        if token.endswith("H"):
            return int(token[:-1], 16)
        return int(token, 10)
    except ValueError:
        return None


def add_pair_components(token, target_set):
    """Add the registers that comprise a register pair (e.g., B -> B,C)."""
    pair = REGISTER_PAIR_COMPONENTS.get(token)
    if not pair:
        return
    for reg in pair:
        if reg in TRACKED_REGISTERS:
            target_set.add(reg)


def get_register_usage(opcode, operands):
    """Return heuristic sets of registers read and written by an instruction."""
    opcode = opcode.upper()
    reads = set()
    writes = set()
    operands = [op.upper() for op in operands]

    if not operands:
        return reads, writes

    first = operands[0]

    if opcode == "MVI":
        if first in TRACKED_REGISTERS:
            writes.add(first)
    elif opcode == "MOV":
        if len(operands) >= 2:
            dest, src = operands[0], operands[1]
            if dest in TRACKED_REGISTERS:
                writes.add(dest)
            if src in TRACKED_REGISTERS:
                reads.add(src)
    elif opcode == "LXI":
        add_pair_components(first, writes)
    elif opcode in {"INR", "DCR"}:
        if first in TRACKED_REGISTERS:
            reads.add(first)
            writes.add(first)
    elif opcode in {"INX", "DCX"}:
        add_pair_components(first, reads)
        add_pair_components(first, writes)
    elif opcode == "DAD":
        add_pair_components(first, reads)
        # HL gets updated by DAD
        add_pair_components("H", reads)
        add_pair_components("H", writes)
    else:
        for operand in operands:
            if operand in TRACKED_REGISTERS:
                reads.add(operand)

    return reads, writes


def estimate_program_cycles(asm_obj):
    """Estimate the total T-states for the assembled program."""
    if not hasattr(asm_obj, "poffset") or not hasattr(asm_obj, "plsize"):
        return 0, 0

    memory = getattr(asm_obj, "pmemory", None)
    if memory is None:
        return 0, 0

    total_cycles = 0
    instruction_count = 0

    for addr, size in zip(asm_obj.poffset, asm_obj.plsize):
        if size <= 0:
            continue
        cycles = get_instruction_cycles(memory, addr)
        total_cycles += cycles
        instruction_count += 1

    return instruction_count, total_cycles


def tokenize_instruction_line(line):
    """Return uppercase tokens for the instruction portion of a line."""
    code_only = line.split(";", 1)[0]
    instruction_text = strip_label_prefix(code_only).strip()
    if not instruction_text:
        return []
    return [tok for tok in re.split(r"[,\s]+", instruction_text.upper()) if tok]


def loop_body_has_flag_progress(clean_lines, start_line, end_line):
    """Heuristically detect whether a loop mutates flags/registers between bounds."""
    if start_line is None or end_line is None:
        return False
    start_idx = max(start_line - 1, 0)
    end_idx = max(end_line - 1, 0)
    if start_idx >= len(clean_lines) or start_idx >= end_idx:
        return False
    for idx in range(start_idx, min(end_idx, len(clean_lines))):
        tokens = tokenize_instruction_line(clean_lines[idx])
        if not tokens:
            continue
        opcode = tokens[0]
        if opcode in FLAG_PROGRESS_OPS:
            return True
    return False


def classify_loop_warning(loop_line, instr, target, target_line, clean_lines):
    """Return severity/message for a detected backward branch."""
    has_progress = loop_body_has_flag_progress(clean_lines, target_line, loop_line)
    if instr == "JMP":
        severity = "warning"
        message = f"Tight JMP loop back to {target}. Ensure a terminating condition or use profiling (-t)."
    elif has_progress:
        severity = "info"
        message = f"Loop detected via {instr} {target}. Condition updated inside loop; profile costs with -t or -s -r."
    else:
        severity = "warning"
        message = f"Loop detected via {instr} {target} but no obvious flag updates inside; double-check termination."
    return severity, message


def analyze_warnings(clean_lines, asm_obj):
    """Analyze assembled code for potential issues

    Args:
        clean_lines: List of cleaned source lines
        asm_obj: The assembler object with symbol table

    Returns:
        List of warning dicts with keys: line, type, severity, message
    """
    warnings = []

    defined_labels = {
        label.upper() for label in getattr(asm_obj, "labeloff", {}).keys()
    }
    referenced_labels = set()
    label_def_lines = {}
    pending_registers = {}
    loop_jumps = []
    last_jump = None  # Track consecutive JMP targets
    sp_initialized = False
    stack_warning_issued = False
    return_found = False
    last_instruction_line = None

    hlt_found = False
    hlt_line = None

    for line_num, line in enumerate(clean_lines, 1):
        # Remove comments
        code_only = line.split(";", 1)[0]
        line_upper = code_only.upper().strip()
        if not line_upper:
            continue

        label_match = re.match(r"\s*([A-Za-z_][\w]*):", code_only)
        if label_match:
            label_name = label_match.group(1).upper()
            label_def_lines[label_name] = line_num
            defined_labels.add(label_name)

        words = line_upper.split()

        # Track HLT instruction
        if not hlt_found and "HLT" in words:
            hlt_found = True
            hlt_line = line_num

        # Check for code after HLT
        elif hlt_found and hlt_line and line_num > hlt_line:
            if words and not (len(words) == 1 and words[0].endswith(":")):
                for word in words:
                    if word in VALID_INSTRUCTIONS:
                        warnings.append(
                            make_warning(
                                line_num,
                                "unreachable",
                                "Code after HLT is unreachable",
                            )
                        )
                        break

        # Jump and call tracking
        for i, word in enumerate(words):
            if word in BRANCH_OPS or word in CALL_OPS:
                if i + 1 >= len(words):
                    continue
                potential_label = words[i + 1].rstrip(",")
                if potential_label.endswith("H") or potential_label.startswith("0X"):
                    continue
                label_upper = potential_label.upper()
                referenced_labels.add(label_upper)
                if word in BRANCH_OPS:
                    target_line = label_def_lines.get(label_upper)
                    if target_line and target_line < line_num:
                        loop_jumps.append(
                            {
                                "line": line_num,
                                "instr": word,
                                "target": potential_label,
                                "target_line": target_line,
                            }
                        )

        # Tokenize instruction portion (strip leading label first)
        instruction_text = strip_label_prefix(code_only).strip()
        if not instruction_text:
            continue

        tokens = [tok for tok in re.split(r"[,\s]+", instruction_text.upper()) if tok]
        if not tokens:
            continue

        opcode = tokens[0]
        operands = tokens[1:]
        last_instruction_line = line_num

        if opcode == "LXI" and operands and operands[0] == "SP":
            sp_initialized = True
        elif opcode == "SPHL":
            sp_initialized = True

        uses_stack = (
            opcode in STACK_OPS
            or opcode == "RST"
            or opcode in CALL_OPS
            or opcode in RETURN_OPS
        )
        if uses_stack and not sp_initialized and not stack_warning_issued:
            warnings.append(
                make_warning(
                    line_num,
                    "stack",
                    "Stack pointer is used before being initialized (add `LXI SP, address`).",
                )
            )
            stack_warning_issued = True

        if opcode in RETURN_OPS:
            return_found = True

        # Register usage tracking (only for B/C/D/E families)
        reads, writes = get_register_usage(opcode, operands)
        for reg in reads:
            pending_registers.pop(reg, None)
        for reg in writes:
            if reg in pending_registers:
                prev_line, _ = pending_registers.pop(reg)
                warnings.append(
                    make_warning(
                        prev_line,
                        "unused-register",
                        f"Register {reg} was loaded but overwritten before being read",
                        severity="info",
                    )
                )
            pending_registers[reg] = (line_num, opcode)

        # Redundant MOV detection
        if opcode == "MOV" and len(operands) >= 2:
            dest, src = operands[0], operands[1]
            if dest == src:
                warnings.append(
                    make_warning(
                        line_num,
                        "redundant",
                        f"Redundant operation: MOV {dest}, {src}",
                        severity="hint",
                    )
                )

        # Consecutive identical JMP detection
        if opcode == "JMP" and operands:
            target = operands[0]
            if last_jump and last_jump["target"] == target:
                warnings.append(
                    make_warning(
                        line_num,
                        "redundant",
                        f"Duplicate JMP to {target}; previous jump at line {last_jump['line']} already transfers control.",
                        severity="hint",
                    )
                )
            last_jump = {"line": line_num, "target": target}
        else:
            last_jump = None

        # XRA vs MVI for clearing accumulator
        if opcode == "MVI" and len(operands) >= 2 and operands[0] == "A":
            value = parse_immediate_value(operands[1])
            if value == 0:
                warnings.append(
                    make_warning(
                        line_num,
                        "optimization",
                        "Consider using XRA A instead of MVI A, 00H (saves 3 cycles)",
                        severity="hint",
                    )
                )

        # Suggest INR/DCR when adding/subtracting 1 via immediate instructions
        if opcode in {"ADI", "ACI"} and operands:
            value = parse_immediate_value(operands[-1])
            if value == 1:
                warnings.append(
                    make_warning(
                        line_num,
                        "optimization",
                        "INR A is faster than ADI/ACI 01H when carry flag updates are optional",
                        severity="hint",
                    )
                )

        if opcode in {"SUI", "SBI"} and operands:
            value = parse_immediate_value(operands[-1])
            if value == 1:
                warnings.append(
                    make_warning(
                        line_num,
                        "optimization",
                        "DCR A is faster than SUI/SBI 01H when borrow handling is optional",
                        severity="hint",
                    )
                )

    # Check for unused labels
    unused_labels = defined_labels - referenced_labels
    for label in unused_labels:
        line_defined = label_def_lines.get(label)
        if line_defined:
            warnings.append(
                make_warning(
                    line_defined,
                    "unused",
                    f"Label '{label}' defined but never used",
                    severity="info",
                )
            )

    # Loop/profiling suggestions
    for loop in loop_jumps[:3]:
        severity, message = classify_loop_warning(
            loop.get("line"),
            loop.get("instr"),
            loop.get("target"),
            loop.get("target_line"),
            clean_lines,
        )
        warnings.append(
            make_warning(loop.get("line"), "profiling", message, severity=severity)
        )

    if not (hlt_found or return_found):
        line_hint = last_instruction_line or len(clean_lines) or 1
        warnings.append(
            make_warning(
                line_hint,
                "termination",
                "Program has no terminating instruction (HLT/RET).",
            )
        )

    _, total_cycles = estimate_program_cycles(asm_obj)
    if total_cycles >= 600:
        warnings.append(
            make_warning(
                1,
                "profiling",
                f"Program is estimated at ~{total_cycles} T-states. Consider profiling hotspots (-t or -s -r).",
                severity="info",
            )
        )

    # Sort warnings by line number
    warnings.sort(key=lambda x: x.get("line", 0))

    return warnings
