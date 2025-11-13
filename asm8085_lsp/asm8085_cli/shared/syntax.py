"""syntax helpers extracted from asm8085."""

import difflib
import re

from .colors import Colors

# All valid 8085 instructions
VALID_INSTRUCTIONS = [
    # Data Transfer
    "MOV",
    "MVI",
    "LXI",
    "LDA",
    "STA",
    "LHLD",
    "SHLD",
    "LDAX",
    "STAX",
    "XCHG",
    # Arithmetic
    "ADD",
    "ADI",
    "ADC",
    "ACI",
    "SUB",
    "SUI",
    "SBB",
    "SBI",
    "INR",
    "DCR",
    "INX",
    "DCX",
    "DAD",
    "DAA",
    # Logical
    "ANA",
    "ANI",
    "ORA",
    "ORI",
    "XRA",
    "XRI",
    "CMP",
    "CPI",
    "RLC",
    "RRC",
    "RAL",
    "RAR",
    "CMA",
    "CMC",
    "STC",
    # Branch
    "JMP",
    "JC",
    "JNC",
    "JZ",
    "JNZ",
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
    "RET",
    "RC",
    "RNC",
    "RZ",
    "RNZ",
    "RP",
    "RM",
    "RPE",
    "RPO",
    "RST",
    "PCHL",
    # Stack
    "PUSH",
    "POP",
    "XTHL",
    "SPHL",
    # I/O and Machine Control
    "IN",
    "OUT",
    "EI",
    "DI",
    "HLT",
    "NOP",
    "RIM",
    "SIM",
]

# Valid assembler directives
VALID_DIRECTIVES = ["ORG", "DB", "DS", "EQU", "END"]

SYNTAX_RULES = {
    "MVI": {
        "pattern": "MVI <register>, <data>",
        "example": "MVI A, 05H",
        "requires_comma": True,
        "operand_count": 2,
        "comma_note": "missing comma",
        "comma_tip": "Add a comma between the register and the immediate byte.",
        "missing_operand_note": "missing immediate byte",
        "missing_operand_tip": "Provide an 8-bit value after the register.",
    },
    "MOV": {
        "pattern": "MOV <dest>, <source>",
        "example": "MOV B, A",
        "requires_comma": True,
        "operand_count": 2,
        "comma_note": "missing comma",
        "comma_tip": "Separate destination and source registers with a comma.",
        "missing_operand_note": "missing source register",
        "missing_operand_tip": "Specify both destination and source operands.",
    },
    "LXI": {
        "pattern": "LXI <pair>, <data16>",
        "example": "LXI H, 2050H",
        "requires_comma": True,
        "operand_count": 2,
        "comma_note": "missing comma",
        "comma_tip": "Add a comma between the register pair and the 16-bit value.",
        "missing_operand_note": "missing 16-bit value",
        "missing_operand_tip": "Provide a 16-bit address or literal after the register pair.",
    },
    "DB": {
        "pattern": "DB <byte1>, <byte2>, ...",
        "example": "DB 0AH, 0BH",
        "requires_comma": True,
        "operand_count": 1,
        "comma_note": "separate byte values with commas",
        "comma_tip": "List each byte separated by commas (DB 0AH, 0BH, 0CH).",
        "missing_operand_note": "missing byte value",
        "missing_operand_tip": "Provide at least one byte value after DB.",
    },
    "ADD": {
        "pattern": "ADD <register>",
        "example": "ADD B",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing source register",
        "missing_operand_tip": "Provide a register operand such as B, C, or M.",
    },
    "ANA": {
        "pattern": "ANA <register>",
        "example": "ANA M",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing source operand",
        "missing_operand_tip": "Specify the register or memory reference to AND with A.",
    },
    "ADI": {
        "pattern": "ADI <data>",
        "example": "ADI 05H",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing immediate byte",
        "missing_operand_tip": "Provide an 8-bit immediate value (e.g., 05H).",
    },
    "STA": {
        "pattern": "STA <address>",
        "example": "STA 2050H",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing destination address",
        "missing_operand_tip": "Provide a 16-bit address like 2050H.",
    },
    "LDA": {
        "pattern": "LDA <address>",
        "example": "LDA 2050H",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing source address",
        "missing_operand_tip": "Provide a 16-bit address like 2050H.",
    },
    "INR": {
        "pattern": "INR <register>",
        "example": "INR M",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing register operand",
        "missing_operand_tip": "Provide the register or memory reference to increment.",
    },
    "DCR": {
        "pattern": "DCR <register>",
        "example": "DCR B",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing register operand",
        "missing_operand_tip": "Provide the register or memory reference to decrement.",
    },
    "ORG": {
        "pattern": "ORG <address>",
        "example": "ORG 0800H",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing start address",
        "missing_operand_tip": "Provide a load address such as 0800H.",
    },
    "DS": {
        "pattern": "DS <count>",
        "example": "DS 16",
        "requires_comma": False,
        "operand_count": 1,
        "missing_operand_note": "missing storage length",
        "missing_operand_tip": "Specify how many bytes to reserve (e.g., DS 16).",
    },
}

SYNTAX_ERROR_KEYWORDS = [
    "invalid args",
    "not enough args",
    "was expecting a comma",
    "was expecting bytes",
    "was expecting shorts",
    "was expecting a byte arg",
    "was expecting two bytes arg",
    "was expecting a reg arg",
]


def strip_label_prefix(line):
    """Remove an optional leading label (LABEL:) from a source line."""
    if not line:
        return ""
    match = re.match(r"\s*([A-Za-z_][\w]*):\s*(.*)", line)
    if match:
        return match.group(2)
    return line


def build_syntax_suggestions(error_message, line_text, existing_suggestions):
    """Generate context-aware syntax hints for common operand mistakes."""
    if not line_text:
        return []

    error_lower = error_message.lower()
    if not any(keyword in error_lower for keyword in SYNTAX_ERROR_KEYWORDS):
        return []

    trimmed_line = strip_label_prefix(line_text).strip()
    if not trimmed_line:
        return []

    tokens = re.split(r"\s+", trimmed_line)
    if not tokens:
        return []

    opcode = tokens[0].upper()
    rule = SYNTAX_RULES.get(opcode)
    if not rule:
        return []

    operands = tokens[1:]
    required_operands = rule.get("operand_count")
    requires_comma = rule.get("requires_comma", False)
    display_line = trimmed_line if trimmed_line else line_text.strip()
    suggestions = []

    has_found_line = any("Found:" in s for s in existing_suggestions)

    if requires_comma and "," not in trimmed_line and required_operands:
        if len(operands) >= required_operands:
            if display_line and not has_found_line:
                suggestions.append(f"  {Colors.CYAN}Found:{Colors.RESET} {display_line}")
            expected = rule.get("example") or rule.get("pattern") or f"{opcode} ..."
            note = rule.get("comma_note")
            if note:
                expected = f"{expected}  ({note})"
            suggestions.append(f"  {Colors.GREEN}Expected:{Colors.RESET} {expected}")
            comma_tip = rule.get("comma_tip")
            if comma_tip:
                suggestions.append(f"  {Colors.GREEN}Tip:{Colors.RESET} {comma_tip}")
            return suggestions

    if required_operands and len(operands) < required_operands:
        if display_line and not has_found_line:
            suggestions.append(f"  {Colors.CYAN}Found:{Colors.RESET} {display_line}")
        expected = rule.get("example") or rule.get("pattern") or f"{opcode} ..."
        note = rule.get("missing_operand_note")
        if note:
            expected = f"{expected}  ({note})"
        suggestions.append(f"  {Colors.GREEN}Expected:{Colors.RESET} {expected}")
        missing_tip = rule.get("missing_operand_tip")
        if missing_tip:
            suggestions.append(f"  {Colors.GREEN}Tip:{Colors.RESET} {missing_tip}")
        return suggestions

    return []


def find_similar_words(word, word_list, n=3, cutoff=0.6):
    """Find similar words using fuzzy matching

    Args:
        word: The word to match
        word_list: List of valid words
        n: Maximum number of suggestions
        cutoff: Similarity threshold (0-1)

    Returns:
        List of similar words
    """
    word_upper = word.upper()
    matches = difflib.get_close_matches(word_upper, word_list, n=n, cutoff=cutoff)
    return matches


BRANCH_OPS = {"JMP", "JC", "JNC", "JZ", "JNZ", "JP", "JM", "JPE", "JPO"}
CALL_OPS = {"CALL", "CC", "CNC", "CZ", "CNZ", "CP", "CM", "CPE", "CPO"}
CONDITIONAL_JUMPS = {"JC", "JNC", "JZ", "JNZ", "JP", "JM", "JPE", "JPO"}
CONDITIONAL_CALLS = {"CC", "CNC", "CZ", "CNZ", "CP", "CM", "CPE", "CPO"}
CONDITIONAL_RETURNS = {"RC", "RNC", "RZ", "RNZ", "RP", "RM", "RPE", "RPO"}
CONDITIONAL_BRANCHES = CONDITIONAL_JUMPS | CONDITIONAL_CALLS | CONDITIONAL_RETURNS
