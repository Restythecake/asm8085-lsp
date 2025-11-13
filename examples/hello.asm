; Example 8085 Assembly Program
; Description: Simple program demonstrating basic 8085 instructions
; Author: asm8085-lsp example

; Set program origin
ORG 8000H

; Program start
START:
    ; Load immediate values
    MVI A, 05H          ; Load 5 into accumulator
    MVI B, 03H          ; Load 3 into register B

    ; Arithmetic operations
    ADD B               ; Add B to A (A = A + B)
    MOV C, A            ; Copy result to register C

    ; Load data from memory
    LXI H, DATA         ; Load HL with address of DATA
    MOV D, M            ; Load data from memory into D

    ; Logical operations
    ANI 0FH             ; AND accumulator with 0FH
    ORI 10H             ; OR accumulator with 10H

    ; Comparison
    CMP B               ; Compare A with B
    JZ EQUAL            ; Jump if zero (A == B)
    JNZ NOTEQUAL        ; Jump if not zero (A != B)

EQUAL:
    MVI A, FFH          ; Load FFH if equal
    JMP DONE

NOTEQUAL:
    MVI A, 00H          ; Load 00H if not equal

DONE:
    ; Store result
    STA RESULT          ; Store accumulator to RESULT address

    ; Halt program
    HLT

; Data section
DATA: DB 42H            ; Define byte with value 42H
RESULT: DS 1            ; Reserve 1 byte for result

; End of program
