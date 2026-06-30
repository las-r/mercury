; input test
; by las-r

; drawing position
LDI R2 0x0a
LDI R3 0x14
LDI R4 10

; loop start
    WKEY R1
    CLR
    FNT R1
    DRW R2 R3 5
JNR R4