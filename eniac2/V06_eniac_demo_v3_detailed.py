
"""
ENIAC Demo — V3 Detailed
------------------------
Upgrades:
- Accumulator per-digit addition with real carry/borrow propagation per pulse.
- Multiplier uses repeated additions; each addition runs across 10 pulses (LSD→MSD).
- Ports semantics (visual): α=receive, A=send (+), S=send (10's complement/-), AS=send both, β/γ reserved control.
- Plugboard panel centered & lowered; no overlap with text.
- Ring counter shown; bank of 20 accumulators (mini tiles) added.

Scenario remains: 1 + 2 × 3  ->  7

Controls:
  ENTER : STEP (advance one digit pulse)
  SPACE : RUN/PAUSE
  R     : Reset
  ESC   : Quit

Run:
  pip install pygame
  python eniac_demo_v3_detailed.py
"""

import sys, time, math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
pygame.init()
W, H = 1400, 980
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V3 Detailed")
clock = pygame.time.Clock()

# ---------- theme ----------
BG    = (54,56,60)
PANEL = (82,84,88)
TEXT  = (235,235,235)
DIMT  = (200,200,200)
OK    = (110,230,130)
ACCENT= (120,220,255)   # data
CTRL  = (255,210,130)   # control
CARRY = (255,120,120)

FONT     = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 16)
FONT_SM  = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 12)
FONT_BIG = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 20, bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, (30,30,30), rect, 1, border_radius=8)
    if title:
        t = FONT_BIG.render(title, True, TEXT)
        screen.blit(t, (rect.x + 10, rect.y + 8))

# ---------- helpers ----------
def digits10(n:int)->List[int]:
    s = f"{abs(n):010d}"
    return [int(ch) for ch in s]

def from_digits(ds:List[int])->int:
    return int("".join(map(str, ds)))

# ---------- Units ----------
class Acc:
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos
        self.digits = [0]*10
        self.sign = '+'
        # active add/sub operation state
        self.add_active = False
        self.addend_digits = [0]*10
        self.add_sign = +1
        self.carry = 0
        self.carry_flash = 0.0
        self.carry_from_idx = None
    def load(self, v:int):
        if v < 0:
            self.sign = '-'; v = -v
        else:
            self.sign = '+'
        self.digits = digits10(v)
    def value(self)->int:
        v = from_digits(self.digits)
        return -v if self.sign=='-' else v
    # --- per-digit addition start (v shifted, sign: +1 add, -1 subtract)
    def start_add(self, v:int, shift:int=0, sign:int=+1):
        # shift left by 10^shift (append zeros at end)
        ds = digits10(abs(v))
        if shift>0:
            ds = ds[:10-shift] + [0]*shift
        self.addend_digits = ds
        self.add_sign = +1 if sign>=0 else -1
        self.carry = 0
        self.add_active = True
    def tick_add_pulse(self, cursor:int):
        """Process one digit under current pulse. Pulses run index 0..9, we compute j = 9-cursor (LSD->MSD)."""
        if not self.add_active: return
        j = 9 - cursor
        a = self.digits[j]
        b = self.addend_digits[j] * self.add_sign
        s = a + b + self.carry
        carry_out = 0
        if s >= 10:
            s -= 10; carry_out = 1
        elif s < 0:
            s += 10; carry_out = -1
        self.digits[j] = s
        self.carry = carry_out
        if carry_out != 0:
            self.carry_flash = 0.35
            self.carry_from_idx = j
        # end of add-time when cursor==9 (just processed MSD)
        if cursor == 9:
            self.add_active = False
            # fold remaining carry into sign/MSD if needed (simple clamp for demo)
            # ENIAC would propagate beyond 10 digits; we ignore overflow for this demo.
            self.carry = 0
    def draw(self, active_idx: Optional[int]=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 236, 94)
        draw_panel(rect, f"Acc {self.name}")
        s = self.sign + "".join(map(str, self.digits))
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+10, rect.y+46))
        # decade lamps MSD..LSD
        y = rect.y+28
        for i in range(10):
            x = rect.x+12+i*20
            on = (active_idx==i)
            pygame.draw.circle(screen, (250,240,140) if on else (90,90,90), (x,y), 6)
            pygame.draw.circle(screen, (35,35,35), (x,y), 6, 1)
        # carry animation
        if self.carry_flash > 0 and self.carry_from_idx is not None:
            self.carry_flash -= 0.05
            i = self.carry_from_idx
            x1 = rect.x+12+i*20
            x2 = rect.x+12+max(0,i-1)*20
            xm = int((x1+x2)/2)
            pygame.draw.circle(screen, CARRY, (xm, y-14), 5)

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

# ---------- Ports & Plugboard ----------
@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str  # "data" or "ctrl"
    lamp: float = 0.0

@dataclass
class Cable:
    a: int
    b: int
    kind: str

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
    def draw(self, active_paths: List[Tuple[str,str,str]], tphase: float):
        # wires
        for c in self.cables:
            a = self.ports[c.a]; b = self.ports[c.b]
            base = (182,182,182) if c.kind=="data" else (170,150,120)
            pygame.draw.line(screen, base, a.pos, b.pos, 5)
        # ports
        for p in self.ports:
            glow = max(0.0, min(1.0, p.lamp))
            col = (18+int(200*glow),18+int(120*glow),18) if p.ptype=="data" else (18+int(180*glow),18+int(160*glow),12)
            pygame.draw.circle(screen, col, p.pos, 7)
            pygame.draw.circle(screen, (200,200,200), p.pos, 7, 1)
            p.lamp *= 0.90
        # pulses
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
            a.lamp = b.lamp = 1.0

# ---------- Timing & Ring ----------
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class Timing:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cursor = 0
        self.running = False
        self.speed = 0.28
        self.ccg_on = False
        self.rp_on = False
    def draw(self, stage_name:str):
        pygame.draw.rect(screen, PANEL, self.rect, border_radius=8)
        pygame.draw.rect(screen, (30,30,30), self.rect, 1, border_radius=8)
        t = FONT_BIG.render(f"Timing — stage: {stage_name}", True, TEXT)
        screen.blit(t, (self.rect.x+10, self.rect.y+8))
        h = self.rect.height - 56
        row_h = h/len(WAVES)
        start_x = self.rect.x + 80
        end_x = self.rect.right - 110
        for i,name in enumerate(WAVES):
            y = int(self.rect.y + 36 + i*row_h)
            pygame.draw.line(screen, (120,120,120), (start_x,y), (end_x,y), 1)
            lab = FONT_SM.render(name, True, TEXT); screen.blit(lab, (self.rect.x+10, y-8))
        # indicators
        ind_ccg = FONT.render("CCG ON" if self.ccg_on else "CCG off", True, CTRL if self.ccg_on else DIMT)
        ind_rp  = FONT.render("RP  ON" if self.rp_on  else "RP  off", True, CTRL if self.rp_on else DIMT)
        screen.blit(ind_ccg, (end_x+10, self.rect.y+40))
        screen.blit(ind_rp,  (end_x+10, self.rect.y+68))
        # cursor
        x = int(start_x + (end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen, (255,120,120), (x, self.rect.y+30), (x, self.rect.bottom-12), 2)
        # ring lamp
        cx, cy, r = self.rect.right-60, self.rect.y+60, 28
        for i in range(10):
            ang = -math.pi/2 + 2*math.pi*i/10
            px = int(cx + r*math.cos(ang)); py = int(cy + r*math.sin(ang))
            on = (i==self.cursor)
            pygame.draw.circle(screen, (90,220,120) if on else (80,80,80), (px,py), 7)
            pygame.draw.circle(screen, (35,35,35), (px,py), 7, 1)

# ---------- Multiplier Controller (digit-by-digit) ----------
class MultController:
    def __init__(self, a2:Acc, a3:Acc, out:Acc):
        self.a2 = a2; self.a3 = a3; self.out = out
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
        self._setup_digit()
    def _setup_digit(self):
        if self.digit_idx < 0:
            self.active = False; self.done = True; return
        m = self.a3.digits[self.digit_idx]
        self.remaining = m
        self.shift = 9 - self.digit_idx
    def begin_add_if_needed(self, acc_target:Acc):
        """At the start of an add-time, if remaining>0, start a per-digit add into acc_target."""
        if not self.active: return
        if self.remaining > 0:
            acc_target.start_add(self.a2.value(), shift=self.shift, sign=+1)
    def on_add_time_complete(self):
        if not self.active: return
        if self.remaining > 0:
            self.remaining -= 1
        if self.remaining == 0:
            self.digit_idx -= 1
            self._setup_digit()

# ---------- Demo orchestrator ----------
class Demo:
    def __init__(self):
        # Units row
        self.reader = LabelBox((20,20,180,76), "Card Reader", lambda: "1 2 3")
        self.ct1 = CT("CT1", (220,20))
        self.ct2 = CT("CT2", (390,20))
        self.ct3 = CT("CT3", (560,20))
        self.acc1 = Acc("A1", (220,120))
        self.acc2 = Acc("A2", (460,120))
        self.acc3 = Acc("A3", (700,120))
        self.acc4 = Acc("A4", (940,120))
        self.acc5 = Acc("A5", (1180,120))
        self.punch= LabelBox((1180,220,180,74), "Card Punch", lambda: self.acc5.value())

        # 20 accumulator overview
        self.acc_bank = [Acc(f"A{i}", (0,0)) for i in range(20)]
        # map: show values of our main Accs into bank indices (0..19 arbitrarily choose 1..5)
        self.bank_map = {1:self.acc1, 2:self.acc2, 3:self.acc3, 4:self.acc4, 5:self.acc5}

        # Timing
        self.timing = Timing((20, 790, 1360, 170))

        # Plugboard
        self.pb = Plugboard()
        self._build_ports_and_wiring()

        # Multiplier
        self.multctl = MultController(self.acc2, self.acc3, self.acc4)

        # stage
        self.stage = 0
        self.running = False
        self._acc = 0.0
        self.tphase = 0.0
        self.ccg_window = 0.0
        self.rp_window = 0.0

        self.reset()

    def _build_ports_and_wiring(self):
        # Plugboard panel baseline (centered & lowered). We'll compute positions relative to pb_rect when drawing.
        # But we still need absolute port positions; set them here according to desired layout:
        # We'll place ports in a gentle arc around y=520 to 620.
        def px(x): return x
        def py(y): return y
        # CT outputs
        self.pb.add_port("CT1.A", (260, 540), "data")
        self.pb.add_port("CT2.A", (430, 540), "data")
        self.pb.add_port("CT3.A", (600, 540), "data")
        # Acc ports (α, β, γ, A, S, AS)
        def add_acc_ports(tag, x):
            y = 600
            offs = {"α":0,"β":1,"γ":2,"A":3,"S":4,"AS":5}
            for k, o in offs.items():
                self.pb.add_port(f"{tag}.{k}", (x+o*30, y), "data")
        add_acc_ports("A1",  260)
        add_acc_ports("A2",  500)
        add_acc_ports("A3",  740)
        add_acc_ports("A4",  980)
        add_acc_ports("A5", 1220)
        # Mult ports
        self.pb.add_port("MULT.IN1", (700, 660), "data")
        self.pb.add_port("MULT.IN2", (760, 660), "data")
        self.pb.add_port("MULT.OUT", (900, 660), "data")
        # Control
        self.pb.add_port("CCG", (120, 620), "ctrl")
        self.pb.add_port("RP",  (170, 620), "ctrl")
        # Wiring for demo
        self.pb.add_cable("CT1.A","A1.α")
        self.pb.add_cable("CT2.A","A2.α")
        self.pb.add_cable("CT3.A","A3.α")
        # Mult wiring uses A (positive) outputs conceptually
        self.pb.add_cable("A2.A","MULT.IN1")
        self.pb.add_cable("A3.A","MULT.IN2")
        self.pb.add_cable("MULT.OUT","A4.α")
        # Add
        self.pb.add_cable("A1.A","A5.α")
        self.pb.add_cable("A4.A","A5.α")
        # Punch (visual)
        self.pb.add_port("PUNCH.IN", (1260, 660), "data")
        self.pb.add_cable("A5.A","PUNCH.IN")

    # ---- Staging & control ----
    def open_ccg(self, sec=0.25):
        self.timing.ccg_on = True; self.ccg_window = sec
    def pulse_rp(self, sec=0.2):
        self.timing.rp_on = True; self.rp_window = sec
    def handle_ctrl_decay(self, dt):
        if self.ccg_window>0:
            self.ccg_window -= dt
            if self.ccg_window<=0: self.timing.ccg_on=False
        if self.rp_window>0:
            self.rp_window -= dt
            if self.rp_window<=0: self.timing.rp_on=False

    def do_pulse(self):
        cur = self.timing.cursor  # 0..9
        # LOAD
        if self.stage == 0:
            if cur == 0:
                self.open_ccg()
                self.ct1.load(1); self.ct2.load(2); self.ct3.load(3)
                self.acc1.load(self.ct1.value); self.acc2.load(self.ct2.value); self.acc3.load(self.ct3.value)
            if cur == 9:
                self.stage = 1
                self.multctl.start()
        # MULTIPLY
        elif self.stage == 1:
            if cur == 0:
                self.open_ccg()
                self.multctl.begin_add_if_needed(self.acc4)
            # tick per-digit addition in A4
            self.acc4.tick_add_pulse(cur)
            if cur == 9:
                self.multctl.on_add_time_complete()
                if self.multctl.done:
                    self.pulse_rp()
                    self.stage = 2
        # ADD
        elif self.stage == 2:
            if cur == 0:
                self.open_ccg()
                self.acc5.start_add(self.acc1.value() + self.acc4.value(), shift=0, sign=+1)
            self.acc5.tick_add_pulse(cur)
            if cur == 9:
                self.pulse_rp()
                self.stage = 3
        # PUNCH
        elif self.stage == 3:
            if cur == 0: self.open_ccg()
            if cur == 9:
                self.pulse_rp()
                self.stage = 4
        # advance cursor
        self.timing.cursor = (self.timing.cursor + 1) % 10

    def active_paths(self)->List[Tuple[str,str,str]]:
        paths = []
        cur = self.timing.cursor
        # control
        if self.timing.ccg_on:
            if   self.stage==0: paths += [("CCG","A1.α","ctrl"),("CCG","A2.α","ctrl"),("CCG","A3.α","ctrl")]
            elif self.stage==1: paths += [("CCG","MULT.IN1","ctrl"),("CCG","MULT.IN2","ctrl"),("CCG","A4.α","ctrl")]
            elif self.stage==2: paths += [("CCG","A5.α","ctrl")]
            elif self.stage==3: paths += [("CCG","PUNCH.IN","ctrl")]
        if self.timing.rp_on:
            targets=["A4.α","A5.α"] if self.stage in (1,2,3) else []
            for t in targets: paths.append(("RP",t,"ctrl"))
        # data
        if self.stage == 0:
            paths += [("CT1.A","A1.α","data"),("CT2.A","A2.α","data"),("CT3.A","A3.α","data")]
        elif self.stage == 1:
            paths += [("A2.A","MULT.IN1","data"),("A3.A","MULT.IN2","data")]
            # show A4 receive towards the end of add-time
            if cur >= 7 or self.acc4.add_active:
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
        self.multctl.reset()
        self.tphase = 0.0; self._acc = 0.0
        self.timing.ccg_on = False; self.timing.rp_on = False
        self.ccg_window = 0.0; self.rp_window = 0.0

    def update(self, dt):
        if self.running:
            self._acc += dt
            if self._acc >= self.timing.speed:
                self._acc = 0.0
                self.do_pulse()
        # animate cable
        self.tphase += dt / max(0.15, self.timing.speed)
        if self.tphase>1: self.tphase = 1.0
        self.handle_ctrl_decay(dt)

    # ---------- draw ----------
    def draw_acc_bank(self, rect):
        draw_panel(rect, "Accumulators (20)")
        cols = 10; rows = 2
        cell_w = (rect.width-20) // cols
        cell_h = (rect.height-40) // rows
        for i in range(20):
            r = pygame.Rect(rect.x+10+(i%cols)*cell_w, rect.y+30+(i//cols)*cell_h, cell_w-6, cell_h-8)
            pygame.draw.rect(screen, (70,72,76), r, border_radius=6)
            pygame.draw.rect(screen, (30,30,30), r, 1, border_radius=6)
            # linked accumulator value if mapped
            label = f"A{i+1:02d}"
            if (i+1) in self.bank_map:
                v = self.bank_map[i+1].value()
                txt = FONT_SM.render(f"{label}:{v}", True, OK)
            else:
                txt = FONT_SM.render(f"{label}:0", True, DIMT)
            screen.blit(txt, (r.x+8, r.y+8))

    def draw(self):
        screen.fill(BG)
        # Units
        self.reader.draw()
        self.ct1.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct2.draw(active_idx=self.timing.cursor if self.stage==0 else None)
        self.ct3.draw(active_idx=self.timing.cursor if self.stage==0 else None)

        self.acc1.draw(active_idx=self.timing.cursor if self.stage in (0,2) else None)
        self.acc2.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc3.draw(active_idx=self.timing.cursor if self.stage==1 else None)
        self.acc4.draw(active_idx=self.timing.cursor if self.stage in (1,2) else None)
        self.acc5.draw(active_idx=self.timing.cursor if self.stage in (2,3) else None)
        self.punch.draw()

        # Instructions above plugboard (to avoid overlap)
        tips = [
            "ENTER = STEP (one digit pulse)   SPACE = RUN/PAUSE   R = Reset   ESC = Quit",
            "Ports: α=receive,  A(+)=send value,  S(-)=send 10's complement,  AS=both;  β/γ: reserved control (visual).",
            "Multiply: Each digit of A3 repeats addition of A2; each addition takes one add-time (10 pulses, LSD→MSD).",
            f"Stage: {['LOAD','MULTIPLY','ADD','PUNCH','DONE'][self.stage]}  |  Cursor: {self.timing.cursor}"
        ]
        for i,s in enumerate(tips):
            t = FONT.render(s, True, TEXT)
            screen.blit(t, (20, 300 + i*18))

        # Plugboard centered & lowered
        pb_rect = pygame.Rect(20, 380, 1360, 360)
        draw_panel(pb_rect, "Plugboard & Ports (centered)")
        for y in range(pb_rect.y+36, pb_rect.bottom-8, 26):
            pygame.draw.line(screen, (120,120,124), (pb_rect.x+8,y), (pb_rect.right-8,y), 1)
        self.pb.draw(self.active_paths(), self.tphase)

        # Accumulator bank (20)
        bank_rect = pygame.Rect(20, 220, 700, 70)
        self.draw_acc_bank(bank_rect)

        # Multiplier progress
        mult_info = f"Mult digit idx: {self.multctl.digit_idx}  remaining add: {self.multctl.remaining}  shift: {self.multctl.shift}"
        t2 = FONT.render(mult_info, True, TEXT)
        screen.blit(t2, (740, 220))

        # Timing at bottom
        self.timing.draw(['LOAD','MULTIPLY','ADD','PUNCH','DONE'][self.stage])

# ---------- main ----------
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
