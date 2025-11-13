"""
Signature help provider for 8085 Assembly LSP.

Provides parameter hints and syntax information while typing instructions.
"""

from typing import Dict, List, Optional


class SignatureHelpProvider:
    """Provides signature help (parameter hints) for 8085 instructions."""

    # Instruction signatures with parameter information
    SIGNATURES = {
        "MOV": {
            "label": "MOV dest, src",
            "documentation": "Move data from source register to destination register",
            "parameters": [
                {
                    "label": "dest",
                    "documentation": "Destination register (A, B, C, D, E, H, L, M)",
                },
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "MVI": {
            "label": "MVI dest, data",
            "documentation": "Move immediate 8-bit data to register",
            "parameters": [
                {
                    "label": "dest",
                    "documentation": "Destination register (A, B, C, D, E, H, L, M)",
                },
                {"label": "data", "documentation": "8-bit immediate data (00H-FFH)"},
            ],
        },
        "LXI": {
            "label": "LXI rp, data16",
            "documentation": "Load register pair immediate with 16-bit data",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, SP)"},
                {
                    "label": "data16",
                    "documentation": "16-bit immediate data (0000H-FFFFH)",
                },
            ],
        },
        "LDA": {
            "label": "LDA addr",
            "documentation": "Load accumulator direct from memory",
            "parameters": [
                {"label": "addr", "documentation": "16-bit memory address"},
            ],
        },
        "STA": {
            "label": "STA addr",
            "documentation": "Store accumulator direct to memory",
            "parameters": [
                {"label": "addr", "documentation": "16-bit memory address"},
            ],
        },
        "LDAX": {
            "label": "LDAX rp",
            "documentation": "Load accumulator indirect from BC or DE",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (B=BC or D=DE)"},
            ],
        },
        "STAX": {
            "label": "STAX rp",
            "documentation": "Store accumulator indirect to BC or DE",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (B=BC or D=DE)"},
            ],
        },
        "LHLD": {
            "label": "LHLD addr",
            "documentation": "Load HL direct from memory (16-bit)",
            "parameters": [
                {"label": "addr", "documentation": "16-bit memory address"},
            ],
        },
        "SHLD": {
            "label": "SHLD addr",
            "documentation": "Store HL direct to memory (16-bit)",
            "parameters": [
                {"label": "addr", "documentation": "16-bit memory address"},
            ],
        },
        "ADD": {
            "label": "ADD src",
            "documentation": "Add register to accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "ADI": {
            "label": "ADI data",
            "documentation": "Add immediate to accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "ADC": {
            "label": "ADC src",
            "documentation": "Add register to accumulator with carry",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "ACI": {
            "label": "ACI data",
            "documentation": "Add immediate to accumulator with carry",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "SUB": {
            "label": "SUB src",
            "documentation": "Subtract register from accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "SUI": {
            "label": "SUI data",
            "documentation": "Subtract immediate from accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "SBB": {
            "label": "SBB src",
            "documentation": "Subtract register from accumulator with borrow",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "SBI": {
            "label": "SBI data",
            "documentation": "Subtract immediate from accumulator with borrow",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "INR": {
            "label": "INR dest",
            "documentation": "Increment register by 1",
            "parameters": [
                {
                    "label": "dest",
                    "documentation": "Register to increment (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "DCR": {
            "label": "DCR dest",
            "documentation": "Decrement register by 1",
            "parameters": [
                {
                    "label": "dest",
                    "documentation": "Register to decrement (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "INX": {
            "label": "INX rp",
            "documentation": "Increment register pair by 1",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, SP)"},
            ],
        },
        "DCX": {
            "label": "DCX rp",
            "documentation": "Decrement register pair by 1",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, SP)"},
            ],
        },
        "DAD": {
            "label": "DAD rp",
            "documentation": "Add register pair to HL",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, SP)"},
            ],
        },
        "ANA": {
            "label": "ANA src",
            "documentation": "AND register with accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "ANI": {
            "label": "ANI data",
            "documentation": "AND immediate with accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "ORA": {
            "label": "ORA src",
            "documentation": "OR register with accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "ORI": {
            "label": "ORI data",
            "documentation": "OR immediate with accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "XRA": {
            "label": "XRA src",
            "documentation": "XOR register with accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "XRI": {
            "label": "XRI data",
            "documentation": "XOR immediate with accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "CMP": {
            "label": "CMP src",
            "documentation": "Compare register with accumulator",
            "parameters": [
                {
                    "label": "src",
                    "documentation": "Source register (A, B, C, D, E, H, L, M)",
                },
            ],
        },
        "CPI": {
            "label": "CPI data",
            "documentation": "Compare immediate with accumulator",
            "parameters": [
                {"label": "data", "documentation": "8-bit immediate data"},
            ],
        },
        "JMP": {
            "label": "JMP addr",
            "documentation": "Jump unconditional to address",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JZ": {
            "label": "JZ addr",
            "documentation": "Jump if zero flag is set",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JNZ": {
            "label": "JNZ addr",
            "documentation": "Jump if zero flag is not set",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JC": {
            "label": "JC addr",
            "documentation": "Jump if carry flag is set",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JNC": {
            "label": "JNC addr",
            "documentation": "Jump if carry flag is not set",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JP": {
            "label": "JP addr",
            "documentation": "Jump if sign flag is not set (positive)",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JM": {
            "label": "JM addr",
            "documentation": "Jump if sign flag is set (minus)",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JPE": {
            "label": "JPE addr",
            "documentation": "Jump if parity is even",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "JPO": {
            "label": "JPO addr",
            "documentation": "Jump if parity is odd",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "CALL": {
            "label": "CALL addr",
            "documentation": "Call subroutine",
            "parameters": [
                {"label": "addr", "documentation": "16-bit address or label"},
            ],
        },
        "PUSH": {
            "label": "PUSH rp",
            "documentation": "Push register pair onto stack",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, PSW)"},
            ],
        },
        "POP": {
            "label": "POP rp",
            "documentation": "Pop register pair from stack",
            "parameters": [
                {"label": "rp", "documentation": "Register pair (BC, DE, HL, PSW)"},
            ],
        },
        "IN": {
            "label": "IN port",
            "documentation": "Input from port to accumulator",
            "parameters": [
                {"label": "port", "documentation": "8-bit port address (00H-FFH)"},
            ],
        },
        "OUT": {
            "label": "OUT port",
            "documentation": "Output accumulator to port",
            "parameters": [
                {"label": "port", "documentation": "8-bit port address (00H-FFH)"},
            ],
        },
        "RST": {
            "label": "RST n",
            "documentation": "Restart (call to fixed address)",
            "parameters": [
                {"label": "n", "documentation": "Restart vector (0-7)"},
            ],
        },
        "ORG": {
            "label": "ORG addr",
            "documentation": "Set program origin address",
            "parameters": [
                {"label": "addr", "documentation": "16-bit starting address"},
            ],
        },
        "DB": {
            "label": "DB data [, data...]",
            "documentation": "Define byte(s) of data",
            "parameters": [
                {"label": "data", "documentation": "8-bit data value(s)"},
            ],
        },
        "DS": {
            "label": "DS count",
            "documentation": "Define storage space",
            "parameters": [
                {"label": "count", "documentation": "Number of bytes to reserve"},
            ],
        },
    }

    def __init__(self):
        """Initialize signature help provider."""
        pass

    def provide_signature_help(self, line: str, character: int) -> Optional[Dict]:
        """
        Provide signature help for the current position.

        Args:
            line: Current line text
            character: Character position in line

        Returns:
            LSP signature help response or None
        """
        # Extract the instruction at the start of the line
        instruction = self._extract_instruction(line)
        if not instruction:
            return None

        instruction_upper = instruction.upper()
        if instruction_upper not in self.SIGNATURES:
            return None

        # Get signature information
        sig_info = self.SIGNATURES[instruction_upper]

        # Determine which parameter we're on based on comma count
        before_cursor = line[:character]
        after_instruction = before_cursor[len(instruction) :].strip()
        comma_count = after_instruction.count(",")
        active_parameter = min(comma_count, len(sig_info["parameters"]) - 1)

        return {
            "signatures": [
                {
                    "label": sig_info["label"],
                    "documentation": sig_info["documentation"],
                    "parameters": sig_info["parameters"],
                }
            ],
            "activeSignature": 0,
            "activeParameter": active_parameter,
        }

    def _extract_instruction(self, line: str) -> Optional[str]:
        """
        Extract the instruction mnemonic from a line.

        Args:
            line: Line of assembly code

        Returns:
            Instruction mnemonic or None
        """
        # Remove label if present (text before colon)
        if ":" in line:
            line = line.split(":", 1)[1]

        # Get first word (the instruction)
        parts = line.strip().split()
        if not parts:
            return None

        return parts[0]
