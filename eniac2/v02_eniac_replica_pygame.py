
import sys, math
import pygame
from dataclasses import dataclass
from typing import List, Tuple, Optional

pygame.init()
pygame.display.set_caption("Virtual ENIAC (Pygame replica — beta)")

W, H = 1280, 760
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

# Colors
BG = (62, 64, 68)        # overall background like screenshot
PANEL = (86, 88, 92)
PANEL_DARK = (66, 68, 72)
GRID = (135, 138, 143)
TEXT = (250, 250, 250)
YELLOW = (240, 220, 70)
GREEN = (100, 230, 120)
RED = (240, 120, 120)
ACCENT = (120, 220, 255)
CTRL = (255, 210, 120)

FONT = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 16)
FONT_SM = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 13, bold=False)
FONT_BIG = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 22, bold=True)

# ------------------ UI helpers ------------------
def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=6)
    pygame.draw.rect(screen, (40,40,40), rect, 1, border_radius=6)
    if title:
        t = FONT_BIG.render(title, True, TEXT)
        tw, th = t.get_size()
        screen.blit(t, (rect.centerx - tw//2, rect.y + 8))

class Button:
    def __init__(self, rect, text, color=(210,210,210)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.enabled = True
    def draw(self):
        col = self.color if self.enabled else (120,120,120)
        pygame.draw.rect(screen, col, self.rect, border_radius=6)
        pygame.draw.rect(screen, (15,15,15), self.rect, 1, border_radius=6)
        t = FONT.render(self.text, True, (20,20,20))
        tw, th = t.get_size()
        screen.blit(t, (self.rect.centerx - tw//2, self.rect.centery - th//2))
    def handle(self, e):
        if not self.enabled: return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos): return True
        return False

class Toggle:
    def __init__(self, rect, label=""):
        self.rect = pygame.Rect(rect)
        self.state = False
        self.label = label
    def draw(self):
        pygame.draw.rect(screen, (200,200,200), self.rect, border_radius=20)
        knob_r = self.rect.height-6
        x = self.rect.x+3 if not self.state else self.rect.right-knob_r-3
        pygame.draw.rect(screen, GREEN if self.state else (150,150,150),
                         (x, self.rect.y+3, knob_r, knob_r), border_radius=20)
        lab = FONT_SM.render(self.label, True, TEXT)
        screen.blit(lab, (self.rect.x, self.rect.y - 18))
    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                self.state = not self.state
                return True
        return False

# ------------------ Plugboard ------------------
@dataclass
class Jack:
    x:int; y:int; r:int=7
    id:str=""
    def draw(self):
        pygame.draw.circle(screen, (15,15,15), (self.x,self.y), self.r)
        pygame.draw.circle(screen, (180,180,180), (self.x,self.y), self.r, 1)

@dataclass
class Cable:
    a:int; b:int; color:Tuple[int,int,int]=ACCENT
    # a,b index into Plugboard.jacks

class Plugboard:
    def __init__(self, rect:pygame.Rect, rows=6, cols=22, label=""):
        self.rect = pygame.Rect(rect)
        self.rows, self.cols = rows, cols
        self.jacks: List[Jack] = []
        self.cables: List[Cable] = []
        pad = 16
        dx = (self.rect.width-2*pad)/(cols-1)
        dy = (self.rect.height-2*pad)/(rows-1)
        for r in range(rows):
            for c in range(cols):
                x = int(self.rect.x + pad + c*dx)
                y = int(self.rect.y + pad + r*dy)
                self.jacks.append(Jack(x,y,id=f"J{r}-{c}"))
        self.pending: Optional[int] = None
        self.label = label
    def draw(self):
        # grid lines
        for r in range(self.rows):
            y = self.jacks[r*self.cols].y
            pygame.draw.line(screen, GRID, (self.rect.x+8,y), (self.rect.right-8,y), 1)
        for c in range(self.cols):
            x = self.jacks[c].x
            pygame.draw.line(screen, GRID, (x,self.rect.y+8), (x,self.rect.bottom-8), 1)
        # jacks
        for j in self.jacks: j.draw()
        # cables
        for cab in self.cables:
            a = self.jacks[cab.a]; b = self.jacks[cab.b]
            pygame.draw.line(screen, cab.color, (a.x,a.y), (b.x,b.y), 4)
            pygame.draw.circle(screen, cab.color, (a.x,a.y), 5, 2)
            pygame.draw.circle(screen, cab.color, (b.x,b.y), 5, 2)
        if self.label:
            t = FONT_BIG.render(self.label, True, YELLOW)
            screen.blit(t, (self.rect.centerx - t.get_width()//2, self.rect.y - 28))
    def handle(self, e)->bool:
        if e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
            for idx,j in enumerate(self.jacks):
                if (j.x-e.pos[0])**2+(j.y-e.pos[1])**2 <= j.r**2:
                    if self.pending is None:
                        self.pending = idx
                    else:
                        if self.pending != idx:
                            self.cables.append(Cable(self.pending, idx))
                        self.pending = None
                    return True
        return False
    def animate_along(self, cable_index:int, t:float):
        if cable_index<0 or cable_index>=len(self.cables): return
        cab = self.cables[cable_index]
        a=self.jacks[cab.a]; b=self.jacks[cab.b]
        x = int(a.x + (b.x-a.x)*t); y = int(a.y + (b.y-a.y)*t)
        pygame.draw.circle(screen, (255,255,255), (x,y), 6)
        pygame.draw.circle(screen, (80,180,255), (x,y), 9, 2)

# ------------------ Cycling waveforms ------------------
WAVES = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
class WavePanel:
    def __init__(self, rect:pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.cursor = 0           # 0..9 step inside add-time, plus CCG/RP illustratively
        self.period = 10
        self.mode = "ONE-ADD"     # ONE-ADD or ONE-PULSE or RUN
    def draw(self):
        pygame.draw.rect(screen, PANEL_DARK, self.rect, border_radius=6)
        pygame.draw.rect(screen, (40,40,40), self.rect, 1, border_radius=6)
        # names and lines
        h = self.rect.height - 20
        row_h = h/len(WAVES)
        for i,name in enumerate(WAVES):
            y = int(self.rect.y + 10 + i*row_h + row_h*0.5)
            # waveform (simple square pulses for 1P..10P principles)
            pygame.draw.line(screen, (130,130,130), (self.rect.x+8,y), (self.rect.right-8,y), 1)
            lab = FONT_SM.render(name, True, TEXT)
            screen.blit(lab,(self.rect.x+6, y-8))
        # cursor
        x = int(self.rect.x + 80 + (self.rect.width-100) * (self.cursor / max(1,self.period)))
        pygame.draw.line(screen, (250,120,120), (x, self.rect.y+6), (x, self.rect.bottom-6), 2)
    def step_pulse(self):
        if self.mode == "ONE-PULSE":
            self.cursor = (self.cursor+1) % self.period
        elif self.mode == "ONE-ADD":
            self.cursor = (self.cursor + self.period) % self.period
        else:
            self.cursor = (self.cursor+1) % self.period

# ------------------ Units ------------------
class InitiatingUnit:
    def __init__(self, rect:pygame.Rect, wave:WavePanel):
        self.rect = pygame.Rect(rect)
        self.on_toggle = Toggle((self.rect.x+24, self.rect.y+70, 60, 24), "off on")
        self.go = Button((self.rect.x+24, self.rect.y+110, 60, 36), "go!")
        self.clear = Button((self.rect.x+94, self.rect.y+110, 60, 36), "clear")
        self.step = Button((self.rect.x+164, self.rect.y+110, 60, 36), "step")
        self.wave = wave
        self.status = "READY"
    def draw(self):
        draw_panel(self.rect, "Initiating Unit")
        # small status box
        box = pygame.Rect(self.rect.x+20, self.rect.y+36, 220, 22)
        pygame.draw.rect(screen, (240,240,240), box, border_radius=6)
        pygame.draw.rect(screen, (40,40,40), box,1,border_radius=6)
        st = FONT_SM.render(self.status, True, (20,20,20))
        screen.blit(st, (box.x+8, box.y+2))
        self.on_toggle.draw()
        self.go.draw(); self.clear.draw(); self.step.draw()
    def handle(self,e):
        if self.on_toggle.handle(e):
            self.status = "POWER ON" if self.on_toggle.state else "POWER OFF"
        if self.go.handle(e):
            self.status = "GO"
        if self.clear.handle(e):
            self.status = "CLEAR"
        if self.step.handle(e):
            self.status = "STEP"
            self.wave.step_pulse()

# ------------------ Accumulator panel (visual shell) ------------------
class AccPanel:
    def __init__(self, rect:pygame.Rect, name="Accumulator"):
        self.rect = pygame.Rect(rect)
        # simplified 10 digits & sign row
        self.digits = [0]*10; self.sign = '+'
        # program switch rows (illustrative)
        self.switch_rects = [pygame.Rect(self.rect.x+14 + (i*22), self.rect.y+130 + (r*20), 16, 12)
                             for r in range(6) for i in range(10)]
    def draw(self):
        draw_panel(self.rect, "Accumulators")
        # two sub-panels like screenshot (left/right)
        left = pygame.Rect(self.rect.x+16, self.rect.y+120, 480, 180)
        right= pygame.Rect(self.rect.x+520, self.rect.y+120, 480, 180)
        for rr in (left,right):
            pygame.draw.rect(screen, (230,230,230), rr, border_radius=4)
            pygame.draw.rect(screen, (30,30,30), rr, 1, border_radius=4)
            # little plus switch
            pygame.draw.rect(screen, (180,255,180), (rr.x+8, rr.y+8, 22, 18), border_radius=4)
            t = FONT_SM.render("+", True, (10,60,10)); screen.blit(t,(rr.x+14, rr.y+8))
            # numeric legends
            for i in range(10):
                n = FONT_SM.render(str(i), True, (10,10,10))
                screen.blit(n, (rr.x+54 + i*40, rr.y+8))
            # fake rotary/switch rows
            for r in range(6):
                y = rr.y + 34 + r*22
                for i in range(10):
                    x = rr.x + 50 + i*40
                    pygame.draw.rect(screen, (250,250,250), (x,y,26,12))
                    pygame.draw.rect(screen, (10,10,10), (x,y,26,12), 1)
        # top lamps (0..9 rows) stylized
        lamp_area = pygame.Rect(self.rect.x+0, self.rect.y+0, self.rect.width, 80)
        for i in range(10):
            for j in range(10):
                tx = FONT_SM.render(str(9-j), True, YELLOW)
                screen.blit(tx, (lamp_area.x+70 + j*40 + (i//5)*520, lamp_area.y+10 + (i%5)*14))
        # plugboards left/right
        self.pb_left.draw(); self.pb_right.draw()

    def attach_boards(self, pb_left:Plugboard, pb_right:Plugboard):
        self.pb_left = pb_left
        self.pb_right = pb_right

# ------------------ Build layout ------------------
wave = WavePanel(pygame.Rect(360, 10, 560, 180))
init_unit = InitiatingUnit(pygame.Rect(20, 10, 270, 180), wave)
acc_pan = AccPanel(pygame.Rect(360, 210, 900, 520))

# plugboards bottom like screenshot (three areas)
pb1 = Plugboard(pygame.Rect(20, 600, 320, 120), rows=4, cols=16, label="")
pb2 = Plugboard(pygame.Rect(360, 600, 420, 120), rows=4, cols=20, label="")
pb3 = Plugboard(pygame.Rect(820, 600, 440, 120), rows=4, cols=22, label="")
acc_pan.attach_boards(pb2, pb3)

# cable animation bookkeeping
anim_index = None
anim_t = 0.0
anim_speed = 0.02

# mode buttons (one-pulse / one-add)
btn_one_pulse = Button((940, 150, 120, 28), "one-pulse")
btn_one_add   = Button((1080,150, 120, 28), "one-add")

def draw():
    screen.fill(BG)
    # top toolbar mock
    pygame.draw.rect(screen, (190,190,190), (0,0,W,36))
    # sections
    draw_panel(pygame.Rect(20, 10, 320, 180), "Überblicksfenster")
    init_unit.draw()
    draw_panel(pygame.Rect(20, 210, 320, 370), "Initiating Unit")  # big left image area
    wave.draw()
    acc_pan.draw()
    # plugboards bottom
    pb1.draw(); pb2.draw(); pb3.draw()
    # animate along first cable of pb2 if any and if in step
    global anim_index, anim_t
    if anim_index is not None and pb2.cables:
        pb2.animate_along(anim_index, anim_t)
        anim_t += anim_speed
        if anim_t >= 1.0:
            anim_index = None
            anim_t = 0.0
    # mode buttons
    btn_one_pulse.draw(); btn_one_add.draw()
    m = FONT.render(f"mode: {wave.mode}  cursor:{wave.cursor}", True, TEXT)
    screen.blit(m, (360, 192))

def handle(e):
    global anim_index, anim_t
    init_unit.handle(e)
    if btn_one_pulse.handle(e): wave.mode = "ONE-PULSE"
    if btn_one_add.handle(e): wave.mode = "ONE-ADD"
    pb1.handle(e); pb2.handle(e); pb3.handle(e)
    # start an animation when STEP pressed: if pb2 has a cable, animate the last one
    if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
        # detect if last action was STEP (status set by InitiatingUnit)
        if init_unit.status == "STEP" and pb2.cables:
            anim_index = len(pb2.cables)-1
            anim_t = 0.0

def main():
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
            handle(e)
        draw()
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
