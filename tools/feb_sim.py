#!/usr/bin/env python3
"""
feb_sim.py - Flashiibo Executable Binary (.feb) Pygame Simulator

A high-fidelity desktop simulator for Flashiibo Pro Gen3 FEB games and applications.
Simulates the FEB runtime, 128x64 monochrome OLED display, 4-button hardware navigation,
u8g2 typography, vector geometry, and sidecar .sav persistence.

Usage:
    python3 tools/feb_sim.py [path_to_game.feb] [options]

Controls:
    UP:          W / Up Arrow / K
    DOWN:        S / Down Arrow / J
    BACK (Left): A / Left Arrow / U / Backspace / Esc
    OK (Right):  D / Right Arrow / O / Enter / Space
    EXIT CHORD:  Hold UP + DOWN simultaneously (or press Q)
    RESTART:     R / F2
    PALETTE:     T / F3 (Cycle OLED Ice, Pure White, Amber CRT, Matrix Green)
    STATS OSD:   F4 (Toggle debug statistics)
    HELP / HUD:  H / F1 / Tab (Toggle controls guide)
    PAUSE:       P
    FULLSCREEN:  F11 / F
"""

import os
import sys
import argparse
import time

# Ensure tools directory is in sys.path
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)

import feb_vm
import feb_fonts

# Display constants
NATIVE_WIDTH = 128
NATIVE_HEIGHT = 64
DEFAULT_SCALE = 6  # 768x384 window
DEFAULT_FPS = 60

# Palette presets: (bg_color, fg_color)
THEMES = {
    "oled": {
        "name": "OLED Ice Blue",
        "bg": (12, 14, 18),
        "fg": (235, 245, 255),
        "hud_bg": (20, 24, 32, 220),
        "hud_fg": (180, 210, 240),
    },
    "white": {
        "name": "Classic Monochrome",
        "bg": (0, 0, 0),
        "fg": (255, 255, 255),
        "hud_bg": (16, 16, 16, 220),
        "hud_fg": (220, 220, 220),
    },
    "amber": {
        "name": "Amber CRT",
        "bg": (20, 14, 8),
        "fg": (255, 176, 0),
        "hud_bg": (28, 20, 10, 220),
        "hud_fg": (255, 200, 80),
    },
    "green": {
        "name": "Phosphor Matrix Green",
        "bg": (8, 16, 10),
        "fg": (64, 255, 64),
        "hud_bg": (12, 24, 14, 220),
        "hud_fg": (120, 255, 120),
    },
}

THEME_KEYS = list(THEMES.keys())

# Lookup table for fast 1-bit to 8-bit unpacking (128x64 1:1)
LUT_1X = [bytes([(b >> (7 - bit)) & 1 for bit in range(8)]) for b in range(256)]

# Lookup table for fast 1-bit to 8-bit unpacking (64x32 2x scale)
LUT_2X = []
for b in range(256):
    row_bytes = bytearray(16)
    for bit in range(8):
        v = (b >> (7 - bit)) & 1
        row_bytes[bit * 2] = v
        row_bytes[bit * 2 + 1] = v
    LUT_2X.append(bytes(row_bytes))


class FebSimulator:
    """Pygame-based Flashiibo FEB desktop simulator."""

    def __init__(self, feb_path, scale=DEFAULT_SCALE, theme="oled", headless=False, ips=10000):
        self.feb_path = feb_path
        self.scale = max(1, int(scale))
        self.theme_idx = THEME_KEYS.index(theme) if theme in THEME_KEYS else 0
        self.headless = headless
        self.ips = ips

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        import pygame
        self.pygame = pygame
        self.pygame.init()
        self.pygame.font.init()

        # UI state
        self.fullscreen = False
        self.paused = False
        self.show_help = False
        self.show_stats = False
        self.running = True

        # Clock & perf tracking
        self.clock = self.pygame.time.Clock()
        self.frame_count = 0
        self.fps = 60.0
        self.last_perf_time = time.perf_counter()
        self.last_instructions = 0
        self.ips_current = 0

        # UI Font for HUD / OSD
        self.osd_font = self.pygame.font.SysFont("menlo,consolas,courier,monospace", 13)
        self.osd_font_large = self.pygame.font.SysFont("menlo,consolas,courier,monospace", 16, bold=True)

        # VM instance
        self.vm = feb_vm.FebVM()
        self.load_app(feb_path)

        # 8-bit indexed surface for authentic monochrome OLED rendering
        self.oled_surf = self.pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT), depth=8)
        self.apply_theme()

        # Pygame display setup
        self.window_w = NATIVE_WIDTH * self.scale
        self.window_h = NATIVE_HEIGHT * self.scale

        if not self.headless:
            self.screen = self.pygame.display.set_mode((self.window_w, self.window_h), self.pygame.RESIZABLE)
            self.update_window_title()
            self.set_window_icon()
        else:
            self.screen = self.pygame.display.set_mode((self.window_w, self.window_h))

    def apply_theme(self):
        """Applies active color palette to 8-bit OLED surface."""
        theme_cfg = THEMES[THEME_KEYS[self.theme_idx]]
        self.oled_surf.set_palette([theme_cfg["bg"], theme_cfg["fg"]])

    def cycle_theme(self):
        """Cycles to the next OLED color palette."""
        self.theme_idx = (self.theme_idx + 1) % len(THEME_KEYS)
        self.apply_theme()

    def update_window_title(self):
        """Updates window title with application title, version, and author."""
        app_name = self.vm.title if self.vm.title else os.path.basename(self.feb_path)
        ver_str = f" v{self.vm.version}" if self.vm.version else ""
        auth_str = f" ({self.vm.author})" if self.vm.author else ""
        mode_str = "128x64" if self.vm.schip_mode else "64x32"
        paused_str = " [PAUSED]" if self.paused else ""
        title = f"[Flashiibo FEB Sim] {app_name}{ver_str}{auth_str} - {mode_str} @ {self.fps:.1f} FPS{paused_str}"
        self.pygame.display.set_caption(title)

    def set_window_icon(self):
        """Extracts and sets the 16x16 1-bit icon from the .feb container header."""
        if not self.vm.icon or len(self.vm.icon) != 32:
            return
        icon_surf = self.pygame.Surface((16, 16))
        theme_cfg = THEMES[THEME_KEYS[self.theme_idx]]
        for row in range(16):
            w = (self.vm.icon[row * 2] << 8) | self.vm.icon[row * 2 + 1]
            for col in range(16):
                color = theme_cfg["fg"] if (w & (0x8000 >> col)) else theme_cfg["bg"]
                icon_surf.set_at((col, row), color)
        self.pygame.display.set_icon(icon_surf)

    def load_app(self, path):
        """Loads a .feb application package or raw .ch8 ROM."""
        self.feb_path = os.path.abspath(path)
        if not os.path.exists(self.feb_path):
            raise FileNotFoundError(f"File not found: '{self.feb_path}'")

        if self.feb_path.endswith(".feb"):
            self.vm.load_feb(self.feb_path)
        else:
            with open(self.feb_path, "rb") as f:
                self.vm.load_rom(f.read())
            self.vm.title = os.path.splitext(os.path.basename(self.feb_path))[0]

    def reset_app(self):
        """Restarts the active application from address 0x200."""
        self.vm.reset()
        if self.feb_path.endswith(".feb"):
            self.vm.load_feb(self.feb_path)
        else:
            with open(self.feb_path, "rb") as f:
                self.vm.load_rom(f.read())

    def handle_input(self):
        """Processes Pygame events, keyboard controls, and shortcuts."""
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.running = False
                return

            elif event.type == self.pygame.VIDEORESIZE and not self.headless:
                self.window_w = event.w
                self.window_h = event.h
                self.screen = self.pygame.display.set_mode((self.window_w, self.window_h), self.pygame.RESIZABLE)

            elif event.type == self.pygame.KEYDOWN:
                # Simulator Meta Controls
                if event.key in (self.pygame.K_h, self.pygame.K_F1, self.pygame.K_TAB):
                    self.show_help = not self.show_help
                elif event.key == self.pygame.K_F4:
                    self.show_stats = not self.show_stats
                elif event.key in (self.pygame.K_t, self.pygame.K_F3):
                    self.cycle_theme()
                elif event.key in (self.pygame.K_r, self.pygame.K_F2):
                    self.reset_app()
                elif event.key == self.pygame.K_p:
                    self.paused = not self.paused
                elif event.key in (self.pygame.K_F11, self.pygame.K_f):
                    self.toggle_fullscreen()
                elif event.key == self.pygame.K_q:
                    # Emulate UP + DOWN exit chord
                    self.vm.exited = True
                    self.vm.flush_save_sidecar()

                # Flashiibo 4-Button Hardware Navigation
                if event.key in (self.pygame.K_UP, self.pygame.K_w, self.pygame.K_k):
                    self.vm.press_key(feb_vm.FEB_KEY_UP)
                elif event.key in (self.pygame.K_DOWN, self.pygame.K_s, self.pygame.K_j):
                    self.vm.press_key(feb_vm.FEB_KEY_DOWN)
                elif event.key in (self.pygame.K_LEFT, self.pygame.K_a, self.pygame.K_u, self.pygame.K_ESCAPE, self.pygame.K_BACKSPACE):
                    self.vm.press_key(feb_vm.FEB_KEY_LEFT)
                elif event.key in (self.pygame.K_RIGHT, self.pygame.K_d, self.pygame.K_o, self.pygame.K_RETURN, self.pygame.K_SPACE):
                    self.vm.press_key(feb_vm.FEB_KEY_RIGHT)

            elif event.type == self.pygame.KEYUP:
                if event.key in (self.pygame.K_UP, self.pygame.K_w, self.pygame.K_k):
                    self.vm.release_key(feb_vm.FEB_KEY_UP)
                elif event.key in (self.pygame.K_DOWN, self.pygame.K_s, self.pygame.K_j):
                    self.vm.release_key(feb_vm.FEB_KEY_DOWN)
                elif event.key in (self.pygame.K_LEFT, self.pygame.K_a, self.pygame.K_u, self.pygame.K_ESCAPE, self.pygame.K_BACKSPACE):
                    self.vm.release_key(feb_vm.FEB_KEY_LEFT)
                elif event.key in (self.pygame.K_RIGHT, self.pygame.K_d, self.pygame.K_o, self.pygame.K_RETURN, self.pygame.K_SPACE):
                    self.vm.release_key(feb_vm.FEB_KEY_RIGHT)

    def toggle_fullscreen(self):
        """Toggles fullscreen display."""
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        flags = self.pygame.FULLSCREEN if self.fullscreen else self.pygame.RESIZABLE
        self.screen = self.pygame.display.set_mode((self.window_w, self.window_h), flags)

    def render_framebuffer(self):
        """Unpacks 1-bit packed display buffer into 8-bit OLED surface."""
        if self.vm.schip_mode:
            # 128x64 1:1 unpack
            unpacked = b"".join(LUT_1X[b] for b in self.vm.display)
            self.oled_surf.get_buffer().write(unpacked)
        else:
            # 64x32 2x2 integer scale to 128x64 matching feb_runner_view.c
            out = bytearray(8192)
            for y in range(32):
                row_packed = self.vm.display[y * 8:(y + 1) * 8]
                row_128 = b"".join(LUT_2X[b] for b in row_packed)
                out[y * 2 * 128:(y * 2 + 1) * 128] = row_128
                out[(y * 2 + 1) * 128:(y * 2 + 2) * 128] = row_128
            self.oled_surf.get_buffer().write(out)

    def draw(self):
        """Blits scaled OLED screen and overlays onto main window."""
        self.render_framebuffer()

        # Compute scaling with aspect ratio preservation
        win_w, win_h = self.screen.get_size()
        scale_x = win_w / NATIVE_WIDTH
        scale_y = win_h / NATIVE_HEIGHT
        int_scale = max(1, int(min(scale_x, scale_y)))

        disp_w = NATIVE_WIDTH * int_scale
        disp_h = NATIVE_HEIGHT * int_scale
        offset_x = (win_w - disp_w) // 2
        offset_y = (win_h - disp_h) // 2

        # Clear letterbox borders
        self.screen.fill((5, 5, 8))

        # Scaled OLED display
        scaled = self.pygame.transform.scale(self.oled_surf, (disp_w, disp_h))
        self.screen.blit(scaled, (offset_x, offset_y))

        # Overlays
        theme = THEMES[THEME_KEYS[self.theme_idx]]
        if self.vm.exited:
            self.draw_exit_banner(offset_x, offset_y, disp_w, disp_h, theme)
        elif self.paused:
            self.draw_paused_banner(offset_x, offset_y, disp_w, disp_h, theme)

        if self.show_help:
            self.draw_help_overlay(win_w, win_h, theme)

        if self.show_stats:
            self.draw_stats_overlay(win_w, win_h, theme)

        if not self.headless:
            self.pygame.display.flip()

    def draw_exit_banner(self, ox, oy, dw, dh, theme):
        """Draws exit notification overlay."""
        overlay = self.pygame.Surface((dw, 56), self.pygame.SRCALPHA)
        overlay.fill((16, 20, 28, 230))
        txt1 = self.osd_font_large.render("APPLICATION EXITED", True, theme["fg"])
        txt2 = self.osd_font.render("Press R to Restart  |  Press Q / ESC to Quit", True, (180, 190, 200))
        overlay.blit(txt1, ((dw - txt1.get_width()) // 2, 8))
        overlay.blit(txt2, ((dw - txt2.get_width()) // 2, 32))
        self.screen.blit(overlay, (ox, oy + (dh - 56) // 2))

    def draw_paused_banner(self, ox, oy, dw, dh, theme):
        """Draws pause banner overlay."""
        overlay = self.pygame.Surface((dw, 36), self.pygame.SRCALPHA)
        overlay.fill((16, 20, 28, 210))
        txt = self.osd_font_large.render("PAUSED (Press P to Resume)", True, theme["fg"])
        overlay.blit(txt, ((dw - txt.get_width()) // 2, 8))
        self.screen.blit(overlay, (ox, oy + (dh - 36) // 2))

    def draw_help_overlay(self, win_w, win_h, theme):
        """Draws on-screen controls HUD guide."""
        w = min(560, win_w - 40)
        h = 240
        x = (win_w - w) // 2
        y = (win_h - h) // 2

        overlay = self.pygame.Surface((w, h), self.pygame.SRCALPHA)
        overlay.fill(theme["hud_bg"])
        self.pygame.draw.rect(overlay, theme["fg"], (0, 0, w, h), 2)

        lines = [
            ("Flashiibo FEB Simulator - Controls", True),
            ("", False),
            ("  [UP]        : W  / Up Arrow / K", False),
            ("  [DOWN]      : S  / Down Arrow / J", False),
            ("  [BACK/LEFT] : A  / Left Arrow / U / Esc / Backspace", False),
            ("  [OK/RIGHT]  : D  / Right Arrow / O / Enter / Space", False),
            ("  [EXIT CHORD]: UP + DOWN held together (or Q)", False),
            ("", False),
            ("Shortcuts: [R] Restart  | [T] Palette  | [F4] Stats  | [P] Pause", False),
            ("Press TAB / H / F1 to close this overlay", False),
        ]

        cur_y = 14
        for text, bold in lines:
            font = self.osd_font_large if bold else self.osd_font
            rendered = font.render(text, True, theme["fg"] if bold else theme["hud_fg"])
            overlay.blit(rendered, (20, cur_y))
            cur_y += 20 if not bold else 24

        self.screen.blit(overlay, (x, y))

    def draw_stats_overlay(self, win_w, win_h, theme):
        """Draws performance and registers debug overlay."""
        overlay = self.pygame.Surface((280, 160), self.pygame.SRCALPHA)
        overlay.fill((12, 16, 22, 220))
        self.pygame.draw.rect(overlay, theme["fg"], (0, 0, 280, 160), 1)

        reg_str1 = " ".join(f"{self.vm.v[i]:02X}" for i in range(8))
        reg_str2 = " ".join(f"{self.vm.v[i]:02X}" for i in range(8, 16))

        lines = [
            f"FPS: {self.fps:.1f}  |  IPS: {self.ips_current}",
            f"Mode: {'128x64 Super-CHIP' if self.vm.schip_mode else '64x32 CHIP-8'}",
            f"PC: 0x{self.vm.pc:03X}  |  I: 0x{self.vm.i:04X}  |  SP: {self.vm.sp}",
            f"DT: {self.vm.delay_timer}  |  ST: {self.vm.sound_timer}  |  Mode: {self.vm.draw_mode}",
            f"V0..V7: {reg_str1}",
            f"V8..VF: {reg_str2}",
            f"Keys: 0x{self.vm.keys:04X} (Btns: 0x{self.vm.physical_buttons_down:02X})",
        ]

        cur_y = 8
        for line in lines:
            t = self.osd_font.render(line, True, theme["hud_fg"])
            overlay.blit(t, (10, cur_y))
            cur_y += 20

        self.screen.blit(overlay, (10, 10))

    def step(self):
        """Executes one 60 Hz frame."""
        if not self.paused and not self.vm.exited:
            self.vm.step_frame(max_steps=self.ips)

        self.frame_count += 1
        now = time.perf_counter()
        elapsed = now - self.last_perf_time
        if elapsed >= 0.5:
            self.fps = self.clock.get_fps()
            delta_inst = self.vm.instructions_executed - self.last_instructions
            self.ips_current = int(delta_inst / elapsed)
            self.last_perf_time = now
            self.last_instructions = self.vm.instructions_executed
            if not self.headless:
                self.update_window_title()

    def run(self, max_frames=None, screenshot_path=None):
        """Main game loop."""
        try:
            while self.running:
                self.handle_input()
                self.step()
                self.draw()

                if max_frames and self.frame_count >= max_frames:
                    break

                self.clock.tick(DEFAULT_FPS)

            if screenshot_path:
                self.save_screenshot(screenshot_path)

        finally:
            self.vm.flush_save_sidecar()
            self.pygame.quit()

    def save_screenshot(self, output_path):
        """Saves current native 128x64 display buffer to a PNG image file."""
        self.render_framebuffer()
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        # Save crisp 128x64 surface
        self.pygame.image.save(self.oled_surf, output_path)
        print(f"[FEB_SIM] Saved screenshot -> {output_path}")


def scan_for_febs(search_dirs=None):
    """Finds available .feb application files in common SDK locations."""
    if search_dirs is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_dirs = [
            os.path.join(root, "build"),
            os.path.join(root, "dist"),
            os.path.join(root, "examples"),
        ]

    found = []
    for d in search_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in sorted(files):
                    if f.endswith(".feb"):
                        found.append(os.path.join(root, f))
    return sorted(list(set(found)))


def main():
    parser = argparse.ArgumentParser(
        description="Flashiibo FEB (Flashiibo Executable Binary) Desktop Pygame Simulator"
    )
    parser.add_argument("file", nargs="?", default=None, help="Path to .feb or .ch8 ROM binary")
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE, help=f"Integer window scale factor (default: {DEFAULT_SCALE}x)")
    parser.add_argument("--theme", choices=THEME_KEYS, default="oled", help="OLED color theme (oled, white, amber, green)")
    parser.add_argument("--ips", type=int, default=10000, help="Instructions per frame budget (default: 10000)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode without window")
    parser.add_argument("--frames", type=int, default=None, help="Exit automatically after N frames")
    parser.add_argument("--screenshot", type=str, default=None, help="Save screenshot PNG to given path on exit")

    args = parser.parse_args()

    target_file = args.file
    if not target_file:
        febs = scan_for_febs()
        if febs:
            # Default to 2048 if present, otherwise first discovered .feb
            default_feb = next((f for f in febs if "2048.feb" in f), febs[0])
            target_file = default_feb
            print(f"[FEB_SIM] No binary specified, running default: {target_file}")
        else:
            print("Error: No .feb binary specified and none found in build/ or examples/.", file=sys.stderr)
            sys.exit(1)

    print(f"[FEB_SIM] Launching Flashiibo FEB Simulator: {target_file}")
    sim = FebSimulator(
        feb_path=target_file,
        scale=args.scale,
        theme=args.theme,
        headless=args.headless,
        ips=args.ips
    )
    sim.run(max_frames=args.frames, screenshot_path=args.screenshot)


if __name__ == "__main__":
    main()
