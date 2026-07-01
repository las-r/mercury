; dvd logo
; by las-r

; constants
LDI R1 1
LDI Re 2

; velocity
LDI R2 1
LDI R3 1

; position
LDI R4 60
LDI R5 30

; sprite pointer
LDI Rb dvd_sprite
STI Rb

; bounds
LDI R6 0
LDI R7 120      ; max x
LDI R8 61       ; max y

; delay
LDI R9 2

; loop address
LDI Ra main_loop

main_loop:
    CLR
    DRW R4 R5 3

    ; x movement
    ADD R4 R4 R2

    ; right wall
    SKE R4 R7
    JPR Re
    LDI R2 0xFF

    ; left wall
    SKE R4 R6
    JPR Re
    LDI R2 1

    ; y movement
    ADD R5 R5 R3

    ; bottom wall
    SKE R5 R8
    JPR Re
    LDI R3 0xFF

    ; top wall
    SKE R5 R6
    JPR Re
    LDI R3 1

    STT R9
    WTT
    JMP R0 Ra R0

dvd_sprite:
    RAW 0x7EE7
    RAW 0x7E00