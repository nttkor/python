
"""
ENIAC Demo — V7c (Full)
- Digital timing chart: 300 columns (10 ring steps × 30 micro-steps).
- Orthogonal BUS routing: port→vertical tap→BUS→vertical tap→port (no occlusion).
- Ports spaced 2× wider; two rows (A1..A10 / A11..A20).
- Wires drawn last; pulses travel along BUS so source→dest가 명확.
- CT1/2/3 mini-panels; 20 Acc mini-panels.
- Stage logic: LOAD → MULT → ADD → SUB → PUNCH (same as earlier demos).
Controls
  SPACE : run/pause
  ENTER : advance simulation by one micro-step (stateful)
  < , > : timeline scrub backward/forward (visual only; state는 변하지 않음)
  CTRL+< / CTRL+> : 10-펄스 직렬 전송(시프트 레지스터) 애니메이션(visual)
  R : reset
  - / + : slower / faster
  S / L : save / load wiring (JSON at /mnt/data/plugboard_v7c.json)
Notes
  * Simulation speed: default ~10× faster. 1 ring (300 micro-steps) 끝나면 1초 대기.
  * Backward scrub은 값 변경 없이 파형/케이블만 표시. 실제 상태를 되감는 기능은 포함하지 않음.
"""
import sys, time, math, json, os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import pygame
pygame.init()
W, H = 1680, 1020
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V7c")
clock = pygame.time.Clock()

# --- theme ---
BG=(48,50,54); PANEL=(75,78,82); EDGE=(32,32,32); TEXT=(236,236,236); DIM=(175,175,175)
OK=(120,235,150); ACCENT=(125,220,255); CTRL=(255,200,110); CARRY=(255,110,110)
FONT=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",16)
FONT_SM=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",12)
FONT_BIG=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",20,bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, EDGE, rect, 1, border_radius=8)
    if title: screen.blit(FONT_BIG.render(title, True, TEXT),(rect.x+10,rect.y+8))

def digits10(n:int): return [int(ch) for ch in f"{abs(n):010d}"]
def from_digits(ds): return int("".join(map(str, ds)))

# --- CT (Card Reader Track) ---
class CT:
    def __init__(self, name:int, value:int):
        self.name=f"CT{name}"; self.value=value
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(70,72,76),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        s=str(self.value); screen.blit(FONT.render(s,True,OK),(rect.x+6,rect.y+22))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)

# --- Accumulator (simplified) ---
class Acc:
    def __init__(self, name):
        self.name=name; self.digits=[0]*10; self.sign='+'
        self.add_active=False; self.addend=[0]*10; self.add_sign=+1; self.carry=0
        self.carry_flash=0.0; self.carry_from=None
    def load(self,v:int):
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
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(70,72,76),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        s=self.sign+"".join(map(str,self.digits)); screen.blit(FONT.render(s,True,OK),(rect.x+6,rect.y+20))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)
        if self.carry_flash>0 and self.carry_from is not None:
            self.carry_flash-=0.05; i=self.carry_from
            xm=int(rect.x+12+i*8); pygame.draw.circle(screen,CARRY,(xm,rect.y+16),3)

@dataclass
class Port:
    name:str; label:str; kind:str # "data" or "ctrl"
    pos:Tuple[float,float] # local coords in board space
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
        self.upper_bus_y=120; self.lower_bus_y=210  # bus rails (board space)
    def add_port(self, name,label,kind,x,y): self.ports[name]=Port(name,label,kind,(x,y))
    def add_cable(self,a,b):
        if a in self.ports and b in self.ports:
            kind=self.ports[a].kind; self.cables.append(Cable(a,b,kind))
    def remove_cable_at(self, mx,my):
        if not self.cables: return
        hit_idx=None; best=9
        for i,c in enumerate(self.cables):
            pts=self.route_points(c.a,c.b)
            # check distance to polyline
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
        # draw bus rails
        y_u=self.to_screen((0,self.upper_bus_y))[1]; y_l=self.to_screen((0,self.lower_bus_y))[1]
        pygame.draw.line(screen,(110,110,120),(board.x+10,y_u),(board.right-10,y_u),6)
        pygame.draw.line(screen,(110,110,120),(board.x+10,y_l),(board.right-10,y_l),6)
        # draw ports (no cables yet)
        for p in self.ports.values():
            glow=max(0.0,min(1.0,p.lamp)); p.lamp*=0.9
            col=(24+int(200*glow),24+int(120*glow),24) if p.kind=="data" else (24+int(180*glow),24+int(160*glow),16)
            x,y=self.to_screen(p.pos)
            pygame.draw.circle(screen,col,(x,y),8); pygame.draw.circle(screen,(210,210,210),(x,y),8,1)
            lab=FONT_SM.render(p.label,True,TEXT); screen.blit(lab,(x-8,y+12))
        tips="Drag port→port | Right-click cable=delete | Wheel=zoom, MMB=pan | S/L save/load | BUS routing visible"
        screen.blit(FONT_SM.render(tips,True,DIM),(r.x+14,r.bottom-18))
    # --- Routing via BUS: port→tap to bus (up/down 18px), run horizontally, then tap to dest
    def route_points(self, a:str, b:str)->List[Tuple[int,int]]:
        pa=self.ports[a].pos; pb=self.ports[b].pos
        ax,ay=self.to_screen(pa); bx,by=self.to_screen(pb)
        # choose upper or lower bus based on source row (ports near to top row use upper bus, else lower)
        src_bus = self.to_screen((0,self.upper_bus_y))[1] if ay < self.to_screen((0,(self.upper_bus_y+self.lower_bus_y)/2))[1] else self.to_screen((0,self.lower_bus_y))[1]
        dst_bus = self.to_screen((0,self.upper_bus_y))[1] if by < self.to_screen((0,(self.upper_bus_y+self.lower_bus_y)/2))[1] else self.to_screen((0,self.lower_bus_y))[1]
        # build polyline
        pts=[(ax,ay),(ax,src_bus-18 if ay<src_bus else src_bus+18),(ax,src_bus),(bx,src_bus)]
        if dst_bus!=src_bus:
            # hop to other bus at destination x (vertical segment on right)
            pts+=[(bx,dst_bus)]
        pts+=[(bx,dst_bus-18 if by<dst_bus else dst_bus+18),(bx,by)]
        # simplify consecutive duplicates
        simp=[pts[0]]
        for p in pts[1:]:
            if p!=simp[-1]: simp.append(p)
        return simp
    def draw_cables(self, active_paths:List[Tuple[str,str,str]], tpos:float):
        # draw all cables routed over bus, last
        for c in self.cables:
            pts=self.route_points(c.a,c.b)
            col=(190,190,190) if c.kind=="data" else (170,150,120)
            pygame.draw.lines(screen,col,False,pts,5)
        # active pulses animate along the polyline
        for (a,b,kind) in active_paths:
            if a not in self.ports or b not in self.ports: continue
            pts=self.route_points(a,b)
            # compute cumulative lengths
            lens=[0.0]
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                lens.append(lens[-1]+math.hypot(x2-x1,y2-y1))
            total=lens[-1]; d=tpos*total
            # find segment
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

class TimingChart:
    """Digital rectangular pulses; 300 columns (10 ring × 30 micro) + history buffer to draw full calc."""
    base_waves=["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP","LOAD","MULT","ADD","SUB","PUNCH"]
    def __init__(self, rect):
        self.rect=pygame.Rect(rect)
        self.total=300; self.index=0
        self.speed=0.006  # fast (~10×)
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
        # draw grid every 30 (one add-time)
        for c in range(0,self.history_len+1,30):
            x=int(inner.x+c*(inner.width/self.history_len))
            pygame.draw.line(screen,(70,70,70),(x,inner.y),(x,inner.bottom),1)
        # waveforms
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

# --- Mult controller ---
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

class Demo:
    def __init__(self):
        # CTs & Accs
        self.cts=[CT(1,1), CT(2,2), CT(3,3)]
        self.accs=[Acc(f"A{i+1}") for i in range(20)]
        # layout rects
        self.ct_rects=[]; x0=20; y0=110; cw=140; ch=66
        for i in range(3): self.ct_rects.append(pygame.Rect(x0+i*cw, y0, cw-6, ch-6))
        self.mini_rects=[]; y1=190
        for r in range(2):
            for c in range(10):
                self.mini_rects.append(pygame.Rect(20+c*164, y1+r*66, 158, 60))
        # boards
        self.pb=Plugboard(pygame.Rect(20,360,1640,440))
        self.timing=TimingChart((20,820,1640,190))
        # helpers
        self.A1=self.accs[0]; self.A2=self.accs[1]; self.A3=self.accs[2]
        self.A4=self.accs[3]; self.A5=self.accs[4]; self.A7=self.accs[6]
        self.mult=MultController(self.A2,self.A3,self.A4)
        self.stage=0; self.running=False; self._acc=0.0
        self.shift_anim=0  # for Ctrl+<> visual 10-pulse animation
        self._build_ports(); self._default_wiring(); self.reset()
    def _build_ports(self):
        # Top CT ports
        self.pb.add_port("CT1.A","CT1","data", 70, 60)
        self.pb.add_port("CT2.A","CT2","data", 140,60)
        self.pb.add_port("CT3.A","CT3","data", 210,60)
        # Two rows of Acc ports (2× spacing)
        def acc_group(tag, x, y):
            labels=[("α","α"),("A","A"),("S","S"),("AS","AS"),("β","β"),("γ","γ")]
            for i,(k,lab) in enumerate(labels):
                self.pb.add_port(f"{tag}.{k}", lab, "data", x+i*42, y)
        xstart=300; row1=110; row2=190
        for i,tag in enumerate([f"A{i+1}" for i in range(10)]):
            acc_group(tag, xstart+i*130, row1)
        for i,tag in enumerate([f"A{i+11}" for i in range(10)]):
            acc_group(tag, xstart+i*130, row2)
        # Mult, Punch, control
        self.pb.add_port("MULT.IN1","M1","data", 1160, 250)
        self.pb.add_port("MULT.IN2","M2","data", 1210, 250)
        self.pb.add_port("MULT.OUT","MOUT","data", 1320, 250)
        self.pb.add_port("PUNCH.IN","P","data", 1560, 250)
        self.pb.add_port("CCG","CCG","ctrl", 80, 250)
        self.pb.add_port("RP","RP","ctrl", 130, 250)
    def _default_wiring(self):
        add=self.pb.add_cable
        add("CT1.A","A1.α"); add("CT2.A","A2.α"); add("CT3.A","A3.α")
        add("A2.A","MULT.IN1"); add("A3.A","MULT.IN2"); add("MULT.OUT","A4.α")
        add("A1.A","A5.α"); add("A4.A","A5.α")
        add("A5.A","A7.α"); add("A2.S","A7.α")
        add("A7.A","PUNCH.IN")
        # control visibility: fanout CCG/RP to a few alphas
        add("CCG","A1.α"); add("CCG","A2.α"); add("CCG","A3.α"); add("CCG","A4.α"); add("CCG","A5.α")
        add("RP","A4.α"); add("RP","A5.α"); add("RP","A7.α")
    def reset(self):
        for a in self.accs: a.load(0)
        self.stage=0; self.timing.reset(); self.mult.reset()
    # mapping timing index to ring/micro
    def ring_state(self, abs_index=None):
        if abs_index is None: abs_index=self.timing.index % self.timing.history_len
        idx=abs_index%300; step=idx//30; micro=idx%30; ring_idx=step
        return ring_idx, micro
    def begin_ring_pulses(self, abs_index):
        # fill standard pulses for this index into history
        idx=abs_index%300; step=idx//30
        active=10-step if (10-step)>0 else 1
        for w in ["10P","9P","8P","7P","6P","5P","4P","3P","2P","1P"]:
            self.timing.record(w, abs_index, 1 if w==f"{active}P" else 0)
        self.timing.record("CPP",abs_index,1)
    def do_microstep(self):
        i=self.timing.index
        ring_idx,micro=self.ring_state(i)
        # record ring base pulses
        self.begin_ring_pulses(i)
        # CCG/RP windows
        if 2<=micro<=20: self.timing.record("CCG", i, 1)
        if 26<=micro<=29: self.timing.record("RP", i, 1)
        # stage flags
        stage_names=['LOAD','MULT','ADD','SUB','PUNCH']
        if self.stage<5: self.timing.record(stage_names[self.stage], i, 1)
        # actions
        cursor=ring_idx
        if self.stage==0:  # LOAD
            if micro==2:
                for port,val in [("CT1.A",1),("CT2.A",2),("CT3.A",3)]:
                    for c in self.pb.cables:
                        if c.a==port and c.b.endswith(".α"):
                            idx=int(c.b.split('.')[0][1:])-1
                            self.accs[idx].load(val)
            if ring_idx==9 and micro==29: self.stage=1; self.mult.start()
        elif self.stage==1:  # MULT
            if micro==2: self.mult.begin(self.A4)
            self.A4.tick_add_pulse(cursor)
            if micro==29:
                self.mult.end()
                if self.mult.done: self.stage=2
        elif self.stage==2:  # ADD
            if micro==2 and not self.A5.add_active: self.A5.start_add(self.A1.value(), sign=+1)
            self.A5.tick_add_pulse(cursor)
            if micro==15 and not self.A5.add_active: self.A5.start_add(self.A4.value(), sign=+1)
            if ring_idx==9 and micro==29: self.stage=3
        elif self.stage==3:  # SUB
            if micro==2 and not self.A7.add_active: self.A7.start_add(self.A5.value(), sign=+1)
            self.A7.tick_add_pulse(cursor)
            if micro==15 and not self.A7.add_active: self.A7.start_add(self.A2.value(), sign=-1)
            if ring_idx==9 and micro==29: self.stage=4
        elif self.stage==4:  # PUNCH
            if ring_idx==9 and micro==29: self.stage=5
        # advance timing with ring pause
        self.timing.index=(self.timing.index+1)%self.timing.history_len
        if self.timing.index%300==0: self.timing.wait_timer=1.0  # 1s pause
    def active_paths(self)->List[Tuple[str,str,str]]:
        paths=[]; ring_idx,_=self.ring_state()
        st=self.stage
        if st==0:
            for src in ["CT1.A","CT2.A","CT3.A"]:
                for c in self.pb.cables:
                    if c.a==src: paths.append((c.a,c.b,c.kind))
        elif st==1:
            for c in self.pb.cables:
                if c.a in ["A2.A","A3.A","MULT.OUT"]: paths.append((c.a,c.b,c.kind))
        elif st==2:
            for c in self.pb.cables:
                if c.a in ["A1.A","A4.A"]: paths.append((c.a,c.b,c.kind))
        elif st==3:
            for c in self.pb.cables:
                if c.a in ["A5.A","A2.S"]: paths.append((c.a,c.b,c.kind))
        elif st==4:
            for c in self.pb.cables:
                if c.a in ["A7.A"]: paths.append((c.a,c.b,c.kind))
        # control highlights follow CCG/RP bits
        idx=self.timing.index%self.timing.history_len
        if self.timing.wave_data["CCG"][idx]:
            for c in self.pb.cables:
                if c.a=="CCG": paths.append((c.a,c.b,"ctrl"))
        if self.timing.wave_data["RP"][idx]:
            for c in self.pb.cables:
                if c.a=="RP": paths.append((c.a,c.b,"ctrl"))
        return paths
    def update(self,dt):
        # run burst animation of 10 pulses (visual only)
        if self.shift_anim>0:
            self._anim_acc=getattr(self,'_anim_acc',0.0)+dt
            if self._anim_acc>=self.timing.speed*0.5:
                self._anim_acc=0.0; self.timing.index=(self.timing.index+1)%self.timing.history_len
                self.shift_anim-=1
            return
        # pause after ring
        if self.timing.wait_timer>0:
            self.timing.wait_timer-=dt; return
        if self.timing.running:
            self._acc+=dt
            if self._acc>=self.timing.speed:
                self._acc=0; self.do_microstep()
    def draw(self):
        screen.fill(BG)
        # headers
        draw_panel(pygame.Rect(20,20,420,80),"Card Reader")
        screen.blit(FONT_BIG.render("CT1:1   CT2:2   CT3:3",True,OK),(30,60))
        draw_panel(pygame.Rect(460,20,1200,80),"ENIAC — compact view")
        screen.blit(FONT.render("20 Accumulators / Ring Distributor / Plugboard Editor",True,TEXT),(470,60))
        # CT & Acc panels
        ring_idx,_=self.ring_state()
        for i,ct in enumerate(self.cts): ct.mini_draw(self.ct_rects[i], ring_idx)
        for i,acc in enumerate(self.accs): acc.mini_draw(self.mini_rects[i], ring_idx)
        # Plugboard (ports & buses first)
        self.pb.draw_base("Plugboard Editor (orthogonal wires via BUS)")
        # Punch panel
        pr=pygame.Rect(20, 318, 420, 40); draw_panel(pr,"Card Punch")
        screen.blit(FONT_BIG.render(str(self.accs[6].value()),True,OK),(pr.x+260,pr.y+8))
        # Info
        st_names=['LOAD','MULT','ADD','SUB','PUNCH','DONE']
        info=f"[Stage {st_names[self.stage]}] SPACE=run/pause ENTER=step R=reset </>=scrub CTRL+</>=shift x10 -/+=speed | Cables:{len(self.pb.cables)}"
        screen.blit(FONT.render(info,True,TEXT),(20,100))
        # Timing
        self.timing.draw(self.timing.index%self.timing.history_len)
        # wires last + pulse position within micro-step
        _,micro=self.ring_state(); tpos=micro/30.0
        self.pb.draw_cables(self.active_paths(), tpos)
    def save_wiring(self): self.pb.save("/mnt/data/plugboard_v7c.json")
    def load_wiring(self): self.pb.load("/mnt/data/plugboard_v7c.json")

def main():
    demo=Demo(); last=time.time()
    while True:
        now=time.time(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                mods=pygame.key.get_mods()
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_SPACE: demo.timing.running=not demo.timing.running
                if e.key==pygame.K_RETURN: demo.do_microstep()
                if e.key==pygame.K_r: demo.reset()
                if e.key==pygame.K_MINUS or e.key==pygame.K_KP_MINUS: demo.timing.speed=min(0.2, demo.timing.speed+0.002)
                if e.key==pygame.K_EQUALS or e.key==pygame.K_PLUS or e.key==pygame.K_KP_PLUS: demo.timing.speed=max(0.001, demo.timing.speed-0.002)
                if e.key==pygame.K_s: demo.save_wiring()
                if e.key==pygame.K_l: demo.load_wiring()
                # Scrub & shift animation
                if e.key in (pygame.K_COMMA, pygame.K_LESS):  # <
                    if mods & pygame.KMOD_CTRL:
                        demo.shift_anim=10  # visual burst of 10 pulses
                    else:
                        demo.timing.index=(demo.timing.index-1) % demo.timing.history_len
                if e.key in (pygame.K_PERIOD, pygame.K_GREATER):  # >
                    if mods & pygame.KMOD_CTRL:
                        demo.shift_anim=10
                    else:
                        demo.timing.index=(demo.timing.index+1) % demo.timing.history_len
            demo.pb.handle_event(e)
        demo.update(dt); demo.draw(); pygame.display.flip(); clock.tick(60)

if __name__=="__main__":
    main()
