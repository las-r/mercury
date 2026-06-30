from .display import Display
from .memory import Memory
import numpy as np
import random

# mercury cpu
# by las-r

# halt exception
class HaltProgram(Exception):
    pass

# cpu class
class Processor:
    def __init__(self, ram: Memory, disp: Display):
        self.ram = ram
        self.disp = disp

        self.r = np.zeros(16, dtype=np.uint8)
        self.i = 0x0000
        self.pc = 0x80
        self.stk = []

        self.timer = np.uint8(0)
        self.timer_paused = False

    def fetch(self):
        hi = int(self.ram[self.pc])
        lo = int(self.ram[self.pc + 1])
        opc = np.uint16(hi << 8 | lo)
        self.pc += 2
        return opc

    def ticktimer(self):
        if not self.timer_paused and self.timer > 0:
            self.timer = np.uint8(self.timer - 1)

    def execute(self, opc):
        opc = int(opc)
        inst = (opc >> 12) & 0xf
        x = (opc >> 8) & 0xf
        y = (opc >> 4) & 0xf
        z = opc & 0xf
        yz = (y << 4) | z
        xyz = (x << 8) | (y << 4) | z

        rx, ry, rz = int(self.r[x]), int(self.r[y]), int(self.r[z])
        rxry = (rx << 4) | ry

        match (inst, x, y, z):
            # misc
            case (0, 0, 0, 0):
                pass
            case (0, 0, 13, 13):
                self.disp.clear_all()
            case (0, 0, 13, 14):
                self.disp.clear()
            case (0, 0, 14, 14):
                raise HaltProgram
            case (15, _, 0, 15):
                self.r[x] = random.randint(0, 255)

            # control flow
            case (1, _, _, _):
                self.r[x] = yz
            case (2, _, _, _):
                self.stk.append(self.pc)
                self.pc = (rxry + rz) & 0xffff
            case (3, _, 0, 0):
                self.pc = (self.stk.pop() + rx) & 0xffff
            case (14, _, _, _):
                self.pc = (rxry + rz) & 0xffff
            case (4, _, 1, 15):
                self.pc = (self.pc + rx) & 0xffff
            case (4, _, 2, 15):
                self.pc = (self.pc - rx) & 0xffff

            # skip
            case (4, _, 0, 0):
                if rx == 0:
                    self.pc += 2
            case (7, _, _, 0):
                if rx == ry:
                    self.pc += 2
                    if rx > ry:
                        self.pc += 2
            case (7, _, _, 1):
                if rx != ry:
                    self.pc += 2
                    if rx < ry:
                        self.pc += 2

            # alu
            case (7, _, _, 15):
                self.r[x] = (~ry) & 0xff
                self.r[0xf] = 0
            case (8, _, _, _):
                self.r[x] = ry & rz
                self.r[0xf] = 0
            case (9, _, _, _):
                self.r[x] = ry | rz
                self.r[0xf] = 0
            case (10, _, _, _):
                self.r[x] = ry ^ rz
                self.r[0xf] = 0
            case (11, _, _, _):
                total = ry + rz
                self.r[x] = total & 0xff
                self.r[0xf] = 1 if total > 0xff else 0
            case (12, _, _, _):
                diff = ry - rz
                self.r[x] = diff & 0xff
                self.r[0xf] = 0 if ry >= rz else 1
            case (15, _, 14, 0):
                flag = (rx >> 7) & 1
                self.r[x] = (rx << 1) & 0xff
                self.r[0xf] = flag
            case (15, _, 15, 1):
                flag = rx & 1
                self.r[x] = (rx >> 1) & 0xff
                self.r[0xf] = flag

            # memory
            case (5, _, 0, 0):
                self.ram[self.i] = self.r[x]
            case (5, _, 0, 1):
                self.r[x] = self.ram[self.i]
            case (5, _, 1, 0):
                self.i = rx & 0xffff
            case (5, _, 1, 1):
                self.i = (self.i + rx) & 0xffff
            case (5, _, 1, 2):
                self.i = (self.i - rx) & 0xffff

            # key input
            case (6, _, 0, 0):
                key = self.disp.any_key_pressed()
                if key is None:
                    self.pc -= 2
                else:
                    self.r[x] = key
            case (6, _, 1, 0):
                if not self.disp.key_down(z):
                    self.pc -= 2
            case (6, _, 1, 1):
                if self.disp.key_down(z):
                    self.pc += 2
            case (6, _, 1, 2):
                if self.disp.key_down(z):
                    self.pc -= 2
            case (6, _, 2, 0):
                if not self.disp.key_down(rz):
                    self.pc -= 2
            case (6, _, 2, 1):
                if self.disp.key_down(rz):
                    self.pc += 2
            case (6, _, 2, 2):
                if self.disp.key_down(rz):
                    self.pc -= 2

            # display
            case (13, _, _, _):
                sprite = [int(self.ram[self.i + row]) for row in range(z)]
                self.r[0xf] = self.disp.draw_sprite(rx, ry, sprite)
            case (15, _, 3, 0):
                self.disp.plane = np.uint8(x)

            # font
            case (15, _, 0, 0):
                self.i = (rx * 5) & 0xffff

            # timer
            case (15, _, 0, 1):
                self.timer = np.uint8(rx)
            case (15, _, 0, 2):
                self.r[x] = self.timer
            case (15, _, 0, 3):
                if self.timer != 0:
                    self.pc -= 2
            case (15, 15, 0, 4):
                self.timer_paused = True
            case (15, 15, 0, 5):
                self.timer_paused = False

            # sound
            case (15, _, 2, 0):
                self.disp.buzz(rx)

            case _:
                pass