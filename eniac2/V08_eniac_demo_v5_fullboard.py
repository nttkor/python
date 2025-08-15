
"""
ENIAC Demo — V5 Fullboard
-------------------------
- Tight layout showing the whole machine at a glance.
- 20 Accumulators (compact mini-panels) with ring counter lamps.
- Plugboard with labeled ports (α, A, S, AS, β, γ) and data/control cables.
- Ring distributor wiring to *every* accumulator; pulses animated to each mini-ring.
- Real per-digit carry/borrow propagation within Accumulator add-times.
- S (subtract) and AS (dual) semantics supported; demo includes a subtraction stage.
- CCG (gate) at the start of each add-time, RP (reset pulse) at the end — both animated.
- Scenario shows: LOAD → MULTIPLY (A2×A3→A4) → ADD (A1+A4→A5) → SUBTRACT (A5−A2→A7) → PUNCH (show result).

Controls:
  ENTER : STEP one digit-pulse (ring 0..9)
  SPACE : RUN/PAUSE
  R     : Reset
  ESC   : Quit
  +/-   : Speed down/up

Requires: pygame 2.x
"""

import sys, time, math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
pygame.init()

W, H = 1420, 980
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V5 Fullboard")
clock = pygame.time.Clock()

# ---- theme ----
BG    = (52,54,58)
PANEL = (78,80,84)
EDGE  = (34,34,34)
TEXT  = (235,235,235)
DIMT  = (190,190,190)
OK    = (120,235,150)
ACCENT= (125,220,255)  # data pulse
CTRL  = (255,200,110)  # control pulse
CARRY = (255,110,110)

FONT     = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 16)
FONT_SM  = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 12)
FONT_BIG = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", 20, bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, EDGE,  rect, 1, border_radius=8)
    if title:
        t = FONT_BIG.render(title, True, TEXT)
        screen.blit(t, (rect.x + 10, rect.y + 8))

def digits10(n:int)->List[int]:
    s = f"{abs(n):010d}"
    return [int(ch) for ch in s]

def from_digits(ds:List[int])->int:
    return int("".join(map(str, ds)))

# ---- Units ----
class Acc:
    def __init__(self, name):
        self.name = name
        self.digits = [0]*10
        self.sign = '+'
        self.add_active = False
        self.addend_digits = [0]*10
        self.add_sign = +1
        self.carry = 0
        self.carry_flash = 0.0
        self.carry_from_idx = None
    def load(self, v:int):
        if v<0: self.sign='-'; v=-v
        else:   self.sign='+'
        self.digits = digits10(v)
    def value(self)->int:
        v = from_digits(self.digits)
        return -v if self.sign=='-' else v
    # controls
    def reset(self): self.load(0)
    def toggle_sign(self): self.sign = '+' if self.sign=='-' else '-'
    # per-digit add/sub (sign=+1 add, -1 subtract)
    def start_add(self, v:int, shift:int=0, sign:int=+1):
        ds = digits10(abs(v))
        if shift>0: ds = ds[:10-shift] + [0]*shift
        self.addend_digits = ds
        self.add_sign = +1 if sign>=0 else -1
        self.carry = 0; self.add_active=True
    def tick_add_pulse(self, cursor:int):
        if not self.add_active: return
        j = 9 - cursor  # LSD->MSD
        a = self.digits[j]
        b = self.addend_digits[j] * self.add_sign
        s = a + b + self.carry
        cout = 0
        if s>=10: s-=10; cout = 1
        elif s<0: s+=10; cout = -1
        self.digits[j] = s
        self.carry = cout
        if cout!=0:
            self.carry_flash = 0.35; self.carry_from_idx=j
        if cursor==9:
            self.add_active=False; self.carry=0

class AccMini:
    """Compact visual of an Acc with value and ring lamps."""
    def __init__(self, acc:Acc, rect:pygame.Rect):
        self.acc = acc
        self.rect = rect
        # ring connection landing point for distributor line
        self.ring_point = (rect.x + rect.width - 18, rect.y + 20)
    def draw(self, ring_idx:int, active_digit_idx:Optional[int]=None):
        r = self.rect
        pygame.draw.rect(screen, (70,72,76), r, border_radius=6)
        pygame.draw.rect(screen, EDGE, r, 1, border_radius=6)
        label = FONT_SM.render(self.acc.name, True, TEXT)
        screen.blit(label, (r.x+8, r.y+6))
        # value
        s = self.acc.sign + "".join(map(str, self.acc.digits))
        t = FONT.render(s, True, OK)
        screen.blit(t, (r.x+8, r.y+26))
        # ring lamps (10)
        cx, cy = r.x+10, r.y + r.height-14
        spacing = (r.width-40)/9
        for i in range(10):
            x = int(cx + i*spacing)
            on = (i==ring_idx)
            pygame.draw.circle(screen, (95,220,125) if on else (75,75,75), (x,cy), 5)
            pygame.draw.circle(screen, EDGE, (x,cy), 5, 1)
        # carry flash line visual
        if self.acc.carry_flash>0 and self.acc.carry_from_idx is not None:
            self.acc.carry_flash -= 0.05
            i = self.acc.carry_from_idx
            x1 = r.x+14 + i*10
            x2 = r.x+14 + max(0,i-1)*10
            xm = int((x1+x2)/2)
            pygame.draw.circle(screen, CARRY, (xm, r.y+18), 4)

# ---- Plugboard ----
@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str  # "data" or "ctrl"
    label: str
    lamp: float = 0.0

@dataclass
class Cable:
    a: int
    b: int
    kind: str  # "data"/"ctrl"

class Plugboard:
    def __init__(self, rect:pygame.Rect):
        self.rect = rect
        self.ports: List[Port] = []
        self.cables: List[Cable] = []
    def add_port(self, fullname:str, x:int, y:int, ptype:str, label:str):
        self.ports.append(Port(fullname, (x,y), ptype, label))
    def add_cable(self, a_name:str, b_name:str):
        ai=self._find(a_name); bi=self._find(b_name)
        self.cables.append(Cable(ai, bi, self.ports[ai].ptype))
    def _find(self, name:str)->int:
        for i,p in enumerate(self.ports):
            if p.name==name: return i
        raise KeyError(name)
    def draw(self, active_paths: List[Tuple[str,str,str]], tphase: float):
        r = self.rect
        draw_panel(r, "Plugboard & Ports")
        # grid lines
        for y in range(r.y+36, r.bottom-6, 26):
            pygame.draw.line(screen, (118,118,122), (r.x+8,y), (r.right-8,y), 1)
        # draw cables
        for c in self.cables:
            a=self.ports[c.a]; b=self.ports[c.b]
            col = (174,174,174) if c.kind=="data" else (170,150,120)
            pygame.draw.line(screen, col, a.pos, b.pos, 5)
        # draw ports with labels
        for p in self.ports:
            glow = max(0.0, min(1.0, p.lamp)); p.lamp*=0.90
            col = (24+int(200*glow),24+int(120*glow),24) if p.ptype=="data" else (24+int(180*glow),24+int(160*glow),16)
            pygame.draw.circle(screen, col, p.pos, 7)
            pygame.draw.circle(screen, (210,210,210), p.pos, 7, 1)
            lab = FONT_SM.render(p.label, True, TEXT)
            screen.blit(lab, (p.pos[0]-8, p.pos[1]+10))
        # active pulses
        for (a_name,b_name,kind) in active_paths:
            try:
                ai=self._find(a_name); bi=self._find(b_name)
            except KeyError: continue
            a=self.ports[ai]; b=self.ports[bi]
            x = int(a.pos[0] + (b.pos[0]-a.pos[0])*tphase)
            y = int(a.pos[1] + (b.pos[1]-a.pos[1])*tphase)
            color = ACCENT if kind=="data" else CTRL
            pygame.draw.circle(screen, (255,255,255), (x,y), 6)
            pygame.draw.circle(screen, color, (x,y), 9, 2)
            a.lamp=b.lamp=1.0

# ---- Timing ----
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class Timing:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cursor = 0
        self.running=False
        self.speed = 0.26
        self.ccg_on=False; self.rp_on=False
    def draw(self, stage_name:str):
        r=self.rect
        draw_panel(r, f"Timing — stage: {stage_name}")
        h=r.height-56
        row_h=h/len(WAVES)
        start_x=r.x+80; end_x=r.right-110
        for i,name in enumerate(WAVES):
            y=int(r.y+36+i*row_h)
            pygame.draw.line(screen,(120,120,120),(start_x,y),(end_x,y),1)
            lab=FONT_SM.render(name,True,TEXT); screen.blit(lab,(r.x+10,y-8))
        x=int(start_x+(end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen,(255,120,120),(x,r.y+30),(x,r.bottom-12),2)
        # indicators
        ind_ccg = FONT.render("CCG ON" if self.ccg_on else "CCG off", True, CTRL if self.ccg_on else DIMT)
        ind_rp  = FONT.render("RP  ON" if self.rp_on  else "RP  off", True, CTRL if self.rp_on else DIMT)
        screen.blit(ind_ccg, (end_x+10, r.y+40))
        screen.blit(ind_rp,  (end_x+10, r.y+68))

# ---- Multiplier Controller ----
class MultController:
    def __init__(self, a2:Acc, a3:Acc, out:Acc):
        self.a2=a2; self.a3=a3; self.out=out; self.reset()
    def reset(self):
        self.digit_idx=9; self.remaining=0; self.shift=0; self.active=False; self.done=False
    def start(self): self.active=True; self.done=False; self._setup_digit()
    def _setup_digit(self):
        if self.digit_idx<0: self.active=False; self.done=True; return
        m=self.a3.digits[self.digit_idx]; self.remaining=m; self.shift=9-self.digit_idx
    def begin_add_if_needed(self, acc_target:Acc):
        if self.active and self.remaining>0:
            acc_target.start_add(self.a2.value(), shift=self.shift, sign=+1)
    def on_add_time_complete(self):
        if not self.active: return
        if self.remaining>0: self.remaining-=1
        if self.remaining==0:
            self.digit_idx-=1; self._setup_digit()

# ---- Orchestrator ----
class Demo:
    def __init__(self):
        # 20 Accumulators model + compact views
        self.accs = [Acc(f"A{i+1}") for i in range(20)]
        self.minis : List[AccMini] = []
        # layout for minis (10 per row)
        top_y=130; rows=2; cols=10; cell_w=136; cell_h=64; x0=20
        for r in range(rows):
            for c in range(cols):
                i=r*cols+c
                rect=pygame.Rect(x0 + c*cell_w, top_y + r*cell_h, cell_w-6, cell_h-6)
                self.minis.append(AccMini(self.accs[i], rect))

        # named references
        self.A1=self.accs[0]; self.A2=self.accs[1]; self.A3=self.accs[2]
        self.A4=self.accs[3]; self.A5=self.accs[4]; self.A6=self.accs[5]
        self.A7=self.accs[6]

        # Plugboard
        self.pb = Plugboard(pygame.Rect(20, 310, 1380, 320))
        self._build_ports_and_wires()

        # Timing
        self.timing = Timing((20, 650, 1380, 300))

        # Ring distributor points (from timing to each mini)
        self.ring_origin = (self.timing.rect.x+60, self.timing.rect.y-40)

        # Controllers
        self.mult = MultController(self.A2, self.A3, self.A4)

        # runtime
        self.stage=0; self.running=False; self._acc=0.0; self.tphase=0.0
        self.ccg_window=0.0; self.rp_window=0.0
        self.reset()

    def _build_ports_and_wires(self):
        r=self.pb.rect
        y1=r.y+90; y2=y1+40; y3=y2+40
        # Helper to place grouped ports with labels
        def add_acc_port_group(acc_tag, x):
            # α,A,S,AS,β,γ
            labels=[("α","α"),("A","A"),("S","S"),("AS","AS"),("β","β"),("γ","γ")]
            for i,(nm,lab) in enumerate(labels):
                self.pb.add_port(f"{acc_tag}.{nm}", x+i*28, y2, "data", lab)
        # CT / Card reader out
        self.pb.add_port("CT1.A", r.x+120, y1, "data", "CT1")
        self.pb.add_port("CT2.A", r.x+200, y1, "data", "CT2")
        self.pb.add_port("CT3.A", r.x+280, y1, "data", "CT3")
        # Acc groups for A1..A7 (used in demo)
        add_acc_port_group("A1", r.x+420)
        add_acc_port_group("A2", r.x+610)
        add_acc_port_group("A3", r.x+800)
        add_acc_port_group("A4", r.x+990)
        add_acc_port_group("A5", r.x+1180)
        add_acc_port_group("A7", r.x+420)  # second row? keep same; we will use separate y for visibility
        # MULT ports
        self.pb.add_port("MULT.IN1", r.x+700, y3, "data", "M.IN1")
        self.pb.add_port("MULT.IN2", r.x+760, y3, "data", "M.IN2")
        self.pb.add_port("MULT.OUT", r.x+900, y3, "data", "M.OUT")
        # Control CCG/RP
        self.pb.add_port("CCG", r.x+60, y3, "ctrl", "CCG")
        self.pb.add_port("RP",  r.x+110,y3, "ctrl", "RP")
        # Punch
        self.pb.add_port("PUNCH.IN", r.x+1240, y3, "data", "PUNCH")

        # Cables for scenario
        self.pb.add_cable("CT1.A","A1.α")
        self.pb.add_cable("CT2.A","A2.α")
        self.pb.add_cable("CT3.A","A3.α")
        # multiply
        self.pb.add_cable("A2.A","MULT.IN1")
        self.pb.add_cable("A3.A","MULT.IN2")
        self.pb.add_cable("MULT.OUT","A4.α")
        # add: A1 + A4 -> A5
        self.pb.add_cable("A1.A","A5.α")
        self.pb.add_cable("A4.A","A5.α")
        # subtract: A5 - A2 -> A7 (S path)
        self.pb.add_cable("A5.A","A7.α")
        self.pb.add_cable("A2.S","A7.α")
        # punch
        self.pb.add_cable("A7.A","PUNCH.IN")

    # --- control helpers ---
    def open_ccg(self, sec=0.25):
        self.timing.ccg_on=True; self.ccg_window=sec
    def pulse_rp(self, sec=0.2):
        self.timing.rp_on=True; self.rp_window=sec
    def decay_ctrl(self, dt):
        if self.ccg_window>0:
            self.ccg_window-=dt; 
            if self.ccg_window<=0: self.timing.ccg_on=False
        if self.rp_window>0:
            self.rp_window-=dt; 
            if self.rp_window<=0: self.timing.rp_on=False

    # --- stepping ---
    def do_pulse(self):
        cur=self.timing.cursor
        # STAGE0: LOAD
        if self.stage==0:
            if cur==0:
                self.open_ccg()
                self.A1.load(1); self.A2.load(2); self.A3.load(3)
            if cur==9:
                self.stage=1; self.mult.start()
        # STAGE1: MULTIPLY A2*A3 -> A4
        elif self.stage==1:
            if cur==0:
                self.open_ccg()
                self.mult.begin_add_if_needed(self.A4)
            self.A4.tick_add_pulse(cur)
            if cur==9:
                self.mult.on_add_time_complete()
                if self.mult.done:
                    self.pulse_rp(); self.stage=2
        # STAGE2: ADD  A1 + A4 -> A5
        elif self.stage==2:
            if cur==0:
                self.open_ccg()
                # AS semantics not needed here; positive adds
                # Use chained additions in same add-time visually: we do A1 then A4 value into A5
                self.A5.start_add(self.A1.value(), sign=+1)
            # tick possibly twice: first pass then start second in mid-window
            self.A5.tick_add_pulse(cur)
            if cur==5 and not self.A5.add_active:
                self.A5.start_add(self.A4.value(), sign=+1)
            if cur==9:
                self.pulse_rp(); self.stage=3
        # STAGE3: SUBTRACT  A5 - A2 -> A7  (S path)
        elif self.stage==3:
            if cur==0:
                self.open_ccg()
                self.A7.start_add(self.A5.value(), sign=+1)
            self.A7.tick_add_pulse(cur)
            if cur==5 and not self.A7.add_active:
                # subtract by negative sign, representing S path
                self.A7.start_add(self.A2.value(), sign=-1)
            if cur==9:
                self.pulse_rp(); self.stage=4
        # STAGE4: PUNCH (display)
        elif self.stage==4:
            if cur==0: self.open_ccg()
            if cur==9: self.pulse_rp(); self.stage=5
        self.timing.cursor = (self.timing.cursor+1)%10

    def reset(self):
        for a in self.accs: a.load(0)
        self.stage=0; self.timing.cursor=0
        self.mult.reset()
        self._acc=0.0; self.tphase=0.0
        self.timing.ccg_on=False; self.timing.rp_on=False
        self.ccg_window=self.rp_window=0.0

    def update(self, dt):
        if self.running:
            self._acc += dt
            if self._acc>=self.timing.speed:
                self._acc = 0.0
                self.do_pulse()
        # cable pulse animation phase
        self.tphase += dt/max(0.12, self.timing.speed)
        if self.tphase>1: self.tphase=1.0
        self.decay_ctrl(dt)

    # --- visuals ---
    def _ring_paths(self)->List[Tuple[Tuple[int,int], Tuple[int,int]]]:
        paths=[]
        for mini in self.minis:
            # from origin to each mini ring point
            p0=self.ring_origin; p1=mini.ring_point
            paths.append((p0,p1))
        return paths

    def draw(self):
        screen.fill(BG)

        # -- Header / Blocks --
        draw_panel(pygame.Rect(20,20,210,90), "Card Reader")
        ct_text = FONT_BIG.render("CT1:1  CT2:2  CT3:3", True, OK)
        screen.blit(ct_text, (30, 60))

        draw_panel(pygame.Rect(240,20,1160,90), "Units (compact)")
        legend = "A1..A20 Accumulators | Multiplier M | Control: CCG gate / RP reset | Expression: 1 + 2×3 then −2"
        screen.blit(FONT.render(legend, True, TEXT), (250, 60))

        # -- Acc minis (20) + ring distributor wiring --
        ring_idx = self.timing.cursor
        for mini in self.minis:
            # active digit highlight only for units being worked on
            active_idx = ring_idx if (mini.acc.add_active) else None
            mini.draw(ring_idx, active_idx)

        # draw ring distributor
        pygame.draw.circle(screen, (90,220,120), self.ring_origin, 6)
        pygame.draw.circle(screen, EDGE, self.ring_origin, 6, 1)
        for (p0,p1) in self._ring_paths():
            pygame.draw.line(screen, (120,160,120), p0, p1, 2)
            # pulse dot along ring line
            t = (ring_idx)/9.0
            x = int(p0[0] + (p1[0]-p0[0])*t)
            y = int(p0[1] + (p1[1]-p0[1])*t)
            pygame.draw.circle(screen, (210,255,210), (x,y), 3)

        # -- Plugboard --
        self.pb.draw(self.active_paths(), self.tphase)

        # -- PUNCH display
        punch_rect = pygame.Rect(20, 260, 380, 40)
        val = self.A7.value()
        draw_panel(punch_rect, "Card Punch (result)")
        screen.blit(FONT_BIG.render(str(val), True, OK), (punch_rect.x+220, punch_rect.y+8))

        # -- Info line
        tips = f"ENTER=STEP  SPACE=RUN/PAUSE  R=Reset  +/-=speed  |  Stage: {['LOAD','MULT','ADD','SUB','PUNCH','DONE'][self.stage]}  Cursor:{ring_idx}  Mult(digit:{self.mult.digit_idx} rem:{self.mult.remaining} shift:{self.mult.shift})"
        screen.blit(FONT.render(tips, True, TEXT), (20, 98))

        # -- Timing panel
        self.timing.draw(['LOAD','MULTIPLY','ADD','SUB','PUNCH','DONE'][self.stage])

    # Active data/control paths for plugboard pulse animation
    def active_paths(self)->List[Tuple[str,str,str]]:
        paths=[]
        cur=self.timing.cursor
        # control CCG/RP to relevant blocks
        if self.timing.ccg_on:
            if   self.stage==0: paths += [("CCG","A1.α","ctrl"),("CCG","A2.α","ctrl"),("CCG","A3.α","ctrl")]
            elif self.stage==1: paths += [("CCG","MULT.IN1","ctrl"),("CCG","MULT.IN2","ctrl"),("CCG","A4.α","ctrl")]
            elif self.stage==2: paths += [("CCG","A5.α","ctrl")]
            elif self.stage==3: paths += [("CCG","A7.α","ctrl")]
            elif self.stage==4: paths += [("CCG","PUNCH.IN","ctrl")]
        if self.timing.rp_on:
            targets = ["A4.α","A5.α","A7.α"] if self.stage in (1,2,3,4) else []
            for t in targets: paths.append(("RP",t,"ctrl"))
        # data flows
        if self.stage==0:
            paths += [("CT1.A","A1.α","data"),("CT2.A","A2.α","data"),("CT3.A","A3.α","data")]
        elif self.stage==1:
            paths += [("A2.A","MULT.IN1","data"),("A3.A","MULT.IN2","data")]
            if cur>=7 or self.A4.add_active: paths += [("MULT.OUT","A4.α","data")]
        elif self.stage==2:
            # show sequential adds into A5 (A1 then A4)
            paths += [("A1.A","A5.α","data")]
            if cur>=5: paths += [("A4.A","A5.α","data")]
        elif self.stage==3:
            paths += [("A5.A","A7.α","data"),("A2.S","A7.α","data")]
        elif self.stage==4:
            paths += [("A7.A","PUNCH.IN","data")]
        return paths

# ---- main ----
def main():
    demo = Demo()
    last=time.time()
    while True:
        now=time.time(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_RETURN: demo.do_pulse()
                if e.key==pygame.K_SPACE: demo.running=not demo.running; demo._acc=0.0
                if e.key==pygame.K_r: demo.reset()
                if e.key==pygame.K_MINUS or e.key==pygame.K_KP_MINUS: demo.timing.speed=min(1.0, demo.timing.speed+0.05)
                if e.key==pygame.K_EQUALS or e.key==pygame.K_PLUS or e.key==pygame.K_KP_PLUS: demo.timing.speed=max(0.05, demo.timing.speed-0.05)
        demo.update(dt)
        demo.draw()
        pygame.display.flip()
        clock.tick(60)

if __name__=="__main__":
    main()
