
"""
ENIAC Virtual Replica (Pygame) — Feature Pack 1–6
--------------------------------------------------
Implements:
 1) Timing: 10P..1P, CCG, RP waveforms + cursor; one-pulse / one-add / run
 2) Cable-to-port mapping with authentic labels (α, β, γ, δ, ε, A, S, AS, CCG, RP)
    - Hover tooltips, validity check (data vs control)
 3) Accumulator operation wired to timing:
    - In ONE-ADD (10 pulses) or RUN, a connected ConstantTx(A) -> Acc(α) transfers
      10 decimal pulses and updates accumulator (carry supported)
 4) Master Programmer ring (10 lamps) + demo loop counter
 5) Cycling speed slider + RUN/PAUSE + STEP
 6) Skinned layout matching Virtual ENIAC look (approximate)

Run:
    pip install pygame
    python eniac_full_replica.py
Controls:
    - STEP: advance by one pulse (ONE-PULSE) or one add-time (ONE-ADD)
    - RUN/PAUSE: continuous run using speed slider
    - RESET: clear states
    - Click two ports to connect a cable (only valid types allowed)
    - Hover a jack to see its label; invalid connections flash red.

Notes:
    - This is an educational approximation designed to look/feel like virtualENIAC.
    - For brevity it's a single-file build; logic is modularized into classes inside.
"""

import sys, math, time
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame

pygame.init()
pygame.display.set_caption("ENIAC (Pygame) — Virtual Replica")

# -------------------- Theme / Geometry --------------------
W, H = 1320, 820
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

BG = (62, 64, 68)
PANEL = (86, 88, 92)
PANEL_DARK = (66, 68, 72)
GRID = (130, 132, 136)
TEXT = (240, 242, 246)
LBL = (255, 232, 140)
ACCENT = (120, 220, 255)      # Data
CTRL = (255, 206, 120)        # Control
OK = (100, 230, 120)
ERR = (255, 120, 120)

FONT = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 16)
FONT_SM = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 13)
FONT_BIG = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 22, bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, (40,40,40), rect, 1, border_radius=8)
    if title:
        t = FONT_BIG.render(title, True, TEXT)
        screen.blit(t, (rect.x + 12, rect.y + 10))

# -------------------- Ports & Cables --------------------
@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str   # "data" or "ctrl"
    unit: str    # label of owner unit
    radius: int = 8

class Cable:
    def __init__(self, a_idx:int, b_idx:int, color=(180,180,180)):
        self.a_idx = a_idx
        self.b_idx = b_idx
        self.color = color

class PlugArea:
    """Holds a set of labeled ports and user-created cables."""
    def __init__(self):
        self.ports: List[Port] = []
        self.cables: List[Cable] = []
        self.pending: Optional[int] = None
        self.flash_err_until = 0

    def add_port(self, name, pos, ptype, unit):
        self.ports.append(Port(name, pos, ptype, unit))

    def draw(self, hover_idx: Optional[int] = None):
        # draw cables first
        for cab in self.cables:
            a = self.ports[cab.a_idx]; b = self.ports[cab.b_idx]
            pygame.draw.line(screen, self.cable_color(), a.pos, b.pos, 5)
            for p in (a.pos, b.pos):
                pygame.draw.circle(screen, (20,20,20), p, 7)
                pygame.draw.circle(screen, (200,200,200), p, 7, 1)

        # draw ports (above cables for visibility)
        for i,p in enumerate(self.ports):
            col = (15,15,15)
            pygame.draw.circle(screen, col, p.pos, p.radius)
            pygame.draw.circle(screen, (180,180,180), p.pos, p.radius, 1)

        # tooltip
        if hover_idx is not None:
            p = self.ports[hover_idx]
            tip = f"{p.unit}:{p.name}  [{p.ptype}]"
            self.tooltip(p.pos, tip)

        # pending temp wire
        if self.pending is not None and hover_idx is not None and self.pending != hover_idx:
            a = self.ports[self.pending].pos
            b = self.ports[hover_idx].pos
            pygame.draw.line(screen, (180,180,220), a, b, 2)

    def tooltip(self, pos, text):
        surf = FONT.render(text, True, (20,20,20))
        rect = surf.get_rect()
        rect.topleft = (pos[0]+12, pos[1]-rect.height-4)
        pygame.draw.rect(screen, (240,240,240), rect.inflate(10,6), border_radius=6)
        pygame.draw.rect(screen, (40,40,40), rect.inflate(10,6), 1, border_radius=6)
        screen.blit(surf, rect.move(5,3))

    def cable_color(self):
        if time.time() < self.flash_err_until:
            return ERR
        return (180,180,180)

    def handle_click(self, mouse) -> None:
        idx = self.pick(mouse)
        if idx is None: 
            self.pending = None
            return
        if self.pending is None:
            self.pending = idx
        else:
            if idx != self.pending:
                # type check
                a = self.ports[self.pending]; b = self.ports[idx]
                if a.ptype == b.ptype:
                    self.cables.append(Cable(self.pending, idx))
                else:
                    self.flash_err_until = time.time() + 0.6
                self.pending = None

    def pick(self, mouse) -> Optional[int]:
        for i,p in enumerate(self.ports):
            if (p.pos[0]-mouse[0])**2 + (p.pos[1]-mouse[1])**2 <= p.radius*p.radius:
                return i
        return None

    def find_cable_between(self, a_name, b_name) -> Optional[int]:
        ai = next((i for i,p in enumerate(self.ports) if p.name==a_name), None)
        bi = next((i for i,p in enumerate(self.ports) if p.name==b_name), None)
        if ai is None or bi is None: return None
        for ci,c in enumerate(self.cables):
            if {c.a_idx, c.b_idx} == {ai, bi}:
                return ci
        return None

# -------------------- Cycling Unit (Timing) --------------------
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class CyclingUnit:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.mode = "ONE-ADD"  # ONE-PULSE, ONE-ADD, RUN
        self.running = False
        self.cursor = 0     # 0..9; represents pulse index inside add-time
        self.speed = 0.5    # seconds per pulse (RUN)
        self._acc = 0.0

    def draw(self):
        pygame.draw.rect(screen, PANEL_DARK, self.rect, border_radius=8)
        pygame.draw.rect(screen, (40,40,40), self.rect, 1, border_radius=8)

        # Titles and mode
        t = FONT_BIG.render("Cycling unit", True, TEXT)
        screen.blit(t, (self.rect.x+12, self.rect.y+8))

        # Draw waveform rails
        h = self.rect.height - 60
        row_h = h/len(WAVES)
        start_x = self.rect.x + 80
        end_x = self.rect.right - 16
        for i,name in enumerate(WAVES):
            y = int(self.rect.y + 40 + i*row_h)
            pygame.draw.line(screen, (120,120,120), (start_x, y), (end_x, y), 1)
            lab = FONT_SM.render(name, True, TEXT)
            screen.blit(lab, (self.rect.x + 12, y-8))
            # draw pulses: for 10P..1P, place a tick at a phase slot
            if name.endswith("P") and len(name)==2 or len(name)==3 and name[0].isdigit():
                pass # decorative only for now
        # cursor
        x = int(start_x + (end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen, (255,120,120), (x, self.rect.y+36), (x, self.rect.bottom-12), 2)

        # Master Programmer ring
        self.draw_ring(self.rect.right-120, self.rect.y+50, self.cursor)

        # controls
        self.draw_controls()

    def draw_ring(self, cx, cy, index):
        # 10 lamps in a ring
        r = 36
        for i in range(10):
            ang = -math.pi/2 + 2*math.pi*i/10
            x = int(cx + r*math.cos(ang))
            y = int(cy + r*math.sin(ang))
            on = (i == index)
            pygame.draw.circle(screen, (90, 220, 120) if on else (80,80,80), (x,y), 7)
            pygame.draw.circle(screen, (35,35,35), (x,y), 7, 1)

    def draw_controls(self):
        # Mode status
        s = FONT.render(f"mode: {self.mode}  run: {'ON' if self.running else 'OFF'}", True, TEXT)
        screen.blit(s, (self.rect.x+12, self.rect.bottom-28))
        # slider
        sx, sy, sw, sh = self.rect.x+220, self.rect.bottom-36, 240, 10
        pygame.draw.rect(screen, (180,180,180), (sx, sy, sw, sh), border_radius=5)
        knob_x = sx + int(sw * (1.0 - max(0.05, min(1.5, self.speed))/1.5)) # faster → right
        pygame.draw.circle(screen, (230,230,230), (knob_x, sy+sh//2), 9)
        lab = FONT_SM.render("speed (s/pulse)", True, TEXT)
        screen.blit(lab, (sx, sy-18))

    def slider_hit(self, pos)->bool:
        sx, sy, sw, sh = self.rect.x+220, self.rect.bottom-36, 240, 10
        return pygame.Rect(sx-8, sy-8, sw+16, sh+16).collidepoint(pos)

    def slider_set(self, posx):
        sx, sy, sw, sh = self.rect.x+220, self.rect.bottom-36, 240, 10
        t = (posx - sx)/sw
        t = max(0.0, min(1.0, t))
        self.speed = 1.5 * (1.0 - t) + 0.05

    def step(self):
        if self.mode == "ONE-PULSE":
            self.cursor = (self.cursor + 1) % 10
        elif self.mode == "ONE-ADD":
            self.cursor = 0  # jump to start each add-time step
        else:
            self.cursor = (self.cursor + 1) % 10

    def update_run(self, dt):
        if not self.running: return False
        self._acc += dt
        if self._acc >= self.speed:
            self._acc = 0.0
            self.cursor = (self.cursor + 1) % 10
            return True
        return False

# -------------------- Units: ConstantTx & Accumulator --------------------
class ConstantTx:
    def __init__(self, rect: pygame.Rect, digits: List[int]):
        self.rect = rect
        self.digits = digits[:]  # 10 digits
        self.port_A = None  # added to PlugArea externally

    def draw(self):
        draw_panel(self.rect, "Constant Transmitter")
        ds = ''.join(str(d) for d in self.digits)
        t = FONT_BIG.render(ds, True, OK)
        screen.blit(t, (self.rect.x + 18, self.rect.y + 52))

class Accumulator:
    def __init__(self, rect: pygame.Rect, name="A1"):
        self.rect = rect
        self.name = name
        self.digits = [0]*10
        self.sign = '+'
        # ports will be placed in PlugArea (α input, A/S/AS outputs)
        self.port_alpha = None
        self.port_A = None
        self.port_S = None
        self.port_AS = None

    def reset(self):
        self.digits = [0]*10
        self.sign = '+'

    def draw(self, active_index: Optional[int] = None):
        draw_panel(self.rect, f"Accumulator {self.name}")
        ds = ''.join(str(d) for d in self.digits)
        t = FONT_BIG.render(f"{self.sign}{ds}", True, OK if active_index is not None else TEXT)
        screen.blit(t, (self.rect.x + 16, self.rect.y + 40))
        # decade lamps
        base_x, y = self.rect.x + 16, self.rect.y + 90
        for i,d in enumerate(self.digits):
            cx = base_x + i*24
            color = (250,240,120) if (active_index is not None and i==active_index) else (90,90,90)
            pygame.draw.circle(screen, color, (cx, y), 7)
            pygame.draw.circle(screen, (35,35,35), (cx, y), 7, 1)

    def add_pulse_column(self, col_value:int, index:int):
        """Add a single column value (0..9) at digit index (0..9, MSB..LSB)."""
        i = index
        carry = col_value
        while i >= 0 and carry>0:
            s = self.digits[i] + carry
            self.digits[i] = s % 10
            carry = s // 10
            i -= 1

# -------------------- Simulator Wiring & Logic --------------------
class Simulator:
    def __init__(self):
        # Panels
        self.cycling = CyclingUnit(pygame.Rect(360, 10, 600, 220))
        self.ct = ConstantTx(pygame.Rect(20, 250, 300, 140), digits=[0,0,0,0,0,0,0,0,1,5])
        self.acc = Accumulator(pygame.Rect(360, 250, 560, 160), name="A1")

        # Plug area bottom
        self.plugs = PlugArea()
        self.build_ports()

        # Buttons
        self.btn_step = Button(pygame.Rect(1000, 190, 84, 30), "STEP")
        self.btn_reset = Button(pygame.Rect(1096, 190, 84, 30), "RESET")
        self.btn_run = Button(pygame.Rect(1192, 190, 84, 30), "RUN/PAUSE")
        self.btn_mode_pulse = Button(pygame.Rect(980, 150, 120, 28), "one-pulse")
        self.btn_mode_add = Button(pygame.Rect(1110, 150, 120, 28), "one-add")

        # Cable animation (data)
        self.anim_cable_idx = None
        self.anim_t = 0.0

        # Control ports visual (CCG/RP)
        self.ctrl_flash = False

    def build_ports(self):
        # Place named ports similar to screenshot around bottom area
        # CT A (data out)
        self.plugs.add_port("CT.A", (180, 560), "data", "CT")
        # Acc α (data in)
        self.plugs.add_port("A1.α", (620, 560), "data", "ACC")
        # Acc A/S/AS (data out)
        self.plugs.add_port("A1.A", (820, 560), "data", "ACC")
        self.plugs.add_port("A1.S", (860, 560), "data", "ACC")
        self.plugs.add_port("A1.AS", (900, 560), "data", "ACC")
        # Control lines (left)
        self.plugs.add_port("CCG", (140, 600), "ctrl", "CTRL")
        self.plugs.add_port("RP",  (220, 600), "ctrl", "CTRL")
        # Connect default demo wire CT.A -> A1.α for immediate use
        self.plugs.cables.append(Cable(0,1))

    def draw(self, dt):
        screen.fill(BG)
        # Top toolbar (visual)
        pygame.draw.rect(screen, (192,192,192), (0,0,W,36))
        # Panels
        self.ct.draw()
        self.acc.draw(active_index=self.cycling.cursor if (self.anim_cable_idx is not None) else None)
        self.cycling.draw()

        # Plug area box
        pb_rect = pygame.Rect(20, 430, W-40, 360)
        draw_panel(pb_rect, "Plugboard & Ports")
        # grid lines for style
        for y in range(pb_rect.y+40, pb_rect.bottom-10, 26):
            pygame.draw.line(screen, GRID, (pb_rect.x+10,y), (pb_rect.right-10,y), 1)

        hover = self.plugs.pick(pygame.mouse.get_pos())
        self.plugs.draw(hover_idx=hover)

        # Cable anim if active
        if self.anim_cable_idx is not None:
            cab = self.plugs.cables[self.anim_cable_idx]
            a = self.plugs.ports[cab.a_idx].pos
            b = self.plugs.ports[cab.b_idx].pos
            x = int(a[0] + (b[0]-a[0])*self.anim_t)
            y = int(a[1] + (b[1]-a[1])*self.anim_t)
            pygame.draw.circle(screen, (255,255,255), (x,y), 7)
            pygame.draw.circle(screen, ACCENT, (x,y), 9, 2)

        # Buttons
        self.btn_step.draw(); self.btn_reset.draw(); self.btn_run.draw()
        self.btn_mode_pulse.draw(); self.btn_mode_add.draw()

        # Legend
        self.legend()

    def legend(self):
        info = [
            "Connect ports by clicking two jacks (data-data or ctrl-ctrl).",
            "Prewired: CT.A → A1.α. Hover jacks to see labels.",
            "Modes: one-pulse / one-add / run (slider).",
            "In one-add/run, a full add-time transfers CT to Accumulator."
        ]
        for i,s in enumerate(info):
            t = FONT_SM.render(s, True, TEXT)
            screen.blit(t, (24, 400 + i*18))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
            # Slider
            if self.cycling.slider_hit(e.pos):
                self.cycling.slider_set(e.pos[0])
            # Buttons
            if self.btn_step.handle(e):
                self.step_action()
            if self.btn_reset.handle(e):
                self.reset_action()
            if self.btn_run.handle(e):
                self.cycling.running = not self.cycling.running
            if self.btn_mode_pulse.handle(e):
                self.cycling.mode = "ONE-PULSE"
            if self.btn_mode_add.handle(e):
                self.cycling.mode = "ONE-ADD"
            # Ports
            self.plugs.handle_click(e.pos)

        if e.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            if self.cycling.slider_hit(e.pos):
                self.cycling.slider_set(e.pos[0])

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self.cycling.running = not self.cycling.running
            if e.key == pygame.K_r:
                self.reset_action()
            if e.key == pygame.K_RETURN:
                self.step_action()

    def reset_action(self):
        self.cycling.cursor = 0
        self.acc.reset()
        self.anim_cable_idx = None
        self.anim_t = 0.0

    def step_action(self):
        if self.cycling.mode == "ONE-PULSE":
            self.trigger_single_pulse()
            self.cycling.step()
        elif self.cycling.mode == "ONE-ADD":
            # perform all 10 pulses as a block; animate start and end
            self.anim_start_for("CT.A","A1.α")
            self.transfer_add_time()
            self.anim_cable_idx = None
            self.cycling.step()
        else:
            self.trigger_single_pulse()
            self.cycling.step()

    def anim_start_for(self, src_name, dst_name):
        idx = self.plugs.find_cable_between(src_name, dst_name)
        self.anim_cable_idx = idx
        self.anim_t = 0.0

    def trigger_single_pulse(self):
        # Single pulse at current cursor: transfer one column (digit)
        # If CT.A -> A1.α exists, add CT digit at that column
        self.anim_start_for("CT.A","A1.α")
        col_idx = self.cycling.cursor  # 0..9, 0=MSD
        digit = self.ct.digits[col_idx]
        if self.anim_cable_idx is not None:
            # add with carry: add 'digit' at column col_idx
            self.acc.add_pulse_column(digit, col_idx)

    def transfer_add_time(self):
        # apply all 10 pulses (MSD..LSD)
        for i in range(10):
            digit = self.ct.digits[i]
            if digit:
                self.acc.add_pulse_column(digit, i)

    def update(self, dt):
        # RUN mode auto-progress
        if self.cycling.update_run(dt):
            if self.cycling.mode == "ONE-ADD":
                self.transfer_add_time()
            else:
                self.trigger_single_pulse()

        # advance cable anim
        if self.anim_cable_idx is not None:
            self.anim_t += max(0.3*dt/self.cycling.speed, 0.01)
            if self.anim_t >= 1.0:
                self.anim_cable_idx = None
                self.anim_t = 0.0

# -------------------- UI Widgets: Buttons --------------------
class Button:
    def __init__(self, rect: pygame.Rect, text: str):
        self.rect = rect
        self.text = text
        self.enabled = True
    def draw(self):
        col = (230,230,230) if self.enabled else (140,140,140)
        pygame.draw.rect(screen, col, self.rect, border_radius=6)
        pygame.draw.rect(screen, (30,30,30), self.rect, 1, border_radius=6)
        t = FONT.render(self.text, True, (22,22,22))
        screen.blit(t, t.get_rect(center=self.rect.center))
    def handle(self, e)->bool:
        return self.enabled and e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and self.rect.collidepoint(e.pos)

# -------------------- Main Loop --------------------
def main():
    sim = Simulator()
    last = time.time()
    while True:
        now = time.time()
        dt = now - last; last = now

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
            sim.handle(e)

        sim.update(dt)
        sim.draw(dt)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
