"""
Code completion provider for 8085 Assembly LSP.

Provides intelligent code completion for:
- Instructions (MOV, MVI, ADD, etc.)
- Registers (A, B, C, D, E, H, L, M)
- Register pairs (BC, DE, HL, SP, PSW)
- Labels (from current document)
- Directives (ORG, DB, DS)
"""

from typing import Dict, List, Optional


class CompletionProvider:
    """Provides code completion for 8085 assembly."""

    # 8085 instruction set
    INSTRUCTIONS = [
        # Data Transfer
        "MOV",
        "MVI",
        "LXI",
        "LDA",
        "STA",
        "LDAX",
        "STAX",
        "LHLD",
        "SHLD",
        "XCHG",
        "SPHL",
        "XTHL",
        "PCHL",
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
        "JZ",
        "JNZ",
        "JC",
        "JNC",
        "JP",
        "JM",
        "JPE",
        "JPO",
        "CALL",
        "CZ",
        "CNZ",
        "CC",
        "CNC",
        "CP",
        "CM",
        "CPE",
        "CPO",
        "RET",
        "RZ",
        "RNZ",
        "RC",
        "RNC",
        "RP",
        "RM",
        "RPE",
        "RPO",
        "RST",
        "PCHL",
        # Stack
        "PUSH",
        "POP",
        # I/O & Control
        "IN",
        "OUT",
        "EI",
        "DI",
        "HLT",
        "NOP",
    ]

    # 8-bit registers
    REGISTERS_8BIT = ["A", "B", "C", "D", "E", "H", "L", "M"]

    # 16-bit register pairs
    REGISTERS_16BIT = ["BC", "DE", "HL", "SP", "PSW"]

    # Assembler directives
    DIRECTIVES = ["ORG", "DB", "DS", "EQU", "END"]

    # Instruction details for completion items
    INSTRUCTION_DETAILS = {
        "MOV": "Move register to register",
        "MVI": "Move immediate to register",
        "LXI": "Load register pair immediate",
        "LDA": "Load accumulator direct",
        "STA": "Store accumulator direct",
        "LDAX": "Load accumulator indirect",
        "STAX": "Store accumulator indirect",
        "LHLD": "Load H and L direct",
        "SHLD": "Store H and L direct",
        "ADD": "Add register to accumulator",
        "ADI": "Add immediate to accumulator",
        "ADC": "Add register to accumulator with carry",
        "ACI": "Add immediate to accumulator with carry",
        "SUB": "Subtract register from accumulator",
        "SUI": "Subtract immediate from accumulator",
        "SBB": "Subtract register from accumulator with borrow",
        "SBI": "Subtract immediate from accumulator with borrow",
        "INR": "Increment register",
        "DCR": "Decrement register",
        "INX": "Increment register pair",
        "DCX": "Decrement register pair",
        "DAD": "Add register pair to HL",
        "DAA": "Decimal adjust accumulator",
        "ANA": "AND register with accumulator",
        "ANI": "AND immediate with accumulator",
        "ORA": "OR register with accumulator",
        "ORI": "OR immediate with accumulator",
        "XRA": "XOR register with accumulator",
        "XRI": "XOR immediate with accumulator",
        "CMP": "Compare register with accumulator",
        "CPI": "Compare immediate with accumulator",
        "RLC": "Rotate accumulator left",
        "RRC": "Rotate accumulator right",
        "RAL": "Rotate accumulator left through carry",
        "RAR": "Rotate accumulator right through carry",
        "CMA": "Complement accumulator",
        "CMC": "Complement carry flag",
        "STC": "Set carry flag",
        "JMP": "Jump unconditional",
        "JZ": "Jump if zero",
        "JNZ": "Jump if not zero",
        "JC": "Jump if carry",
        "JNC": "Jump if no carry",
        "JP": "Jump if positive",
        "JM": "Jump if minus",
        "JPE": "Jump if parity even",
        "JPO": "Jump if parity odd",
        "CALL": "Call subroutine",
        "RET": "Return from subroutine",
        "PUSH": "Push register pair onto stack",
        "POP": "Pop register pair from stack",
        "IN": "Input from port",
        "OUT": "Output to port",
        "EI": "Enable interrupts",
        "DI": "Disable interrupts",
        "HLT": "Halt processor",
        "NOP": "No operation",
        "XCHG": "Exchange DE and HL",
        "SPHL": "Move HL to SP",
        "XTHL": "Exchange top of stack with HL",
        "PCHL": "Move HL to PC",
        "RST": "Restart (call to fixed address)",
    }

    def __init__(self):
        """Initialize completion provider."""
        self._label_cache: Dict[str, List[str]] = {}

    def update_labels(self, uri: str, labels: List[str]) -> None:
        """
        Update cached labels for a document.

        Args:
            uri: Document URI
            labels: List of label names from the document
        """
        self._label_cache[uri] = labels

    def provide_completion(self, uri: str, line: str, character: int) -> List[Dict]:
        """
        Provide completion items for the current position.

        Args:
            uri: Document URI
            line: Current line text
            character: Character position in line

        Returns:
            List of LSP completion items
        """
        # Get the word being typed
        word = self._get_word_at_position(line, character)
        word_upper = word.upper()

        completions = []

        # At the start of a line or after whitespace - suggest instructions and directives
        if self._is_instruction_position(line, character):
            completions.extend(self._get_instruction_completions(word_upper))
            completions.extend(self._get_directive_completions(word_upper))

        # After instruction - suggest registers or labels
        else:
            completions.extend(self._get_register_completions(word_upper))
            completions.extend(self._get_label_completions(uri, word_upper))

        return completions

    def _get_word_at_position(self, line: str, character: int) -> str:
        """
        Extract the word being typed at the cursor position.

        Args:
            line: Line text
            character: Character position

        Returns:
            Partial word being typed
        """
        if character > len(line):
            character = len(line)

        # Find word start
        start = character
        while start > 0 and line[start - 1].isalnum():
            start -= 1

        return line[start:character]

    def _is_instruction_position(self, line: str, character: int) -> bool:
        """
        Check if cursor is in instruction position (start of line).

        Args:
            line: Line text
            character: Character position

        Returns:
            True if at instruction position
        """
        before_cursor = line[:character].strip()
        # Empty or only whitespace before cursor = instruction position
        return not before_cursor or before_cursor.endswith(":")

    def _get_instruction_completions(self, prefix: str) -> List[Dict]:
        """
        Get instruction completions matching prefix.

        Args:
            prefix: Prefix to match (uppercase)

        Returns:
            List of completion items
        """
        completions = []

        for instr in self.INSTRUCTIONS:
            if instr.startswith(prefix):
                detail = self.INSTRUCTION_DETAILS.get(instr, "8085 instruction")
                completions.append(
                    {
                        "label": instr,
                        "kind": 3,  # Function
                        "detail": detail,
                        "insertText": instr,
                        "documentation": detail,
                    }
                )

        return completions

    def _get_directive_completions(self, prefix: str) -> List[Dict]:
        """
        Get directive completions matching prefix.

        Args:
            prefix: Prefix to match (uppercase)

        Returns:
            List of completion items
        """
        completions = []
        directive_details = {
            "ORG": "Set origin address",
            "DB": "Define byte",
            "DS": "Define storage",
            "EQU": "Define constant",
            "END": "End of program",
        }

        for directive in self.DIRECTIVES:
            if directive.startswith(prefix):
                detail = directive_details.get(directive, "Assembler directive")
                completions.append(
                    {
                        "label": directive,
                        "kind": 14,  # Keyword
                        "detail": detail,
                        "insertText": directive,
                        "documentation": detail,
                    }
                )

        return completions

    def _get_register_completions(self, prefix: str) -> List[Dict]:
        """
        Get register completions matching prefix.

        Args:
            prefix: Prefix to match (uppercase)

        Returns:
            List of completion items
        """
        completions = []

        # 8-bit registers
        for reg in self.REGISTERS_8BIT:
            if reg.startswith(prefix):
                completions.append(
                    {
                        "label": reg,
                        "kind": 6,  # Variable
                        "detail": "8-bit register",
                        "insertText": reg,
                    }
                )

        # 16-bit register pairs
        for reg in self.REGISTERS_16BIT:
            if reg.startswith(prefix):
                completions.append(
                    {
                        "label": reg,
                        "kind": 6,  # Variable
                        "detail": "16-bit register pair",
                        "insertText": reg,
                    }
                )

        return completions

    def _get_label_completions(self, uri: str, prefix: str) -> List[Dict]:
        """
        Get label completions matching prefix.

        Args:
            uri: Document URI
            prefix: Prefix to match (uppercase)

        Returns:
            List of completion items
        """
        completions = []
        labels = self._label_cache.get(uri, [])

        for label in labels:
            if label.upper().startswith(prefix):
                completions.append(
                    {
                        "label": label,
                        "kind": 14,  # Keyword (label)
                        "detail": "Label",
                        "insertText": label,
                    }
                )

        return completions
