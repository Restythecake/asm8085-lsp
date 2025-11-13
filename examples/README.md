# asm8085-lsp Examples

This directory contains example 8085 assembly programs that demonstrate the features of the asm8085-lsp Language Server.

## Files

### hello.asm
A simple 8085 assembly program demonstrating:
- Basic instruction usage (MOV, MVI, ADD)
- Arithmetic and logical operations
- Memory operations (LDA, STA, LXI)
- Conditional jumps (JZ, JNZ)
- Labels and program structure
- Data definition (DB, DS)
- Comments and documentation

## Using These Examples

### With the LSP Server

1. Open any `.asm` file in an editor configured with asm8085-lsp
2. You should see:
   - **Syntax highlighting** (if your editor/extension provides it)
   - **Code completion** when typing instructions
   - **Hover information** when hovering over instructions
   - **Go to definition** for labels (Ctrl/Cmd + Click)
   - **Document outline** showing all labels

### Testing LSP Features

Try these actions in your editor:

1. **Code Completion**
   - Start typing an instruction (e.g., `MO`) and press Ctrl+Space
   - You should see suggestions for MOV, MVI, etc.

2. **Hover Information**
   - Hover your mouse over any instruction (e.g., `ADD`)
   - You should see detailed documentation with opcode, flags, and examples

3. **Go to Definition**
   - Ctrl/Cmd + Click on a label usage (e.g., `JMP DONE`)
   - Your cursor should jump to the label definition

4. **Document Symbols**
   - Open the document outline/symbol view in your editor
   - You should see all labels (START, EQUAL, NOTEQUAL, DONE, DATA, RESULT)

5. **Signature Help**
   - Type an instruction and see parameter hints
   - Example: Type `MVI` and see the expected operands

6. **Diagnostics**
   - Try introducing an error (e.g., `INVALID_INSTRUCTION`)
   - You should see an error highlight and message

## Creating Your Own Examples

Feel free to create your own 8085 assembly programs in this directory. The LSP server works with files having these extensions:
- `.asm`
- `.a85`
- `.8085`

## Common 8085 Instructions

### Data Transfer
- `MOV r1, r2` - Move data from register to register
- `MVI r, data` - Move immediate data to register
- `LDA addr` - Load accumulator from memory
- `STA addr` - Store accumulator to memory
- `LXI rp, data16` - Load register pair immediate

### Arithmetic
- `ADD r` - Add register to accumulator
- `ADI data` - Add immediate to accumulator
- `SUB r` - Subtract register from accumulator
- `INR r` - Increment register
- `DCR r` - Decrement register

### Logical
- `ANA r` - AND register with accumulator
- `ANI data` - AND immediate with accumulator
- `ORA r` - OR register with accumulator
- `XRA r` - XOR register with accumulator
- `CMP r` - Compare register with accumulator

### Branch
- `JMP addr` - Unconditional jump
- `JZ addr` - Jump if zero
- `JNZ addr` - Jump if not zero
- `JC addr` - Jump if carry
- `CALL addr` - Call subroutine
- `RET` - Return from subroutine

### Stack & I/O
- `PUSH rp` - Push register pair onto stack
- `POP rp` - Pop register pair from stack
- `IN port` - Input from port
- `OUT port` - Output to port

### Control
- `HLT` - Halt execution
- `NOP` - No operation
- `EI` - Enable interrupts
- `DI` - Disable interrupts

## Registers

- **A** - Accumulator (8-bit)
- **B, C, D, E, H, L** - General purpose registers (8-bit)
- **M** - Memory location pointed by HL
- **BC, DE, HL** - Register pairs (16-bit)
- **SP** - Stack pointer (16-bit)
- **PSW** - Program status word (A + Flags)

## Assembler Directives

- `ORG address` - Set origin/starting address
- `DB value` - Define byte(s)
- `DS count` - Define storage (reserve bytes)
