; define swatch block
LDI R1 4
JPR R1
swatch:
    RAW 0xFFFF
    RAW 0xFFFF

; setup values
LDI R1 swatch
STI R1
LDI R2 2

; draw rectangles
LDI R3 0    
PLN 1    
DRW R3 R2 4
LDI R3 8    
PLN 2    
DRW R3 R2 4
LDI R3 16   
PLN 3    
DRW R3 R2 4
LDI R3 24   
PLN 4    
DRW R3 R2 4
LDI R3 32   
PLN 5    
DRW R3 R2 4
LDI R3 40   
PLN 6    
DRW R3 R2 4
LDI R3 48   
PLN 7    
DRW R3 R2 4

; final loop
RAW 0
JNR R2