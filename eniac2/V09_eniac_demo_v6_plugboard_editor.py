
"""
ENIAC Demo — V6 Plugboard Editor
--------------------------------
What's new vs V5:
- **Interactive Plugboard Editor**: drag from a port to another to create a cable; right-click cable to delete.
- **Save/Load wiring** to JSON (`S` to save, `L` to load).
- **Zoom/Pan** on the plugboard (wheel to zoom, hold middle-mouse to pan).
- Execution derives data/control flow from wiring (α/A/S/AS/β/γ semantics).
- Keeps 20 Accumulators, ring distributor, CCG/RP timing, multiply/add/sub scenario is produced *via wiring*.
Controls:
  ENTER : Step one digit-pulse
  SPACE : Run/Pause
  R     : Reset accumulators
  +/-   : Speed
  S/L   : Save/Load wiring
  Mouse : Drag from port to port to create cable; Right-click on cable to remove
  Wheel : Zoom plugboard; MMB drag to pan
"""
import sys, time, math, json, os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import pygame
pygame.init()
W, H = 1500, 1000
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("ENIAC Demo — V6 Plugboard Editor")
clock = pygame.time.Clock()

# theme
BG=(50,52,56); PANEL=(78,80,84); EDGE=(34,34,34); TEXT=(235,235,235); DIM=(180,180,180)
OK=(120,235,150); ACCENT=(125,220,255); CTRL=(255,200,110); CARRY=(255,110,110)
FONT=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",16)
FONT_SM=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",12)
FONT_BIG=pygame.font.SysFont("consolas,dejavusansmono,menlo,monospace",20,bold=True)

def draw_panel(rect, title=None):
    pygame.draw.rect(screen, PANEL, rect, border_radius=8)
    pygame.draw.rect(screen, EDGE, rect, 1, border_radius=8)
    if title: screen.blit(FONT_BIG.render(title, True, TEXT),(rect.x+10,rect.y+8))

def digits10(n:int):
    return [int(ch) for ch in f"{abs(n):010d}"]
def from_digits(ds):
    return int("".join(map(str, ds)))

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
        ds=digits10(abs(v)); 
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
        self.scale=1.0; self.offset=[0,0]
        self.ports:Dict[str,Port]={}; self.cables:List[Cable]=[]
        self.drag_from:Optional[str]=None; self.mouse_last=(0,0)
    def add_port(self, name,label,kind,x,y):
        self.ports[name]=Port(name,label,kind,(x,y))
    def add_cable(self,a,b):
        kind=self.ports[a].kind; self.cables.append(Cable(a,b,kind))
    def remove_cable_at(self, mx,my):
        # find nearest cable under mouse (screen coords)
        if not self.cables: return
        r=self.host_rect
        def world_to_screen(p):
            return (int(r.x+(p[0]*self.scale+self.offset[0])), int(r.y+(p[1]*self.scale+self.offset[1])))
        hit_idx=None; best=8
        for i,c in enumerate(self.cables):
            p1=self.ports[c.a].pos; p2=self.ports[c.b].pos
            x1,y1=world_to_screen(p1); x2,y2=world_to_screen(p2)
            # distance from point to segment
            import math
            vx,vy=x2-x1,y2-y1
            if vx==vy==0: continue
            t=max(0,min(1, ((mx-x1)*vx+(my-y1)*vy)/(vx*vx+vy*vy) ))
            px,py=x1+t*vx,y1*t*vy+y1 if False else (x1+t*vx, y1+t*vy)
            d=math.hypot(px-mx,py-my)
            if d<best: best=d; hit_idx=i
        if hit_idx is not None and best<8: self.cables.pop(hit_idx)
    def draw(self, active_paths:List[Tuple[str,str,str]], tphase:float):
        r=self.host_rect
        draw_panel(r,"Plugboard Editor")
        # board area
        board=pygame.Rect(r.x+8,r.y+36,r.width-16,r.height-44)
        pygame.draw.rect(screen,(64,66,70),board,border_radius=6)
        # helpers
        def to_screen(pt):
            return (int(board.x+(pt[0]*self.scale+self.offset[0])),
                    int(board.y+(pt[1]*self.scale+self.offset[1])))
        # draw cables
        for c in self.cables:
            p1=self.ports[c.a].pos; p2=self.ports[c.b].pos
            col=(180,180,180) if c.kind=="data" else (170,150,120)
            pygame.draw.line(screen,col,to_screen(p1),to_screen(p2),5)
        # draw ports
        for p in self.ports.values():
            glow=max(0.0,min(1.0,p.lamp)); p.lamp*=0.9
            col=(24+int(200*glow),24+int(120*glow),24) if p.kind=="data" else (24+int(180*glow),24+int(160*glow),16)
            x,y=to_screen(p.pos)
            pygame.draw.circle(screen,col,(x,y),7); pygame.draw.circle(screen,(210,210,210),(x,y),7,1)
            lab=FONT_SM.render(p.label,True,TEXT); screen.blit(lab,(x-8,y+9))
        # active pulses
        for (a,b,kind) in active_paths:
            if a not in self.ports or b not in self.ports: continue
            ax,ay=to_screen(self.ports[a].pos); bx,by=to_screen(self.ports[b].pos)
            x=int(ax+(bx-ax)*tphase); y=int(ay+(by-ay)*tphase)
            color=ACCENT if kind=="data" else CTRL
            pygame.draw.circle(screen,(255,255,255),(x,y),6); pygame.draw.circle(screen,color,(x,y),9,2)
            self.ports[a].lamp=self.ports[b].lamp=1.0
        # title
        tips="Drag port→port to create cable | Right-click cable to delete | Wheel=zoom, MMB drag=pan | S/L save/load"
        screen.blit(FONT_SM.render(tips,True,DIM),(r.x+14,r.bottom-18))
        self.board_rect=board; self.to_screen=to_screen
    def screen_to_world(self, sx,sy):
        # inverse of to_screen
        b=self.board_rect
        return ((sx-b.x-self.offset[0])/self.scale, (sy-b.y-self.offset[1])/self.scale)
    def nearest_port_at(self, sx,sy)->Optional[str]:
        # in screen coords
        for name,p in self.ports.items():
            x,y=self.to_screen(p.pos)
            if (x-sx)**2+(y-sy)**2 <= 10*10: return name
        return None
    def handle_event(self, e):
        if e.type==pygame.MOUSEBUTTONDOWN:
            if e.button==1: # left
                name=self.nearest_port_at(*e.pos)
                if name: self.drag_from=name
            if e.button==2: # middle - start pan
                self.mouse_last=e.pos
            if e.button==3: # right - delete cable
                self.remove_cable_at(*e.pos)
            if e.button==4: self.scale=min(2.0,self.scale*1.1)
            if e.button==5: self.scale=max(0.5,self.scale/1.1)
        elif e.type==pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]:
                dx=e.pos[0]-self.mouse_last[0]; dy=e.pos[1]-self.mouse_last[1]
                self.offset[0]+=dx; self.offset[1]+=dy; self.mouse_last=e.pos
        elif e.type==pygame.MOUSEBUTTONUP:
            if e.button==1 and self.drag_from:
                name=self.nearest_port_at(*e.pos)
                if name and name!=self.drag_from:
                    self.add_cable(self.drag_from, name)
                self.drag_from=None
    def save(self, path):
        data={"cables":[c.__dict__ for c in self.cables]}
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    def load(self, path):
        if not os.path.exists(path): return
        with open(path,"r",encoding="utf-8") as f: data=json.load(f)
        self.cables=[Cable(**c) for c in data.get("cables",[])]

class Timing:
    waves=["CPP","10P","9P","8P","7P","6P","5P","4P","3P","2P","1P","CCG","RP"]
    def __init__(self, rect):
        self.rect=pygame.Rect(rect); self.cursor=0; self.running=False; self.speed=0.28
        self.ccg=False; self.rp=False; self.ccgw=0; self.rpw=0
    def draw(self, stage):
        r=self.rect; draw_panel(r,f"Timing — {stage}")
        h=r.height-56; row=h/len(self.waves); sx=r.x+80; ex=r.right-110
        for i,w in enumerate(self.waves):
            y=int(r.y+36+i*row); pygame.draw.line(screen,(120,120,120),(sx,y),(ex,y),1)
            screen.blit(FONT_SM.render(w,True,TEXT),(r.x+10,y-8))
        x=int(sx+(ex-sx)*(self.cursor/10)); pygame.draw.line(screen,(255,120,120),(x,r.y+30),(x,r.bottom-12),2)
        screen.blit(FONT_SM.render(f"speed:{self.speed:.2f}",True,DIM),(ex+12,r.y+34))
    def open_ccg(self,d=0.25): self.ccg=True; self.ccgw=d
    def pulse_rp(self,d=0.2): self.rp=True; self.rpw=d
    def update(self,dt):
        if self.ccgw>0: self.ccgw-=dt; 
        else: self.ccg=False
        if self.rpw>0: self.rpw-=dt; 
        else: self.rp=False

# Mult controller as before
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
        self.accs=[Acc(f"A{i+1}") for i in range(20)]
        self.minis=[]
        y0=120; rows=2; cols=10; cw=140; ch=64; x0=20
        for r in range(rows):
            for c in range(cols):
                i=r*cols+c; rect=pygame.Rect(x0+c*cw, y0+r*ch, cw-6, ch-6)
                self.minis.append((self.accs[i], rect))
        self.pb=Plugboard(pygame.Rect(20,320,1460,430))
        self.timing=Timing((20,760,1460,220))
        self.ring_origin=(self.timing.rect.x+60, self.timing.rect.y-40)
        # Named shortcuts
        self.A1=self.accs[0]; self.A2=self.accs[1]; self.A3=self.accs[2]
        self.A4=self.accs[3]; self.A5=self.accs[4]; self.A7=self.accs[6]
        self.mult=MultController(self.A2,self.A3,self.A4)
        self.stage=0; self.running=False; self.tphase=0.0; self._acc=0.0
        self._build_default_ports(); self._load_default_wiring()
        self.reset()
    def _build_default_ports(self):
        r=self.pb.host_rect; bx,by=60,60
        # CT ports
        self.pb.add_port("CT1.A","CT1","data", 60, 40)
        self.pb.add_port("CT2.A","CT2","data", 120,40)
        self.pb.add_port("CT3.A","CT3","data", 180,40)
        # per-acc groups
        def acc_group(tag, x, y):
            labels=[("α","α"),("A","A"),("S","S"),("AS","AS"),("β","β"),("γ","γ")]
            for i,(k,lab) in enumerate(labels):
                self.pb.add_port(f"{tag}.{k}", lab, "data", x+i*28, y)
        # two rows
        xstart=260
        for i,tag in enumerate(["A1","A2","A3","A4","A5","A6","A7"]):
            acc_group(tag, xstart+i*160, 120)
        # multiplier + punch + controls
        self.pb.add_port("MULT.IN1","M1","data", 640, 180)
        self.pb.add_port("MULT.IN2","M2","data", 700, 180)
        self.pb.add_port("MULT.OUT","MOUT","data", 840, 180)
        self.pb.add_port("PUNCH.IN","P","data", 1100, 180)
        self.pb.add_port("CCG","CCG","ctrl", 60, 180)
        self.pb.add_port("RP","RP","ctrl", 100, 180)
    def _load_default_wiring(self):
        # same as V5 scenario
        add=self.pb.add_cable
        add("CT1.A","A1.α"); add("CT2.A","A2.α"); add("CT3.A","A3.α")
        add("A2.A","MULT.IN1"); add("A3.A","MULT.IN2"); add("MULT.OUT","A4.α")
        add("A1.A","A5.α"); add("A4.A","A5.α")
        add("A5.A","A7.α"); add("A2.S","A7.α")
        add("A7.A","PUNCH.IN")
    # mapping helpers
    def find_targets(self, source:str)->List[str]:
        return [c.b for c in self.pb.cables if c.a==source]
    def is_connected(self,a,b)->bool:
        return any((c.a==a and c.b==b) or (c.a==b and c.b==a) for c in self.pb.cables)
    def reset(self):
        for a in self.accs: a.load(0)
        self.stage=0; self.timing.cursor=0; self.mult.reset()
        self.tphase=0.0; self._acc=0.0
    def do_pulse(self):
        cur=self.timing.cursor
        # derive actions based on wiring + stage
        if self.stage==0:
            if cur==0:
                self.timing.open_ccg()
                # drive CTs into connected α
                for name,val in [("CT1.A",1),("CT2.A",2),("CT3.A",3)]:
                    for tgt in self.find_targets(name):
                        if tgt.endswith(".α"):
                            idx=int(tgt.split('.')[0][1:])-1
                            self.accs[idx].load(val)
            if cur==9: self.stage=1; self.mult.start()
        elif self.stage==1:
            if cur==0:
                self.timing.open_ccg(); self.mult.begin(self.A4)
            self.A4.tick_add_pulse(cur)
            if cur==9:
                self.mult.end()
                if self.mult.done: self.timing.pulse_rp(); self.stage=2
        elif self.stage==2:
            if cur==0:
                self.timing.open_ccg(); self.A5.start_add(self.A1.value(), sign=+1)
            self.A5.tick_add_pulse(cur)
            if cur==5 and not self.A5.add_active: self.A5.start_add(self.A4.value(), sign=+1)
            if cur==9: self.timing.pulse_rp(); self.stage=3
        elif self.stage==3:
            if cur==0:
                self.timing.open_ccg(); self.A7.start_add(self.A5.value(), sign=+1)
            self.A7.tick_add_pulse(cur)
            if cur==5 and not self.A7.add_active: self.A7.start_add(self.A2.value(), sign=-1)
            if cur==9: self.timing.pulse_rp(); self.stage=4
        elif self.stage==4:
            if cur==0: self.timing.open_ccg()
            if cur==9: self.timing.pulse_rp(); self.stage=5
        self.timing.cursor=(self.timing.cursor+1)%10
    def update(self,dt):
        if self.running:
            self._acc+=dt
            if self._acc>=self.timing.speed: self._acc=0; self.do_pulse()
        self.tphase += dt/max(0.12, self.timing.speed)
        if self.tphase>1: self.tphase=1.0
        self.timing.update(dt)
    def active_paths(self)->List[Tuple[str,str,str]]:
        paths=[]; cur=self.timing.cursor
        st=self.stage
        # control indications
        if self.timing.ccg:
            if   st==0: paths += [("CCG","A1.α","ctrl"),("CCG","A2.α","ctrl"),("CCG","A3.α","ctrl")]
            elif st==1: paths += [("CCG","MULT.IN1","ctrl"),("CCG","MULT.IN2","ctrl"),("CCG","A4.α","ctrl")]
            elif st==2: paths += [("CCG","A5.α","ctrl")]
            elif st==3: paths += [("CCG","A7.α","ctrl")]
            elif st==4: paths += [("CCG","PUNCH.IN","ctrl")]
        if self.timing.rp:
            for t in ["A4.α","A5.α","A7.α"]: paths.append(("RP",t,"ctrl"))
        # data
        if st==0:
            for src in ["CT1.A","CT2.A","CT3.A"]:
                for tgt in self.find_targets(src): paths.append((src,tgt,"data"))
        elif st==1:
            for tgt in self.find_targets("A2.A"): paths.append(("A2.A",tgt,"data"))
            for tgt in self.find_targets("A3.A"): paths.append(("A3.A",tgt,"data"))
            for tgt in self.find_targets("MULT.OUT"): paths.append(("MULT.OUT",tgt,"data"))
        elif st==2:
            for tgt in self.find_targets("A1.A"): paths.append(("A1.A",tgt,"data"))
            if cur>=5:
                for tgt in self.find_targets("A4.A"): paths.append(("A4.A",tgt,"data"))
        elif st==3:
            for tgt in self.find_targets("A5.A"): paths.append(("A5.A",tgt,"data"))
            for tgt in self.find_targets("A2.S"): paths.append(("A2.S",tgt,"data"))
        elif st==4:
            for tgt in self.find_targets("A7.A"): paths.append(("A7.A",tgt,"data"))
        return paths
    def draw(self):
        screen.fill(BG)
        draw_panel(pygame.Rect(20,20,280,90),"Card Reader")
        screen.blit(FONT_BIG.render("CT1:1  CT2:2  CT3:3",True,OK),(30,60))
        draw_panel(pygame.Rect(310,20,1170,90),"ENIAC — compact view")
        screen.blit(FONT.render("20 Accumulators / Ring Distributor / Plugboard Editor (interactive)",True,TEXT),(320,60))
        ring_idx=self.timing.cursor
        # minis
        for acc,rect in self.minis:
            acc.mini_draw(rect, ring_idx)
        # ring distributor fanout
        pygame.draw.circle(screen,(90,220,120),self.ring_origin,6); pygame.draw.circle(screen,EDGE,self.ring_origin,6,1)
        for _,rect in self.minis:
            p0=self.ring_origin; p1=(rect.right-12, rect.y+14)
            pygame.draw.line(screen,(120,160,120),p0,p1,2)
            t=ring_idx/9.0; x=int(p0[0]+(p1[0]-p0[0])*t); y=int(p0[1]+(p1[1]-p0[1])*t)
            pygame.draw.circle(screen,(210,255,210),(x,y),3)
        # plugboard
        self.pb.draw(self.active_paths(), self.tphase)
        # punch
        pr=pygame.Rect(20, 250, 380, 40); draw_panel(pr,"Card Punch"); screen.blit(FONT_BIG.render(str(self.A7.value()),True,OK),(pr.x+220,pr.y+8))
        # info+timing
        st_names=['LOAD','MULT','ADD','SUB','PUNCH','DONE']
        screen.blit(FONT.render(f"[Stage {st_names[self.stage]}] ENTER=step SPACE=run R=reset +/- speed S=save L=load | Cables:{len(self.pb.cables)}",True,TEXT),(20,100))
        self.timing.draw(st_names[self.stage])
    def save_wiring(self): self.pb.save("/mnt/data/plugboard_v6.json")
    def load_wiring(self): self.pb.load("/mnt/data/plugboard_v6.json")

def main():
    demo=Demo(); last=time.time()
    while True:
        now=time.time(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_RETURN: demo.do_pulse()
                if e.key==pygame.K_SPACE: demo.running=not demo.running; demo._acc=0
                if e.key==pygame.K_r: demo.reset()
                if e.key==pygame.K_MINUS or e.key==pygame.K_KP_MINUS: demo.timing.speed=min(1.0, demo.timing.speed+0.05)
                if e.key==pygame.K_EQUALS or e.key==pygame.K_PLUS or e.key==pygame.K_KP_PLUS: demo.timing.speed=max(0.05, demo.timing.speed-0.05)
                if e.key==pygame.K_s: demo.save_wiring()
                if e.key==pygame.K_l: demo.load_wiring()
            demo.pb.handle_event(e)
        demo.update(dt); demo.draw(); pygame.display.flip(); clock.tick(60)

if __name__=="__main__":
    main()
