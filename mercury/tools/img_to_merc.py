import sys
from PIL import Image

# mercury asset converter
# by las-r

# settings
WIDTH = 128
HEIGHT = 64

def convert_image(in_path: str, out_path: str):
    # load and force format
    try:
        img = Image.open(in_path).convert("RGB")
    except Exception as e:
        print(f"error opening image: {e}")
        sys.exit(1)

    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT))

    pixels = img.load()
    planes_data = {1: [], 2: [], 4: []}

    # extract planar graphics (8x8 blocks)
    for mask, ch_idx in [(1, 0), (2, 1), (4, 2)]:
        for col in range(16):
            x_start = col * 8
            for block in range(8):
                y_start = block * 8
                for row in range(8):
                    y = y_start + row
                    byte_val = 0
                    for bit in range(8):
                        x = x_start + bit
                        if pixels[x, y][ch_idx] > 127: #type:ignore
                            byte_val |= (1 << (7 - bit))
                    planes_data[mask].append(byte_val)

    # unroll rendering routine
    render_asm = []
    for mask in [1, 2, 4]:
        render_asm.append(f"PLN 0x{mask:01X}")
        for col in range(16):
            render_asm.append(f"LDI R2 0x{col * 8:02X}")
            for block in range(8):
                render_asm.append(f"LDI R3 0x{block * 8:02X}")
                render_asm.append("DRW R2 R3 8")
                render_asm.append("ADI RA")

    # calculate exact memory offsets
    base_asm = ["CLR", "LDI RA 0x08"] + render_asm + ["END"]
    base_size = len(base_asm) * 2

    # fixed-point convergence loop for I pointer
    target_addr = 0x80 + base_size
    while True:
        set_i_insts = 1 + (target_addr // 255)
        if (target_addr % 255) > 0:
            set_i_insts += 2

        if 0x80 + base_size + set_i_insts * 2 == target_addr:
            break
        target_addr = 0x80 + base_size + set_i_insts * 2

    # push I pointer to start of payload
    set_i_asm = ["LDI R1 0xFF"]
    for _ in range(target_addr // 255):
        set_i_asm.append("ADI R1")
    rem = target_addr % 255
    if rem > 0:
        set_i_asm.append(f"LDI R1 0x{rem:02X}")
        set_i_asm.append("ADI R1")

    # pack 16-bit payload definitions
    raw_asm = []
    for mask in [1, 2, 4]:
        data = planes_data[mask]
        for i in range(0, len(data), 2):
            val = (data[i] << 8) | data[i+1]
            raw_asm.append(f"RAW 0x{val:04X}")

    # write asm source
    with open(out_path, "w") as f:
        f.write("; ====== MERCURY ASSET RENDERER ======\n")
        f.write("; unrolled visual macro routines\n\n")
        f.write("CLR\n")
        f.write("LDI RA 0x08\n\n")
        
        f.write("; advance i-pointer past code\n")
        for line in set_i_asm:
            f.write(f"{line}\n")
            
        f.write("\n; renderer sequence\n")
        for line in render_asm:
            f.write(f"{line}\n")
            
        f.write("END\n\n")
        
        f.write("; ====== IMAGE PAYLOAD ======\n")
        for line in raw_asm:
            f.write(f"{line}\n")

    # report specs
    code_sz = target_addr - 0x80
    data_sz = len(raw_asm) * 2
    pct = round(((code_sz + data_sz) / 65536) * 100, 2)
    print(f"compiled {in_path} -> {out_path}")
    print(f"-> code size: {code_sz} bytes | data size: {data_sz} bytes")
    print(f"-> memory usage: {pct}% of 64kb memory.")

# main
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"usage: python {__file__} <input_image> <output_asm>")
        sys.exit(1)
    convert_image(sys.argv[1], sys.argv[2])