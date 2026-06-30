PLN 15

; constant registers
LDI R1 1
LDI R5 24
LDI R6 15
LDI R7 63
LDI R8 127
LDI R9 4

; x y pos
LDI R2 0x0a
LDI R3 0x14

; counter
SUB R4 R4 R4

; loop start
    CLR
    FNT R4
    DRW R2 R3 5

    ; increment drawn number
    ADD R4 R4 R1
    AND R4 R4 R6 ; keep inbounds

    ; increment x
    ADD R2 R2 R1
    AND R2 R2 R8 ; keep inbounds

    ; increment y
    ADD R3 R3 R1
    AND R3 R3 R7 ; keep inbounds

    ; timer
    STT R9
    WTT
JNR R5 ; loop end