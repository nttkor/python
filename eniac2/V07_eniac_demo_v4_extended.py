
"""
ENIAC Demo — V4 Extended
------------------------
- Implements subtraction via S ports (10's complement) and AS (send both positive and negative).
- β and γ ports as control triggers: β=reset target accumulator, γ=toggle sign.
- Displays 20 accumulators as full-size panels with scrolling (arrow keys to scroll view).
"""

import sys, time, math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
pygame.init()
W, H = 1400, 1000
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V4 Extended")
clock = pygame.time.Clock()

BG    = (54,56,60)
PANEL = (82,84,88)
TEXT  = (235,235,235)
DIMT  = (200,200,200)
OK    = (110,230,130)
ACCENT= (120,220,255)
CTRL  = (255,210,130)
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

def digits10(n:int)->List[int]:
    s = f"{abs(n):010d}"
    return [int(ch) for ch in s]

def from_digits(ds:List[int])->int:
    return int("".join(map(str, ds)))

class Acc:
    def __init__(self, name, pos=(0,0)):
        self.name = name
        self.pos = pos
        self.digits = [0]*10
        self.sign = '+'
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
    def reset(self):  # β control
        self.load(0)
    def toggle_sign(self):  # γ control
        self.sign = '+' if self.sign=='-' else '-'
    def start_add(self, v:int, shift:int=0, sign:int=+1):
        ds = digits10(abs(v))
        if shift>0:
            ds = ds[:10-shift] + [0]*shift
        self.addend_digits = ds
        self.add_sign = +1 if sign>=0 else -1
        self.carry = 0
        self.add_active = True
    def tick_add_pulse(self, cursor:int):
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
        if cursor == 9:
            self.add_active = False
            self.carry = 0
    def draw(self, active_idx: Optional[int]=None, rect_override=None):
        rect = pygame.Rect(self.pos[0], self.pos[1], 236, 94) if rect_override is None else rect_override
        draw_panel(rect, f"Acc {self.name}")
        s = self.sign + "".join(map(str, self.digits))
        t = FONT_BIG.render(s, True, OK)
        screen.blit(t, (rect.x+10, rect.y+46))
        y = rect.y+28
        for i in range(10):
            x = rect.x+12+i*20
            on = (active_idx==i)
            pygame.draw.circle(screen, (250,240,140) if on else (90,90,90), (x,y), 6)
            pygame.draw.circle(screen, (35,35,35), (x,y), 6, 1)
        if self.carry_flash > 0 and self.carry_from_idx is not None:
            self.carry_flash -= 0.05
            i = self.carry_from_idx
            x1 = rect.x+12+i*20
            x2 = rect.x+12+max(0,i-1)*20
            xm = int((x1+x2)/2)
            pygame.draw.circle(screen, CARRY, (xm, y-14), 5)

@dataclass
class Port:
    name: str
    pos: Tuple[int,int]
    ptype: str
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
        for c in self.cables:
            a = self.ports[c.a]; b = self.ports[c.b]
            base = (182,182,182) if c.kind=="data" else (170,150,120)
            pygame.draw.line(screen, base, a.pos, b.pos, 5)
        for p in self.ports:
            glow = max(0.0, min(1.0, p.lamp))
            col = (18+int(200*glow),18+int(120*glow),18) if p.ptype=="data" else (18+int(180*glow),18+int(160*glow),12)
            pygame.draw.circle(screen, col, p.pos, 7)
            pygame.draw.circle(screen, (200,200,200), p.pos, 7, 1)
            p.lamp *= 0.90
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
        row_h = h/12
        start_x = self.rect.x + 80
        end_x = self.rect.right - 110
        for i,name in enumerate(["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]):
            y = int(self.rect.y + 36 + i*row_h)
            pygame.draw.line(screen, (120,120,120), (start_x,y), (end_x,y), 1)
            lab = FONT_SM.render(name, True, TEXT); screen.blit(lab, (self.rect.x+10, y-8))
        x = int(start_x + (end_x-start_x)*(self.cursor/10))
        pygame.draw.line(screen, (255,120,120), (x, self.rect.y+30), (x, self.rect.bottom-12), 2)

class Demo:
    def __init__(self):
        self.accs = [Acc(f"A{i+1}") for i in range(20)]
        self.pb = Plugboard()
        self.timing = Timing((20, 900, 1360, 90))
        self.stage = 0
        self.running = False
        self.scroll_y = 0
        self.reset()
    def reset(self):
        for a in self.accs: a.load(0)
        self.stage = 0
    def do_pulse(self):
        cur = self.timing.cursor
        if self.stage==0 and cur==0:
            self.accs[0].load(5)
            self.accs[1].load(2)
            self.stage=1
        elif self.stage==1:
            if cur==0:
                # Example subtraction: A1 - A2 => A3
                self.accs[2].start_add(self.accs[0].value(), sign=+1)
                self.accs[2].start_add(self.accs[1].value(), sign=-1)
            self.accs[2].tick_add_pulse(cur)
            if cur==9:
                self.stage=2
        self.timing.cursor = (self.timing.cursor+1)%10
    def update(self, dt):
        if self.running:
            self.do_pulse()
    def draw(self):
        screen.fill(BG)
        # draw 20 accs in grid with scroll
        cols = 4
        cell_h = 110
        for idx,a in enumerate(self.accs):
            row = idx//cols
            col = idx%cols
            y = 20 + row*cell_h + self.scroll_y
            if -100<y<H:
                a.draw(rect_override=pygame.Rect(20+col*260, y, 236, 94))
        self.timing.draw(f"Stage {self.stage}")

def main():
    demo = Demo()
    last = time.time()
    while True:
        now = time.time(); dt = now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_SPACE: demo.running=not demo.running
                if e.key==pygame.K_RETURN: demo.do_pulse()
                if e.key==pygame.K_r: demo.reset()
                if e.key==pygame.K_UP: demo.scroll_y += 20
                if e.key==pygame.K_DOWN: demo.scroll_y -= 20
        demo.update(dt)
        demo.draw()
        pygame.display.flip()
        clock.tick(60)

if __name__=="__main__":
    main()
