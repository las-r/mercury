import re
import sys

# mercury assembler
# by las-r

class MercuryAssembler:
    def __init__(self):
        self.labels = {}
        self.aliases = {}      # Stores alias_name -> register_string (e.g., 'ptr' -> 'r2')
        self.constants = {}    # Stores value_name -> integer_value (e.g., 'max_limit' -> 10)
        self.instructions = []
        
    def parse_reg(self, token):
        token_str = token.strip(',')
        # Check if the token is a registered alias first
        if token_str in self.aliases:
            token_str = self.aliases[token_str]
            
        # parses register strings like r0-rf to an integer 0-15
        match = re.match(r'^[rR]([0-9a-fA-F])$', token_str)
        if not match:
            raise ValueError(f"invalid register: {token}")
        return int(match.group(1), 16)

    def parse_int(self, token):
        token_str = token.strip(',')
        # Check if the token is a defined constant first
        if token_str in self.constants:
            return self.constants[token_str]
            
        # parses integer tokens (hex like 0x12 or decimal like 18)
        if token_str.lower().startswith('0x'):
            return int(token_str, 16)
        return int(token_str)

    def first_pass(self, lines):
        # first pass to clean up lines, record definitions, and extract label positions
        cleaned_lines = []
        current_address = 0x80  # program data starts at 0x80
        
        # Reset tables on every assembly run
        self.labels.clear()
        self.aliases.clear()
        self.constants.clear()
        
        for line_num, line in enumerate(lines, 1):
            # strip comments and whitespace
            line = re.sub(r'[;#].*$', '', line).strip()
            if not line:
                continue
                
            # check for labels (e.g., "main:")
            if line.endswith(':'):
                label_name = line[:-1].strip()
                if label_name in self.labels:
                    raise SyntaxError(f"duplicate label: {label_name}")
                self.labels[label_name] = current_address
                continue
            
            # Split line into raw parts to check for directives
            tokens = line.replace(',', ' ').split()
            directive = tokens[0].upper()
            
            # --- Handle ALI (Registry Alias) Directive ---
            if directive == "ALI":
                if len(tokens) != 3:
                    raise SyntaxError(f"Line {line_num}: ALI directive requires exactly 2 arguments (alias, register)")
                alias_name = tokens[1]
                target_reg = tokens[2]
                self.aliases[alias_name] = target_reg
                continue
                
            # --- Handle CON (Constant Value) Directive ---
            elif directive == "CON":
                if len(tokens) != 3:
                    raise SyntaxError(f"Line {line_num}: CON directive requires exactly 2 arguments (name, value)")
                const_name = tokens[1]
                try:
                    # Evaluate standard numbers/hex integers directly
                    const_value = int(tokens[2], 16) if tokens[2].lower().startswith('0x') else int(tokens[2])
                except ValueError:
                    raise SyntaxError(f"Line {line_num}: Constant value must be a valid integer.")
                self.constants[const_name] = const_value
                continue
                
            cleaned_lines.append((current_address, line))
            current_address += 2  # all instructions are 2 bytes
            
        return cleaned_lines

    def second_pass(self, cleaned_lines):
        # second pass to translate mnemonics into 16-bit binary opcodes
        binary_output = bytearray()
        
        for addr, line in cleaned_lines:
            # replace commas with spaces and split into tokens
            tokens = line.replace(',', ' ').split()
            mnemonic = tokens[0].upper()
            args = tokens[1:]
            
            try:
                opcode = 0

                # --- misc ---
                if mnemonic == "NOP":
                    opcode = 0x0000
                elif mnemonic == "RAW":
                    if len(args) != 1:
                        raise SyntaxError("raw expects exactly one 16-bit value")

                    opcode = self.labels[args[0]] if args[0] in self.labels else self.parse_int(args[0])

                    if not (0 <= opcode <= 0xFFFF):
                        raise ValueError("raw value must be between 0x0000 and 0xffff")
                elif mnemonic == "CLR":
                    opcode = 0x00DD
                elif mnemonic == "CLP":
                    opcode = 0x00DE
                elif mnemonic == "END":
                    opcode = 0x00EE
                elif mnemonic == "RNG":
                    rx = self.parse_reg(args[0])
                    opcode = 0xF00F | (rx << 8)

                # --- control flow ---
                elif mnemonic == "LDI":
                    rx = self.parse_reg(args[0])
                    val = self.labels[args[1]] if args[1] in self.labels else self.parse_int(args[1])
                    opcode = 0x1000 | (rx << 8) | (val & 0xFF)
                elif mnemonic in ("CALL", "JMP"):
                    # Pre-process arguments to swap aliases before the custom parser math splits them up
                    processed_args = []
                    for arg in args:
                        # Normalize string out of potential symbols
                        clean_arg = arg.replace('+', '').strip()
                        if clean_arg in self.aliases:
                            arg = arg.replace(clean_arg, self.aliases[clean_arg])
                        processed_args.append(arg)

                    joined = "".join(processed_args).replace('+', ' ').replace('R', ' R').replace('r', ' r')
                    sub_tokens = joined.split()
                    rx = self.parse_reg(sub_tokens[0])
                    ry = self.parse_reg(sub_tokens[1])
                    rz = self.parse_reg(sub_tokens[2])
                    prefix = 0x2000 if mnemonic == "CALL" else 0xE000
                    opcode = prefix | (rx << 8) | (ry << 4) | rz
                elif mnemonic == "RET":
                    rx = self.parse_reg(args[0])
                    opcode = 0x3000 | (rx << 8)
                elif mnemonic == "JPR":
                    rx = self.parse_reg(args[0])
                    opcode = 0x400E | (rx << 8)
                elif mnemonic == "JNR":
                    rx = self.parse_reg(args[0])
                    opcode = 0x400F | (rx << 8)

                # --- skip (single-skip only, no more of the old skip+1 weirdness) ---
                elif mnemonic in ("SKE", "SKNE", "SKGT", "SKLT"):
                    rx = self.parse_reg(args[0])
                    ry = self.parse_reg(args[1])
                    suffix = {"SKE": 0x0, "SKNE": 0x1, "SKGT": 0x2, "SKLT": 0x3}[mnemonic]
                    opcode = 0x4000 | (rx << 8) | (ry << 4) | suffix

                # --- alu ---
                elif mnemonic in ("MOV", "NOT"):
                    rx = self.parse_reg(args[0])
                    ry = self.parse_reg(args[1])
                    suffix = 0x0 if mnemonic == "MOV" else 0x1
                    opcode = 0x7000 | (rx << 8) | (ry << 4) | suffix
                elif mnemonic in ("AND", "OR", "XOR", "ADD", "SUB"):
                    rx = self.parse_reg(args[0])
                    ry = self.parse_reg(args[1])
                    rz = self.parse_reg(args[2])
                    prefix = {"AND": 0x8000, "OR": 0x9000, "XOR": 0xA000, "ADD": 0xB000, "SUB": 0xC000}[mnemonic]
                    opcode = prefix | (rx << 8) | (ry << 4) | rz
                elif mnemonic == "SHL":
                    rx = self.parse_reg(args[0])
                    opcode = 0xF0E0 | (rx << 8)
                elif mnemonic == "SHR":
                    rx = self.parse_reg(args[0])
                    opcode = 0xF0F0 | (rx << 8)

                # --- memory & I ---
                elif mnemonic in ("STM", "LDM", "STI", "ADI", "SBI"):
                    rx = self.parse_reg(args[0])
                    suffix = {"STM": 0x00, "LDM": 0x01, "STI": 0x10, "ADI": 0x11, "SBI": 0x12}[mnemonic]
                    opcode = 0x5000 | (rx << 8) | suffix

                # --- key input ---
                elif mnemonic == "WKEY":
                    rx = self.parse_reg(args[0])
                    opcode = 0x6000 | (rx << 8)
                elif mnemonic in ("WKDR", "SKDR", "WKUR", "SKUR"):
                    rz = self.parse_reg(args[0])
                    suffix = {"WKDR": 0x10, "SKDR": 0x11, "WKUR": 0x12, "SKUR": 0x13}[mnemonic]
                    opcode = 0x6000 | (rz << 8) | suffix

                # --- display ---
                elif mnemonic == "DRW":
                    rx = self.parse_reg(args[0])
                    ry = self.parse_reg(args[1])
                    z = self.parse_int(args[2]) & 0xF
                    opcode = 0xD000 | (rx << 8) | (ry << 4) | z
                elif mnemonic == "PLN":
                    x = self.parse_int(args[0]) & 0x7
                    opcode = 0xF030 | (x << 8)

                # --- font ---
                elif mnemonic == "FNT":
                    rx = self.parse_reg(args[0])
                    opcode = 0xF000 | (rx << 8)

                # --- timer ---
                elif mnemonic in ("STT", "GTT"):
                    rx = self.parse_reg(args[0])
                    suffix = 0x01 if mnemonic == "STT" else 0x02
                    opcode = 0xF000 | (rx << 8) | suffix
                elif mnemonic == "WTT":
                    opcode = 0xF003
                elif mnemonic == "PTT":
                    opcode = 0xFF04
                elif mnemonic == "RTT":
                    opcode = 0xFF05

                # --- sound ---
                elif mnemonic == "BUZ":
                    rx = self.parse_reg(args[0])
                    opcode = 0xF020 | (rx << 8)
                else:
                    raise SyntaxError(f"unknown instruction mnemonic: {mnemonic}")
                
                # big-endian push
                binary_output.append((opcode >> 8) & 0xFF)
                binary_output.append(opcode & 0xFF)
                
            except Exception as e:
                print(f"error on line [0x{addr:04x}]: '{line}' -> {e}", file=sys.stderr)
                sys.exit(1)
                
        return binary_output

    def assemble(self, source_code):
        lines = source_code.splitlines()
        cleaned = self.first_pass(lines)
        return self.second_pass(cleaned)

# cli setup
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: python {sys.argv[0]} <input_src_file> <output_bin_file>")
        sys.exit(1)
    src_filename = sys.argv[1]
    bin_filename = sys.argv[2]
    
    with open(src_filename, "r") as f:
        code = f.read()
    assembler = MercuryAssembler()
    binary = assembler.assemble(code)
    
    with open(bin_filename, "wb") as f_out:
        f_out.write(binary)
    
    print(f"successfully assembled! size: {len(binary)} bytes.")
    print(f"saved binary to: {bin_filename}")