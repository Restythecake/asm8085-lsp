"""disasm helpers extracted from asm8085."""


def get_instruction_cycles(memory, addr, jump_taken=None):
    """Get the number of clock cycles (T-states) for an 8085 instruction

    Args:
        memory: Memory array
        addr: Address of instruction
        jump_taken: For conditional instructions, whether jump was taken (None if not applicable)

    Returns:
        Number of T-states/clock cycles
    """
    opcode = memory[addr].value if hasattr(memory[addr], "value") else memory[addr]

    # MOV instructions (0x40-0x7F)
    if 0x40 <= opcode <= 0x7F:
        if opcode == 0x76:  # HLT
            return 5
        # MOV r, M or MOV M, r takes 7 cycles, MOV r, r takes 4
        src = opcode & 0x07
        dst = (opcode >> 3) & 0x07
        if src == 6 or dst == 6:  # M (memory) involved
            return 7
        return 4

    # MVI instructions (7 cycles)
    if opcode in [0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E]:
        return 7 if opcode != 0x36 else 10  # MVI M is 10 cycles

    # LXI (10 cycles)
    if opcode in [0x01, 0x11, 0x21, 0x31]:
        return 10

    # ADD, ADC, SUB, SBB, ANA, XRA, ORA, CMP (4 cycles for register, 7 for M)
    if 0x80 <= opcode <= 0xBF:
        return 7 if (opcode & 0x07) == 6 else 4

    # ADI, ACI, SUI, SBI, ANI, XRI, ORI, CPI (7 cycles)
    if opcode in [0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE]:
        return 7

    # INR, DCR (4 cycles for register, 10 for M)
    if opcode in [
        0x04,
        0x0C,
        0x14,
        0x1C,
        0x24,
        0x2C,
        0x34,
        0x3C,
        0x05,
        0x0D,
        0x15,
        0x1D,
        0x25,
        0x2D,
        0x35,
        0x3D,
    ]:
        return (
            10 if (opcode & 0x0F) in [0x04, 0x05] and ((opcode >> 4) & 0x03) == 3 else 4
        )

    # INX, DCX (6 cycles)
    if opcode in [0x03, 0x13, 0x23, 0x33, 0x0B, 0x1B, 0x2B, 0x3B]:
        return 6

    # DAD (10 cycles)
    if opcode in [0x09, 0x19, 0x29, 0x39]:
        return 10

    # LDA, STA (13 cycles)
    if opcode in [0x3A, 0x32]:
        return 13

    # LHLD, SHLD (16 cycles)
    if opcode in [0x2A, 0x22]:
        return 16

    # LDAX, STAX (7 cycles)
    if opcode in [0x0A, 0x1A, 0x02, 0x12]:
        return 7

    # JMP (10 cycles)
    if opcode == 0xC3:
        return 10

    # Conditional jumps (10 if taken, 7 if not)
    if opcode in [0xDA, 0xD2, 0xCA, 0xC2, 0xF2, 0xFA, 0xEA, 0xE2]:
        if jump_taken is None:
            return 10  # Default assume taken
        return 10 if jump_taken else 7

    # CALL (18 cycles)
    if opcode == 0xCD:
        return 18

    # Conditional calls (18 if taken, 9 if not)
    if opcode in [0xDC, 0xD4, 0xCC, 0xC4, 0xF4, 0xFC, 0xEC, 0xE4]:
        if jump_taken is None:
            return 18  # Default assume taken
        return 18 if jump_taken else 9

    # RET (10 cycles)
    if opcode == 0xC9:
        return 10

    # Conditional returns (12 if taken, 6 if not)
    if opcode in [0xD8, 0xD0, 0xC8, 0xC0, 0xF0, 0xF8, 0xE8, 0xE0]:
        if jump_taken is None:
            return 12  # Default assume taken
        return 12 if jump_taken else 6

    # RST (12 cycles)
    if opcode in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]:
        return 12

    # PUSH (12 cycles)
    if opcode in [0xC5, 0xD5, 0xE5, 0xF5]:
        return 12

    # POP (10 cycles)
    if opcode in [0xC1, 0xD1, 0xE1, 0xF1]:
        return 10

    # IN, OUT (10 cycles)
    if opcode in [0xDB, 0xD3]:
        return 10

    # Rotate instructions (4 cycles)
    if opcode in [0x07, 0x0F, 0x17, 0x1F]:
        return 4

    # Other single-byte instructions
    if opcode in [0x27, 0x2F, 0x37, 0x3F]:  # DAA, CMA, STC, CMC
        return 4
    if opcode == 0xEB:  # XCHG
        return 4
    if opcode == 0xE3:  # XTHL
        return 16
    if opcode == 0xF9:  # SPHL
        return 6
    if opcode == 0xE9:  # PCHL
        return 6
    if opcode in [0xFB, 0xF3]:  # EI, DI
        return 4
    if opcode in [0x20, 0x30]:  # RIM, SIM
        return 4
    if opcode == 0x00:  # NOP
        return 4

    # Unknown/unimplemented
    return 4  # Default


def get_instruction_description(instruction):
    """Get a brief description of what an instruction does

    Args:
        instruction: The disassembled instruction string

    Returns:
        Brief description string
    """
    parts = instruction.split()
    if not parts:
        return ""

    op = parts[0]

    # Data Transfer
    if op == "MOV":
        return "Copy register to register"
    elif op == "MVI":
        return "Load immediate value"
    elif op == "LXI":
        return "Load register pair immediate"
    elif op == "LDA":
        return "Load accumulator direct"
    elif op == "STA":
        return "Store accumulator direct"
    elif op == "LHLD":
        return "Load H and L direct"
    elif op == "SHLD":
        return "Store H and L direct"
    elif op == "LDAX":
        return "Load accumulator indirect"
    elif op == "STAX":
        return "Store accumulator indirect"
    elif op == "XCHG":
        return "Exchange DE and HL"

    # Arithmetic
    elif op == "ADD":
        return "Add to accumulator"
    elif op == "ADI":
        return "Add immediate to accumulator"
    elif op == "ADC":
        return "Add with carry"
    elif op == "ACI":
        return "Add immediate with carry"
    elif op == "SUB":
        return "Subtract from accumulator"
    elif op == "SUI":
        return "Subtract immediate"
    elif op == "SBB":
        return "Subtract with borrow"
    elif op == "SBI":
        return "Subtract immediate with borrow"
    elif op == "INR":
        return "Increment register"
    elif op == "DCR":
        return "Decrement register"
    elif op == "INX":
        return "Increment register pair"
    elif op == "DCX":
        return "Decrement register pair"
    elif op == "DAD":
        return "Add register pair to HL"
    elif op == "DAA":
        return "Decimal adjust accumulator"

    # Logical
    elif op == "ANA":
        return "AND with accumulator"
    elif op == "ANI":
        return "AND immediate"
    elif op == "ORA":
        return "OR with accumulator"
    elif op == "ORI":
        return "OR immediate"
    elif op == "XRA":
        return "XOR with accumulator"
    elif op == "XRI":
        return "XOR immediate"
    elif op == "CMP":
        return "Compare with accumulator"
    elif op == "CPI":
        return "Compare immediate"
    elif op == "RLC":
        return "Rotate left"
    elif op == "RRC":
        return "Rotate right"
    elif op == "RAL":
        return "Rotate left through carry"
    elif op == "RAR":
        return "Rotate right through carry"
    elif op == "CMA":
        return "Complement accumulator"
    elif op == "CMC":
        return "Complement carry flag"
    elif op == "STC":
        return "Set carry flag"

    # Branch
    elif op == "JMP":
        return "Unconditional jump"
    elif op == "JC":
        return "Jump if carry"
    elif op == "JNC":
        return "Jump if no carry"
    elif op == "JZ":
        return "Jump if zero"
    elif op == "JNZ":
        return "Jump if not zero"
    elif op == "JP":
        return "Jump if positive"
    elif op == "JM":
        return "Jump if minus"
    elif op == "JPE":
        return "Jump if parity even"
    elif op == "JPO":
        return "Jump if parity odd"
    elif op == "CALL":
        return "Unconditional call"
    elif op in ["CC", "CNC", "CZ", "CNZ", "CP", "CM", "CPE", "CPO"]:
        return "Conditional call"
    elif op == "RET":
        return "Unconditional return"
    elif op in ["RC", "RNC", "RZ", "RNZ", "RP", "RM", "RPE", "RPO"]:
        return "Conditional return"
    elif op == "RST":
        return "Restart (call to vector)"
    elif op == "PCHL":
        return "Jump to address in HL"

    # Stack
    elif op == "PUSH":
        return "Push register pair to stack"
    elif op == "POP":
        return "Pop stack to register pair"
    elif op == "XTHL":
        return "Exchange stack top with HL"
    elif op == "SPHL":
        return "Copy HL to stack pointer"

    # I/O and Control
    elif op == "IN":
        return "Input from port"
    elif op == "OUT":
        return "Output to port"
    elif op == "EI":
        return "Enable interrupts"
    elif op == "DI":
        return "Disable interrupts"
    elif op == "HLT":
        return "Halt execution"
    elif op == "NOP":
        return "No operation"
    elif op == "RIM":
        return "Read interrupt mask"
    elif op == "SIM":
        return "Set interrupt mask"

    return ""


def disassemble_instruction(memory, addr):
    """Complete 8085 disassembler - returns (instruction_str, bytes_consumed)"""
    # Handle both int arrays and c_ubyte arrays
    opcode = memory[addr].value if hasattr(memory[addr], "value") else memory[addr]

    def get_byte(offset):
        val = memory[addr + offset]
        return val.value if hasattr(val, "value") else val

    # Complete 8085 instruction set
    # MOV instructions (0x40-0x7F except 0x76)
    regs = ["B", "C", "D", "E", "H", "L", "M", "A"]
    if 0x40 <= opcode <= 0x7F:
        if opcode == 0x76:  # HLT
            return "HLT", 1
        dst = regs[(opcode >> 3) & 0x07]
        src = regs[opcode & 0x07]
        return f"MOV {dst}, {src}", 1

    # MVI instructions
    mvi_map = {
        0x06: "B",
        0x0E: "C",
        0x16: "D",
        0x1E: "E",
        0x26: "H",
        0x2E: "L",
        0x36: "M",
        0x3E: "A",
    }
    if opcode in mvi_map:
        return f"MVI {mvi_map[opcode]}, {get_byte(1):02X}H", 2

    # LXI instructions
    lxi_map = {0x01: "B", 0x11: "D", 0x21: "H", 0x31: "SP"}
    if opcode in lxi_map:
        return f"LXI {lxi_map[opcode]}, {get_byte(2):02X}{get_byte(1):02X}H", 3

    # ADD instructions (0x80-0x87)
    if 0x80 <= opcode <= 0x87:
        return f"ADD {regs[opcode & 0x07]}", 1

    # ADC instructions (0x88-0x8F)
    if 0x88 <= opcode <= 0x8F:
        return f"ADC {regs[opcode & 0x07]}", 1

    # SUB instructions (0x90-0x97)
    if 0x90 <= opcode <= 0x97:
        return f"SUB {regs[opcode & 0x07]}", 1

    # SBB instructions (0x98-0x9F)
    if 0x98 <= opcode <= 0x9F:
        return f"SBB {regs[opcode & 0x07]}", 1

    # ANA instructions (0xA0-0xA7)
    if 0xA0 <= opcode <= 0xA7:
        return f"ANA {regs[opcode & 0x07]}", 1

    # XRA instructions (0xA8-0xAF)
    if 0xA8 <= opcode <= 0xAF:
        return f"XRA {regs[opcode & 0x07]}", 1

    # ORA instructions (0xB0-0xB7)
    if 0xB0 <= opcode <= 0xB7:
        return f"ORA {regs[opcode & 0x07]}", 1

    # CMP instructions (0xB8-0xBF)
    if 0xB8 <= opcode <= 0xBF:
        return f"CMP {regs[opcode & 0x07]}", 1

    # INR instructions
    inr_map = {
        0x04: "B",
        0x0C: "C",
        0x14: "D",
        0x1C: "E",
        0x24: "H",
        0x2C: "L",
        0x34: "M",
        0x3C: "A",
    }
    if opcode in inr_map:
        return f"INR {inr_map[opcode]}", 1

    # DCR instructions
    dcr_map = {
        0x05: "B",
        0x0D: "C",
        0x15: "D",
        0x1D: "E",
        0x25: "H",
        0x2D: "L",
        0x35: "M",
        0x3D: "A",
    }
    if opcode in dcr_map:
        return f"DCR {dcr_map[opcode]}", 1

    # INX instructions
    inx_map = {0x03: "B", 0x13: "D", 0x23: "H", 0x33: "SP"}
    if opcode in inx_map:
        return f"INX {inx_map[opcode]}", 1

    # DCX instructions
    dcx_map = {0x0B: "B", 0x1B: "D", 0x2B: "H", 0x3B: "SP"}
    if opcode in dcx_map:
        return f"DCX {dcx_map[opcode]}", 1

    # DAD instructions
    dad_map = {0x09: "B", 0x19: "D", 0x29: "H", 0x39: "SP"}
    if opcode in dad_map:
        return f"DAD {dad_map[opcode]}", 1

    # PUSH/POP instructions
    push_map = {0xC5: "B", 0xD5: "D", 0xE5: "H", 0xF5: "PSW"}
    pop_map = {0xC1: "B", 0xD1: "D", 0xE1: "H", 0xF1: "PSW"}
    if opcode in push_map:
        return f"PUSH {push_map[opcode]}", 1
    if opcode in pop_map:
        return f"POP {pop_map[opcode]}", 1

    # Jump instructions
    jump_map = {
        0xC3: "JMP",
        0xDA: "JC",
        0xD2: "JNC",
        0xCA: "JZ",
        0xC2: "JNZ",
        0xF2: "JP",
        0xFA: "JM",
        0xEA: "JPE",
        0xE2: "JPO",
    }
    if opcode in jump_map:
        return f"{jump_map[opcode]} {get_byte(2):02X}{get_byte(1):02X}H", 3

    # Call instructions
    call_map = {
        0xCD: "CALL",
        0xDC: "CC",
        0xD4: "CNC",
        0xCC: "CZ",
        0xC4: "CNZ",
        0xF4: "CP",
        0xFC: "CM",
        0xEC: "CPE",
        0xE4: "CPO",
    }
    if opcode in call_map:
        return f"{call_map[opcode]} {get_byte(2):02X}{get_byte(1):02X}H", 3

    # Return instructions
    ret_map = {
        0xC9: "RET",
        0xD8: "RC",
        0xD0: "RNC",
        0xC8: "RZ",
        0xC0: "RNZ",
        0xF0: "RP",
        0xF8: "RM",
        0xE8: "RPE",
        0xE0: "RPO",
    }
    if opcode in ret_map:
        return ret_map[opcode], 1

    # RST instructions (0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF)
    if opcode in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]:
        return f"RST {(opcode >> 3) & 0x07}", 1

    # Immediate instructions
    imm_map = {
        0xC6: "ADI",
        0xCE: "ACI",
        0xD6: "SUI",
        0xDE: "SBI",
        0xE6: "ANI",
        0xEE: "XRI",
        0xF6: "ORI",
        0xFE: "CPI",
    }
    if opcode in imm_map:
        return f"{imm_map[opcode]} {get_byte(1):02X}H", 2

    # Memory instructions
    mem_map = {0x3A: "LDA", 0x32: "STA", 0x2A: "LHLD", 0x22: "SHLD"}
    if opcode in mem_map:
        return f"{mem_map[opcode]} {get_byte(2):02X}{get_byte(1):02X}H", 3

    # LDAX/STAX instructions
    if opcode in [0x0A, 0x1A]:
        reg = "B" if opcode == 0x0A else "D"
        return f"LDAX {reg}", 1
    if opcode in [0x02, 0x12]:
        reg = "B" if opcode == 0x02 else "D"
        return f"STAX {reg}", 1

    # I/O instructions
    if opcode == 0xDB:
        return f"IN {get_byte(1):02X}H", 2
    if opcode == 0xD3:
        return f"OUT {get_byte(1):02X}H", 2

    # Rotate and control instructions
    control_map = {
        0x07: "RLC",
        0x0F: "RRC",
        0x17: "RAL",
        0x1F: "RAR",
        0x27: "DAA",
        0x2F: "CMA",
        0x37: "STC",
        0x3F: "CMC",
        0x00: "NOP",
        0xEB: "XCHG",
        0xE3: "XTHL",
        0xF9: "SPHL",
        0xE9: "PCHL",
        0xFB: "EI",
        0xF3: "DI",
        0x20: "RIM",
        0x30: "SIM",
    }
    if opcode in control_map:
        return control_map[opcode], 1

    # Unknown opcode
    return f"DB {opcode:02X}H", 1
