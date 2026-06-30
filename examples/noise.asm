; font noise
; by las-r

PLN 15

; constants
LDI R1 1
LDI R6 15
LDI R7 63
LDI R8 127

; loop back offset
; 8 instructions to jump back: (8 * 2) + 2 = 18 bytes
LDI R9 22     

; main blast loop
    RNG R2 ; [PC here] 1
    AND R2 R2 R8 ; 2

    RNG R3 ; 3
    AND R3 R3 R7 ; 4

    RNG R4 ; 5
    AND R4 R4 R6 ; 6

    FNT R4 ; 7
    DRW R2 R3 5 ; 8

    SKU 0xd
    CLR

JNR R9 ; Loops back to first RNG