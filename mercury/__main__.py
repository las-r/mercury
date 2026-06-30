import sys
import pyray as rl

from .memory import Memory
from .display import Display
from .cpu import Processor, HaltProgram

# mercury main
# by las-r

# settings
CPF = 11

# program loader
def load_program(ram: Memory, path: str):
    with open(path, "rb") as f:
        data = f.read()
    for offset, byte in enumerate(data):
        ram[0x80 + offset] = byte

# main
def main():
    if len(sys.argv) < 2:
        print("usage: python -m mercury <program.bin>")
        sys.exit(1)
    ram = Memory()
    load_program(ram, sys.argv[1])
    disp = Display()
    cpu = Processor(ram, disp)
    halted = False
    try:
        while not rl.window_should_close():
            if not halted:
                for _ in range(CPF):
                    try:
                        opc = cpu.fetch()
                        cpu.execute(opc)
                    except HaltProgram:
                        halted = True
                        break
            cpu.ticktimer()
            disp.update_sound()
            disp.render()
    finally:
        disp.deinit()

if __name__ == "__main__":
    main()