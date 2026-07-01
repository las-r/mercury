import re
import sys

# mercury assembler
# by las-r

# assembler class
class MercuryAssembler:
    def __init__(self):
        self.labels = {}
        self.aliases = {}      # alias -> register
        self.constants = {}    # name -> value
        
    def parse_reg(self, token: str) -> int:
        tok = token.strip(',')
        if tok in self.aliases:
            tok = self.aliases[tok]
            
        match = re.match(r'^[rR]([0-9a-fA-F])$', tok)
        if not match:
            raise ValueError(f"invalid register: {token}")
        return int(match.group(1), 16)

    def parse_int(self, token: str) -> int:
        tok = token.strip(',')
        if tok in self.constants:
            return self.constants[tok]
            
        if tok.lower().startswith('0x'):
            return int(tok, 16)
        return int(tok)

    def first_pass(self, lines: list) -> list:
        cleaned_lines = []
        addr = 0x80  # program start offset
        
        self.labels.clear()
        self.aliases.clear()
        self.constants.clear()
        
        for line_num, line in enumerate(lines, 1):
            line = re.sub(r'[;#].*$', '', line).strip()
            if not line:
                continue
                
            if line.endswith(':'):
                label_name = line[:-1].strip()
                if label_name in self.labels:
                    raise SyntaxError(f"duplicate label: {label_name}")
                self.labels[label_name] = addr
                continue
            
            tokens = line.replace(',', ' ').split()
            directive = tokens[0].upper()
            
            if directive == "ALI":
                if len(tokens) != 3:
                    raise SyntaxError(f"line {line_num}: ali needs 2 args (alias, reg)")
                self.aliases[tokens[1]] = tokens[2]
                continue
                
            elif directive == "CON":
                if len(tokens) != 3:
                    raise SyntaxError(f"line {line_num}: con needs 2 args (name, val)")
                try:
                    val = int(tokens[2], 16) if tokens[2].lower().startswith('0x') else int(tokens[2])
                except ValueError:
                    raise SyntaxError(f"line {line_num}: constant must be int")
                self.constants[tokens[1]] = val
                continue
                
            cleaned_lines.append((addr, line))
            addr += 2  # all instructions are 2 bytes
            
        return cleaned_lines

    def second_pass(self, cleaned_lines: list) -> bytearray:
        buf = bytearray()
        
        for addr, line in cleaned_lines:
            tokens = line.replace(',', ' ').split()
            mnemonic = tokens[0].upper()
            args = tokens[1:]
            
            try:
                opc = 0

                # --- misc ---
                if mnemonic == "NOP":   opc = 0x0000
                elif mnemonic == "CLR": opc = 0x00DD
                elif mnemonic == "CLP": opc = 0x00DE
                elif mnemonic == "END": opc = 0x00EE
                elif mnemonic == "RAW":
                    if len(args) != 1:
                        raise SyntaxError("raw expects 1 arg")
                    opc = self.labels[args[0]] if args[0] in self.labels else self.parse_int(args[0])
                    if not (0 <= opc <= 0xFFFF):
                        raise ValueError("raw value out of bounds")
                elif mnemonic == "RNG":
                    opc = 0xF00F | (self.parse_reg(args[0]) << 8)

                # --- control flow ---
                elif mnemonic == "LDI":
                    rx = self.parse_reg(args[0])
                    val = self.labels[args[1]] if args[1] in self.labels else self.parse_int(args[1])
                    opc = 0x1000 | (rx << 8) | (val & 0xFF)
                elif mnemonic in ("CALL", "JMP"):
                    p_args = [arg.replace(arg.replace('+', '').strip(), self.aliases.get(arg.replace('+', '').strip(), arg.replace('+', '').strip())) for arg in args]
                    sub = "".join(p_args).replace('+', ' ').replace('R', ' R').replace('r', ' r').split()
                    rx, ry, rz = self.parse_reg(sub[0]), self.parse_reg(sub[1]), self.parse_reg(sub[2])
                    prefix = 0x2000 if mnemonic == "CALL" else 0xE000
                    opc = prefix | (rx << 8) | (ry << 4) | rz
                elif mnemonic == "RET": opc = 0x3000 | (self.parse_reg(args[0]) << 8)
                elif mnemonic == "JPR": opc = 0x400E | (self.parse_reg(args[0]) << 8)
                elif mnemonic == "JNR": opc = 0x400F | (self.parse_reg(args[0]) << 8)

                # --- skip ---
                elif mnemonic in ("SKE", "SKNE", "SKGT", "SKLT"):
                    rx, ry = self.parse_reg(args[0]), self.parse_reg(args[1])
                    sfx = {"SKE": 0x0, "SKNE": 0x1, "SKGT": 0x2, "SKLT": 0x3}[mnemonic]
                    opc = 0x4000 | (rx << 8) | (ry << 4) | sfx

                # --- alu ---
                elif mnemonic in ("MOV", "NOT"):
                    rx, ry = self.parse_reg(args[0]), self.parse_reg(args[1])
                    opc = 0x7000 | (rx << 8) | (ry << 4) | (0x0 if mnemonic == "MOV" else 0x1)
                elif mnemonic in ("AND", "OR", "XOR", "ADD", "SUB"):
                    rx, ry, rz = self.parse_reg(args[0]), self.parse_reg(args[1]), self.parse_reg(args[2])
                    pfx = {"AND": 0x8000, "OR": 0x9000, "XOR": 0xA000, "ADD": 0xB000, "SUB": 0xC000}[mnemonic]
                    opc = pfx | (rx << 8) | (ry << 4) | rz
                elif mnemonic == "SHL": opc = 0xF0E0 | (self.parse_reg(args[0]) << 8)
                elif mnemonic == "SHR": opc = 0xF0F0 | (self.parse_reg(args[0]) << 8)

                # --- memory & I ---
                elif mnemonic in ("STM", "LDM", "STI", "ADI", "SBI"):
                    rx = self.parse_reg(args[0])
                    sfx = {"STM": 0x00, "LDM": 0x01, "STI": 0x10, "ADI": 0x11, "SBI": 0x12}[mnemonic]
                    opc = 0x5000 | (rx << 8) | sfx

                # --- key input ---
                elif mnemonic == "WKEY": opc = 0x6000 | (self.parse_reg(args[0]) << 8)
                elif mnemonic in ("WKDR", "SKDR", "WKUR", "SKUR"):
                    rz = self.parse_reg(args[0])
                    sfx = {"WKDR": 0x10, "SKDR": 0x11, "WKUR": 0x12, "SKUR": 0x13}[mnemonic]
                    opc = 0x6000 | (rz << 8) | sfx

                # --- display ---
                elif mnemonic == "DRW":
                    rx, ry = self.parse_reg(args[0]), self.parse_reg(args[1])
                    opc = 0xD000 | (rx << 8) | (ry << 4) | (self.parse_int(args[2]) & 0xF)
                elif mnemonic == "PLN": opc = 0xF030 | ((self.parse_int(args[0]) & 0x7) << 8)

                # --- font ---
                elif mnemonic == "FNT": opc = 0xF000 | (self.parse_reg(args[0]) << 8)

                # --- timer & sound ---
                elif mnemonic in ("STT", "GTT"):
                    opc = 0xF000 | (self.parse_reg(args[0]) << 8) | (0x1 if mnemonic == "STT" else 0x2)
                elif mnemonic == "WTT": opc = 0xF003
                elif mnemonic == "PTT": opc = 0xFF04
                elif mnemonic == "RTT": opc = 0xFF05
                elif mnemonic == "BUZ": opc = 0xF020 | (self.parse_reg(args[0]) << 8)
                else:
                    raise SyntaxError(f"unknown mnemonic: {mnemonic}")
                
                # big-endian pack
                buf.append((opc >> 8) & 0xFF)
                buf.append(opc & 0xFF)
                
            except Exception as e:
                print(f"error [0x{addr:04x}]: '{line}' -> {e}", file=sys.stderr)
                sys.exit(1)
                
        return buf

    def assemble(self, src: str) -> bytearray:
        return self.second_pass(self.first_pass(src.splitlines()))

# main
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: python {sys.argv[0]} <src> <bin>")
        sys.exit(1)
        
    with open(sys.argv[1], "r") as f:
        code = f.read()
        
    asm = MercuryAssembler()
    binary = asm.assemble(code)
    
    with open(sys.argv[2], "wb") as f_out:
        f_out.write(binary)
        
    print(f"assembled size: {len(binary)} bytes -> {sys.argv[2]}")