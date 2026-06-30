import numpy as np
import pyray as rl

# color palette
PALETTE = np.array([
    0x00_00_00_ff, # 0b0000: Black
    0x00_00_00_ff, # 0b0001: Black
    0x00_00_7f_ff, # 0b0010: Blue (Low)
    0x00_00_ff_ff, # 0b0011: Blue (High)
    0x00_7f_00_ff, # 0b0100: Green (Low)
    0x00_ff_00_ff, # 0b0101: Green (High)
    0x00_7f_7f_ff, # 0b0110: Cyan (Low)
    0x00_ff_ff_ff, # 0b0111: Cyan (High)
    0x7f_00_00_ff, # 0b1000: Red (Low)
    0xff_00_00_ff, # 0b1001: Red (High)
    0x7f_00_7f_ff, # 0b1010: Magenta (Low)
    0xff_00_ff_ff, # 0b1011: Magenta (High)
    0x7f_7f_00_ff, # 0b1100: Yellow (Low)
    0xff_ff_00_ff, # 0b1101: Yellow (High)
    0x7f_7f_7f_ff, # 0b1110: Gray (Low)
    0xff_ff_ff_ff, # 0b1111: White (High)
], dtype=np.uint32)

# keypad layout
KEYMAP = {
    0x1: rl.KeyboardKey.KEY_ONE, 0x2: rl.KeyboardKey.KEY_TWO, 0x3: rl.KeyboardKey.KEY_THREE, 0xC: rl.KeyboardKey.KEY_FOUR,
    0x4: rl.KeyboardKey.KEY_Q, 0x5: rl.KeyboardKey.KEY_W, 0x6: rl.KeyboardKey.KEY_E, 0xD: rl.KeyboardKey.KEY_R,
    0x7: rl.KeyboardKey.KEY_A, 0x8: rl.KeyboardKey.KEY_S, 0x9: rl.KeyboardKey.KEY_D, 0xE: rl.KeyboardKey.KEY_F,
    0xA: rl.KeyboardKey.KEY_Z, 0x0: rl.KeyboardKey.KEY_X, 0xB: rl.KeyboardKey.KEY_C, 0xF: rl.KeyboardKey.KEY_V,
}

# display class
class Display:
    def __init__(self):
        self.grids = [np.zeros((64, 128), dtype=np.uint8) for _ in range(4)]
        self.plane = np.uint8(0xf)
        self.rscale = 5
        
        # init window
        rl.init_window(128 * self.rscale, 64 * self.rscale, "Mercury")
        rl.set_target_fps(60)

        # init audio
        rl.init_audio_device()
        self.sound_ticks_remaining = 0
        self._tone = self._make_tone()
        
        # init buffer texture
        self.screen_buffer = np.zeros((64, 128), dtype=np.uint32)
        img = rl.gen_image_color(128, 64, rl.BLACK)
        self.texture = rl.load_texture_from_image(img)
        rl.unload_image(img)
        
    def clear_all(self):
        for grid in self.grids:
            grid.fill(0)
        
    def clear(self):
        for bit in range(4):
            if (self.plane >> bit) & 1:
                self.grids[bit].fill(0)
                
    def draw_sprite(self, x, y, sprite_bytes):
        x = int(x) % 128
        y = int(y) % 64
        collision = 0
        for bit in range(4):
            if not (self.plane >> bit) & 1:
                continue
            grid = self.grids[bit]
            for row, byte in enumerate(sprite_bytes):
                py = (y + row) % 64
                for col in range(8):
                    if not (byte >> (7 - col)) & 1:
                        continue
                    px = (x + col) % 128
                    if grid[py, px]:
                        collision = 1
                    grid[py, px] ^= 1
        return collision

    def render(self):
        active_masks = np.unpackbits(np.uint8(self.plane) << 4, count=4)
        color_indices = np.zeros((64, 128), dtype=np.uint8)
        for i in range(4):
            if active_masks[i]:
                color_indices |= (np.clip(self.grids[i], 0, 1) << i)
        self.screen_buffer[:, :] = PALETTE[color_indices]
        pixel_ptr = rl.ffi.cast('void *', rl.ffi.from_buffer(self.screen_buffer))
        rl.update_texture(self.texture, pixel_ptr)
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)
        rl.draw_texture_ex(
            self.texture, 
            rl.Vector2(0, 0), 
            0.0, 
            float(self.rscale), 
            rl.WHITE
        )
        rl.end_drawing()

    def deinit(self):
        rl.unload_texture(self.texture)
        rl.unload_sound(self._tone)
        rl.close_audio_device()
        rl.close_window()

    def _make_tone(self, freq=440, duration=0.05, sample_rate=44100):
        n = int(sample_rate * duration)
        t = np.arange(n) / sample_rate
        wave = np.where(np.sin(2 * np.pi * freq * t) >= 0, 1.0, -1.0)
        samples = (wave * 0.3 * 32767).astype(np.int16)
        wave_struct = rl.Wave(n, sample_rate, 16, 1, samples)
        return rl.load_sound_from_wave(wave_struct)

    def buzz(self, ticks):
        self.sound_ticks_remaining = int(ticks)
        if self.sound_ticks_remaining > 0 and not rl.is_sound_playing(self._tone):
            rl.play_sound(self._tone)

    def update_sound(self):
        if self.sound_ticks_remaining > 0:
            self.sound_ticks_remaining -= 1
            if self.sound_ticks_remaining == 0:
                rl.stop_sound(self._tone)

    # key input helpers
    def key_down(self, key):
        phys = KEYMAP.get(key & 0xf)
        return phys is not None and rl.is_key_down(phys)

    def key_pressed(self, key):
        phys = KEYMAP.get(key & 0xf)
        return phys is not None and rl.is_key_pressed(phys)

    def any_key_pressed(self):
        for k, phys in KEYMAP.items():
            if rl.is_key_pressed(phys):
                return k
        return None