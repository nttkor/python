
"""
ENIAC Demo — Full Enhanced
--------------------------
- Scenario: 1 + 2 × 3
- Features:
  * Plugboard with expanded ports (A, S, AS, β, γ) for each accumulator (visual + partial routing)
  * Cable animation for DATA and CONTROL (CCG, RP)
  * Timing diagram (10P..1P) with ring-lamp
  * Multiplier with digit-by-digit partial product accumulation:
      - For each digit of multiplier (A3) from LSD→MSD
      - Repeat addition of multiplicand (A2) "m" times (where m is that digit)
      - Each addition consumes one add-time (10 pulses) with cable animation
      - Shift by decimal position (×10^k) handled during accumulation
  * Adder stage (A1 + A4 → A5)
  * Punch stage (A5 output label)
- Controls:
    ENTER : STEP (advance one digit pulse)
    SPACE : RUN / Pause
    R     : Reset
    ESC   : Quit

Run:
    pip install pygame
    python eniac_demo_full_enhanced.py
"""

import sys, time, math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
pygame.init()
W, H = 1360, 940
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — Full Enhanced")
clock = pygame.time.Clock()

# --------- theme ---------
BG = (54,56,60)
PANEL = (82,84,88)
TEXT = (240,240,240)
DIMT = (200,200,200)
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

# --------- utility ---------
def digits10(n:int)->List[int]:
    s = f"{abs(n):010d}"
    return [int(ch) for ch in s]

def from_digits(ds:List[int])->int:
    return int("".join(map(str, ds)))

# --------- Units ---------
class Acc:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.digits = [0]*10
        self.sign = '+'
    def load(self, v:int):
        if v < 0:
            self.sign = '-'; v = -v
        else:
            self.sign = '+'
        self.digits = digits10(v)
    def value(self)->int:
        v = from_digits(self.digits)
        return -v if self.sign=='-' else v
    def add(self, v:int):
        total = self.value() + v
        self.load(total)
    def shift_add(self, v:int, shift:int):
        total = self.value() + v*(10**shift)
        self.load(total)
    def draw(self, active_idx: Optional[int]=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 230, 92)
        draw_panel(rect, f"Acc {self.name}")
        s = self.sign + "".join(map(str, self.digits))
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+12, rect.y+46))
        # decade lamps (MSD..LSD)
        y = rect.y+28
        for i in range(10):
            x = rect.x+12+i*20
            on = (active_idx==i)
            pygame.draw.circle(screen, (250,240,140) if on else (90,90,90), (x,y), 6)
            pygame.draw.circle(screen, (35,35,35), (x,y), 6, 1)

class CT:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.value = 0
    def load(self, v:int): self.value = v
    def digits(self)->List[int]: return digits10(self.value)
    def draw(self, active_idx: Optional[int]=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 160, 74)
        draw_panel(rect, self.name)
        s = str(self.value)
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+10, rect.y+40))
        # decade lamps row
        y = rect.y+26
        for i in range(10):
            x = rect.x+12+i*13
            on = (active_idx==i)
            pygame.draw.circle(screen, (140,220,250) if on else (80,80,80), (x,y), 4)
            pygame.draw.circle(screen, (35,35,35), (x,y), 4, 1)

class LabelBox:
    def __init__(self, rect, title, get_value):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.get_value = get_value
    def draw(self):
        draw_panel(self.rect, self.title)
        val = self.get_value()
        t = FONT_BIG.render(str(val), True, TEXT)
        screen.blit(t, (self.rect.x+12, self.rect.y+42))

# --------- Ports & Plugboard ---------
@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str   # "data" or "ctrl"
    lamp: float = 0.0

@dataclass
class Cable:
    a: int
    b: int
    kind: str    # "data" or "ctrl"

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
    def pulse_on(self, name, amount=1.0):
        try:
            i = self._find_port(name)
            self.ports[i].lamp = 1.0
        except KeyError:
            pass
    def draw(self, active_paths: List[Tuple[str,str,str]], tphase: float):
        # draw cables
        for c in self.cables:
            a = self.ports[c.a]; b = self.ports[c.b]
            base = (180,180,180) if c.kind=="data" else (170,150,120)
            pygame.draw.line(screen, base, a.pos, b.pos, 5)
        # draw ports with lamps
        for p in self.ports:
            glow = max(0.0, min(1.0, p.lamp))
            col = (18+int(200*glow),18+int(120*glow),18) if p.ptype=="data" else (18+int(180*glow),18+int(160*glow),12)
            pygame.draw.circle(screen, col, p.pos, 7)
            pygame.draw.circle(screen, (200,200,200), p.pos, 7, 1)
            p.lamp *= 0.90  # decay
        # animate pulses
        for (a_name,b_name,kind) in active_paths:
            try:
                ai = self._find_port(a_name); bi = self._find_port(b_name)
            except KeyError:
                continue
            a = self.ports[ai]; b = self.ports[bi]
            x = int(a.pos[0] + (b.pos[0]-a.pos[0])*tphase)
            y = int(a.pos[1] + (b.pos[1]-a.pos[1])*tphase)
            color = ACCENT if kind=="data" else CTRL
            pygame.draw.circle(screen, (255,255,255), (x,y), 6)
            pygame.draw.circle(screen, color, (x,y), 9, 2)
            # light lamps at endpoints
            a.lamp = b.lamp = 1.0

# --------- Timing ---------
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class Timing:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cursor = 0         # 0..9
        self.running = False
        self.speed = 0.30       # seconds per pulse
        self.ccg_on = False
        self.rp_on = False
    def draw(self, stage_name:str):
        pygame.draw.rect(screen, PANEL, self.rect, border_radius=8)
        pygame.draw.rect(screen, (30,30,30), self.rect, 1, border_radius=8)
        t = FONT_BIG.render(f"Timing — stage: {stage_name}", True, TEXT)
        screen.blit(t, (self.rect.x+10, self.rect.y+8))
        h = self.rect.height - 50
        row_h = h/len(WAVES)
        start_x = self.rect.x + 80
        end_x = self.rect.right - 110
        # rails
        for i,name in enumerate(WAVES):
            y = int(self.rect.y + 36 + i*row_h)
            pygame.draw.line(screen, (120,120,120), (start_x,y), (end_x,y), 1)
            lab = FONT_SM.render(name, True, TEXT); screen.blit(lab, (self.rect.x+10, y-8))
        # CC/RP indicators
        ind_ccg = FONT.render("CCG ON" if self.ccg_on else "CCG off", True, CTRL if self.ccg_on else DIMT)
        ind_rp  = FONT.render("RP  ON" if self.rp_on  else "RP  off", True, CTRL if self.rp_on else DIMT)
        screen.blit(ind_ccg, (end_x+10, self.rect.y+40))
        screen.blit(ind_rp,  (end_x+10, self.rect.y+65))
        # cursor
        x = int(start_x + (end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen, (255,120,120), (x, self.rect.y+30), (x, self.rect.bottom-10), 2)
        # ring
        cx, cy, r = self.rect.right-60, self.rect.y+60, 28
        for i in range(10):
            ang = -math.pi/2 + 2*math.pi*i/10
            px = int(cx + r*math.cos(ang)); py = int(cy + r*math.sin(ang))
            on = (i==self.cursor)
            pygame.draw.circle(screen, (90,220,120) if on else (80,80,80), (px,py), 7)
            pygame.draw.circle(screen, (35,35,35), (px,py), 7, 1)

# --------- Multiplier Controller ---------
class MultController:
    """
    Drives digit-by-digit multiplication using repeated addition per digit.
    - multiplicand from A2
    - multiplier from A3
    - accumulate into A4
    - order: LSD (index 9) -> MSD (0)
    - Each addition consumes one add-time (10 pulses). At cursor wrap (from 9 to 0),
      if remaining_additions > 0, do one shift_add and decrement remaining.
    """
    def __init__(self, acc_mulcand: Acc, acc_mult: Acc, acc_out: Acc):
        self.a2 = acc_mulcand
        self.a3 = acc_mult
        self.a4 = acc_out
        self.reset()
    def reset(self):
        self.digit_idx = 9
        self.remaining = 0
        self.shift = 0
        self.active = False
        self.done = False
    def start(self):
        self.active = True
        self.done = False
        self._setup_current_digit()
    def _setup_current_digit(self):
        if self.digit_idx < 0:
            self.active = False
            self.done = True
            return
        m = self.a3.digits[self.digit_idx]
        self.remaining = m
        self.shift = 9 - self.digit_idx  # LSD=9 -> shift 0; MSD=0 -> shift 9
    def on_add_time_complete(self):
        """Called when timing cursor wraps (completed 10 pulses)."""
        if not self.active: return
        if self.remaining > 0:
            self.a4.shift_add(self.a2.value(), self.shift)
            self.remaining -= 1
        if self.remaining == 0:
            # move to next digit
            self.digit_idx -= 1
            self._setup_current_digit()

# --------- Demo Orchestrator ---------
class Demo:
    def __init__(self):
        # Units
        self.reader = LabelBox((20,20,170,74), "Card Reader", lambda: "1 2 3")
        self.ct1 = CT("CT1", (210,20))
        self.ct2 = CT("CT2", (380,20))
        self.ct3 = CT("CT3", (550,20))
        self.acc1 = Acc("A1", (210,120))
        self.acc2 = Acc("A2", (440,120))
        self.acc3 = Acc("A3", (670,120))
        self.acc4 = Acc("A4", (900,120))
        self.acc5 = Acc("A5", (1130,120))
        self.punch = LabelBox((1130,220,180,74), "Card Punch", lambda: self.acc5.value())

        # Timing
        self.timing = Timing((20, 760, 1320, 160))

        # Plugboard
        self.pb = Plugboard()
        self._build_ports_and_wiring()

        # Multiplier controller
        self.multctl = MultController(self.acc2, self.acc3, self.acc4)

        # Stage
        self.stage = 0  # 0: LOAD, 1: MULTIPLY, 2: ADD, 3: PUNCH, 4 DONE
        self.running = False
        self._acc = 0.0
        self.tphase = 0.0

        # CCG/RP gating visuals
        self.ccg_window = 0.0   # time remaining of gate ON for current stage (seconds)
        self.rp_pulse = 0.0     # time remaining of reset pulse ON (seconds)

        self.reset()

    def _build_ports_and_wiring(self):
        # Expanded ports for A1..A5 : A,S,AS, α, β, γ (visual)
        xmap = {
            'A1': (240, 420), 'A2': (470, 420), 'A3': (700, 420),
            'A4': (930, 420), 'A5': (1160, 420)
        }
        # CT outputs
        self.pb.add_port("CT1.A", (250, 360), "data")
        self.pb.add_port("CT2.A", (420, 360), "data")
        self.pb.add_port("CT3.A", (590, 360), "data")

        for name,(x,y) in xmap.items():
            for off,label in enumerate(["α","β","γ","A","S","AS"]):
                self.pb.add_port(f"{name}.{label}", (x+off*30, y), "data")

        # Mult in/out
        self.pb.add_port("MULT.IN1", (700, 500), "data")
        self.pb.add_port("MULT.IN2", (760, 500), "data")
        self.pb.add_port("MULT.OUT", (860, 500), "data")

        # Control lines
        self.pb.add_port("CCG", (120, 500), "ctrl")
        self.pb.add_port("RP",  (170, 500), "ctrl")

        # Wiring for demo
        # LOAD
        self.pb.add_cable("CT1.A", "A1.α")
        self.pb.add_cable("CT2.A", "A2.α")
        self.pb.add_cable("CT3.A", "A3.α")
        # MULT
        self.pb.add_cable("A2.A", "MULT.IN1")
        self.pb.add_cable("A3.A", "MULT.IN2")
        self.pb.add_cable("MULT.OUT", "A4.α")
        # ADD
        self.pb.add_cable("A1.A", "A5.α")
        self.pb.add_cable("A4.A", "A5.α")
        # PUNCH (visual only)
        self.pb.add_port("PUNCH.IN", (1180, 500), "data")
        self.pb.add_cable("A5.A", "PUNCH.IN")

    # ---- Stage helpers ----
    def stage_name(self):
        return ["LOAD","MULTIPLY","ADD","PUNCH","DONE"][self.stage]

    def open_ccg_gate(self, seconds=0.25):
        self.timing.ccg_on = True
        self.ccg_window = seconds

    def emit_rp(self, seconds=0.2):
        self.timing.rp_on = True
        self.rp_pulse = seconds

    def handle_ccg_rp(self, dt):
        if self.ccg_window > 0.0:
            self.ccg_window -= dt
            if self.ccg_window <= 0.0:
                self.timing.ccg_on = False
        if self.rp_pulse > 0.0:
            self.rp_pulse -= dt
            if self.rp_pulse <= 0.0:
                self.timing.rp_on = False

    # ---- Simulation tick ----
    def do_pulse(self):
        idx = self.timing.cursor  # 0..9
        # Stage-specific behavior aligned to digit pulses
        if self.stage == 0:  # LOAD
            if idx == 0:
                # CCG gate opens to allow CT->Acc transfer
                self.open_ccg_gate()
                self.ct1.load(1); self.ct2.load(2); self.ct3.load(3)
                self.acc1.load(self.ct1.value); self.acc2.load(self.ct2.value); self.acc3.load(self.ct3.value)
        elif self.stage == 1:  # MULTIPLY
            # Kickoff CCG at the start of each add-time
            if idx == 0: self.open_ccg_gate()
            # At end of each add-time, execute one repeated addition if needed
            if idx == 9:
                self.multctl.on_add_time_complete()
                # When first entering multiply
                if not self.multctl.active and not self.multctl.done:
                    self.multctl.start()
                # If finished all digits, advance stage and RP
                if self.multctl.done:
                    self.emit_rp()
                    self.stage = 2
        elif self.stage == 2:  # ADD A1 + A4 -> A5
            if idx == 0: self.open_ccg_gate()
            if idx == 9:
                self.acc5.load(self.acc1.value() + self.acc4.value())
                self.emit_rp()
                self.stage = 3
        elif self.stage == 3:  # PUNCH
            if idx == 0: self.open_ccg_gate()
            if idx == 9:
                # done
                self.emit_rp()
                self.stage = 4

        # advance timing cursor
        self.timing.cursor = (self.timing.cursor + 1) % 10

    def active_paths(self)->List[Tuple[str,str,str]]:
        """List of (src,dst,kind) for anim this pulse window."""
        paths = []
        idx = self.timing.cursor
        # Control pulses (brief visualization)
        if self.timing.ccg_on:
            # Show CCG -> gate ports for the current stage
            if self.stage == 0:
                paths += [("CCG","A1.α","ctrl"),("CCG","A2.α","ctrl"),("CCG","A3.α","ctrl")]
            elif self.stage == 1:
                paths += [("CCG","MULT.IN1","ctrl"),("CCG","MULT.IN2","ctrl"),("CCG","A4.α","ctrl")]
            elif self.stage == 2:
                paths += [("CCG","A5.α","ctrl")]
            elif self.stage == 3:
                paths += [("CCG","PUNCH.IN","ctrl")]
        if self.timing.rp_on:
            # RP to affected units
            affected = []
            if self.stage in (1,2): affected = ["A4.α","A5.α"]
            for port in affected:
                paths.append(("RP", port, "ctrl"))

        # Data flows
        if self.stage == 0:
            paths += [("CT1.A","A1.α","data"),("CT2.A","A2.α","data"),("CT3.A","A3.α","data")]
        elif self.stage == 1:
            # During multiply, show A2->MULT, A3->MULT, and MULT->A4 every add-time
            paths += [("A2.A","MULT.IN1","data"),("A3.A","MULT.IN2","data")]
            # Show MULT.OUT->A4.α when an addition occurs (near the end of add-time)
            # Approx: if cursor in last 30% of window show output
            if idx >= 7:
                paths += [("MULT.OUT","A4.α","data")]
        elif self.stage == 2:
            paths += [("A1.A","A5.α","data"),("A4.A","A5.α","data")]
        elif self.stage == 3:
            paths += [("A5.A","PUNCH.IN","data")]
        return paths

    def reset(self):
        self.stage = 0
        self.timing.cursor = 0
        self.acc1.load(0); self.acc2.load(0); self.acc3.load(0); self.acc4.load(0); self.acc5.load(0)
        self.ct1.load(0); self.ct2.load(0); self.ct3.load(0)
        self.tphase = 0.0
        self._acc = 0.0
        self.multctl.reset()
        self.timing.ccg_on = False
        self.timing.rp_on = False

    def update(self, dt):
        # run mode
        if self.running:
            self._acc += dt
            if self._acc >= self.timing.speed:
                self._acc = 0.0
                self.do_pulse()
        # animation along cables
        self.tphase += dt / max(0.15, self.timing.speed)
        if self.tphase > 1.0: self.tphase = 1.0
        # control windows
        self.handle_ccg_rp(dt)

    # ---- draw ----
    def draw(self):
        screen.fill(BG)
        # Units
        self.reader.draw()
        self.ct1.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct2.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct3.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.acc1.draw(active_idx=self.timing.cursor if self.stage in (0,2) else None)
        # Highlight multiplicand/multiplier columns during multiply by showing cursor lamps
        self.acc2.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc3.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc4.draw(active_idx=self.timing.cursor if self.stage in (1,2) else None)
        self.acc5.draw(active_idx=self.timing.cursor if self.stage in (2,3) else None)
        self.punch.draw()

        # Plugboard
        pb_rect = pygame.Rect(20, 340, 1320, 380)
        draw_panel(pb_rect, "Plugboard & Ports (expanded: A, S, AS, β, γ)")
        for y in range(pb_rect.y+36, pb_rect.bottom-8, 26):
            pygame.draw.line(screen, (120,120,124), (pb_rect.x+8,y), (pb_rect.right-8,y), 1)
        self.pb.draw(self.active_paths(), self.tphase)

        # Multiplier progress label
        mult_info = f"Mult digit idx: {self.multctl.digit_idx}  remaining add: {self.multctl.remaining}  shift: {self.multctl.shift}"
        t = FONT.render(mult_info, True, TEXT)
        screen.blit(t, (20, 720))

        # Timing
        self.timing.draw(self.stage_name())

        # UI hints
        tips = [
            "ENTER = STEP (one digit pulse)",
            "SPACE = RUN/PAUSE",
            "R = Reset",
            f"Stage: {self.stage_name()} | Cursor: {self.timing.cursor} | RUN: {'ON' if self.running else 'OFF'}",
            "Multiply uses repeated addition per digit. Each addition takes one add-time (10 pulses)."
        ]
        for i,s in enumerate(tips):
            ts = FONT.render(s, True, TEXT)
            screen.blit(ts, (20, 300 + i*18))

# --------- main ---------
def main():
    demo = Demo()
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
