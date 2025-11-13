"""explain helpers extracted from asm8085."""

import sys

from ...shared.colors import Colors
from ...shared.instruction_db import INSTRUCTION_DB
from ...shared.syntax import find_similar_words


def format_value(val, bits, base):
    """Format a value in the specified base

    Args:
        val: The value to format
        bits: Number of bits (8 or 16)
        base: 2 (binary), 10 (decimal), or 16 (hexadecimal)

    Returns:
        Formatted string
    """
    if base == 16:
        if bits == 8:
            return f"{val:02X}H"
        else:  # 16 bits
            return f"{val:04X}H"
    elif base == 10:
        return f"{val}"
    elif base == 2:
        if bits == 8:
            return f"{val:08b}₂"
        else:  # 16 bits
            return f"{val:016b}₂"
    return str(val)


def explain_instruction(instr, cpu_before, cpu_after, memory, base=16):
    """Generate a mathematical explanation of what the instruction does

    Args:
        instr: The disassembled instruction string
        cpu_before: CPU state before execution (dict with A, B, C, D, E, H, L, F, PC, SP)
        cpu_after: CPU state after execution
        memory: Memory array for memory operations
        base: Number base for display (2, 10, or 16)

    Returns:
        String with mathematical notation explaining the operation
    """
    parts = instr.split()
    if not parts:
        return ""

    op = parts[0]

    # Helper to format 8-bit values
    def fmt8(val):
        return format_value(val, 8, base)

    # Helper to format 16-bit values
    def fmt16(val):
        return format_value(val, 16, base)

    # Helper to format addresses (always hex for readability)
    def fmt_addr(val):
        return f"{val:04X}H"

    # MOV operations
    if op == "MOV" and len(parts) >= 2:
        args = parts[1].replace(",", "").split()
        if len(args) == 2:
            dst, src = args[0], args[1]
            if src == "M":
                addr = (cpu_before["H"] << 8) | cpu_before["L"]
                val = (
                    memory[addr].value
                    if hasattr(memory[addr], "value")
                    else memory[addr]
                )
                return f"{dst} ← [HL] = [{fmt_addr(addr)}] = {fmt8(val)}"
            elif dst == "M":
                addr = (cpu_before["H"] << 8) | cpu_before["L"]
                return f"[HL] = [{fmt_addr(addr)}] ← {src} = {fmt8(cpu_before[src])}"
            else:
                return f"{dst} ← {src} = {fmt8(cpu_before[src])}"

    # MVI operations
    elif op == "MVI" and len(parts) >= 2:
        args = instr.split()[1].split(",")
        if len(args) == 2:
            reg = args[0].strip()
            val = args[1].strip()
            return f"{reg} ← {val}"

    # LXI operations
    elif op == "LXI" and len(parts) >= 2:
        args = instr.split()[1].split(",")
        if len(args) == 2:
            reg = args[0].strip()
            val = args[1].strip()
            return f"{reg} ← {val}"

    # Load operations
    elif op == "LDA":
        addr = int(parts[1].rstrip("H"), 16) if "H" in parts[1] else int(parts[1], 16)
        val = cpu_after["A"]
        return f"A ← [{fmt_addr(addr)}] = {fmt8(val)}"

    elif op == "LDAX":
        if parts[1] == "B":
            addr = (cpu_before["B"] << 8) | cpu_before["C"]
        else:  # D
            addr = (cpu_before["D"] << 8) | cpu_before["E"]
        val = cpu_after["A"]
        return f"A ← [{parts[1]}] = [{addr:04X}H] = {val:02X}H"

    elif op == "LHLD":
        addr = int(parts[1].rstrip("H"), 16) if "H" in parts[1] else int(parts[1], 16)
        return f"L ← [{addr:04X}H] = {cpu_after['L']:02X}H, H ← [{addr + 1:04X}H] = {cpu_after['H']:02X}H"

    # Store operations
    elif op == "STA":
        addr = int(parts[1].rstrip("H"), 16) if "H" in parts[1] else int(parts[1], 16)
        return f"[{fmt_addr(addr)}] ← A = {fmt8(cpu_before['A'])}"

    elif op == "STAX":
        if parts[1] == "B":
            addr = (cpu_before["B"] << 8) | cpu_before["C"]
        else:  # D
            addr = (cpu_before["D"] << 8) | cpu_before["E"]
        return f"[{parts[1]}] = [{addr:04X}H] ← A = {cpu_before['A']:02X}H"

    elif op == "SHLD":
        addr = int(parts[1].rstrip("H"), 16) if "H" in parts[1] else int(parts[1], 16)
        return f"[{addr:04X}H] ← L = {cpu_before['L']:02X}H, [{addr + 1:04X}H] ← H = {cpu_before['H']:02X}H"

    # Arithmetic operations
    elif op == "ADD":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A + [HL] = {fmt8(cpu_before['A'])} + {fmt8(src_val)} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A + {src} = {fmt8(cpu_before['A'])} + {fmt8(cpu_before[src])} = {fmt8(cpu_after['A'])}"

    elif op == "ADI":
        val = parts[1]
        val_int = int(val.rstrip("H"), 16) if "H" in val else int(val, 16)
        return f"A ← A + {val} = {fmt8(cpu_before['A'])} + {fmt8(val_int)} = {fmt8(cpu_after['A'])}"

    elif op == "ADC":
        src = parts[1] if len(parts) > 1 else "M"
        carry = cpu_before["F"] & 1
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A + [HL] + CY = {fmt8(cpu_before['A'])} + {fmt8(src_val)} + {carry} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A + {src} + CY = {fmt8(cpu_before['A'])} + {fmt8(cpu_before[src])} + {carry} = {fmt8(cpu_after['A'])}"

    elif op == "SUB":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A - [HL] = {fmt8(cpu_before['A'])} - {fmt8(src_val)} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A - {src} = {fmt8(cpu_before['A'])} - {fmt8(cpu_before[src])} = {fmt8(cpu_after['A'])}"

    elif op == "SUI":
        val = parts[1]
        val_int = int(val.rstrip("H"), 16) if "H" in val else int(val, 16)
        return f"A ← A - {val} = {fmt8(cpu_before['A'])} - {fmt8(val_int)} = {fmt8(cpu_after['A'])}"

    # Increment/Decrement
    elif op == "INR":
        reg = parts[1] if len(parts) > 1 else "A"
        if reg == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            before_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            after_val = (before_val + 1) & 0xFF
            return f"[HL] = [{fmt_addr(addr)}] ← [HL] + 1 = {fmt8(before_val)} + 1 = {fmt8(after_val)}"
        else:
            return f"{reg} ← {reg} + 1 = {fmt8(cpu_before[reg])} + 1 = {fmt8(cpu_after[reg])}"

    elif op == "DCR":
        reg = parts[1] if len(parts) > 1 else "A"
        if reg == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            before_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            after_val = (before_val - 1) & 0xFF
            return f"[HL] = [{fmt_addr(addr)}] ← [HL] - 1 = {fmt8(before_val)} - 1 = {fmt8(after_val)}"
        else:
            return f"{reg} ← {reg} - 1 = {fmt8(cpu_before[reg])} - 1 = {fmt8(cpu_after[reg])}"

    elif op == "INX":
        reg = parts[1] if len(parts) > 1 else "B"
        if reg == "SP":
            return f"SP ← SP + 1 = {fmt16(cpu_before['SP'])} + 1 = {fmt16(cpu_after['SP'])}"
        else:
            # Get 16-bit value before/after
            if reg == "B":
                before_val = (cpu_before["B"] << 8) | cpu_before["C"]
                after_val = (cpu_after["B"] << 8) | cpu_after["C"]
                return f"BC ← BC + 1 = {fmt16(before_val)} + 1 = {fmt16(after_val)}"
            elif reg == "D":
                before_val = (cpu_before["D"] << 8) | cpu_before["E"]
                after_val = (cpu_after["D"] << 8) | cpu_after["E"]
                return f"DE ← DE + 1 = {fmt16(before_val)} + 1 = {fmt16(after_val)}"
            elif reg == "H":
                before_val = (cpu_before["H"] << 8) | cpu_before["L"]
                after_val = (cpu_after["H"] << 8) | cpu_after["L"]
                return f"HL ← HL + 1 = {fmt16(before_val)} + 1 = {fmt16(after_val)}"

    elif op == "DCX":
        reg = parts[1] if len(parts) > 1 else "B"
        if reg == "SP":
            return f"SP ← SP - 1 = {fmt16(cpu_before['SP'])} - 1 = {fmt16(cpu_after['SP'])}"
        else:
            # Get 16-bit value before/after
            if reg == "B":
                before_val = (cpu_before["B"] << 8) | cpu_before["C"]
                after_val = (cpu_after["B"] << 8) | cpu_after["C"]
                return f"BC ← BC - 1 = {fmt16(before_val)} - 1 = {fmt16(after_val)}"
            elif reg == "D":
                before_val = (cpu_before["D"] << 8) | cpu_before["E"]
                after_val = (cpu_after["D"] << 8) | cpu_after["E"]
                return f"DE ← DE - 1 = {fmt16(before_val)} - 1 = {fmt16(after_val)}"
            elif reg == "H":
                before_val = (cpu_before["H"] << 8) | cpu_before["L"]
                after_val = (cpu_after["H"] << 8) | cpu_after["L"]
                return f"HL ← HL - 1 = {fmt16(before_val)} - 1 = {fmt16(after_val)}"

    # Logical operations
    elif op == "ANA":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A ∧ [HL] = {fmt8(cpu_before['A'])} ∧ {fmt8(src_val)} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A ∧ {src} = {fmt8(cpu_before['A'])} ∧ {fmt8(cpu_before[src])} = {fmt8(cpu_after['A'])}"

    elif op == "ORA":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A ∨ [HL] = {fmt8(cpu_before['A'])} ∨ {fmt8(src_val)} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A ∨ {src} = {fmt8(cpu_before['A'])} ∨ {fmt8(cpu_before[src])} = {fmt8(cpu_after['A'])}"

    elif op == "XRA":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"A ← A ⊕ [HL] = {fmt8(cpu_before['A'])} ⊕ {fmt8(src_val)} = {fmt8(cpu_after['A'])}"
        else:
            return f"A ← A ⊕ {src} = {fmt8(cpu_before['A'])} ⊕ {fmt8(cpu_before[src])} = {fmt8(cpu_after['A'])}"

    elif op == "CMP":
        src = parts[1] if len(parts) > 1 else "M"
        if src == "M":
            addr = (cpu_before["H"] << 8) | cpu_before["L"]
            src_val = (
                memory[addr].value if hasattr(memory[addr], "value") else memory[addr]
            )
            return f"Compare: A - [HL] = {fmt8(cpu_before['A'])} - {fmt8(src_val)} (set flags only)"
        else:
            return f"Compare: A - {src} = {fmt8(cpu_before['A'])} - {fmt8(cpu_before[src])} (set flags only)"

    elif op == "CMA":
        return f"A ← ¬A = ¬{fmt8(cpu_before['A'])} = {fmt8(cpu_after['A'])}"

    # Jump operations
    elif op in ["JMP", "JC", "JNC", "JZ", "JNZ", "JP", "JM", "JPE", "JPO"]:
        addr = parts[1] if len(parts) > 1 else "????"
        condition = ""
        if op == "JC":
            condition = " if CY=1"
        elif op == "JNC":
            condition = " if CY=0"
        elif op == "JZ":
            condition = " if Z=1"
        elif op == "JNZ":
            condition = " if Z=0"
        elif op == "JP":
            condition = " if S=0"
        elif op == "JM":
            condition = " if S=1"
        elif op == "JPE":
            condition = " if P=1"
        elif op == "JPO":
            condition = " if P=0"

        jumped = cpu_after["PC"] == int(addr.rstrip("H"), 16) if "H" in addr else False
        return f"PC ← {addr}{condition} {'✓ taken' if jumped else '✗ not taken'}"

    # Call/Return
    elif op in ["CALL", "CC", "CNC", "CZ", "CNZ", "CP", "CM", "CPE", "CPO"]:
        addr = parts[1] if len(parts) > 1 else "????"
        return f"[SP] ← PC, SP ← SP - 2, PC ← {addr}"

    elif op in ["RET", "RC", "RNC", "RZ", "RNZ", "RP", "RM", "RPE", "RPO"]:
        return f"PC ← [SP], SP ← SP + 2 (return to {cpu_after['PC']:04X}H)"

    # Stack operations
    elif op == "PUSH":
        reg = parts[1] if len(parts) > 1 else "PSW"
        return f"[SP-1] ← {reg}_high, [SP-2] ← {reg}_low, SP ← SP - 2"

    elif op == "POP":
        reg = parts[1] if len(parts) > 1 else "PSW"
        return f"{reg}_low ← [SP], {reg}_high ← [SP+1], SP ← SP + 2"

    # I/O
    elif op == "IN":
        port = parts[1] if len(parts) > 1 else "??"
        return f"A ← Input(Port {port})"

    elif op == "OUT":
        port = parts[1] if len(parts) > 1 else "??"
        return f"Output(Port {port}) ← A = {cpu_before['A']:02X}H"

    # Other
    elif op == "HLT":
        return "⏸ HALT - Stop execution"

    elif op == "NOP":
        return "No operation"

    elif op == "XCHG":
        return "H ↔ D, L ↔ E (exchange DE and HL)"

    # Default
    return ""


def explain_instruction_detailed(instruction_str):
    """Provide detailed explanation of an 8085 instruction

    Args:
        instruction_str: The instruction to explain (e.g., "MVI A, 05H")

    Returns:
        None (prints explanation and exits)
    """
    parts = instruction_str.upper().strip().split()
    if not parts:
        print(f"{Colors.RED}Error:{Colors.RESET} No instruction provided")
        sys.exit(1)

    op = parts[0]

    # Instruction database with detailed information
    instruction_db = INSTRUCTION_DB

    if op not in instruction_db:
        # Try fuzzy matching
        similar = find_similar_words(op, list(instruction_db.keys()), n=5, cutoff=0.6)
        print(f"{Colors.RED}Unknown instruction:{Colors.RESET} {op}")
        if similar:
            print(f"{Colors.YELLOW}Did you mean:{Colors.RESET} {', '.join(similar)}")
        print(
            f"\n{Colors.DIM}Tip: Use all caps for instruction names (e.g., MVI, ADD, JNZ){Colors.RESET}"
        )
        sys.exit(1)

    info = instruction_db[op]

    # Print detailed explanation
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'═' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}8085 Instruction: {op}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'═' * 70}{Colors.RESET}\n")

    print(f"{Colors.BOLD}Name:{Colors.RESET} {info['name']}")
    print(f"{Colors.BOLD}Opcode:{Colors.RESET} {info['opcode_base']} (pattern)")
    print(f"         {Colors.DIM}{info['example_opcode']}{Colors.RESET}")
    print(
        f"{Colors.BOLD}Size:{Colors.RESET} {info['size']} byte{'s' if info['size'] > 1 else ''}"
    )

    # Cycles
    cycles_info = info["cycles"]
    if len(cycles_info) == 1:
        cycles_val = list(cycles_info.values())[0]
        print(
            f"{Colors.BOLD}Cycles:{Colors.RESET} {Colors.CYAN}{cycles_val}{Colors.RESET} T-states"
        )
    else:
        cycle_strs = [
            f"{k}: {Colors.CYAN}{v}T{Colors.RESET}" for k, v in cycles_info.items()
        ]
        print(f"{Colors.BOLD}Cycles:{Colors.RESET} {', '.join(cycle_strs)}")

    print(f"{Colors.BOLD}Flags:{Colors.RESET} {info['flags']}")
    print()

    print(f"{Colors.BOLD}Description:{Colors.RESET}")
    print(f"  {info['description']}")
    print()

    print(f"{Colors.BOLD}Syntax:{Colors.RESET}")
    print(f"  {Colors.CYAN}{info['syntax']}{Colors.RESET}")
    print()

    example_lines = info["example"].split("\n")
    plural = "s" if len(example_lines) > 1 else ""
    print(f"{Colors.BOLD}Example{plural}:{Colors.RESET}")
    for line in example_lines:
        print(f"  {Colors.GREEN}{line}{Colors.RESET}")
    print()

    if info.get("notes"):
        print(f"{Colors.YELLOW}Note:{Colors.RESET} {info['notes']}")
        print()

    print(f"{Colors.BOLD}Related Instructions:{Colors.RESET}")
    print(f"  {', '.join(info['related'])}")

    print(f"\n{Colors.DIM}{'─' * 70}{Colors.RESET}")
    print(
        f"{Colors.DIM}Tip: Use --explain-instr with other instruction names{Colors.RESET}\n"
    )
