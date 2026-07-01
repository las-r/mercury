import os
import subprocess
import sys
import pyray as rl

from .memory import Memory
from .display import Display
from .cpu import Processor, HaltProgram

# mercury main
# by las-r

# settings
CPF = 11
ASM_TOOL = os.path.join(os.path.dirname(__file__), "tools/assembler.py")
CONV_TOOL = os.path.join(os.path.dirname(__file__), "tools/img_to_merc.py")

# program loader
def load_program(ram: Memory, path: str):
    with open(path, "rb") as f:
        data = f.read()
    for offset, byte in enumerate(data):
        ram[0x80 + offset] = byte

# tool wrapper
def run_tool(tool_path: str, args: list):
    try:
        subprocess.run([sys.executable, tool_path] + args, check=True)
    except subprocess.CalledProcessError:
        sys.exit(1)

# main
def main():
    if len(sys.argv) < 2:
        print("usage: python -m mercury [--asm <src> <bin>] [--conv <img> <asm>] <program.bin>")
        sys.exit(1)

    # handle tools
    if sys.argv[1] == "--asm":
        if len(sys.argv) < 4:
            print("usage: python -m mercury --asm <src> <bin>")
            sys.exit(1)
        run_tool(ASM_TOOL, sys.argv[2:4])
        sys.exit(0)

    if sys.argv[1] == "--conv":
        if len(sys.argv) < 4:
            print("usage: python -m mercury --conv <img> <asm>")
            sys.exit(1)
        run_tool(CONV_TOOL, sys.argv[2:4])
        sys.exit(0)

    # run emulator
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