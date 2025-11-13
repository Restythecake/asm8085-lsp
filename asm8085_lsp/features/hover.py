"""
Hover documentation provider for 8085 Assembly LSP.

Provides detailed documentation when hovering over:
- Instructions (shows opcode, cycles, description, examples)
- Registers (shows register information)
- Labels (shows definition location)
"""

from typing import Dict, Optional


class HoverProvider:
    """Provides hover documentation for 8085 assembly."""

    # Detailed instruction documentation
    INSTRUCTION_DOCS = {
        "MOV": {
            "description": "Move data from source register to destination register",
            "syntax": "MOV dest, src",
            "opcode": "01DDD SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "MOV A, B  ; Move B to A\nMOV M, C  ; Move C to memory[HL]",
        },
        "MVI": {
            "description": "Move immediate 8-bit data to register",
            "syntax": "MVI dest, data",
            "opcode": "00DDD110",
            "bytes": 2,
            "cycles": 7,
            "flags": "None",
            "example": "MVI A, 05H  ; Load 5 into A\nMVI M, FFH  ; Store FF at memory[HL]",
        },
        "LXI": {
            "description": "Load register pair immediate with 16-bit data",
            "syntax": "LXI rp, data16",
            "opcode": "00RP0001",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "LXI H, 8000H  ; HL = 8000H\nLXI SP, FFFFH  ; SP = FFFFH",
        },
        "LDA": {
            "description": "Load accumulator direct from memory",
            "syntax": "LDA addr",
            "opcode": "00111010",
            "bytes": 3,
            "cycles": 13,
            "flags": "None",
            "example": "LDA 9000H  ; A = [9000H]",
        },
        "STA": {
            "description": "Store accumulator direct to memory",
            "syntax": "STA addr",
            "opcode": "00110010",
            "bytes": 3,
            "cycles": 13,
            "flags": "None",
            "example": "STA 9000H  ; [9000H] = A",
        },
        "LDAX": {
            "description": "Load accumulator indirect from BC or DE",
            "syntax": "LDAX rp",
            "opcode": "00RP1010",
            "bytes": 1,
            "cycles": 7,
            "flags": "None",
            "example": "LDAX B  ; A = [BC]\nLDAX D  ; A = [DE]",
        },
        "STAX": {
            "description": "Store accumulator indirect to BC or DE",
            "syntax": "STAX rp",
            "opcode": "00RP0010",
            "bytes": 1,
            "cycles": 7,
            "flags": "None",
            "example": "STAX B  ; [BC] = A\nSTAX D  ; [DE] = A",
        },
        "LHLD": {
            "description": "Load HL direct from memory (16-bit)",
            "syntax": "LHLD addr",
            "opcode": "00101010",
            "bytes": 3,
            "cycles": 16,
            "flags": "None",
            "example": "LHLD 9000H  ; L = [9000H], H = [9001H]",
        },
        "SHLD": {
            "description": "Store HL direct to memory (16-bit)",
            "syntax": "SHLD addr",
            "opcode": "00100010",
            "bytes": 3,
            "cycles": 16,
            "flags": "None",
            "example": "SHLD 9000H  ; [9000H] = L, [9001H] = H",
        },
        "ADD": {
            "description": "Add register to accumulator",
            "syntax": "ADD src",
            "opcode": "10000SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "ADD B  ; A = A + B\nADD M  ; A = A + [HL]",
        },
        "ADI": {
            "description": "Add immediate to accumulator",
            "syntax": "ADI data",
            "opcode": "11000110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY, AC",
            "example": "ADI 05H  ; A = A + 5",
        },
        "ADC": {
            "description": "Add register to accumulator with carry",
            "syntax": "ADC src",
            "opcode": "10001SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "ADC B  ; A = A + B + CY",
        },
        "ACI": {
            "description": "Add immediate to accumulator with carry",
            "syntax": "ACI data",
            "opcode": "11001110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY, AC",
            "example": "ACI 05H  ; A = A + 5 + CY",
        },
        "SUB": {
            "description": "Subtract register from accumulator",
            "syntax": "SUB src",
            "opcode": "10010SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "SUB B  ; A = A - B",
        },
        "SUI": {
            "description": "Subtract immediate from accumulator",
            "syntax": "SUI data",
            "opcode": "11010110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY, AC",
            "example": "SUI 05H  ; A = A - 5",
        },
        "SBB": {
            "description": "Subtract register from accumulator with borrow",
            "syntax": "SBB src",
            "opcode": "10011SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "SBB B  ; A = A - B - CY",
        },
        "SBI": {
            "description": "Subtract immediate from accumulator with borrow",
            "syntax": "SBI data",
            "opcode": "11011110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY, AC",
            "example": "SBI 05H  ; A = A - 5 - CY",
        },
        "INR": {
            "description": "Increment register by 1",
            "syntax": "INR dest",
            "opcode": "00DDD100",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, AC",
            "example": "INR A  ; A = A + 1\nINR M  ; [HL] = [HL] + 1",
        },
        "DCR": {
            "description": "Decrement register by 1",
            "syntax": "DCR dest",
            "opcode": "00DDD101",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, AC",
            "example": "DCR A  ; A = A - 1\nDCR M  ; [HL] = [HL] - 1",
        },
        "INX": {
            "description": "Increment register pair by 1",
            "syntax": "INX rp",
            "opcode": "00RP0011",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "INX H  ; HL = HL + 1\nINX SP  ; SP = SP + 1",
        },
        "DCX": {
            "description": "Decrement register pair by 1",
            "syntax": "DCX rp",
            "opcode": "00RP1011",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "DCX H  ; HL = HL - 1\nDCX SP  ; SP = SP - 1",
        },
        "DAD": {
            "description": "Add register pair to HL (16-bit add)",
            "syntax": "DAD rp",
            "opcode": "00RP1001",
            "bytes": 1,
            "cycles": 10,
            "flags": "CY",
            "example": "DAD B  ; HL = HL + BC\nDAD D  ; HL = HL + DE",
        },
        "DAA": {
            "description": "Decimal adjust accumulator for BCD",
            "syntax": "DAA",
            "opcode": "00100111",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "DAA  ; Adjust A for BCD after ADD",
        },
        "ANA": {
            "description": "AND register with accumulator",
            "syntax": "ANA src",
            "opcode": "10100SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY=0, AC=1",
            "example": "ANA B  ; A = A & B",
        },
        "ANI": {
            "description": "AND immediate with accumulator",
            "syntax": "ANI data",
            "opcode": "11100110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY=0, AC=1",
            "example": "ANI 0FH  ; A = A & 0F",
        },
        "ORA": {
            "description": "OR register with accumulator",
            "syntax": "ORA src",
            "opcode": "10110SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY=0, AC=0",
            "example": "ORA B  ; A = A | B",
        },
        "ORI": {
            "description": "OR immediate with accumulator",
            "syntax": "ORI data",
            "opcode": "11110110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY=0, AC=0",
            "example": "ORI 80H  ; A = A | 80H",
        },
        "XRA": {
            "description": "XOR register with accumulator",
            "syntax": "XRA src",
            "opcode": "10101SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY=0, AC=0",
            "example": "XRA A  ; A = 0 (common idiom)\nXRA B  ; A = A ^ B",
        },
        "XRI": {
            "description": "XOR immediate with accumulator",
            "syntax": "XRI data",
            "opcode": "11101110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY=0, AC=0",
            "example": "XRI FFH  ; A = ~A (invert bits)",
        },
        "CMP": {
            "description": "Compare register with accumulator",
            "syntax": "CMP src",
            "opcode": "10111SSS",
            "bytes": 1,
            "cycles": 4,
            "flags": "Z, S, P, CY, AC",
            "example": "CMP B  ; Compare A with B (sets flags)",
        },
        "CPI": {
            "description": "Compare immediate with accumulator",
            "syntax": "CPI data",
            "opcode": "11111110",
            "bytes": 2,
            "cycles": 7,
            "flags": "Z, S, P, CY, AC",
            "example": "CPI 05H  ; Compare A with 5",
        },
        "RLC": {
            "description": "Rotate accumulator left",
            "syntax": "RLC",
            "opcode": "00000111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY",
            "example": "RLC  ; A = rotate left, CY = bit 7",
        },
        "RRC": {
            "description": "Rotate accumulator right",
            "syntax": "RRC",
            "opcode": "00001111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY",
            "example": "RRC  ; A = rotate right, CY = bit 0",
        },
        "RAL": {
            "description": "Rotate accumulator left through carry",
            "syntax": "RAL",
            "opcode": "00010111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY",
            "example": "RAL  ; A = rotate left through CY",
        },
        "RAR": {
            "description": "Rotate accumulator right through carry",
            "syntax": "RAR",
            "opcode": "00011111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY",
            "example": "RAR  ; A = rotate right through CY",
        },
        "CMA": {
            "description": "Complement accumulator (1's complement)",
            "syntax": "CMA",
            "opcode": "00101111",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "CMA  ; A = ~A",
        },
        "CMC": {
            "description": "Complement carry flag",
            "syntax": "CMC",
            "opcode": "00111111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY",
            "example": "CMC  ; CY = ~CY",
        },
        "STC": {
            "description": "Set carry flag",
            "syntax": "STC",
            "opcode": "00110111",
            "bytes": 1,
            "cycles": 4,
            "flags": "CY=1",
            "example": "STC  ; CY = 1",
        },
        "JMP": {
            "description": "Jump unconditional to address",
            "syntax": "JMP addr",
            "opcode": "11000011",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JMP LOOP  ; Jump to LOOP label",
        },
        "JZ": {
            "description": "Jump if zero flag is set",
            "syntax": "JZ addr",
            "opcode": "11001010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JZ ZERO  ; Jump if Z=1",
        },
        "JNZ": {
            "description": "Jump if zero flag is not set",
            "syntax": "JNZ addr",
            "opcode": "11000010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JNZ NOTZERO  ; Jump if Z=0",
        },
        "JC": {
            "description": "Jump if carry flag is set",
            "syntax": "JC addr",
            "opcode": "11011010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JC CARRY  ; Jump if CY=1",
        },
        "JNC": {
            "description": "Jump if carry flag is not set",
            "syntax": "JNC addr",
            "opcode": "11010010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JNC NOCARRY  ; Jump if CY=0",
        },
        "JP": {
            "description": "Jump if sign flag is not set (positive)",
            "syntax": "JP addr",
            "opcode": "11110010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JP POSITIVE  ; Jump if S=0",
        },
        "JM": {
            "description": "Jump if sign flag is set (minus)",
            "syntax": "JM addr",
            "opcode": "11111010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JM NEGATIVE  ; Jump if S=1",
        },
        "JPE": {
            "description": "Jump if parity is even",
            "syntax": "JPE addr",
            "opcode": "11101010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JPE EVEN  ; Jump if P=1",
        },
        "JPO": {
            "description": "Jump if parity is odd",
            "syntax": "JPO addr",
            "opcode": "11100010",
            "bytes": 3,
            "cycles": 10,
            "flags": "None",
            "example": "JPO ODD  ; Jump if P=0",
        },
        "CALL": {
            "description": "Call subroutine (push PC, jump to address)",
            "syntax": "CALL addr",
            "opcode": "11001101",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CALL DELAY  ; Call subroutine at DELAY",
        },
        "RET": {
            "description": "Return from subroutine (pop PC)",
            "syntax": "RET",
            "opcode": "11001001",
            "bytes": 1,
            "cycles": 10,
            "flags": "None",
            "example": "RET  ; Return to caller",
        },
        "CZ": {
            "description": "Call if zero",
            "syntax": "CZ addr",
            "opcode": "11001100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CZ HANDLE_ZERO  ; Call if Z=1",
        },
        "CNZ": {
            "description": "Call if not zero",
            "syntax": "CNZ addr",
            "opcode": "11000100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CNZ HANDLE_NZERO  ; Call if Z=0",
        },
        "CC": {
            "description": "Call if carry",
            "syntax": "CC addr",
            "opcode": "11011100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CC HANDLE_CARRY  ; Call if CY=1",
        },
        "CNC": {
            "description": "Call if no carry",
            "syntax": "CNC addr",
            "opcode": "11010100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CNC HANDLE_NC  ; Call if CY=0",
        },
        "CP": {
            "description": "Call if positive",
            "syntax": "CP addr",
            "opcode": "11110100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CP HANDLE_POS  ; Call if S=0",
        },
        "CM": {
            "description": "Call if minus",
            "syntax": "CM addr",
            "opcode": "11111100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CM HANDLE_NEG  ; Call if S=1",
        },
        "CPE": {
            "description": "Call if parity even",
            "syntax": "CPE addr",
            "opcode": "11101100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CPE HANDLE_EVEN  ; Call if P=1",
        },
        "CPO": {
            "description": "Call if parity odd",
            "syntax": "CPO addr",
            "opcode": "11100100",
            "bytes": 3,
            "cycles": 18,
            "flags": "None",
            "example": "CPO HANDLE_ODD  ; Call if P=0",
        },
        "RZ": {
            "description": "Return if zero",
            "syntax": "RZ",
            "opcode": "11001000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RZ  ; Return if Z=1",
        },
        "RNZ": {
            "description": "Return if not zero",
            "syntax": "RNZ",
            "opcode": "11000000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RNZ  ; Return if Z=0",
        },
        "RC": {
            "description": "Return if carry",
            "syntax": "RC",
            "opcode": "11011000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RC  ; Return if CY=1",
        },
        "RNC": {
            "description": "Return if no carry",
            "syntax": "RNC",
            "opcode": "11010000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RNC  ; Return if CY=0",
        },
        "RP": {
            "description": "Return if positive",
            "syntax": "RP",
            "opcode": "11110000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RP  ; Return if S=0",
        },
        "RM": {
            "description": "Return if minus",
            "syntax": "RM",
            "opcode": "11111000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RM  ; Return if S=1",
        },
        "RPE": {
            "description": "Return if parity even",
            "syntax": "RPE",
            "opcode": "11101000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RPE  ; Return if P=1",
        },
        "RPO": {
            "description": "Return if parity odd",
            "syntax": "RPO",
            "opcode": "11100000",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "RPO  ; Return if P=0",
        },
        "RST": {
            "description": "Restart (call to fixed address 0-7)",
            "syntax": "RST n",
            "opcode": "11NNN111",
            "bytes": 1,
            "cycles": 12,
            "flags": "None",
            "example": "RST 0  ; Call to 0000H\nRST 7  ; Call to 0038H",
        },
        "PUSH": {
            "description": "Push register pair onto stack",
            "syntax": "PUSH rp",
            "opcode": "11RP0101",
            "bytes": 1,
            "cycles": 12,
            "flags": "None",
            "example": "PUSH B  ; Push BC onto stack\nPUSH PSW  ; Push A and flags",
        },
        "POP": {
            "description": "Pop register pair from stack",
            "syntax": "POP rp",
            "opcode": "11RP0001",
            "bytes": 1,
            "cycles": 10,
            "flags": "None (PSW restores flags)",
            "example": "POP B  ; Pop BC from stack\nPOP PSW  ; Pop A and flags",
        },
        "IN": {
            "description": "Input from port to accumulator",
            "syntax": "IN port",
            "opcode": "11011011",
            "bytes": 2,
            "cycles": 10,
            "flags": "None",
            "example": "IN 01H  ; A = input from port 1",
        },
        "OUT": {
            "description": "Output accumulator to port",
            "syntax": "OUT port",
            "opcode": "11010011",
            "bytes": 2,
            "cycles": 10,
            "flags": "None",
            "example": "OUT 01H  ; Output A to port 1",
        },
        "EI": {
            "description": "Enable interrupts",
            "syntax": "EI",
            "opcode": "11111011",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "EI  ; Enable interrupt system",
        },
        "DI": {
            "description": "Disable interrupts",
            "syntax": "DI",
            "opcode": "11110011",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "DI  ; Disable interrupt system",
        },
        "HLT": {
            "description": "Halt processor execution",
            "syntax": "HLT",
            "opcode": "01110110",
            "bytes": 1,
            "cycles": 5,
            "flags": "None",
            "example": "HLT  ; Stop execution",
        },
        "NOP": {
            "description": "No operation (does nothing)",
            "syntax": "NOP",
            "opcode": "00000000",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "NOP  ; Delay or placeholder",
        },
        "XCHG": {
            "description": "Exchange DE and HL register pairs",
            "syntax": "XCHG",
            "opcode": "11101011",
            "bytes": 1,
            "cycles": 4,
            "flags": "None",
            "example": "XCHG  ; Swap DE <-> HL",
        },
        "SPHL": {
            "description": "Move HL to stack pointer",
            "syntax": "SPHL",
            "opcode": "11111001",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "SPHL  ; SP = HL",
        },
        "XTHL": {
            "description": "Exchange top of stack with HL",
            "syntax": "XTHL",
            "opcode": "11100011",
            "bytes": 1,
            "cycles": 16,
            "flags": "None",
            "example": "XTHL  ; Swap [SP] <-> HL",
        },
        "PCHL": {
            "description": "Move HL to program counter (jump indirect)",
            "syntax": "PCHL",
            "opcode": "11101001",
            "bytes": 1,
            "cycles": 6,
            "flags": "None",
            "example": "PCHL  ; PC = HL (jump to address in HL)",
        },
    }

    REGISTER_DOCS = {
        "A": "Accumulator - Primary 8-bit register for arithmetic and logic operations",
        "B": "General purpose 8-bit register - Can be used with C as BC pair",
        "C": "General purpose 8-bit register - Can be used with B as BC pair",
        "D": "General purpose 8-bit register - Can be used with E as DE pair",
        "E": "General purpose 8-bit register - Can be used with D as DE pair",
        "H": "General purpose 8-bit register - High byte of HL pair (memory pointer)",
        "L": "General purpose 8-bit register - Low byte of HL pair (memory pointer)",
        "M": "Memory reference - Refers to memory location pointed by HL register pair",
        "BC": "16-bit register pair - B (high) and C (low)",
        "DE": "16-bit register pair - D (high) and E (low)",
        "HL": "16-bit register pair - H (high) and L (low) - Often used for memory addressing",
        "SP": "Stack Pointer - 16-bit register pointing to top of stack",
        "PSW": "Program Status Word - Accumulator (A) and Flags register combined",
    }

    def __init__(self):
        """Initialize hover provider."""
        self._label_locations: Dict[str, Dict[str, int]] = {}

    def update_labels(self, uri: str, label_map: Dict[str, int]) -> None:
        """
        Update label locations for a document.

        Args:
            uri: Document URI
            label_map: Dictionary mapping label names to addresses
        """
        self._label_locations[uri] = label_map

    def provide_hover(self, uri: str, word: str) -> Optional[Dict]:
        """
        Provide hover documentation for a word.

        Args:
            uri: Document URI
            word: Word under cursor

        Returns:
            LSP hover response or None
        """
        word_upper = word.upper()

        # Check for instruction
        if word_upper in self.INSTRUCTION_DOCS:
            return self._format_instruction_hover(word_upper)

        # Check for register
        if word_upper in self.REGISTER_DOCS:
            return self._format_register_hover(word_upper)

        # Check for label
        label_map = self._label_locations.get(uri, {})
        if word_upper in label_map:
            return self._format_label_hover(word_upper, label_map[word_upper])

        return None

    def _format_instruction_hover(self, instruction: str) -> Dict:
        """
        Format instruction documentation for hover.

        Args:
            instruction: Instruction name (uppercase)

        Returns:
            LSP hover response
        """
        doc = self.INSTRUCTION_DOCS[instruction]

        markdown = f"**{instruction}** - {doc['description']}\n\n"
        markdown += f"**Syntax:** `{doc['syntax']}`\n\n"
        markdown += f"**Opcode:** `{doc['opcode']}`  \n"
        markdown += f"**Size:** {doc['bytes']} byte(s)  \n"
        markdown += f"**Cycles:** {doc['cycles']} T-states  \n"
        markdown += f"**Flags:** {doc['flags']}\n\n"
        markdown += f"**Example:**\n```asm\n{doc['example']}\n```"

        return {
            "contents": {
                "kind": "markdown",
                "value": markdown,
            }
        }

    def _format_register_hover(self, register: str) -> Dict:
        """
        Format register documentation for hover.

        Args:
            register: Register name (uppercase)

        Returns:
            LSP hover response
        """
        description = self.REGISTER_DOCS[register]

        markdown = f"**{register}** Register\n\n{description}"

        return {
            "contents": {
                "kind": "markdown",
                "value": markdown,
            }
        }

    def _format_label_hover(self, label: str, address: int) -> Dict:
        """
        Format label documentation for hover.

        Args:
            label: Label name
            address: Label address

        Returns:
            LSP hover response
        """
        markdown = f"**{label}** (Label)\n\nAddress: `{address:04X}H`"

        return {
            "contents": {
                "kind": "markdown",
                "value": markdown,
            }
        }
