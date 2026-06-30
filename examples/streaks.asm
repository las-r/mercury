; streaks
; by las-r

PLN 15

; constants
LDI R1 1
LDI R6 15
LDI R7 63
LDI R8 127
LDI R9 8      ; horizontal bar spacing stride

; screen coordinates
LDI R2 16     ; start x offset
LDI R3 0      ; start y offset
LDI R4 13     ; solid character glyph index

; setup absolute loop target
LDI Ra waterfall_loop

waterfall_loop:
    FNT R4
    DRW R2 R3 5

    ; move down quickly
    LDI Re 3
    ADD R3 R3 Re
    AND R3 R3 R7   ; naturally wraps y past 63 back to 0

    ; slide columns right continuously
    ADD R2 R2 R1
    AND R2 R2 R8   ; naturally wraps x past 127 back to 0

; loop back safely
JMP R0 Ra R0
