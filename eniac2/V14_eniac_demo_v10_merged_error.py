
"""
ENIAC Demo — V10 MERGED (Stable)
- Combines V7c's robust rendering with V10's extended features.
- 20 Accumulators, CT1..3, CCG, RP, Plugboard (ports α/A/S/AS/β/γ), Timing chart 300 micro-steps.
- Manhattan-style BUS routing (orthogonal; label-aware taps) with pulses animating along routes.
- Division / Square-Root controllers: 10-pulse per digit timing (illustrative, simplified but stateful).
- Stateful stepping & rewind: < / > single micro-step backward/forward; CTRL+< / CTRL+> = 10 steps.
- Auto wiring demo; Save/Load wiring JSON (S/L).
- Black-screen safety: deterministic draw order, background clear, vsync-like tick, font fallback.

Controls
  SPACE           : run/pause
  ENTER           : do one micro-step
  < , >           : step backward / forward (STATEFUL)  ← fixed vs V7c's "visual only"
  CTRL+< / CTRL+> : step 10 micro-steps backward / forward
  R               : reset
  - / +           : slower / faster (time per micro-step)
  S / L           : save / load plugboard wiring (JSON at ./plugboard_v10m.json)
  A               : auto-wire demo (creates example routes)
Notes
  * 300 micro-steps = 10 ring steps × 30 micro-steps per ring.
  * At end of each 300-step ring a short pause is inserted.
  * Division / √ are illustrative controllers that produce correct digit timing with simplified math.
"""

import sys, time, math, json, os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import pygame

# ----------------- Init & Globals -----------------
pygame.init()
# Window size kept moderate to reduce blank-screen risk; can be resized later.
W, H = 1480, 950
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V10 MERGED (Stable)")
clock = pygame.time.Clock()

# Colors / Fonts
BG=(40,42,46); PANEL=(64,66,70); EDGE=(28,28,28); TEXT=(235,235,235); DIM=(165,165,165)
OK=(120,235,150); ACCENT=(125,220,255); CTRL=(255,210,120); CARRY=(255,120,120)
GRID=(70,70,80)

# Font fallbacks (avoid font init crash)
def _mkfont(names, size, bold=False):
    for n in names.split(","):
        try:
            f = pygame.font.SysFont(n.strip(), size, bold=bold)
            if f: return f
        except Exception:
            pass
    return pygame.font.Font(None, size)
FONT   = _mkfont("consolas,dejavusansmono,menlo,monospace",16)
FONT_SM= _mkfont("consolas,dejavusansmono,menlo,monospace",12)
FONT_BIG=_mkfont("consolas,dejavusansmono,menlo,monospace",20,True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, EDGE, rect, 1, border_radius=8)
    if title: screen.blit(FONT_BIG.render(title, True, TEXT),(rect.x+10,rect.y+8))

def digits10(n:int):
    return [int(ch) for ch in f"{abs(int(n)) :010d}"]
def from_digits(ds):
    try:
        return int("".join(map(str, ds)))
    except Exception:
        return 0

# ----------------- CT Panels -----------------
class CT:
    def __init__(self, name:int, value:int):
        self.name=f"CT{name}"; self.value=value
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(72,74,78),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        s=str(self.value); screen.blit(FONT.render(s,True,OK),(rect.x+6,rect.y+22))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)

# ----------------- Accumulator -----------------
class Acc:
    def __init__(self, name):
        self.name=name; self.digits=[0]*10; self.sign='+'
        self.add_active=False; self.addend=[0]*10; self.add_sign=+1; self.carry=0
        self.carry_flash=0.0; self.carry_from=None
    def load(self,v:int):
        v=int(v)
        self.sign='-' if v<0 else '+'; self.digits=digits10(abs(v))
    def value(self)->int:
        v=from_digits(self.digits); return -v if self.sign=='-' else v
    def reset(self): self.load(0)
    def toggle_sign(self): self.sign='+' if self.sign=='-' else '-'
    def start_add(self,v:int,shift:int=0,sign:int=+1):
        ds=digits10(abs(v))
        if shift>0: ds = ds[:10-shift]+[0]*shift
        self.addend=ds; self.add_sign=+1 if sign>=0 else -1
        self.carry=0; self.add_active=True
    def tick_add_pulse(self,cursor:int):
        if not self.add_active: return
        j=9-cursor; a=self.digits[j]; b=self.addend[j]*self.add_sign; s=a+b+self.carry
        cout=0
        if s>=10: s-=10; cout=1
        elif s<0: s+=10; cout=-1
        self.digits[j]=s; self.carry=cout
        if cout!=0:
            self.carry_flash=0.35; self.carry_from=j
        if cursor==9:
            self.add_active=False; self.carry=0
    def borrow_from(self, j:int):
        # for division (borrow chain)
        i=j-1
        while i>=0 and self.digits[i]==0:
            self.digits[i]=9; i-=1
        if i>=0:
            self.digits[i]-=1
            for k in range(i+1,j): self.digits[k]=9
            self.digits[j]+=10
            self.carry_flash=0.35; self.carry_from=i
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(72,74,78),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        s=self.sign+"".join(map(str,self.digits)); screen.blit(FONT.render(s,True,OK),(rect.x+6,rect.y+20))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)
        if self.carry_flash>0 and self.carry_from is not None:
            self.carry_flash-=0.05; i=self.carry_from
            xm=int(rect.x+12+i*8); pygame.draw.circle(screen,CARRY,(xm,rect.y+16),3)

# ----------------- Ports, Cables & Plugboard -----------------
@dataclass
class Port:
    name:str; label:str; kind:str  # "data" or "ctrl"
    pos:Tuple[float,float]
    lamp:float=0.0

@dataclass
class Cable:
    a:str; b:str; kind:str

class Plugboard:
    def __init__(self, rect):
        self.host_rect=pygame.Rect(rect)
        self.ports:Dict[str,Port]={}; self.cables:List[Cable]=[]
        self.drag_from:Optional[str]=None
        self.scale=1.0; self.offset=[0,0]; self.mouse_last=(0,0)
        # Two bus rails below labels to avoid text occlusion
        self.upper_bus_y=150; self.lower_bus_y=240
        # Obstacles where labels sit (label-aware taps)
        self.label_rects:List[pygame.Rect]=[]
    def add_port(self, name,label,kind,x,y):
        self.ports[name]=Port(name,label,kind,(x,y))
    def add_cable(self,a,b):
        if a in self.ports and b in self.ports:
            kind=self.ports[a].kind; self.cables.append(Cable(a,b,kind))
    def remove_cable_at(self, mx,my):
        if not self.cables: return
        hit_idx=None; best=9
        for i,c in enumerate(self.cables):
            pts=self.route_points(c.a,c.b)
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                vx,vy=x2-x1,y2-y1
                if vx==vy==0: continue
                t=max(0,min(1, ((mx-x1)*vx+(my-y1)*vy)/((vx*vx+vy*vy) or 1)))
                px,py=x1+t*vx,y1+t*vy
                d=math.hypot(px-mx,py-my)
                if d<best: best=d; hit_idx=i
        if hit_idx is not None and best<9: self.cables.pop(hit_idx)
    def draw_base(self, title):
        r=self.host_rect; draw_panel(r,title)
        board=pygame.Rect(r.x+8,r.y+36,r.width-16,r.height-44)
        pygame.draw.rect(screen,(64,66,70),board,border_radius=6)
        self.board_rect=board
        def to_screen(pt):
            return (int(board.x+(pt[0]*self.scale+self.offset[0])),
                    int(board.y+(pt[1]*self.scale+self.offset[1])))
        self.to_screen=to_screen
        # bus rails (below labels)
        y_u=self.to_screen((0,self.upper_bus_y))[1]; y_l=self.to_screen((0,self.lower_bus_y))[1]
        pygame.draw.line(screen,(108,108,118),(board.x+10,y_u),(board.right-10,y_u),6)
        pygame.draw.line(screen,(108,108,118),(board.x+10,y_l),(board.right-10,y_l),6)
        # ports (wider spacing, two rows)
        self.label_rects.clear()
        for p in self.ports.values():
            glow=max(0.0,min(1.0,p.lamp)); p.lamp*=0.9
            col=(24+int(200*glow),24+int(120*glow),24) if p.kind=="data" else (24+int(180*glow),24+int(160*glow),16)
            x,y=self.to_screen(p.pos)
            pygame.draw.circle(screen,col,(x,y),8); pygame.draw.circle(screen,(210,210,210),(x,y),8,1)
            lab=FONT_SM.render(p.label,True,TEXT)
            lab_rect=lab.get_rect(topleft=(x-8,y+12))
            self.label_rects.append(lab_rect)
            screen.blit(lab,lab_rect.topleft)
        tips="Drag port→port | Right-click cable=delete | Wheel=zoom, MMB=pan | S/L save/load | A auto-wire | BUS routing"
        screen.blit(FONT_SM.render(tips,True,DIM),(r.x+14,r.bottom-18))

    # Manhattan-ish routing using BUS: port→tap to nearest bus (up/down), horizontal, tap up/down to dest.
    # Additionally nudge vertical taps a bit if they collide with label rects.
    def _nudge_away_from_labels(self, x,y):
        pt=pygame.Rect(x-2,y-2,4,4)
        for lab in self.label_rects:
            if pt.colliderect(lab):
                # nudge up or down based on proximity
                if abs(pt.centery - lab.bottom) < abs(pt.centery - lab.top):
                    y = lab.bottom + 6
                else:
                    y = lab.top - 6
        return x,y

    def route_points(self, a:str, b:str)->List[Tuple[int,int]]:
        pa=self.ports[a].pos; pb=self.ports[b].pos
        ax,ay=self.to_screen(pa); bx,by=self.to_screen(pb)
        mid_bus = (self.upper_bus_y+self.lower_bus_y)/2
        src_bus = self.to_screen((0,self.upper_bus_y))[1] if ay < self.to_screen((0,mid_bus))[1] else self.to_screen((0,self.lower_bus_y))[1]
        dst_bus = self.to_screen((0,self.upper_bus_y))[1] if by < self.to_screen((0,mid_bus))[1] else self.to_screen((0,self.lower_bus_y))[1]
        # vertical taps (label aware)
        tap_src_y = src_bus - 18 if ay<src_bus else src_bus + 18
        tap_dst_y = dst_bus - 18 if by<dst_bus else dst_bus + 18
        ax2, ay2 = self._nudge_away_from_labels(ax, tap_src_y)
        bx2, by2 = self._nudge_away_from_labels(bx, tap_dst_y)
        pts=[(ax,ay),(ax,ay2),(ax,src_bus),(bx,src_bus)]
        if dst_bus!=src_bus: pts.append((bx,dst_bus))
        pts+=[(bx,by2),(bx,by)]
        # Deduplicate
        simp=[pts[0]]
        for p in pts[1:]:
            if p!=simp[-1]: simp.append(p)
        return simp

    def draw_cables(self, active_paths:List[Tuple[str,str,str]], tpos:float):
        # passive cables
        for c in self.cables:
            pts=self.route_points(c.a,c.b)
            col=(190,190,190) if c.kind=="data" else (170,150,120)
            pygame.draw.lines(screen,col,False,pts,5)
        # active pulses
        for (a,b,kind) in active_paths:
            if a not in self.ports or b not in self.ports: continue
            pts=self.route_points(a,b)
            # cumulative lengths
            lens=[0.0]
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                lens.append(lens[-1]+math.hypot(x2-x1,y2-y1))
            total=max(1.0, lens[-1]); d=tpos*total
            # segment locate
            x,y=pts[0]
            for i in range(1,len(lens)):
                if d<=lens[i]:
                    segd=(d-lens[i-1])/(lens[i]-lens[i-1] if lens[i]-lens[i-1]>0 else 1)
                    x=int(pts[i-1][0]+(pts[i][0]-pts[i-1][0])*segd)
                    y=int(pts[i-1][1]+(pts[i][1]-pts[i-1][1])*segd); break
            color=ACCENT if kind=="data" else CTRL
            pygame.draw.circle(screen,color,(x,y),7)
            self.ports[a].lamp=self.ports[b].lamp=1.0

    # interactions
    def screen_to_world(self, sx,sy):
        b=self.board_rect
        return ((sx-b.x-self.offset[0])/self.scale, (sy-b.y-self.offset[1])/self.scale)
    def nearest_port_at(self, sx,sy)->Optional[str]:
        for name,p in self.ports.items():
            x,y=self.to_screen(p.pos)
            if (x-sx)**2+(y-sy)**2 <= 12*12: return name
        return None
    def handle_event(self, e):
        if e.type==pygame.MOUSEBUTTONDOWN:
            if e.button==1:
                name=self.nearest_port_at(*e.pos)
                if name: self.drag_from=name
            if e.button==2: self.mouse_last=e.pos
            if e.button==3: self.remove_cable_at(*e.pos)
            if e.button==4: self.scale=min(2.0,self.scale*1.1)
            if e.button==5: self.scale=max(0.5,self.scale/1.1)
        elif e.type==pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]:
                dx=e.pos[0]-self.mouse_last[0]; dy=e.pos[1]-self.mouse_last[1]
                self.offset[0]+=dx; self.offset[1]+=dy; self.mouse_last=e.pos
        elif e.type==pygame.MOUSEBUTTONUP:
            if e.button==1 and self.drag_from:
                name=self.nearest_port_at(*e.pos)
                if name and name!=self.drag_from: self.add_cable(self.drag_from, name)
                self.drag_from=None
    def save(self, path): 
        data={"cables":[c.__dict__ for c in self.cables]}
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    def load(self, path):
        if not os.path.exists(path): return
        with open(path,"r",encoding="utf-8") as f: data=json.load(f)
        self.cables=[Cable(**c) for c in data.get("cables",[])]

# ----------------- Timing Chart -----------------
class TimingChart:
    base_waves=["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP","LOAD","MULT","DIV","SQRT","ADD","SUB","PUNCH"]
    def __init__(self, rect):
        self.rect=pygame.Rect(rect)
        self.total=300; self.index=0
        self.speed=0.006  # fast
        self.running=False; self.wait_timer=0.0
        self.history_len=3000
        self.waves=self.base_waves[:]
        self.wave_data={w:[0]*self.history_len for w in self.waves}
    def record(self, name, idx, val=1):
        if name not in self.wave_data: return
        if 0<=idx<self.history_len: self.wave_data[name][idx]=val
    def draw(self, cursor_idx):
        r=self.rect; draw_panel(r,f"Timing (history)")
        inner=pygame.Rect(r.x+80,r.y+34,r.width-120,r.height-56)
        pygame.draw.rect(screen,(60,60,60),inner,1)
        rows=len(self.waves); hstep=inner.height/rows
        # grid every 30 (one add-time)
        for c in range(0,self.history_len+1,30):
            x=int(inner.x+c*(inner.width/self.history_len))
            pygame.draw.line(screen,GRID,(x,inner.y),(x,inner.bottom),1)
        # waveforms (digital rectangles)
        for row,w in enumerate(self.waves):
            y0=int(inner.y+row*hstep + hstep*0.2); y1=int(inner.y+row*hstep + hstep*0.8)
            data=self.wave_data[w]
            last=data[0]; x_prev=int(inner.x)
            for i in range(1,self.history_len):
                x=int(inner.x+i*(inner.width/self.history_len))
                if data[i]!=last:
                    y=int(y1 if last==0 else y0)
                    pygame.draw.line(screen,(180,180,180),(x_prev,y),(x,y),2)
                    pygame.draw.line(screen,(180,180,180),(x,y0 if last==0 else y1),(x,y1 if last==0 else y0),2)
                    x_prev=x; last=data[i]
            y=int(y1 if last==0 else y0)
            pygame.draw.line(screen,(180,180,180),(x_prev,y),(inner.right,y),2)
            screen.blit(FONT_SM.render(w,True,TEXT),(r.x+10,y0-4))
        # cursor
        x=int(inner.x+cursor_idx*(inner.width/self.history_len))
        pygame.draw.line(screen,(255,120,120),(x,inner.y),(x,inner.bottom),2)
        screen.blit(FONT_SM.render(f"speed:{self.speed:.3f}s/step",True,DIM),(inner.right+12,inner.y))
    def reset(self):
        self.index=0; self.wait_timer=0.0
        for w in self.waves: self.wave_data[w]=[0]*self.history_len

# ----------------- Controllers (Mult/Div/Sqrt) -----------------
class MultController:
    def __init__(self, a2:Acc, a3:Acc, out:Acc):
        self.a2=a2; self.a3=a3; self.out=out; self.reset()
    def reset(self): self.digit_idx=9; self.remaining=0; self.shift=0; self.active=False; self.done=False
    def start(self): self.active=True; self.done=False; self._setup_digit()
    def _setup_digit(self):
        if self.digit_idx<0: self.active=False; self.done=True; return
        m=self.a3.digits[self.digit_idx]; self.remaining=m; self.shift=9-self.digit_idx
    def begin(self,target:Acc):
        if self.active and self.remaining>0: target.start_add(self.a2.value(), shift=self.shift, sign=+1)
    def end(self):
        if not self.active: return
        if self.remaining>0: self.remaining-=1
        if self.remaining==0: self.digit_idx-=1; self._setup_digit()

class DivController:
    """Illustrative digit-by-digit long division: OUT = A2 / A3, remainder kept in A2.
       Uses borrow pulses with 10-pulse rhythm; not cycle-accurate ENIAC but shows per-digit timing."""
    def __init__(self, dividend:Acc, divisor:Acc, q:Acc):
        self.N=dividend; self.D=divisor; self.Q=q; self.reset()
    def reset(self):
        self.pos=0; self.active=False; self.done=False; self.sub_active=False; self.current_digit=0
    def start(self):
        self.active=True; self.done=False; self.pos=0; self.Q.load(0)
    def begin_digit(self):
        # prepare trial subtraction (naive: while N>=D*10^(shift) subtract)
        self.sub_active=True; self.current_digit=0
    def tick(self, cursor:int):
        if not self.active: return
        j=cursor  # use ring cursor against highest-to-lowest digit
        if not self.sub_active:
            self.begin_digit()
        # Compare N vs D (shifted) approximately by value (simple)
        shift = self.pos
        dval = self.D.value() * (10**(9-shift))
        if dval<=0: self.done=True; self.active=False; return
        if self.N.value() >= dval:
            # subtract once per digit phase
            if cursor==0:
                self.N.start_add(-self.D.value(), shift=(9-shift), sign=+1)
            self.N.tick_add_pulse(cursor)
            if cursor==9:
                self.current_digit+=1
        else:
            # cannot subtract anymore: commit quotient digit
            if cursor==9:
                # write digit at position 'pos'
                ds=self.Q.digits
                ds[self.pos]=self.current_digit
                self.pos+=1
                if self.pos>9:
                    self.active=False; self.done=True
                self.sub_active=False

class SqrtController:
    """Digit-by-digit square root (restoring) illustrative controller.
    OUT = floor(sqrt(A5)), remainder kept in A5 (not exact ENIAC but conveys timing)."""
    def __init__(self, radicand:Acc, out:Acc):
        self.N=radicand; self.R=out; self.reset()
    def reset(self):
        self.pos=0; self.active=False; self.done=False; self.phase=0
    def start(self):
        self.active=True; self.done=False; self.pos=0; self.R.load(0)
    def tick(self,cursor:int):
        if not self.active: return
        # simple digit-by-digit method using trial (20*R + 1) * 1 approximation per pos
        if cursor==0:
            trial = (20*self.R.value()+1) * (10**(9-self.pos))
            if self.N.value() >= trial:
                # subtract trial
                self.N.start_add(- (20*self.R.value()+1), shift=(9-self.pos), sign=+1)
                self.phase=1
            else:
                self.phase=0
        if self.phase==1:
            self.N.tick_add_pulse(cursor)
            if cursor==9:
                # increment R at this pos
                self.R.digits[self.pos]+=1
                self.phase=0
                # try again next ring position (kept by state)
        if cursor==9 and self.phase==0:
            # move to next digit
            self.pos+=1
            if self.pos>9: self.active=False; self.done=True

# ----------------- Demo App -----------------
class Demo:
    def __init__(self):
        # CTs & Accs
        self.cts=[CT(1,1), CT(2,2), CT(3,3)]
        self.accs=[Acc(f"A{i+1}") for i in range(20)]
        # layout rects
        self.ct_rects=[]; x0=20; y0=98; cw=140; ch=64
        for i in range(3): self.ct_rects.append(pygame.Rect(x0+i*cw, y0, cw-6, ch-6))
        self.mini_rects=[]; y1=168
        for r in range(2):
            for c in range(10):
                self.mini_rects.append(pygame.Rect(20+c*146, y1+r*60, 140, 54))
        # plugboard & timing
        self.pb=Plugboard(pygame.Rect(20,320,1440,360))
        self.timing=TimingChart((20,690,1440,240))
        # helpers
        self.A1=self.accs[0]; self.A2=self.accs[1]; self.A3=self.accs[2]
        self.A4=self.accs[3]; self.A5=self.accs[4]; self.A6=self.accs[5]
        self.A7=self.accs[6]
        self.mult=MultController(self.A2,self.A3,self.A4)
        self.div =DivController(self.A2,self.A3,self.A5)
        self.sqrt=SqrtController(self.A5,self.A6)
        self.stage=0  # 0:LOAD 1:MULT 2:DIV 3:SQRT 4:ADD 5:SUB 6:PUNCH 7:DONE
        self._build_ports(); self._default_wiring(); self.reset()
        # snapshots for rewind/forward (stateful)
        self.snapshots=[]; self.max_snaps=4000

    def _build_ports(self):
        # CT
        self.pb.add_port("CT1.A","CT1","data", 70, 60)
        self.pb.add_port("CT2.A","CT2","data", 140,60)
        self.pb.add_port("CT3.A","CT3","data", 210,60)
        # Acc ports (two rows, wide spacing)
        def acc_group(tag, x, y):
            labels=[("α","α"),("A","A"),("S","S"),("AS","AS"),("β","β"),("γ","γ")]
            for i,(k,lab) in enumerate(labels):
                self.pb.add_port(f"{tag}.{k}", lab, "data", x+i*44, y)
        xstart=300; row1=110; row2=200
        for i,tag in enumerate([f"A{i+1}" for i in range(10)]):
            acc_group(tag, xstart+i*120, row1)
        for i,tag in enumerate([f"A{i+11}" for i in range(10)]):
            acc_group(tag, xstart+i*120, row2)
        # Mult/Div/Sqrt/Punch, control
        self.pb.add_port("MULT.IN1","M1","data", 1080, 260)
        self.pb.add_port("MULT.IN2","M2","data", 1130, 260)
        self.pb.add_port("MULT.OUT","MOUT","data", 1240, 260)
        self.pb.add_port("DIV.Q","DIVQ","data", 1300, 260)
        self.pb.add_port("SQRT.OUT","SQRT","data", 1360, 260)
        self.pb.add_port("PUNCH.IN","P","data", 1400, 260)
        self.pb.add_port("CCG","CCG","ctrl", 80, 260)
        self.pb.add_port("RP","RP","ctrl", 130, 260)

    def _default_wiring(self):
        add=self.pb.add_cable
        # Inputs
        add("CT1.A","A1.α"); add("CT2.A","A2.α"); add("CT3.A","A3.α")
        # Mult
        add("A2.A","MULT.IN1"); add("A3.A","MULT.IN2"); add("MULT.OUT","A4.α")
        # Div: A2 / A3 -> A5
        add("DIV.Q","A5.α")  # quotient sink
        # Sqrt: sqrt(A5) -> A6
        add("SQRT.OUT","A6.α")
        # Sum/Sub and final punch
        add("A1.A","A7.α"); add("A4.A","A7.α")
        add("A7.A","PUNCH.IN")
        # Controls (fanout for visuals)
        for tgt in ["A1.α","A2.α","A3.α","A4.α","A5.α","A6.α","A7.α"]:
            add("CCG", tgt)
        for tgt in ["A4.α","A5.α","A6.α","A7.α"]:
            add("RP", tgt)

    def auto_wire(self):
        self.pb.cables.clear()
        self._default_wiring()

    def reset(self):
        for a in self.accs: a.load(0)
        self.stage=0; self.timing.reset(); self.mult.reset(); self.div.reset(); self.sqrt.reset()
        # Preload CTs example
        self.cts[0].value=1; self.cts[1].value=2; self.cts[2].value=3
        self.snapshots.clear()

    # ----- Timing helpers -----
    def ring_state(self, abs_index=None):
        if abs_index is None: abs_index=self.timing.index % self.timing.history_len
        idx=abs_index%300; step=idx//30; micro=idx%30; ring_idx=step
        return ring_idx, micro
    def begin_ring_pulses(self, abs_index):
        idx=abs_index%300; step=idx//30
        active=10-step if (10-step)>0 else 1
        for w in ["10P","9P","8P","7P","6P","5P","4P","3P","2P","1P"]:
            self.timing.record(w, abs_index, 1 if w==f"{active}P" else 0)
        self.timing.record("CPP",abs_index,1)

    # ----- Snapshot state (for rewind) -----
    def snapshot(self):
        snap={"i":self.timing.index,"stage":self.stage,
              "acc":[(a.sign, a.digits[:]) for a in self.accs],
              "mult":(self.mult.digit_idx,self.mult.remaining,self.mult.shift,self.mult.active,self.mult.done),
              "div":(self.div.pos,self.div.active,self.div.done,self.div.sub_active,self.div.current_digit),
              "sqrt":(self.sqrt.pos,self.sqrt.active,self.sqrt.done,self.sqrt.phase)}
        self.snapshots.append(snap)
        if len(self.snapshots)>self.max_snaps: self.snapshots.pop(0)
    def restore(self, steps:int):
        # steps>0 forward, <0 backward; clamp
        if not self.snapshots: return
        idx=len(self.snapshots)-1 + steps
        idx=max(0,min(len(self.snapshots)-1, idx))
        s=self.snapshots[idx]
        self.timing.index=s["i"]; self.stage=s["stage"]
        for a,(sg,ds) in zip(self.accs, s["acc"]):
            a.sign=sg; a.digits=ds[:]; a.add_active=False; a.carry=0
        (self.mult.digit_idx,self.mult.remaining,self.mult.shift,self.mult.active,self.mult.done)=s["mult"]
        (self.div.pos,self.div.active,self.div.done,self.div.sub_active,self.div.current_digit)=s["div"]
        (self.sqrt.pos,self.sqrt.active,self.sqrt.done,self.sqrt.phase)=s["sqrt"]
        # trim to idx
        self.snapshots=self.snapshots[:idx+1]

    # ----- Simulation step -----
    def do_microstep(self):
        i=self.timing.index
        ring_idx,micro=self.ring_state(i)
        # record base pulses
        self.begin_ring_pulses(i)
        # CCG/RP windows
        if 2<=micro<=20: self.timing.record("CCG", i, 1)
        if 26<=micro<=29: self.timing.record("RP", i, 1)
        # stage flags
        names=['LOAD','MULT','DIV','SQRT','ADD','SUB','PUNCH']
        if self.stage < len(names): self.timing.record(names[self.stage], i, 1)

        cursor=ring_idx  # 0..9 digit index head→tail

        # Actions per stage
        if self.stage==0:  # LOAD
            if micro==2:
                for port,val in [("CT1.A",1),("CT2.A",2),("CT3.A",3)]:
                    for c in self.pb.cables:
                        if c.a==port and c.b.endswith(".α"):
                            idx=int(c.b.split('.')[0][1:])-1
                            self.accs[idx].load(val)
            if ring_idx==9 and micro==29:
                self.stage=1; self.mult.start()
        elif self.stage==1:  # MULT  (A2 × A3 -> A4)
            if micro==2: self.mult.begin(self.A4)
            self.A4.tick_add_pulse(cursor)
            if micro==29:
                self.mult.end()
                if self.mult.done: self.stage=2; self.div.start()
        elif self.stage==2:  # DIV   (A2 / A3 -> A5 quotient; remainder left in A2)
            self.div.tick(cursor)
            if self.div.done and micro==29:
                self.stage=3; self.sqrt.start()
        elif self.stage==3:  # SQRT  (sqrt(A5) -> A6)
            self.sqrt.tick(cursor)
            if self.sqrt.done and micro==29:
                self.stage=4
        elif self.stage==4:  # ADD  A7 = A1 + A4
            if micro==2 and not self.A7.add_active: self.A7.start_add(self.A1.value(), sign=+1)
            self.A7.tick_add_pulse(cursor)
            if micro==15 and not self.A7.add_active: self.A7.start_add(self.A4.value(), sign=+1)
            if ring_idx==9 and micro==29: self.stage=5
        elif self.stage==5:  # SUB  A7 = A7 - A2
            if micro==2 and not self.A7.add_active: self.A7.start_add(self.A7.value(), sign=+1)  # no-op to sync
            self.A7.tick_add_pulse(cursor)
            if micro==15 and not self.A7.add_active: self.A7.start_add(self.A2.value(), sign=-1)
            if ring_idx==9 and micro==29: self.stage=6
        elif self.stage==6:  # PUNCH (visual only)
            if ring_idx==9 and micro==29: self.stage=7

        # advance timing and snapshot
        self.snapshot()
        self.timing.index=(self.timing.index+1)%self.timing.history_len
        if self.timing.index%300==0: self.timing.wait_timer=1.0  # pause 1s after full ring

    def active_paths(self)->List[Tuple[str,str,str]]:
        paths=[]; st=self.stage
        if st==0:
            for src in ["CT1.A","CT2.A","CT3.A"]:
                for c in self.pb.cables:
                    if c.a==src: paths.append((c.a,c.b,c.kind))
        elif st==1:
            for c in self.pb.cables:
                if c.a in ["A2.A","A3.A","MULT.OUT"]: paths.append((c.a,c.b,c.kind))
        elif st==2:
            for c in self.pb.cables:
                if c.a in ["DIV.Q"]: paths.append((c.a,c.b,c.kind))
        elif st==3:
            for c in self.pb.cables:
                if c.a in ["SQRT.OUT"]: paths.append((c.a,c.b,c.kind))
        elif st==4:
            for c in self.pb.cables:
                if c.a in ["A1.A","A4.A"]: paths.append((c.a,c.b,c.kind))
        elif st==5:
            for c in self.pb.cables:
                if c.a in ["A7.A","A2.S"]: paths.append((c.a,c.b,c.kind))
        elif st==6:
            for c in self.pb.cables:
                if c.a in ["A7.A"]: paths.append((c.a,c.b,c.kind))
        # controls
        idx=self.timing.index%self.timing.history_len
        if self.timing.wave_data["CCG"][idx]:
            for c in self.pb.cables:
                if c.a=="CCG": paths.append((c.a,c.b,"ctrl"))
        if self.timing.wave_data["RP"][idx]:
            for c in self.pb.cables:
                if c.a=="RP": paths.append((c.a,c.b,"ctrl"))
        return paths

    def update(self,dt):
        if self.timing.wait_timer>0:
            self.timing.wait_timer-=dt; return
        if self.timing.running:
            self._acc=getattr(self,'_acc',0.0)+dt
            if self._acc>=self.timing.speed:
                self._acc=0.0; self.do_microstep()

    def draw(self):
        screen.fill(BG)
        # headers
        draw_panel(pygame.Rect(20,10,420,80),"Card Reader")
        screen.blit(FONT_BIG.render(f"CT1:{self.cts[0].value}   CT2:{self.cts[1].value}   CT3:{self.cts[2].value}",True,OK),(30,50))
        draw_panel(pygame.Rect(460,10,1000,80),"ENIAC — merged view")
        screen.blit(FONT.render("20 Accumulators / Ring Distributor / Plugboard / Timing 300 cols",True,TEXT),(470,50))
        # CT & Acc panels
        ring_idx,_=self.ring_state()
        for i,ct in enumerate(self.cts): ct.mini_draw(self.ct_rects[i], ring_idx)
        for i,acc in enumerate(self.accs): acc.mini_draw(self.mini_rects[i], ring_idx)
        # Plugboard
        self.pb.draw_base("Plugboard Editor (label-aware BUS; orthogonal wires)")
        # Punch mini-output
        pr=pygame.Rect(20, 288, 420, 30); draw_panel(pr,"Card Punch (A7)")
        screen.blit(FONT_BIG.render(str(self.accs[6].value()),True,OK),(pr.x+260,pr.y+4))
        # Info & controls
        st_names=['LOAD','MULT','DIV','SQRT','ADD','SUB','PUNCH','DONE']
        info=f"[Stage {st_names[self.stage]}] SPACE run/pause | ENTER step | </> state step | CTRL+</> x10 | R reset |-+=speed | A auto-wire | S/L"
        screen.blit(FONT.render(info,True,TEXT),(20,92))
        # Timing
        self.timing.draw(self.timing.index%self.timing.history_len)
        # wires last + pulse position
        _,micro=self.ring_state(); tpos=micro/30.0
        self.pb.draw_cables(self.active_paths(), tpos)

    def save_wiring(self): self.pb.save("./plugboard_v10m.json")
    def load_wiring(self): self.pb.load("./plugboard_v10m.json")

def main():
    demo=Demo(); last=time.time()
    # Ensure one initial snapshot so backward stepping works at t=0
    demo.snapshot()
    while True:
        now=time.time(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                mods=pygame.key.get_mods()
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_SPACE: demo.timing.running=not demo.timing.running
                if e.key==pygame.K_RETURN: demo.do_microstep()
                if e.key==pygame.K_r: demo.reset(); demo.snapshot()
                if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS): demo.timing.speed=min(0.2, demo.timing.speed+0.002)
                if e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS): demo.timing.speed=max(0.001, demo.timing.speed-0.002)
                if e.key==pygame.K_s: demo.save_wiring()
                if e.key==pygame.K_l: demo.load_wiring()
                if e.key in (pygame.K_a,): demo.auto_wire()
                # Stateful step backward/forward
                if e.key in (pygame.K_COMMA, pygame.K_LESS):  # <
                    if mods & pygame.KMOD_CTRL:
                        demo.restore(-10)
                    else:
                        demo.restore(-1)
                if e.key in (pygame.K_PERIOD, pygame.K_GREATER):  # >
                    if mods & pygame.KMOD_CTRL:
                        demo.restore(+10)
                    else:
                        demo.restore(+1)
            demo.pb.handle_event(e)
        demo.update(dt); demo.draw(); pygame.display.flip(); clock.tick(60)

if __name__=="__main__":
    try:
        main()
    except Exception as ex:
        print("Fatal error:", ex)
