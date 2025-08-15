
# ENIAC Step Demo (Pygame)
# --------------------------------------
# Features (MVP):
# - Initiating Unit with STEP and RESET buttons
# - Constant Transmitter (fixed 10-digit constant) -> Accumulator(α) via cable
# - Step-by-step progression:
#     READY -> CONTROL -> DATA (10 sub-steps) -> APPLY -> DONE
# - Visuals: panels, ports, cable with moving pulse indicator, decade lamps + sign
#
# How to run:
#   1) pip install pygame
#   2) python eniac_step_pygame.py
#
# Controls:
#   - Click STEP to advance one phase/sub-step
#   - Click RESET to clear and return to READY
#   - Esc / window close to exit
#
# Notes:
#   - This is a minimal educational visualization faithful to the "feel" of Virtual ENIAC.
#   - Accumulator implements decimal addition with carry across 10 digits (sign not used here).
#   - The constant is editable below (CONST_DIGITS).
#
import sys
import pygame
from dataclasses import dataclass
from typing import List, Tuple

pygame.init()
pygame.display.set_caption('ENIAC (Pygame) — Step Demo')

# ----------------------------
# Config
# ----------------------------
W, H = 980, 600
BG = (26, 28, 34)
PANEL = (46, 49, 56)
PANEL_DARK = (36, 38, 44)
OUTLINE = (90, 95, 105)
TEXT = (230, 232, 237)
ACCENT = (120, 226, 255)   # Data bus highlight
CTRL = (255, 206, 120)     # Control bus highlight
OK = (90, 220, 90)
WARN = (255, 110, 90)
DIM = (150, 150, 155)

FONT = pygame.font.SysFont("consolas,menlo,monospace", 18)
FONT_SMALL = pygame.font.SysFont("consolas,menlo,monospace", 14)
FONT_BIG = pygame.font.SysFont("consolas,menlo,monospace", 22, bold=True)

# 10-digit constant to transmit (edit freely)
# Example: 0000000015 -> adds 15
CONST_DIGITS = [0,0,0,0,0,0,0,0,1,5]

# ----------------------------
# Helpers
# ----------------------------
def draw_panel(screen, rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=10)
    pygame.draw.rect(screen, OUTLINE, rect, width=1, border_radius=10)
    if title:
        label = FONT.render(title, True, TEXT)
        screen.blit(label, (rect.x + 10, rect.y + 8))

def draw_led(screen, center, on, label=None, on_color=OK):
    r = 7
    color = on_color if on else (70, 72, 78)
    pygame.draw.circle(screen, color, center, r)
    pygame.draw.circle(screen, OUTLINE, center, r, 1)
    if label:
        t = FONT_SMALL.render(label, True, TEXT)
        screen.blit(t, (center[0] + 12, center[1] - 8))

class Button:
    def __init__(self, rect: pygame.Rect, text: str):
        self.rect = rect
        self.text = text
        self.enabled = True

    def draw(self, screen, color=(82, 122, 255)):
        fill = color if self.enabled else (80, 80, 90)
        pygame.draw.rect(screen, fill, self.rect, border_radius=8)
        pygame.draw.rect(screen, OUTLINE, self.rect, width=1, border_radius=8)
        label = FONT_BIG.render(self.text, True, (10, 12, 14))
        tw, th = label.get_size()
        screen.blit(label, (self.rect.centerx - tw//2, self.rect.centery - th//2))

    def handle(self, event) -> bool:
        if not self.enabled: return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

# ----------------------------
# Cable with pulse visualization
# ----------------------------
@dataclass
class Cable:
    start: Tuple[int, int]
    end: Tuple[int, int]
    color: Tuple[int, int, int] = ACCENT
    width: int = 4

    def draw(self, screen, t: float = None):
        # Base line
        pygame.draw.line(screen, self.color, self.start, self.end, self.width)
        pygame.draw.circle(screen, (10, 10, 12), self.start, 6)  # jack caps
        pygame.draw.circle(screen, (10, 10, 12), self.end, 6)
        # Moving pulse (0..1)
        if t is not None:
            t = max(0.0, min(1.0, t))
            x = self.start[0] + (self.end[0] - self.start[0]) * t
            y = self.start[1] + (self.end[1] - self.start[1]) * t
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 6)
            pygame.draw.circle(screen, (90, 180, 255), (int(x), int(y)), 8, 2)

# ----------------------------
# Units
# ----------------------------
class InitiatingUnit:
    def __init__(self, x, y, step_cb, reset_cb):
        self.rect = pygame.Rect(x, y, 200, 120)
        self.step_btn = Button(pygame.Rect(x+20, y+50, 70, 40), "STEP")
        self.reset_btn = Button(pygame.Rect(x+110, y+50, 70, 40), "RESET")
        self.step_cb = step_cb
        self.reset_cb = reset_cb

    def draw(self, screen, status_text):
        draw_panel(screen, self.rect, "INITIATING")
        # Status line
        s = FONT.render(status_text, True, TEXT)
        screen.blit(s, (self.rect.x + 12, self.rect.y + 28))
        # Buttons
        self.step_btn.draw(screen, (255, 230, 120))
        self.reset_btn.draw(screen, (180, 180, 255))

    def handle(self, event):
        if self.step_btn.handle(event):
            self.step_cb()
        if self.reset_btn.handle(event):
            self.reset_cb()

class ConstantTransmitter:
    def __init__(self, x, y, digits: List[int]):
        self.rect = pygame.Rect(x, y, 220, 120)
        self.digits = digits[:]  # 10 digits
        # Port positions (A output)
        self.port_A = (self.rect.right - 10, self.rect.centery + 20)

    def draw(self, screen, flash=False):
        draw_panel(screen, self.rect, "CONSTANT TX")
        # digits display
        ds = ''.join(str(d) for d in self.digits)
        label = FONT_BIG.render(ds, True, OK if flash else TEXT)
        screen.blit(label, (self.rect.x + 12, self.rect.y + 44))
        # A output jack
        pygame.draw.circle(screen, (0, 0, 0), self.port_A, 7)
        pygame.draw.circle(screen, OUTLINE, self.port_A, 7, 1)
        t = FONT_SMALL.render("A", True, TEXT)
        screen.blit(t, (self.port_A[0] - 5, self.port_A[1] + 10))

class Accumulator:
    def __init__(self, x, y, id="ACC1"):
        self.rect = pygame.Rect(x, y, 260, 260)
        self.id = id
        self.digits = [0]*10  # most significant -> least significant
        self.sign = '+'
        # Ports
        self.port_alpha = (self.rect.x + 10, self.rect.y + self.rect.height - 30)  # α in (left)
        self.port_A = (self.rect.right - 10, self.rect.y + self.rect.height - 30)  # A out (right)

    def reset(self):
        self.digits = [0]*10
        self.sign = '+'

    def apply_add(self, rhs: List[int]):
        # Decimal add rhs (10 digits) into self.digits, LSD-right alignment.
        carry = 0
        for i in range(9, -1, -1):
            s = self.digits[i] + rhs[i] + carry
            self.digits[i] = s % 10
            carry = s // 10
        # ignore overflow beyond 10 digits for MVP

    def draw(self, screen, active=False):
        draw_panel(screen, self.rect, f"ACCUMULATOR {self.id}")
        # Sign + digits row
        ds = ''.join(str(d) for d in self.digits)
        label = FONT_BIG.render(f"{self.sign}{ds}", True, OK if active else TEXT)
        screen.blit(label, (self.rect.x + 16, self.rect.y + 40))

        # decade LEDs (stylized)
        base_x = self.rect.x + 20
        y = self.rect.y + 90
        for i, d in enumerate(self.digits):
            cx = base_x + i * 22
            draw_led(screen, (cx, y), on=(d != 0), label=str(d))

        # ports
        pygame.draw.circle(screen, (0, 0, 0), self.port_alpha, 8)
        pygame.draw.circle(screen, OUTLINE, self.port_alpha, 8, 1)
        t = FONT_SMALL.render("α", True, TEXT)
        screen.blit(t, (self.port_alpha[0] - 6, self.port_alpha[1] + 10))

        pygame.draw.circle(screen, (0, 0, 0), self.port_A, 8)
        pygame.draw.circle(screen, OUTLINE, self.port_A, 8, 1)
        t2 = FONT_SMALL.render("A", True, TEXT)
        screen.blit(t2, (self.port_A[0] - 6, self.port_A[1] + 10))

# ----------------------------
# Simulator Core
# ----------------------------
class Phase:
    READY = "READY"
    CONTROL = "CONTROL"   # trigger issued
    DATA = "DATA"         # transit 0..10
    APPLY = "APPLY"       # apply addition
    DONE = "DONE"

class Simulator:
    def __init__(self, screen):
        self.screen = screen
        # Units
        self.init = InitiatingUnit(30, 30, self.on_step, self.on_reset)
        self.ct = ConstantTransmitter(260, 210, CONST_DIGITS)
        self.acc = Accumulator(560, 160, "A1")

        # Cable from CT.A to ACC.α
        self.cable = Cable(self.ct.port_A, self.acc.port_alpha, color=ACCENT, width=5)

        # State
        self.phase = Phase.READY
        self.data_progress = 0  # 0..10 (DATA phase sub-steps)
        self.last_status = "READY"

    def on_reset(self):
        self.phase = Phase.READY
        self.data_progress = 0
        self.acc.reset()
        self.last_status = "READY"

    def on_step(self):
        # Step state machine
        if self.phase == Phase.READY:
            self.phase = Phase.CONTROL
            self.last_status = "CONTROL: trigger α"
        elif self.phase == Phase.CONTROL:
            self.phase = Phase.DATA
            self.data_progress = 0
            self.last_status = "DATA: transmitting (0/10)"
        elif self.phase == Phase.DATA:
            if self.data_progress < 10:
                self.data_progress += 1
                self.last_status = f"DATA: transmitting ({self.data_progress}/10)"
            if self.data_progress >= 10:
                self.phase = Phase.APPLY
                self.last_status = "APPLY: add constant → accumulator"
        elif self.phase == Phase.APPLY:
            self.acc.apply_add(self.ct.digits)
            self.phase = Phase.DONE
            self.last_status = "DONE: result updated"
        elif self.phase == Phase.DONE:
            # allow chaining another cycle
            self.phase = Phase.CONTROL
            self.data_progress = 0
            self.last_status = "CONTROL: trigger α (repeat)"
        else:
            self.phase = Phase.READY
            self.last_status = "READY"

    def draw(self):
        self.screen.fill(BG)

        # Title
        title = FONT_BIG.render("ENIAC — Pygame Step Demo (CT → α → Accumulator)", True, TEXT)
        self.screen.blit(title, (30, H - 40))

        # Panels
        self.init.draw(self.screen, self.last_status)

        # Control bus (Init to CT) — visual only
        ctrl_line = Cable((130, 150), (self.ct.rect.centerx, self.ct.rect.y - 10), color=CTRL, width=3)
        ctrl_t = None
        if self.phase == Phase.CONTROL:
            ctrl_t = 0.5  # flash marker mid-line
        ctrl_line.draw(self.screen, ctrl_t)

        # Constant Tx
        flash_ct = (self.phase in (Phase.CONTROL, Phase.DATA))
        self.ct.draw(self.screen, flash=flash_ct)

        # Data cable CT.A -> ACC.α
        t = None
        if self.phase == Phase.DATA:
            t = self.data_progress / 10.0
        self.cable.draw(self.screen, t)

        # Accumulator
        active = (self.phase in (Phase.APPLY, Phase.DONE))
        self.acc.draw(self.screen, active=active)

        # Legend
        self.draw_legend()

    def draw_legend(self):
        legend_rect = pygame.Rect(W-260, 20, 220, 140)
        draw_panel(self.screen, legend_rect, "LEGEND")
        y = legend_rect.y + 36
        def put(txt, color):
            nonlocal y
            t = FONT_SMALL.render(txt, True, color)
            self.screen.blit(t, (legend_rect.x + 12, y))
            y += 22
        put("Data bus / cable", ACCENT)
        put("Control bus", CTRL)
        put("STEP: advance phase", TEXT)
        put("RESET: clear & READY", TEXT)

# ----------------------------
# Main loop
# ----------------------------
def main():
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    sim = Simulator(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)
            sim.init.handle(event)

        sim.draw()
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
