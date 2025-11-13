"""Template library for 8085 assembly programs."""

from datetime import datetime
from pathlib import Path

# Template definitions
TEMPLATES = {
    "basic": {
        "name": "Basic Program",
        "description": "Simple program template with minimal boilerplate",
        "category": "General",
        "template": """; 8085 Assembly Program
; Author: {author}
; Date: {date}
; Description: {description}

; Program start
ORG 8000H

START:
    ; Initialize registers
    MVI A, 00H    ; Clear accumulator

    ; Your code here

    HLT           ; Halt the program

; Data section (if needed)
; DATA: DB 00H
""",
    },
    "loop": {
        "name": "Loop Example",
        "description": "Program with loop using counter",
        "category": "Control Flow",
        "template": """; Loop Example
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Initialize loop counter
    MVI C, 0AH    ; Loop 10 times
    MVI A, 00H    ; Initialize result

LOOP:
    ; Loop body
    INR A         ; Increment A

    ; Decrement counter and check
    DCR C
    JNZ LOOP      ; Jump if not zero

    ; After loop
    HLT

; Data section
COUNT: DB 0AH     ; Loop count
""",
    },
    "arithmetic": {
        "name": "Arithmetic Operations",
        "description": "Addition, subtraction, multiplication template",
        "category": "Math",
        "template": """; Arithmetic Operations
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Addition example
    MVI A, 05H    ; First number
    MVI B, 03H    ; Second number
    ADD B         ; A = A + B

    ; Subtraction example
    MVI A, 08H
    MVI B, 02H
    SUB B         ; A = A - B

    ; Multiplication (repeated addition)
    MVI A, 00H    ; Result
    MVI B, 05H    ; Multiplicand
    MVI C, 03H    ; Multiplier

MUL_LOOP:
    ADD B         ; Add multiplicand
    DCR C         ; Decrement counter
    JNZ MUL_LOOP  ; Repeat

    HLT

; Data section
NUM1: DB 05H
NUM2: DB 03H
RESULT: DB 00H    ; Result storage
""",
    },
    "subroutine": {
        "name": "Subroutine Template",
        "description": "Program with subroutine calls and stack usage",
        "category": "Control Flow",
        "template": """; Subroutine Example
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Initialize stack pointer
    LXI SP, FFFFH

    ; Call subroutine
    MVI A, 05H    ; Pass parameter in A
    CALL SQUARE   ; Call subroutine
    ; Result returns in A

    HLT

; Subroutine: Square the number in A
; Input: A = number
; Output: A = number^2
; Modifies: B, C
SQUARE:
    MOV B, A      ; Save original
    MVI C, 00H    ; Result = 0

SQ_LOOP:
    ADD C         ; Add current result
    MOV C, A      ; Save result
    DCR B         ; Decrement counter
    JNZ SQ_LOOP

    RET           ; Return to caller

; Data section
INPUT: DB 05H
OUTPUT: DB 00H
""",
    },
    "array": {
        "name": "Array Processing",
        "description": "Working with arrays/memory blocks",
        "category": "Data",
        "template": """; Array Processing
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Initialize HL to point to array
    LXI H, ARRAY
    MVI C, 05H    ; Array length
    MVI A, 00H    ; Sum accumulator

SUM_LOOP:
    ; Add array element to sum
    MOV B, M      ; Load from memory [HL]
    ADD B         ; Add to accumulator

    ; Move to next element
    INX H         ; Increment HL
    DCR C         ; Decrement counter
    JNZ SUM_LOOP

    ; Store result
    STA RESULT

    HLT

; Data section
ARRAY: DB 10H, 20H, 30H, 40H, 50H
RESULT: DB 00H
""",
    },
    "io": {
        "name": "Input/Output Example",
        "description": "Port I/O operations",
        "category": "I/O",
        "template": """; Input/Output Example
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Read from input port
    IN 10H        ; Read from port 10H
    MOV B, A      ; Save input

    ; Process data
    INR A         ; Increment value

    ; Write to output port
    OUT 20H       ; Write to port 20H

    HLT

; Port definitions
INPUT_PORT  EQU 10H
OUTPUT_PORT EQU 20H
""",
    },
    "conditional": {
        "name": "Conditional Branching",
        "description": "If-then-else logic using jumps",
        "category": "Control Flow",
        "template": """; Conditional Branching
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Compare two numbers
    LDA NUM1
    MOV B, A
    LDA NUM2
    CMP B         ; Compare A with B

    ; Branch based on result
    JZ EQUAL      ; Jump if equal
    JC LESS_THAN  ; Jump if A < B
    ; If we get here, A > B

GREATER:
    MVI A, 01H    ; Set result = 1
    JMP DONE

LESS_THAN:
    MVI A, FFH    ; Set result = -1
    JMP DONE

EQUAL:
    MVI A, 00H    ; Set result = 0

DONE:
    STA RESULT
    HLT

; Data section
NUM1: DB 05H
NUM2: DB 03H
RESULT: DB 00H
""",
    },
    "stack": {
        "name": "Stack Operations",
        "description": "PUSH, POP, and stack management",
        "category": "Stack",
        "template": """; Stack Operations
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Initialize stack pointer
    LXI SP, FFFFH

    ; Save registers to stack
    MVI A, 55H
    MVI B, AAH
    PUSH PSW      ; Push A and Flags
    PUSH B        ; Push B and C

    ; Modify registers
    MVI A, 00H
    MVI B, 00H

    ; Restore from stack
    POP B         ; Restore B and C
    POP PSW       ; Restore A and Flags

    HLT

; Data section
SAVE_A: DB 00H
SAVE_B: DB 00H
""",
    },
    "interrupt": {
        "name": "Interrupt Handling",
        "description": "Interrupt service routine template",
        "category": "Advanced",
        "template": """; Interrupt Handling
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Setup interrupt vector
    LXI SP, FFFFH  ; Initialize stack

    ; Enable interrupts
    EI

MAIN_LOOP:
    ; Main program loop
    NOP
    JMP MAIN_LOOP

; Interrupt Service Routine (ISR)
; Entry point for RST 7.5 at 003CH
ORG 003CH
ISR:
    PUSH PSW      ; Save registers
    PUSH B
    PUSH D
    PUSH H

    ; Handle interrupt
    ; Your ISR code here

    ; Restore registers
    POP H
    POP D
    POP B
    POP PSW

    EI            ; Re-enable interrupts
    RET           ; Return from interrupt

; Data section
ISR_COUNT: DB 00H
""",
    },
    "string": {
        "name": "String Operations",
        "description": "String/byte manipulation",
        "category": "Data",
        "template": """; String Operations
; Author: {author}
; Date: {date}
; Description: {description}

ORG 8000H

START:
    ; Copy string
    LXI H, SOURCE   ; Source pointer
    LXI D, DEST     ; Destination pointer
    MVI C, 05H      ; String length

COPY_LOOP:
    MOV A, M        ; Load from source
    STAX D          ; Store to destination
    INX H           ; Increment source
    INX D           ; Increment destination
    DCR C           ; Decrement counter
    JNZ COPY_LOOP

    HLT

; Data section
SOURCE: DB 'HELLO'
DEST: DB 00H, 00H, 00H, 00H, 00H          ; Reserve 5 bytes
""",
    },
}


def list_templates():
    """List all available templates with details."""
    # Group by category
    categories = {}
    for key, tmpl in TEMPLATES.items():
        cat = tmpl["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, tmpl))

    print("Available Templates:")
    print("=" * 70)
    for cat in sorted(categories.keys()):
        print(f"\n{cat}:")
        print("-" * 70)
        for key, tmpl in sorted(categories[cat], key=lambda x: x[0]):
            print(f"  {key:15} - {tmpl['name']}")
            print(f"{'':17} {tmpl['description']}")


def create_from_template(
    template_name: str,
    output_file: str,
    author: str = "",
    description: str = "",
):
    """Create a new assembly file from template.

    Args:
        template_name: Name of the template to use
        output_file: Path to output file
        author: Author name
        description: Program description
    """
    if template_name not in TEMPLATES:
        print(f"Error: Unknown template '{template_name}'")
        print("\nAvailable templates:")
        for key in sorted(TEMPLATES.keys()):
            print(f"  - {key}")
        return False

    template = TEMPLATES[template_name]["template"]

    # Fill in template variables
    content = template.format(
        author=author or "Your Name",
        date=datetime.now().strftime("%Y-%m-%d"),
        description=description or "Program description",
    )

    # Write to file
    output_path = Path(output_file)
    if output_path.exists():
        print(f"Error: File already exists: {output_file}")
        return False

    try:
        output_path.write_text(content, encoding="utf-8")
        print(f"✓ Created: {output_file}")
        print(f"  Template: {TEMPLATES[template_name]['name']}")
        print()
        print("Next steps:")
        print(f"  1. Edit the file: {output_file}")
        print(f"  2. Run it: asm {output_file}")
        print(f"  3. Debug it: asm -s -H {output_file}")
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False


def interactive_template_selector():
    """Interactive template selection with preview."""
    import sys

    # Group templates by category
    categories = {}
    for key, tmpl in TEMPLATES.items():
        cat = tmpl["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, tmpl))

    print("\n" + "=" * 70)
    print("8085 Assembly Template Selector")
    print("=" * 70)

    # Show categories
    print("\nCategories:")
    cat_list = sorted(categories.keys())
    for i, cat in enumerate(cat_list, 1):
        count = len(categories[cat])
        print(f"  {i}. {cat} ({count} templates)")

    # Select category
    try:
        cat_choice = input("\nSelect category (1-{}): ".format(len(cat_list)))
        cat_idx = int(cat_choice) - 1
        if cat_idx < 0 or cat_idx >= len(cat_list):
            print("Invalid choice")
            return None

        selected_cat = cat_list[cat_idx]
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled")
        return None

    # Show templates in category
    print(f"\n{selected_cat} Templates:")
    print("-" * 70)
    tmpl_list = sorted(categories[selected_cat], key=lambda x: x[0])
    for i, (key, tmpl) in enumerate(tmpl_list, 1):
        print(f"  {i}. {tmpl['name']}")
        print(f"     {tmpl['description']}")

    # Select template
    try:
        tmpl_choice = input(f"\nSelect template (1-{len(tmpl_list)}): ")
        tmpl_idx = int(tmpl_choice) - 1
        if tmpl_idx < 0 or tmpl_idx >= len(tmpl_list):
            print("Invalid choice")
            return None

        selected_key = tmpl_list[tmpl_idx][0]
        return selected_key
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled")
        return None
