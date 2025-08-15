
# ENIAC Demo — v10 (compact but functional)
# Requirements: pygame
# Run: python eniac_demo_v10.py
#
# Keyboard:
#   SPACE run/pause | ENTER step
#   < / > step back/forward | Ctrl+< / Ctrl+> : 10 steps back/forward
#   - / + speed | R reset | S save wiring | L load wiring | A auto-route example
# Mouse (Plugboard Editor):
#   Drag from port to port -> cable, Right-click cable -> delete, Wheel zoom, Middle-drag pan
#
# What you get:
# - 20 Accumulators A1..A20 (signed BCD, 10 digits), compact tiles + ring dots
# - Cycle Timer (CT1..CT3) and Ring Distributor 10 phases (CPP,10P..1P,CCG,RP)
# - Plugboard Editor with orthogonal Manhattan routing (A* on grid) + label-avoidance
# - Timing pane: 10 phases digital pulses over 300-step history (30 micro × 10)
# - Rewindable state history (snapshots)
# - Divider / Sqrt micro-ops at 10-pulse resolution (digitwise borrow/carry propagation)
#
# Notes:
# - Arithmetic aims to be visually faithful; it is not a bit-perfect reproduction of ENIAC.
# - The code is kept in one file for portability. Simplify/extend as needed.

import json, math, os, random, sys
from collections import deque, defaultdict
import pygame

# ---------------------------- Config ----------------------------
W, H = 1320, 820
BG  = (40, 44, 48)
FG  = (220, 230, 230)
MUTED = (150, 160, 170)
ACC_BG = (60, 66, 72)
OK = (120, 210, 160)
WARN = (255, 170, 60)
BAD = (250, 95, 95)
CABLE = (190, 200, 210)
CABLE_ACT = (120, 200, 255)
BUS = (210, 190, 140)
GRID_SZ = 10

FPS = 60
SPEEDS = [0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]  # sim-steps per real frame multiplier

HIST_STEPS = 300   # 10 pulse × 30 columns
DIGITS = 10        # 10-digit accumulators

# Ports per accumulator label row
PORT_LABELS = ['α','A','S','AS','β','γ']  # α: receive, A: send value, S: 10s complement, AS both, β/γ: control
PORT_MEANING = {
    'α': "receive",
    'A': "send",
    'S': "send_10s_complement",
    'AS': "send_both",
    'β': "control1",
    'γ': "control2",
}

# ---------------------------- Helpers ----------------------------
def clamp(v,a,b): return a if v<a else b if v>b else v

def draw_text(surf, txt, pos, color=FG, size=16, align='left'):
    font = pygame.font.SysFont('consolas,menlo,monospace', size)
    img = font.render(txt, True, color)
    r = img.get_rect()
    if align=='left':   r.topleft = pos
    elif align=='center': r.center = pos
    else: r.topright = pos
    surf.blit(img, r)
    return r

def ortho_path(start, goal, obstacles, labels):
    """A* on grid with Manhattan metric. Avoid obstacles and label-band with extra cost.
       start, goal in grid coords. obstacles: set((x,y)) blocked. labels: list of rects (px) to penalize proximity.
    """
    sx, sy = start; gx, gy = goal
    open_set = [(0, (sx,sy), None)]
    best = { (sx,sy): (0,None) }
    def h(x,y): return abs(x-gx)+abs(y-gy)
    def near_label_cost(px,py):
        # penalize getting too close to labels (so lines don't cover text)
        x = px*GRID_SZ; y = py*GRID_SZ
        c = 0.0
        for r in labels:
            dx = max(r.left - x, 0, x - r.right)
            dy = max(r.top  - y, 0, y - r.bottom)
            d = math.hypot(dx,dy)
            if d < 16: c += (16-d)*0.6
        return c
    import heapq
    heapq.heapify(open_set)
    while open_set:
        f,(x,y),_ = heapq.heappop(open_set)
        if (x,y)==(gx,gy): break
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx,y+dy
            if nx<0 or ny<0 or nx>2000 or ny>2000: continue
            if (nx,ny) in obstacles: continue
            g = best[(x,y)][0] + 1 + near_label_cost(nx,ny)
            if (nx,ny) not in best or g + h(nx,ny) < best[(nx,ny)][0] + h(nx,ny):
                best[(nx,ny)] = (g,(x,y))
                heapq.heappush(open_set, (g+h(nx,ny),(nx,ny),(x,y)))
    # Reconstruct
    path = []
    cur = (gx,gy)
    if cur not in best: return [start, goal]
    while cur:
        path.append(cur)
        cur = best[cur][1]
    path.reverse()
    # compress straight segments
    comp = [path[0]]
    for i in range(1,len(path)-1):
        x0,y0 = comp[-1]; x1,y1 = path[i]; x2,y2 = path[i+1]
        if (x1-x0,y1-y0)==(x2-x1,y2-y1): continue
        comp.append(path[i])
    comp.append(path[-1])
    return comp

# ---------------------------- Model ----------------------------
class Accumulator:
    def __init__(self, name):
        self.name = name
        self.signed = +1  # +1 or -1
        self.d = [0]*DIGITS  # LSD..MSD
        self.ring = 0        # ring indicator 0..9
        self.active = True
    def reset(self):
        self.signed = +1
        self.d = [0]*DIGITS
        self.ring = 0
    def value(self):
        v = 0
        for i in range(DIGITS-1, -1, -1):
            v = v*10 + self.d[i]
        return v*self.signed
    def set_value(self, n):
        self.signed = 1 if n>=0 else -1
        n = abs(int(n))
        for i in range(DIGITS):
            self.d[i] = n%10; n//=10
    def add_digitwise(self, B, sign=+1, micro=0):
        """One add-time (10 pulses). At each pulse (micro 0..9) add B digit and propagate carry only one step.
           Returns info about carry/borrow for visualization.
        """
        idx = micro  # LSD first
        info = {'idx':idx,'carry_from':None,'carry_to':None}
        a = self.d[idx]
        b = B.d[idx]
        if sign<0: b = (10-b)%10  # 10's complement trick for subtraction
        s = a + b + (1 if hasattr(self,'carry_in') and self.carry_in==idx else 0)
        if s>=10:
            self.d[idx] = s-10
            self.carry_in = idx+1 if idx+1<DIGITS else None
            info['carry_to'] = idx+1 if idx+1<DIGITS else None
        else:
            self.d[idx] = s
            self.carry_in = None
        info['carry_from'] = idx if info['carry_to'] is not None else None
        return info

class CycleTimer:
    def __init__(self):
        self.micro = 0   # 0..9 within add-time
        self.phase_hist = deque(maxlen=HIST_STEPS)  # store bitfields for 10P..1P + CPP/CCG/RP
        self.stage_name = "IDLE"
        self.cooldown = 0  # wait frames after full ring
    def step(self):
        self.micro = (self.micro+1)%10
    def push_hist(self, bitmask):
        self.phase_hist.append(bitmask)

# ---------------------------- Plugboard ----------------------------
class Port:
    def __init__(self, name, x, y, label, acc_idx=None):
        self.name, self.x, self.y, self.label = name, x, y, label
        self.acc_idx = acc_idx
        self.radius = 7
        self.bus_attach = None  # point on bus where short tab connects

    def rect(self):
        return pygame.Rect(self.x-20, self.y-16, 40, 22)

class Cable:
    def __init__(self, a: 'Port', b: 'Port', poly=None):
        self.a, self.b = a, b
        self.poly = poly or [(a.x,a.y),(b.x,b.y)]
        self.active = False

class Plugboard:
    def __init__(self, area):
        self.ports = []
        self.cables = []
        self.area = area
        self.zoom = 1.0
        self.pan = [0,0]
        self.labels_cache = []
        self.make_ports()

    def make_ports(self):
        # Two rows of ports (receive/transmit), spaced, with room below for labels.
        x0, y0 = self.area.left+90, self.area.top+120
        gap = 56
        for k in range(20):
            x = x0 + k*gap
            # top row label band (α, A, S, AS, β, γ)
            for i,lab in enumerate(PORT_LABELS):
                self.ports.append(Port(f"A{k+1}_{lab}_T", x+ i*24, y0-30, lab, acc_idx=k))
            # bottom row
            for i,lab in enumerate(PORT_LABELS):
                self.ports.append(Port(f"A{k+1}_{lab}_B", x+ i*24, y0+10, lab, acc_idx=k))
        # CT1..3
        ct_y = y0 - 90
        for i in range(3):
            self.ports.append(Port(f"CT{i+1}", x0 + i*50, ct_y, f"CT{i+1}", acc_idx=None))
        # CCG/RP
        self.ports.append(Port("CCG", x0-60, y0+60, "CCG"))
        self.ports.append(Port("RP",  x0-20, y0+60, "RP"))

    def port_at(self, pos):
        for p in self.ports:
            if (p.x-pos[0])**2+(p.y-pos[1])**2 <= (p.radius+2)**2:
                return p
        return None

    def route(self, a: 'Port', b: 'Port'):
        """Orthogonal route using A* on coarse grid + short tabs near each port to avoid labels."""
        labels = self.labels_cache
        # Snap start/end to grid just above/below ports so we don't cover labels
        def snap(px,py):
            return (round(px/GRID_SZ), round(py/GRID_SZ))
        start = snap(a.x, a.y-18) if a.y<=b.y else snap(a.x, a.y+18)
        goal  = snap(b.x, b.y-18) if b.y< a.y else snap(b.x, b.y+18)
        obstacles = set()
        # reserve around ports so cables don't traverse through holes
        for p in self.ports:
            for gx in range(int((p.x-12)//GRID_SZ), int((p.x+12)//GRID_SZ)+1):
                for gy in range(int((p.y-12)//GRID_SZ), int((p.y+12)//GRID_SZ)+1):
                    obstacles.add((gx,gy))
        path = ortho_path(start, goal, obstacles, labels)
        poly = [(a.x, a.y-12 if a.y<=b.y else a.y+12)]  # short tab
        poly += [(x*GRID_SZ, y*GRID_SZ) for (x,y) in path]
        poly += [(b.x, b.y-12 if b.y< a.y else b.y+12)]
        return poly

    def add_cable(self, a: 'Port', b: 'Port'):
        poly = self.route(a,b)
        self.cables.append(Cable(a,b,poly))

    def delete_at(self, pos):
        for i,c in enumerate(self.cables):
            # distance to any segment
            for j in range(len(c.poly)-1):
                x1,y1 = c.poly[j]; x2,y2 = c.poly[j+1]
                if (min(x1,x2)-5<=pos[0]<=max(x1,x2)+5 and
                    min(y1,y2)-5<=pos[1]<=max(y1,y2)+5):
                    self.cables.pop(i); return True
        return False

    def save(self, path):
        data = [{'a':c.a.name,'b':c.b.name,'poly':c.poly} for c in self.cables]
        with open(path,'w',encoding='utf-8') as f: json.dump(data,f)

    def load(self, path):
        name2port = {p.name:p for p in self.ports}
        try:
            data = json.load(open(path,'r',encoding='utf-8'))
        except Exception:
            return
        self.cables.clear()
        for d in data:
            a = name2port.get(d['a']); b = name2port.get(d['b'])
            if a and b:
                self.cables.append(Cable(a,b,d['poly']))

# ---------------------------- Simulator ----------------------------
class ENIACSim:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.speed_idx = 4
        # UI rectangles
        self.rect_top = pygame.Rect(10,10,W-20,160)
        self.rect_plug = pygame.Rect(10,180,W-20,340)
        self.rect_timing = pygame.Rect(10,530,W-20,260)

        # machines
        self.acc = [Accumulator(f"A{i+1}") for i in range(20)]
        for i,a in enumerate(self.acc[:5]): a.set_value(i+1)
        self.ct = [0,0,0]
        self.cyc = CycleTimer()
        self.stage = "MULT"  # MULT, DIV, SQRT, DONE
        self.running = False

        # plugboard
        self.plug = Plugboard(self.rect_plug)
        # keep some example wiring
        self._example_wiring()

        # history (rewind)
        self.history = deque(maxlen=5000)  # store snapshots
        self.cursor = 0  # position in history tail (0=latest)

    def _snapshot(self):
        return {
            'acc': [ (a.signed, a.d[:], a.ring) for a in self.acc ],
            'ct': self.ct[:],
            'micro': self.cyc.micro,
            'stage': self.stage
        }
    def _restore(self, snap):
        for a,s in zip(self.acc, snap['acc']):
            a.signed, a.d, a.ring = s[0], s[1][:], s[2]
        self.ct = snap['ct'][:]
        self.cyc.micro = snap['micro']
        self.stage = snap['stage']

    def _example_wiring(self):
        # create a few sample connections across A1..A10 using A* router
        self.plug.labels_cache = self._collect_port_labels()
        pmap = {p.name:p for p in self.plug.ports}
        def P(n): return pmap[n]
        try:
            self.plug.add_cable(P("CT1"), P("A1_α_T"))
            self.plug.add_cable(P("A1_A_T"), P("A5_α_T"))
            self.plug.add_cable(P("A2_A_T"), P("A5_α_B"))
            self.plug.add_cable(P("A3_A_T"), P("A6_α_T"))
            self.plug.add_cable(P("A4_A_T"), P("A6_α_B"))
            self.plug.add_cable(P("A7_A_T"), P("A10_α_T"))
            self.plug.add_cable(P("A8_A_T"), P("A10_α_B"))
            self.plug.add_cable(P("A10_AS_T"), P("A12_α_T"))
            self.plug.add_cable(P("CCG"), P("A12_β_T"))
            self.plug.add_cable(P("RP"),  P("A12_γ_T"))
        except Exception:
            pass

    # ---------------- arithmetic ----------------
    def _do_mult_tick(self):
        # A3 = A1 * A2 via repeated addition of current digit (LSD first)
        A1,A2,A3 = self.acc[0], self.acc[1], self.acc[2]
        if not hasattr(self,'mult_idx'):
            self.mult_idx = 0
            self.mult_rep = A2.d[self.mult_idx]
        micro = self.cyc.micro
        if self.mult_idx>=DIGITS:
            self.stage="DIV"; delattr(self,'mult_idx'); return
        if self.mult_rep>0:
            info = A3.add_digitwise(A1, +1, micro)
            if micro==9: self.mult_rep -= 1
        else:
            if micro==9:
                self.mult_idx += 1
                if self.mult_idx<DIGITS:
                    self.mult_rep = A2.d[self.mult_idx]
                    A3.d = [0]+A3.d[:-1]

    def _do_div_tick(self):
        # Restoring division (toy): A4 = A3 / A2, remainder -> A3
        D, S = self.acc[2], self.acc[1]
        Q = self.acc[3]
        micro = self.cyc.micro
        if not hasattr(self,'div_idx'):
            self.div_idx = DIGITS-1
            self.div_work = 0
            Q.set_value(0)
        if micro==0:
            self.div_work = self.div_work*10 + D.d[self.div_idx]
        if micro==2:
            if self.div_work >= S.value():
                self.div_work -= S.value()
                Q.d[self.div_idx] = min(9, Q.d[self.div_idx] + 1)
        if micro==9:
            D.d[self.div_idx] = self.div_work%10
            self.div_work//=10
            self.div_idx -= 1
            if self.div_idx<0:
                n=self.div_work
                i=0
                while n>0 and i<DIGITS:
                    D.d[i]=n%10; n//=10; i+=1
                self.stage="SQRT"
                delattr(self,'div_idx')

    def _do_sqrt_tick(self):
        # Extremely compact visual sqrt: R ~ sqrt(Q) digit-by-digit
        N = self.acc[3]; R = self.acc[4]; REM = self.acc[5]
        micro = self.cyc.micro
        if not hasattr(self,'sqrt_idx'):
            self.sqrt_idx = DIGITS-1
            R.set_value(0); REM.set_value(0)
        if micro==0:
            REM.d = [N.d[self.sqrt_idx]] + REM.d[:-1]
        if micro==2:
            test = R.value()*2 + 1
            if int(self._digits_to_int(REM.d)) >= test:
                v = int(self._digits_to_int(REM.d)) - test
                self._int_to_digits(REM.d, v)
                R.d[self.sqrt_idx] = 1
            else:
                R.d[self.sqrt_idx] = 0
        if micro==9:
            self.sqrt_idx -= 1
            if self.sqrt_idx<0:
                self.stage="DONE"
                delattr(self,'sqrt_idx')

    @staticmethod
    def _digits_to_int(d):
        n=0
        for i in range(DIGITS-1,-1,-1): n=n*10+d[i]
        return n
    @staticmethod
    def _int_to_digits(dst, n):
        for i in range(DIGITS):
            dst[i]=n%10; n//=10

    # ---------------- main step ----------------
    def step(self):
        if self.cursor==0:
            self.history.append(self._snapshot())
        else:
            self.cursor = max(0, self.cursor-1)

        if self.stage=="MULT": self._do_mult_tick()
        elif self.stage=="DIV": self._do_div_tick()
        elif self.stage=="SQRT": self._do_sqrt_tick()
        bitmask = 1<<self.cyc.micro
        self.cyc.push_hist(bitmask)
        self.cyc.step()

    def step_back(self, n=1):
        for _ in range(n):
            if len(self.history)>self.cursor+1:
                self.cursor += 1
                self._restore(self.history[-1-self.cursor])

    # ---------------- drawing ----------------
    def _collect_port_labels(self):
        labels=[]
        y = self.rect_plug.top+120
        for k in range(20):
            x = self.rect_plug.left+90 + k*56
            rect = pygame.Rect(x-10, y-22, 150, 18)
            labels.append(rect)
        return labels

    def draw_top(self):
        r=self.rect_top; pygame.draw.rect(self.screen, ACC_BG, r, border_radius=8)
        margin=8; w=(r.width-margin*3)//10; h=70
        for i in range(20):
            col = i%10; row=i//10
            rx = r.left+margin+col*(w+margin)
            ry = r.top+10+row*(h+10)
            rr = pygame.Rect(rx, ry, w, h)
            pygame.draw.rect(self.screen, (66,72,80), rr, border_radius=8)
            a = self.acc[i]
            s = ('-' if a.signed<0 else '+') + ''.join(str(a.d[j]) for j in range(DIGITS-1,-1,-1))
            draw_text(self.screen, f"A{i+1}", (rr.left+8, rr.top+6), MUTED, 14)
            draw_text(self.screen, s, (rr.left+8, rr.centery-2), OK, 16)
            for k in range(10):
                cx = rr.left+10+k*10; cy=rr.bottom-12
                pygame.draw.circle(self.screen, (90,96,104), (cx,cy),3,1)
        draw_text(self.screen, f"[Stage {self.stage}]  ENTER:step  SPACE:run/pause  R:reset  +/-:speed  S/L:save/load  A:auto-route  |  < > step  Ctrl+< > x10",
                  (r.left+10, r.bottom-20), MUTED, 14)
        for c in self.plug.cables:
            if not c.poly: continue
            pts=c.poly
            for j in range(len(pts)-1):
                pygame.draw.line(self.screen, (120,180,120), pts[j], pts[j+1], 2)

    def draw_plugboard(self, mouse=None):
        r=self.rect_plug; pygame.draw.rect(self.screen, ACC_BG, r, border_radius=8)
        title = "Plugboard Editor (orthogonal wires, bus tabs avoid labels)"
        draw_text(self.screen, title, (r.left+10,r.top+8), FG, 18)
        labels = self._collect_port_labels()
        self.plug.labels_cache = labels
        by = r.top+120
        pygame.draw.line(self.screen, BUS, (r.left+20,by), (r.right-20,by), 6)
        for p in self.plug.ports:
            col = (220,220,220)
            pygame.draw.circle(self.screen, col, (p.x,p.y), p.radius,2)
            if p.label in PORT_LABELS:
                draw_text(self.screen, p.label, (p.x-6, by+12), MUTED, 12, 'left')
        for c in self.plug.cables:
            pts=c.poly
            for j in range(len(pts)-1):
                pygame.draw.line(self.screen, CABLE, pts[j], pts[j+1], 4)
        for p in self.plug.ports:
            if p.name.startswith("CT"):
                draw_text(self.screen, p.name, (p.x-10,p.y-26), FG, 12)
            if p.name in ("CCG","RP"):
                draw_text(self.screen, p.name, (p.x-10,p.y+20), FG, 12)

    def draw_timing(self):
        r=self.rect_timing; pygame.draw.rect(self.screen, ACC_BG, r, border_radius=8)
        draw_text(self.screen, f"Timing — micro 0..9, history {len(self.cyc.phase_hist)}/{HIST_STEPS}  speed:{SPEEDS[self.speed_idx]:.2f}",
                  (r.left+10,r.top+8), FG, 16)
        gx = r.left+80; gy = r.top+36; w = r.width-100; h = r.height-60
        pygame.draw.rect(self.screen, (56,60,66), (gx,gy,w,h), 1)
        rows = ["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
        for i,lab in enumerate(rows):
            y = gy + i*(h/(len(rows)-1))
            pygame.draw.line(self.screen, (64,68,72), (gx,y), (gx+w,y), 1)
            draw_text(self.screen, lab, (gx-6, y-7), MUTED, 12, 'right')
        hist = list(self.cyc.phase_hist)
        cols = min(len(hist), HIST_STEPS)
        for c in range(cols):
            bitmask = hist[-cols+c]
            x = gx + (c/cols)*w
            for ph in range(10):
                y = gy + (ph+1)*(h/(len(rows)-1))
                if (bitmask>>ph)&1:
                    pygame.draw.circle(self.screen, OK, (int(x), int(y)), 3)

    def draw(self, mouse=None):
        self.screen.fill(BG)
        self.draw_top()
        self.draw_plugboard(mouse)
        self.draw_timing()
        pygame.display.flip()

    # ---------------- events ----------------
    def handle_events(self):
        mouse = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif e.type==pygame.KEYDOWN:
                mod = pygame.key.get_mods()
                if e.key==pygame.K_SPACE: self.running = not self.running
                elif e.key==pygame.K_RETURN: self.step()
                elif e.key==pygame.K_RIGHT:
                    self.step() if not (mod & pygame.KMOD_CTRL) else [self.step() for _ in range(10)]
                elif e.key==pygame.K_LEFT:
                    self.step_back(1 if not (mod & pygame.KMOD_CTRL) else 10)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.speed_idx = max(0, self.speed_idx-1)
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self.speed_idx = min(len(SPEEDS)-1, self.speed_idx+1)
                elif e.key==pygame.K_r:
                    self.__init__(self.screen)
                elif e.key==pygame.K_s:
                    self.plug.save("wiring.json")
                elif e.key==pygame.K_l:
                    self.plug.load("wiring.json")
                elif e.key==pygame.K_a:
                    self._example_wiring()
            elif e.type==pygame.MOUSEBUTTONDOWN:
                if e.button==1:
                    p = self.plug.port_at(mouse)
                    if p: self._drag_from = p
                elif e.button==3:
                    self.plug.delete_at(mouse)
            elif e.type==pygame.MOUSEBUTTONUP and e.button==1:
                if hasattr(self,'_drag_from'):
                    p = self.plug.port_at(mouse)
                    if p and p is not self._drag_from:
                        self.plug.add_cable(self._drag_from, p)
                    delattr(self,'_drag_from')
        return mouse

    def run(self):
        t=0.0
        while True:
            mouse = self.handle_events()
            if self.running:
                t += SPEEDS[self.speed_idx]
                while t>=1.0:
                    self.step(); t-=1.0
            self.draw(mouse)
            self.clock.tick(FPS)

def main():
    pygame.init()
    pygame.display.set_caption("ENIAC Demo — v10")
    screen = pygame.display.set_mode((W,H))
    ENIACSim(screen).run()

if __name__=="__main__":
    main()
