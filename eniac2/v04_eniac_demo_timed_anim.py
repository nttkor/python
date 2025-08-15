
"""
ENIAC Demo (Timed + Cable Animation)
------------------------------------
- Simulates "1 + 2 × 3" with:
  * Card Reader -> CT1..3 -> Acc1..3
  * Multiplier stage: A2 × A3 -> A4
  * Adder stage: A1 + A4 -> A5
  * Card Punch: output A5
- Shows plug-style ports and animated pulses along cables.
- Timing diagram for 10P..1P + control tags (CCG/RP). STEP is one digit pulse.

Run:
    pip install pygame
    python eniac_demo_timed_anim.py

Keys:
  ENTER  : STEP (advance one digit pulse)
  SPACE  : RUN / Pause
  R      : Reset
  ESC    : Quit
"""

import sys, time, math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
pygame.init()
W, H = 1320, 900
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — Timed + Cable Animation")
clock = pygame.time.Clock()

# ---------- theme ----------
BG = (54,56,60)
PANEL = (82,84,88)
TEXT = (240,240,240)
OK = (110,230,130)
ACCENT = (120,220,255)   # data pulse
CTRL = (255,210,130)     # control pulse
ERR = (255,120,120)

FONT = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 16)
FONT_SM = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 13)
FONT_BIG = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 20, bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, (30,30,30), rect, 1, border_radius=8)
    if title:
        t = FONT_BIG.render(title, True, TEXT)
        screen.blit(t, (rect.x + 10, rect.y + 8))

# ---------- core widgets ----------
class LabelBox:
    def __init__(self, rect, title, get_value):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.get_value = get_value
    def draw(self):
        draw_panel(self.rect, self.title)
        val = self.get_value()
        t = FONT_BIG.render(str(val), True, OK)
        screen.blit(t, (self.rect.x+12, self.rect.y+40))

class Acc:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.digits = [0]*10
    def load(self, v:int):
        s = f"{v:010d}"
        self.digits = [int(ch) for ch in s]
    def value(self)->int:
        return int("".join(map(str,self.digits)))
    def draw(self, active_idx: Optional[int]=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 210, 88)
        draw_panel(rect, f"Acc {self.name}")
        s = "".join(map(str,self.digits))
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+12, rect.y+42))
        # decade lamps
        y = rect.y+28
        for i in range(10):
            x = rect.x+12+i*20
            on = (active_idx==i)
            pygame.draw.circle(screen, (250,240,140) if on else (80,80,80), (x,y), 6)
            pygame.draw.circle(screen, (35,35,35), (x,y), 6, 1)

class CT:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.value = 0
    def load(self, v:int): self.value = v
    def digits(self)->List[int]:
        s = f"{self.value:010d}"
        return [int(ch) for ch in s]
    def draw(self, active_idx: Optional[int]=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 150, 70)
        draw_panel(rect, f"{self.name}")
        s = str(self.value)
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+10, rect.y+38))
        # decade lamps row
        y = rect.y+26
        for i in range(10):
            x = rect.x+12+i*13
            on = (active_idx==i)
            pygame.draw.circle(screen, (140,220,250) if on else (80,80,80), (x,y), 4)
            pygame.draw.circle(screen, (35,35,35), (x,y), 4, 1)

# ---------- ports & cables ----------
@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str  # "data" or "ctrl"

@dataclass
class Cable:
    a: int
    b: int
    kind: str   # "data" or "ctrl"

class Plugboard:
    def __init__(self):
        self.ports: List[Port] = []
        self.cables: List[Cable] = []
    def add_port(self, name, pos, ptype):
        self.ports.append(Port(name, pos, ptype))
    def add_cable(self, a_name, b_name):
        ai = self._find_port(a_name); bi = self._find_port(b_name)
        kind = self.ports[ai].ptype
        self.cables.append(Cable(ai, bi, kind))
    def _find_port(self, name)->int:
        for i,p in enumerate(self.ports):
            if p.name == name: return i
        raise KeyError(name)
    def draw(self, active_paths: List[Tuple[str,str]], tphase: float):
        # Draw cables
        for c in self.cables:
            a = self.ports[c.a]; b = self.ports[c.b]
            color = (180,180,180)
            pygame.draw.line(screen, color, a.pos, b.pos, 5)
        # Draw ports
        for p in self.ports:
            pygame.draw.circle(screen, (18,18,18), p.pos, 7)
            pygame.draw.circle(screen, (200,200,200), p.pos, 7, 1)
        # Animate pulses along active paths
        for (a_name,b_name) in active_paths:
            try:
                ai = self._find_port(a_name); bi = self._find_port(b_name)
            except KeyError:
                continue
            a = self.ports[ai]; b = self.ports[bi]
            x = int(a.pos[0] + (b.pos[0]-a.pos[0])*tphase)
            y = int(a.pos[1] + (b.pos[1]-a.pos[1])*tphase)
            pygame.draw.circle(screen, (255,255,255), (x,y), 6)
            pygame.draw.circle(screen, ACCENT, (x,y), 9, 2)

# ---------- timing panel ----------
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class Timing:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cursor = 0         # 0..9 for 10P..1P
        self.running = False
        self.speed = 0.35       # seconds per pulse
    def draw(self, stage_name:str):
        pygame.draw.rect(screen, PANEL, self.rect, border_radius=8)
        pygame.draw.rect(screen, (30,30,30), self.rect, 1, border_radius=8)
        t = FONT_BIG.render(f"Timing — stage: {stage_name}", True, TEXT)
        screen.blit(t, (self.rect.x+10, self.rect.y+8))
        h = self.rect.height - 50
        row_h = h/len(WAVES)
        start_x = self.rect.x + 80
        end_x = self.rect.right - 16
        # rails
        for i,name in enumerate(WAVES):
            y = int(self.rect.y + 36 + i*row_h)
            pygame.draw.line(screen, (120,120,120), (start_x,y), (end_x,y), 1)
            lab = FONT_SM.render(name, True, TEXT); screen.blit(lab, (self.rect.x+10, y-8))
        # cursor for digits (10P..1P)
        x = int(start_x + (end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen, (255,120,120), (x, self.rect.y+30), (x, self.rect.bottom-10), 2)
        # ring lamps 0..9
        cx, cy, r = self.rect.right-70, self.rect.y+60, 32
        for i in range(10):
            ang = -math.pi/2 + 2*math.pi*i/10
            px = int(cx + r*math.cos(ang)); py = int(cy + r*math.sin(ang))
            on = (i==self.cursor)
            pygame.draw.circle(screen, (90,220,120) if on else (80,80,80), (px,py), 7)
            pygame.draw.circle(screen, (35,35,35), (px,py), 7, 1)

# ---------- simulation for "1 + 2 × 3" ----------
class Demo:
    def __init__(self):
        # units
        self.reader = LabelBox((20,20,170,70), "Card Reader", lambda: "1 2 3")
        self.ct1 = CT("CT1", (210,20))
        self.ct2 = CT("CT2", (370,20))
        self.ct3 = CT("CT3", (530,20))
        self.acc1 = Acc("A1", (210,120))
        self.acc2 = Acc("A2", (420,120))
        self.acc3 = Acc("A3", (630,120))
        self.acc4 = Acc("A4", (840,120))
        self.acc5 = Acc("A5", (1050,120))
        self.mult = LabelBox((420,220,160,70), "Multiplier", lambda: "A2×A3→A4")
        self.punch = LabelBox((1050,220,170,70), "Card Punch", lambda: self.acc5.value())

        # timing
        self.timing = Timing((20, 720, 1280, 160))

        # plugboard
        self.pb = Plugboard()
        self._build_ports_and_cables()

        # sequence state
        self.stage = 0      # 0: load, 1: multiply, 2: add, 3: punch, 4: done
        self.tphase = 0.0   # 0.0..1.0 along cable
        self.running = False
        self._last = time.time()

    def _build_ports_and_cables(self):
        # Data ports (left to right rough layout under units)
        # CT outputs
        self.pb.add_port("CT1.A", (240, 360), "data")
        self.pb.add_port("CT2.A", (400, 360), "data")
        self.pb.add_port("CT3.A", (560, 360), "data")
        # Acc inputs (α) & outputs (A)
        self.pb.add_port("A1.α", (260, 420), "data"); self.pb.add_port("A1.A", (300, 420), "data")
        self.pb.add_port("A2.α", (470, 420), "data"); self.pb.add_port("A2.A", (510, 420), "data")
        self.pb.add_port("A3.α", (680, 420), "data"); self.pb.add_port("A3.A", (720, 420), "data")
        self.pb.add_port("A4.α", (890, 420), "data"); self.pb.add_port("A4.A", (930, 420), "data")
        self.pb.add_port("A5.α", (1100, 420), "data"); self.pb.add_port("A5.A", (1140, 420), "data")
        # Mult ports (conceptual)
        self.pb.add_port("MULT.IN1", (600, 500), "data")
        self.pb.add_port("MULT.IN2", (680, 500), "data")
        self.pb.add_port("MULT.OUT", (820, 500), "data")
        # Control ports (visual only here)
        self.pb.add_port("CCG", (120, 500), "ctrl")
        self.pb.add_port("RP", (170, 500), "ctrl")

        # Cables for the demo flow
        # Card->CT->Acc loads
        self.pb.add_cable("CT1.A", "A1.α")
        self.pb.add_cable("CT2.A", "A2.α")
        self.pb.add_cable("CT3.A", "A3.α")
        # Acc to Mult and back
        self.pb.add_cable("A2.A", "MULT.IN1")
        self.pb.add_cable("A3.A", "MULT.IN2")
        self.pb.add_cable("MULT.OUT", "A4.α")
        # Add A1 + A4 -> A5
        self.pb.add_cable("A1.A", "A5.α")
        self.pb.add_cable("A4.A", "A5.α")

    # ---------- stage logic ----------
    def stage_name(self):
        return ["LOAD", "MULTIPLY", "ADD", "PUNCH", "DONE"][self.stage]

    def do_pulse(self):
        """Advance by one digit pulse according to current stage."""
        idx = self.timing.cursor  # 0..9 (MSD..LSD)
        # Stage 0: Load CT -> Acc
        if self.stage == 0:
            # On the first pulse, perform the data load, animate three lines
            if idx == 0:
                self.ct1.load(1); self.ct2.load(2); self.ct3.load(3)
                self.acc1.load(self.ct1.value); self.acc2.load(self.ct2.value); self.acc3.load(self.ct3.value)
            # show animation from CTx.A -> Ax.α
            self.tphase = 0.0  # reset animation each pulse

        # Stage 1: Multiply A2*A3 -> A4 (animate across 10 pulses; apply at last)
        elif self.stage == 1:
            if idx == 9:
                prod = self.acc2.value() * self.acc3.value()
                self.acc4.load(prod)
            self.tphase = 0.0

        # Stage 2: Add A1 + A4 -> A5
        elif self.stage == 2:
            if idx == 9:
                self.acc5.load(self.acc1.value() + self.acc4.value())
            self.tphase = 0.0

        # Stage 3: Punch
        elif self.stage == 3:
            if idx == 9:
                # done
                self.stage = 4

        # advance timing cursor
        self.timing.cursor = (self.timing.cursor + 1) % 10
        # if we completed a full add-time, move to next stage
        if self.timing.cursor == 0:
            if self.stage < 3:
                self.stage += 1

    def active_paths(self)->List[Tuple[str,str]]:
        """Return list of cable names that should show a pulse right now."""
        if self.stage == 0:
            return [("CT1.A","A1.α"), ("CT2.A","A2.α"), ("CT3.A","A3.α")]
        if self.stage == 1:
            return [("A2.A","MULT.IN1"), ("A3.A","MULT.IN2"), ("MULT.OUT","A4.α")]
        if self.stage == 2:
            return [("A1.A","A5.α"), ("A4.A","A5.α")]
        if self.stage == 3:
            return [("A5.A","PUNCH.IN")] if False else []  # visual only
        return []

    def update(self, dt):
        # run mode
        if self.running:
            self._acc += dt
            if self._acc >= self.timing.speed:
                self._acc = 0.0
                self.do_pulse()
        # animate tphase along active path(s)
        self.tphase += dt / max(0.15, self.timing.speed)
        if self.tphase > 1.0: self.tphase = 1.0

    def reset(self):
        self.stage = 0
        self.timing.cursor = 0
        self.acc1.load(0); self.acc2.load(0); self.acc3.load(0); self.acc4.load(0); self.acc5.load(0)
        self.ct1.load(0); self.ct2.load(0); self.ct3.load(0)
        self.tphase = 0.0
        self._acc = 0.0

    # ---------- draw ----------
    def draw(self):
        screen.fill(BG)
        # units
        self.reader.draw()
        self.ct1.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct2.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct3.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.acc1.draw(active_idx=self.timing.cursor if self.stage in (0,2) else None)
        self.acc2.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc3.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc4.draw(active_idx=self.timing.cursor if self.stage in (1,2) else None)
        self.acc5.draw(active_idx=self.timing.cursor if self.stage in (2,3) else None)
        self.mult.draw(); self.punch.draw()

        # plugboard region
        pb_rect = pygame.Rect(20, 320, 1280, 380)
        draw_panel(pb_rect, "Plugboard & Ports (animated)")
        # grid lines
        for y in range(pb_rect.y+36, pb_rect.bottom-8, 26):
            pygame.draw.line(screen, (120,120,124), (pb_rect.x+8,y), (pb_rect.right-8,y), 1)

        # draw plugs/cables with active paths
        self.pb.draw(self.active_paths(), self.tphase)

        # timing
        self.timing.draw(self.stage_name())

        # UI hints
        tips = [
            "ENTER = STEP (one digit pulse)",
            "SPACE = RUN/PAUSE",
            "R = Reset",
            f"Stage: {self.stage_name()}  |  Cursor: {self.timing.cursor}",
            "Flow: LOAD (CT->A1..3) → MULTIPLY (A2,A3->A4) → ADD (A1+A4->A5) → PUNCH"
        ]
        for i,s in enumerate(tips):
            t = FONT.render(s, True, TEXT)
            screen.blit(t, (20, 290 + i*18))

# ---------- main ----------
def main():
    demo = Demo()
    demo.reset()
    last = time.time()
    while True:
        now = time.time(); dt = now - last; last = now
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if e.key == pygame.K_RETURN:
                    demo.do_pulse()
                if e.key == pygame.K_SPACE:
                    demo.running = not demo.running
                    demo._acc = 0.0
                if e.key == pygame.K_r:
                    demo.reset()
        demo.update(dt)
        demo.draw()
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
