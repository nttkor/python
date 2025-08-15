
"""
ENIAC Demo — V7b
- Orthogonal wiring with port-clearance (elbows lift above/below before going sideways)
- Control lines CCG/RP appear as cables and animate when active
- Timing chart now shows the **entire computation** timeline (history), not one ring only.
  * 3000 columns (10 rings × 30 micro × 10 cycles window)
  * Digital rectangular pulses for 10P..1P, CPP, CCG, RP
  * Stage rows: LOAD/MULT/ADD/SUB/PUNCH (one-hot)
"""
import sys, time, math, json, os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import pygame
pygame.init()
W, H = 1700, 1020
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V7b")
clock = pygame.time.Clock()

BG=(50,52,56); PANEL=(78,80,84); EDGE=(36,36,36); TEXT=(235,235,235); DIM=(180,180,180)
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

class CT:
    def __init__(self, name:int, value:int):
        self.name=f"CT{name}"; self.value=value
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(70,72,76),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        screen.blit(FONT.render(str(self.value),True,OK),(rect.x+6,rect.y+22))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)

class Acc:
    def __init__(self, name):
        self.name=name; self.digits=[0]*10; self.sign='+'
        self.add_active=False; self.addend=[0]*10; self.add_sign=+1; self.carry=0
        self.carry_flash=0.0; self.carry_from=None
    def load(self,v:int): self.sign='-' if v<0 else '+'; self.digits=digits10(abs(v))
    def value(self)->int: v=from_digits(self.digits); return -v if self.sign=='-' else v
    def reset(self): self.load(0)
    def toggle_sign(self): self.sign='+' if self.sign=='-' else '-'
    def start_add(self,v:int,shift:int=0,sign:int=+1):
        ds=digits10(abs(v)); 
        if shift>0: ds = ds[:10-shift]+[0]*shift
        self.addend=ds; self.add_sign=+1 if sign>=0 else -1; self.carry=0; self.add_active=True
    def tick_add_pulse(self,cursor:int):
        if not self.add_active: return
        j=9-cursor; a=self.digits[j]; b=self.addend[j]*self.add_sign; s=a+b+self.carry; cout=0
        if s>=10: s-=10; cout=1
        elif s<0: s+=10; cout=-1
        self.digits[j]=s; self.carry=cout
        if cout!=0: self.carry_flash=0.3; self.carry_from=j
        if cursor==9: self.add_active=False; self.carry=0
    def mini_draw(self, rect, ring_idx):
        pygame.draw.rect(screen,(70,72,76),rect,border_radius=6); pygame.draw.rect(screen,EDGE,rect,1,border_radius=6)
        screen.blit(FONT_SM.render(self.name,True,TEXT),(rect.x+6,rect.y+4))
        s=self.sign+"".join(map(str,self.digits)); screen.blit(FONT.render(s,True,OK),(rect.x+6,rect.y+20))
        cy=rect.y+rect.height-12; cx=rect.x+8; sp=(rect.width-30)/9
        for i in range(10):
            x=int(cx+i*sp); on=(i==ring_idx)
            pygame.draw.circle(screen,(95,220,125) if on else (75,75,75),(x,cy),4); pygame.draw.circle(screen,EDGE,(x,cy),4,1)
        if self.carry_flash>0 and self.carry_from is not None:
            self.carry_flash-=0.05; i=self.carry_from; pygame.draw.circle(screen,CARRY,(rect.x+16+i*8,rect.y+16),3)

@dataclass
class Port:
    name:str; label:str; kind:str
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
    def add_port(self, name,label,kind,x,y): self.ports[name]=Port(name,label,kind,(x,y))
    def add_cable(self,a,b):
        if a not in self.ports or b not in self.ports: return
        self.cables.append(Cable(a,b,self.ports[a].kind))
    def remove_cable_at(self,mx,my):
        if not self.cables: return
        r=self.host_rect
        def to_scr(p): return (int(r.x+(p[0]*self.scale+self.offset[0])), int(r.y+(p[1]*self.scale+self.offset[1])))
        hit_idx=None; best=7.5
        for i,c in enumerate(self.cables):
            x1,y1=to_scr(self.ports[c.a].pos); x2,y2=to_scr(self.ports[c.b].pos)
            midx=(x1+x2)//2
            path=[(x1,y1-18),(midx,y1-18),(midx,y2+18),(x2,y2+18),(x2,y2)]
            # measure distance to polyline
            for (xa,ya),(xb,yb) in zip(path[:-1],path[1:]):
                vx,vy=xb-xa,yb-ya
                if vx==vy==0: continue
                t=max(0,min(1, ((mx-xa)*vx+(my-ya)*vy)/((vx*vx+vy*vy) or 1)))
                px,py=xa+t*vx, ya+t*vy
                d=math.hypot(px-mx,py-my)
                if d<best: best=d; hit_idx=i
        if hit_idx is not None: self.cables.pop(hit_idx)
    def draw_base(self, title):
        r=self.host_rect; draw_panel(r,title)
        board=pygame.Rect(r.x+8,r.y+36,r.width-16,r.height-44)
        pygame.draw.rect(screen,(64,66,70),board,border_radius=6); self.board_rect=board
        def to_screen(pt): return (int(board.x+(pt[0]*self.scale+self.offset[0])), int(board.y+(pt[1]*self.scale+self.offset[1])))
        self.to_screen=to_screen
        # ports
        for p in self.ports.values():
            glow=max(0.0,min(1.0,p.lamp)); p.lamp*=0.9
            col=(40,40,40); ring=(210,210,210)
            pygame.draw.circle(screen,col,self.to_screen(p.pos),7); pygame.draw.circle(screen,ring,self.to_screen(p.pos),7,1)
            screen.blit(FONT_SM.render(p.label,True,TEXT),(self.to_screen(p.pos)[0]-8,self.to_screen(p.pos)[1]+9))
        tips="Drag port→port | Right-click cable=delete | Wheel=zoom, MMB=pan | S/L save/load"
        screen.blit(FONT_SM.render(tips,True,DIM),(r.x+14,r.bottom-18))
    def draw_cables(self, active_paths:List[Tuple[str,str,str]], tpos:float):
        def s(pt): return self.to_screen(self.ports[pt].pos)
        for c in self.cables:
            ax,ay=s(c.a); bx,by=s(c.b); mid=(ax+bx)//2
            # elevate above ports then travel, then drop near target (no overlap across port row)
            path=[(ax,ay-18),(mid,ay-18),(mid,by+18),(bx,by+18),(bx,by)]
            base=(190,190,190) if c.kind=="data" else (170,150,120)
            for (x1,y1),(x2,y2) in zip(path[:-1],path[1:]):
                pygame.draw.line(screen,base,(x1,y1),(x2,y2),5)
        # Active pulse marker
        for (a,b,kind) in active_paths:
            if a not in self.ports or b not in self.ports: continue
            ax,ay=s(a); bx,by=s(b); mid=(ax+bx)//2
            segs=[((ax,ay-18),(mid,ay-18)),((mid,ay-18),(mid,by+18)),((mid,by+18),(bx,by+18)),((bx,by+18),(bx,by))]
            total=sum(math.hypot(x2-x1,y2-y1) for (x1,y1),(x2,y2) in segs)
            d=tpos*total; acc=0
            for (x1,y1),(x2,y2) in segs:
                L=math.hypot(x2-x1,y2-y1); 
                if d<=acc+L:
                    t=(d-acc)/L if L>0 else 0; x=int(x1+(x2-x1)*t); y=int(y1+(y2-y1)*t); break
                acc+=L
            color=ACCENT if kind=="data" else CTRL
            pygame.draw.circle(screen,color,(x,y),7)
            self.ports[a].lamp=self.ports[b].lamp=1.0
    def screen_to_world(self, sx,sy):
        b=self.board_rect; return ((sx-b.x-self.offset[0])/self.scale, (sy-b.y-self.offset[1])/self.scale)
    def nearest_port_at(self, sx,sy)->Optional[str]:
        for name,p in self.ports.items():
            x,y=self.to_screen(p.pos)
            if (x-sx)**2+(y-sy)**2 <= 10*10: return name
        return None
    def handle_event(self, e):
        if e.type==pygame.MOUSEBUTTONDOWN:
            if e.button==1: 
                name=self.nearest_port_at(*e.pos)
                if name: self.drag_from=name
            if e.button==2: self.mouse_last=e.pos
            if e.button==3: self.remove_cable_at(*e.pos)
            if e.button==4: self.scale=min(2.2,self.scale*1.1)
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
    """History timing: 3000 columns, draws digital rectangles"""
    base_waves=["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP","LOAD","MULT","ADD","SUB","PUNCH"]
    def __init__(self, rect):
        self.rect=pygame.Rect(rect); self.total=3000; self.index=0; self.speed=0.05; self.running=False
        self.wave_data={w:[0]*self.total for w in self.base_waves}
        self._seed_ring()
    def _seed_ring(self):
        # generate repeating ring for the entire buffer
        for i in range(self.total):
            step=(i//30)%10
            active=10-step
            for w in ["10P","9P","8P","7P","6P","5P","4P","3P","2P","1P"]:
                self.wave_data[w][i]=0
            name=f"{active}P"; self.wave_data[name][i]=1; self.wave_data["CPP"][i]=1
    def mark(self, wave:str, start:int, width:int):
        end=min(self.total,start+width)
        arr=self.wave_data[wave]
        for i in range(start,end): arr[i]=1
    def clear_dynamic(self):
        for w in ["CCG","RP","LOAD","MULT","ADD","SUB","PUNCH"]:
            self.wave_data[w]=[0]*self.total
    def draw(self, stage_label):
        r=self.rect; draw_panel(r,f"Timing — {stage_label} (history)")
        inner=pygame.Rect(r.x+80,r.y+34,r.width-120,r.height-56)
        pygame.draw.rect(screen,(60,60,60),inner,1)
        waves=list(self.base_waves)
        rows=len(waves); hstep=inner.height/rows
        # vertical markers every ring (30 cols)
        for c in range(0,self.total+1,30):
            x=int(inner.x+c*(inner.width/self.total)); pygame.draw.line(screen,(70,70,70),(x,inner.y),(x,inner.bottom),1)
        # draw each wave
        for row,w in enumerate(waves):
            y0=int(inner.y+row*hstep + hstep*0.2); y1=int(inner.y+row*hstep + hstep*0.8)
            data=self.wave_data[w]
            last=data[0]; x_prev=int(inner.x)
            for i in range(1,self.total):
                x=int(inner.x+i*(inner.width/self.total))
                if data[i]!=last:
                    y=int(y1 if last==0 else y0)
                    pygame.draw.line(screen,(180,180,180),(x_prev,y),(x,y),2)  # horizontal until transition
                    pygame.draw.line(screen,(180,180,180),(x,y0 if last==0 else y1),(x,y1 if last==0 else y0),2)  # vertical edge
                    x_prev=x; last=data[i]
            y=int(y1 if last==0 else y0)
            pygame.draw.line(screen,(180,180,180),(x_prev,y),(inner.right,y),2)
            screen.blit(FONT_SM.render(w,True,TEXT),(r.x+10,y0-4))
        # red cursor at current index
        x=int(inner.x+self.index*(inner.width/self.total)); pygame.draw.line(screen,(255,120,120),(x,inner.y),(x,inner.bottom),2)
        screen.blit(FONT_SM.render(f"speed:{self.speed:.2f}",True,DIM),(inner.right+12,inner.y))
    def step(self): self.index=min(self.total-1, self.index+1)
    def reset(self): self.index=0; self.clear_dynamic()

class MultController:
    def __init__(self, a2:Acc, a3:Acc, out:Acc): self.a2=a2; self.a3=a3; self.out=out; self.reset()
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
        self.cts=[CT(1,1), CT(2,2), CT(3,3)]
        self.accs=[Acc(f"A{i+1}") for i in range(20)]
        self.ct_rects=[]; x0=20; y0=110; cw=120; ch=64
        for i in range(3): self.ct_rects.append(pygame.Rect(x0+i*cw, y0, cw-6, ch-6))
        self.mini_rects=[]; y1=180
        for r in range(2):
            for c in range(10): self.mini_rects.append(pygame.Rect(20+c*160, y1+r*64, 154, 58))
        self.pb=Plugboard(pygame.Rect(20,360,1650,430))
        self.timing=TimingChart((20,800,1650,200))
        self.A1=self.accs[0]; self.A2=self.accs[1]; self.A3=self.accs[2]; self.A4=self.accs[3]; self.A5=self.accs[4]; self.A7=self.accs[6]
        self.mult=MultController(self.A2,self.A3,self.A4)
        self.stage=0; self.running=False; self._acc=0.0
        self._build_ports(); self._default_wiring(); self.reset()
    def _build_ports(self):
        self.pb.add_port("CT1.A","CT1","data", 60, 40)
        self.pb.add_port("CT2.A","CT2","data", 110,40)
        self.pb.add_port("CT3.A","CT3","data", 160,40)
        def acc_group(tag, x, y):
            for i,(k,lab) in enumerate([("α","α"),("A","A"),("S","S"),("AS","AS"),("β","β"),("γ","γ")]):
                self.pb.add_port(f"{tag}.{k}", lab, "data", x+i*28, y)
        xstart=240; row1=120; row2=160
        for i,tag in enumerate([f"A{i+1}" for i in range(10)]): acc_group(tag, xstart+i*130, row1)
        for i,tag in enumerate([f"A{i+11}" for i in range(10)]): acc_group(tag, xstart+i*130, row2)
        self.pb.add_port("MULT.IN1","M1","data", 1020, 210)
        self.pb.add_port("MULT.IN2","M2","data", 1060, 210)
        self.pb.add_port("MULT.OUT","MOUT","data", 1160, 210)
        self.pb.add_port("PUNCH.IN","P","data", 1500, 210)
        self.pb.add_port("CCG","CCG","ctrl", 60, 210)
        self.pb.add_port("RP","RP","ctrl", 100, 210)
    def _default_wiring(self):
        add=self.pb.add_cable
        # data
        add("CT1.A","A1.α"); add("CT2.A","A2.α"); add("CT3.A","A3.α")
        add("A2.A","MULT.IN1"); add("A3.A","MULT.IN2"); add("MULT.OUT","A4.α")
        add("A1.A","A5.α"); add("A4.A","A5.α")
        add("A5.A","A7.α"); add("A2.S","A7.α"); add("A7.A","PUNCH.IN")
        # control depiction (not enforced logic-wise, but visualized)
        for t in ["A1.α","A2.α","A3.α","A4.α","A5.α","A7.α"]: add("CCG", t)
        for t in ["A4.α","A5.α","A7.α"]: add("RP", t)
    def find_targets(self, source:str)->List[str]: return [c.b for c in self.pb.cables if c.a==source]
    def reset(self):
        for a in self.accs: a.load(0)
        self.stage=0; self.mult.reset(); self.timing.reset()
    def ring_state(self):
        idx=self.timing.index; step=(idx//30)%10; micro=idx%30; return step, micro
    def mark_stage_wave(self, name:str, width:int=30):
        self.timing.mark(name, self.timing.index, width)
    def do_microstep(self):
        ring_idx, micro = self.ring_state()
        # mark stage name for history (one full ring per stage marker repetition)
        if micro==0:
            stage_name=['LOAD','MULT','ADD','SUB','PUNCH','PUNCH'][self.stage]
            self.mark_stage_wave(stage_name, width=30)
        # CCG/RP windows
        if micro==2: self.timing.mark("CCG", self.timing.index, 18)
        if micro==26: self.timing.mark("RP", self.timing.index, 4)
        # operations
        cursor=ring_idx
        if self.stage==0:  # LOAD
            if micro==2:
                for port,val in [("CT1.A",1),("CT2.A",2),("CT3.A",3)]:
                    for tgt in self.find_targets(port):
                        if tgt.endswith(".α"):
                            idx=int(tgt.split('.')[0][1:])-1; self.accs[idx].load(val)
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
        elif self.stage==4:  # PUNCH (visual hold)
            if ring_idx==9 and micro==29: self.stage=5
        self.timing.step()
    def active_paths(self)->List[Tuple[str,str,str]]:
        paths=[]; st=self.stage
        if st==0:
            for src in ["CT1.A","CT2.A","CT3.A"]:
                for tgt in self.find_targets(src): paths.append((src,tgt,"data"))
        elif st==1:
            for tgt in self.find_targets("A2.A"): paths.append(("A2.A",tgt,"data"))
            for tgt in self.find_targets("A3.A"): paths.append(("A3.A",tgt,"data"))
            for tgt in self.find_targets("MULT.OUT"): paths.append(("MULT.OUT",tgt,"data"))
        elif st==2:
            for tgt in self.find_targets("A1.A"): paths.append(("A1.A",tgt,"data"))
            for tgt in self.find_targets("A4.A"): paths.append(("A4.A",tgt,"data"))
        elif st==3:
            for tgt in self.find_targets("A5.A"): paths.append(("A5.A",tgt,"data"))
            for tgt in self.find_targets("A2.S"): paths.append(("A2.S",tgt,"data"))
        elif st==4:
            for tgt in self.find_targets("A7.A"): paths.append(("A7.A",tgt,"data"))
        # control: if high at this index, animate from CCG/RP to connected
        if self.timing.wave_data["CCG"][self.timing.index]:
            for tgt in self.find_targets("CCG"): paths.append(("CCG",tgt,"ctrl"))
        if self.timing.wave_data["RP"][self.timing.index]:
            for tgt in self.find_targets("RP"): paths.append(("RP",tgt,"ctrl"))
        return paths
    def update(self,dt):
        if self.running:
            self._acc+=dt
            if self._acc>=self.timing.speed: self._acc=0; self.do_microstep()
    def draw(self):
        screen.fill(BG)
        draw_panel(pygame.Rect(20,20,380,80),"Card Reader")
        screen.blit(FONT_BIG.render("CT1:1   CT2:2   CT3:3",True,OK),(30,60))
        draw_panel(pygame.Rect(420,20,1260,80),"ENIAC — compact view")
        screen.blit(FONT.render("20 Accumulators / Ring Distributor / Plugboard Editor",True,TEXT),(430,60))
        ring_idx,_=self.ring_state()
        for i,ct in enumerate(self.cts): ct.mini_draw(self.ct_rects[i], ring_idx)
        for i,acc in enumerate(self.accs): acc.mini_draw(self.mini_rects[i], ring_idx)
        self.pb.draw_base("Plugboard Editor (orthogonal wires, cleared over ports)")
        pr=pygame.Rect(20, 310, 380, 40); draw_panel(pr,"Card Punch"); screen.blit(FONT_BIG.render(str(self.accs[6].value()),True,OK),(pr.x+220,pr.y+8))
        st_names=['LOAD','MULT','ADD','SUB','PUNCH','DONE']
        info=f"[Stage {st_names[self.stage]}] ENTER=step SPACE=run R=reset +/-=speed S/L=save/load | Cables:{len(self.pb.cables)}"
        screen.blit(FONT.render(info,True,TEXT),(20,100))
        self.timing.draw(st_names[self.stage])
        _,micro=self.ring_state(); tpos=micro/30.0
        self.pb.draw_cables(self.active_paths(), tpos)
    def save_wiring(self): self.pb.save("/mnt/data/plugboard_v7b.json")
    def load_wiring(self): self.pb.load("/mnt/data/plugboard_v7b.json")

def main():
    demo=Demo(); last=time.time()
    while True:
        now=time.time(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_RETURN: demo.do_microstep()
                if e.key==pygame.K_SPACE: demo.running=not demo.running
                if e.key==pygame.K_r: demo.reset()
                if e.key==pygame.K_MINUS or e.key==pygame.K_KP_MINUS: demo.timing.speed=min(0.6, demo.timing.speed+0.01)
                if e.key==pygame.K_EQUALS or e.key==pygame.K_PLUS or e.key==pygame.K_KP_PLUS: demo.timing.speed=max(0.01, demo.timing.speed-0.01)
                if e.key==pygame.K_s: demo.save_wiring()
                if e.key==pygame.K_l: demo.load_wiring()
            demo.pb.handle_event(e)
        demo.update(dt); demo.draw(); pygame.display.flip(); clock.tick(60)

if __name__=="__main__":
    main()
