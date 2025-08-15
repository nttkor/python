# eniac_ballistics_orcad.py
# ------------------------------------------------------------------
# ENIAC Ballistics Animation (OrCAD-style layout)
# - Edge-docked orthogonal wires (no lines inside blocks)
# - Arithmetic Unit on the far right, inputs/IO on the left, accumulators center grid
# - Working Play / Pause / Step / Reset buttons
# - F11 fullscreen toggle
# - Based on the earlier expanded demo; preserves pulses & simple looped computation
# ------------------------------------------------------------------

import math
import pygame
from dataclasses import dataclass

# ---------------- Screen & Style ----------------
WIN_W, WIN_H = 1600, 950
FPS = 60
MARGIN = 20

BG = (18, 20, 24)
PANEL = (40, 44, 54)
PANEL_ALT = (46, 50, 62)
TEXT = (235, 238, 245)
MUTED = (165, 170, 185)
BORDER = (88, 94, 110)

DATA = (76, 201, 137)       # data pulses
CTRL = (255, 200, 84)       # control pulses
FUNC = (160, 120, 255)      # function/constant
CARD = (80, 180, 255)       # card IO
RESULT = (255, 120, 160)    # result pulses
WIRE = (140, 145, 160)
WIRE_ACTIVE = (240, 244, 255)

ACC_BG = (44, 49, 60)
ACC_HI = (90, 180, 255)

FONT_NAME = "consolas"


# ---------------- Helpers ----------------
def clamp(a, lo, hi): return max(lo, min(hi, a))


# ---------------- Nodes ----------------
class Node:
    """Generic rectangular node with named edge ports for OrCAD-style routing."""
    def __init__(self, name, x, y, w, h, color=PANEL):
        self.name, self.x, self.y, self.w, self.h = name, x, y, w, h
        self.color = color
        self.state = "IDLE"  # IDLE/RECV/CALC/SEND/DONE

        # port channels on each edge: normalized 0..1 slots to keep wires spaced
        self.port_slots_out_r = 0
        self.port_slots_in_l = 0
        self.port_slots_out_l = 0
        self.port_slots_in_r = 0

    def rect(self): return pygame.Rect(self.x, self.y, self.w, self.h)

    def _edge_point(self, side, slot, slots):
        slot = clamp(slot, 0, max(0, slots-1))
        t = (slot + 1) / (slots + 1) if slots > 0 else 0.5
        if side == "right":
            return (self.x + self.w, int(self.y + t * self.h))
        elif side == "left":
            return (self.x, int(self.y + t * self.h))
        elif side == "top":
            return (int(self.x + t * self.w), self.y)
        else:
            return (int(self.x + t * self.w), self.y + self.h)

    def alloc_out(self, side="right"):
        if side == "right":
            s = self.port_slots_out_r; self.port_slots_out_r += 1
        else:
            s = self.port_slots_out_l; self.port_slots_out_l += 1
        return s

    def alloc_in(self, side="left"):
        if side == "left":
            s = self.port_slots_in_l; self.port_slots_in_l += 1
        else:
            s = self.port_slots_in_r; self.port_slots_in_r += 1
        return s

    def out_pos(self, side="right", slot=None):
        slots = self.port_slots_out_r if side == "right" else self.port_slots_out_l
        if slot is None: slot = slots // 2
        return self._edge_point(side, slot, max(1, slots))

    def in_pos(self, side="left", slot=None):
        slots = self.port_slots_in_l if side == "left" else self.port_slots_in_r
        if slot is None: slot = slots // 2
        return self._edge_point(side, slot, max(1, slots))

    def draw(self, s, font, title=None):
        pygame.draw.rect(s, self.color, self.rect(), border_radius=12)
        pygame.draw.rect(s, BORDER, self.rect(), 2, border_radius=12)
        s.blit(font.render(title or self.name, True, TEXT), (self.x + 10, self.y + 8))
        stc = {"IDLE": MUTED, "RECV": CARD, "CALC": CTRL, "SEND": DATA, "DONE": RESULT}.get(self.state, MUTED)
        pygame.draw.circle(s, stc, (self.x + self.w - 16, self.y + 16), 6)


class Accumulator(Node):
    def __init__(self, name, x, y):
        super().__init__(name, x, y, 230, 130, color=PANEL_ALT)
        self.value = 0

    def set(self, v): self.value = int(v) % (10**10)

    def draw(self, s, font, title=None):
        super().draw(s, font, title=f"{self.name}  (Accumulator)")
        txt = f"{self.value:010d}"
        s.blit(font.render(txt, True, TEXT), (self.x + 12, self.y + self.h - 26))


class ALU(Node):
    def __init__(self, x, y):
        super().__init__("Arithmetic Units", x, y, 310, 420, color=(46, 52, 66))

    def draw(self, s, font, title=None):
        super().draw(s, font, title=self.name)
        names = [("Adder / Subtracter", DATA), ("Multiplier", CTRL), ("Divider / Sqrt", FUNC)]
        for i, (n, col) in enumerate(names):
            ry = self.y + 60 + i * 130
            r = pygame.Rect(self.x + 12, ry, self.w - 24, 100)
            pygame.draw.rect(s, (52, 58, 72), r, border_radius=10)
            pygame.draw.rect(s, BORDER, r, 2, border_radius=10)
            s.blit(font.render(n, True, col), (r.x + 12, r.y + 34))


class Button:
    def __init__(self, x, y, w, h, label, hotkey=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.hotkey = hotkey
        self.enabled = True

    def draw(self, s, font, active=False):
        color = (58, 64, 80) if not self.enabled else (56, 120, 96) if active else (52, 58, 72)
        pygame.draw.rect(s, color, self.rect, border_radius=8)
        pygame.draw.rect(s, BORDER, self.rect, 2, border_radius=8)
        s.blit(font.render(self.label, True, TEXT), (self.rect.x + 12, self.rect.y + 8))

    def hit(self, pos): return self.enabled and self.rect.collidepoint(pos)


# ---------------- Wires ----------------
class Wire:
    """Orthogonal wire between nodes, docked to edges with slotting to avoid overlap."""
    def __init__(self, src: Node, dst: Node, color=WIRE, src_side="right", dst_side="left"):
        self.src, self.dst = src, dst
        self.color = color
        self.src_side, self.dst_side = src_side, dst_side
        self.src_slot = src.alloc_out(src_side)
        self.dst_slot = dst.alloc_in(dst_side)

    def _dock(self, node: Node, side: str, slot: int):
        # compute dock position just outside edge to keep wire off the box border
        x, y = node._edge_point(side, slot, (node.port_slots_out_r if side=="right" else node.port_slots_out_l) if side in ("right","left") else 1)
        # move one pixel outside
        if side == "right": x += 2
        elif side == "left": x -= 2
        elif side == "top": y -= 2
        else: y += 2
        return (x, y)

    def path(self):
        sx, sy = self._dock(self.src, self.src_side, self.src_slot)
        dx, dy = self._dock(self.dst, self.dst_side, self.dst_slot)

        # route orthogonally via a mid-x column outside of both boxes
        # choose mid_x between boxes with clearance
        gap = 18
        if sx < dx:
            mid_x = (sx + dx) // 2
        else:
            mid_x = (dx + sx) // 2
        # ensure mid_x is outside any node rects by nudging
        # (simple approach: if within src rect x-range, push to right; if within dst rect, push to left)
        if self.src.x < mid_x < self.src.x + self.src.w: mid_x = self.src.x + self.src.w + gap
        if self.dst.x < mid_x < self.dst.x + self.dst.w: mid_x = self.dst.x - gap

        return [(sx, sy), (mid_x, sy), (mid_x, dy), (dx, dy)]

    def draw(self, s, active=False):
        pygame.draw.lines(s, WIRE_ACTIVE if active else self.color, False, self.path(), 2)


class Pulse:
    def __init__(self, wire: Wire, color, label="", speed=600):
        self.wire = wire
        self.color = color
        self.label = label
        self.speed = speed
        self.done = False
        self.seg = 0
        self.pos = wire.path()[0]

    def update(self, dt):
        if self.done: return
        path = self.wire.path()
        if self.seg >= len(path) - 1:
            self.done = True; return
        x1, y1 = path[self.seg]
        x2, y2 = path[self.seg + 1]
        dx, dy = x2 - x1, y2 - y1
        dist = max(1e-6, (dx*dx + dy*dy) ** 0.5)
        step = self.speed * dt
        if step >= dist:
            self.seg += 1
            self.pos = (x2, y2)
            if self.seg >= len(path) - 1: self.done = True
        else:
            self.pos = (self.pos[0] + step * (dx / dist), self.pos[1] + step * (dy / dist))

    def draw(self, s, font):
        if self.done: return
        pygame.draw.circle(s, self.color, (int(self.pos[0]), int(self.pos[1])), 5)
        if self.label:
            s.blit(font.render(self.label, True, self.color), (self.pos[0] + 8, self.pos[1] - 12))


# ---------------- Simulation state ----------------
@dataclass
class BallisticState:
    x: int = 0; y: int = 0; vx: int = 0; vy: int = 0
    t: int = 0; loop: int = 0; done: bool = False


class Context:
    def __init__(self, font, small, big):
        self.font, self.small, self.big = font, small, big
        self.fullscreen = False

        # Layout (OrCAD-style):
        # Left column
        self.reader = Node("Card Reader", 40, 100, 240, 110)
        self.tx = Node("Constant Transmitter", 40, 240, 240, 110)
        self.func = Node("Function Table", 40, 380, 240, 110)
        self.master = Node("Master Programmer", 40, 520, 240, 110)
        self.punch = Node("Card Punch", 40, 700, 240, 110)

        # Center grid of accumulators (3 cols x 4 rows)
        start_x, start_y = 340, 80
        gap_x, gap_y = 260, 160
        self.accs = []
        for r in range(4):
            for c in range(3):
                idx = r*3 + c + 1
                self.accs.append(Accumulator(f"A{idx}", start_x + c*gap_x, start_y + r*gap_y))

        # Right: ALU
        self.alu = ALU(1200, 220)

        # Wires (edge-docked & orthogonal)
        self.wires = []
        def W(src, dst, col=WIRE): self.wires.append(Wire(src, dst, color=col))

        # Example routing reflecting the earlier pipeline:
        W(self.reader, self.tx, CARD)
        for i in range(3): W(self.tx, self.accs[i], DATA)                # A1..A3 constants
        W(self.func, self.accs[3], FUNC)                                 # A4 trig/func
        W(self.func, self.accs[4], FUNC)                                 # A5 trig/func
        W(self.func, self.accs[5], FUNC)                                 # A6 trig/func
        for i in range(6, 9): W(self.accs[i], self.alu, DATA)            # A7..A9 to ALU
        for i in range(9, 12): W(self.alu, self.accs[i], CTRL)           # ALU back to A10..A12
        W(self.accs[11], self.punch, RESULT)                              # A12 -> Punch

        # Buttons
        bx = 1440; by = 100
        self.btn_play  = Button(bx, by, 120, 34, "▶ Play", hotkey="SPACE")
        self.btn_pause = Button(bx, by+44, 120, 34, "⏸ Pause")
        self.btn_step  = Button(bx, by+88, 120, 34, "⏩ Step (N)")
        self.btn_reset = Button(bx, by+132, 120, 34, "↺ Reset")
        self.btn_full  = Button(bx, by+176, 120, 34, "⛶ Fullscreen (F11)")

        # Pulses & log
        self.pulses = []
        self.logs = []

        # Sim values
        self.dt = 20         # 0.20 s
        self.inputs = {"v0": 25000, "angle": 4500, "g": 981, "k": 15}
        self.state = BallisticState()
        self.running = False
        self.fast = False

        # one-time init demo
        self._initial_load()

    def _initial_load(self):
        # Card→TX
        self.reader.state = "SEND"; self.tx.state = "RECV"
        self._pulse(self.reader, self.tx, CARD, "CARD")
        self.reader.state = "DONE"; self.tx.state = "DONE"
        # Load constants to A1..A3
        for i, lbl, val in [(0, "v0", self.inputs["v0"]), (1, "θ", self.inputs["angle"]), (2, "g", self.inputs["g"])]:
            self.accs[i].set(val); self.accs[i].state = "RECV"
            self._pulse(self.tx, self.accs[i], DATA, lbl)

    # --- utility ---
    def _pulse(self, a, b, col, label="", speed=None):
        w = next((w for w in self.wires if w.src is a and w.dst is b), None)
        if w is None: w = Wire(a, b, color=col)
        self.pulses.append(Pulse(w, col, label, speed if speed else (900 if self.fast else 600)))

    def log(self, msg):
        self.logs.append(msg); self.logs = self.logs[-9:]

    # --- control ---
    def play(self): self.running = True
    def pause(self): self.running = False
    def step(self): self._run_step()
    def reset(self):
        self.running = False
        for a in self.accs: a.set(0); a.state = "IDLE"
        for n in (self.reader, self.tx, self.func, self.master, self.punch): n.state = "IDLE"
        self.alu.state = "IDLE"; self.pulses.clear(); self.logs.clear()
        self.state = BallisticState()
        self._initial_load()

    # --- simple step demo (integrate vy with gravity, x/y with vx/vy) ---
    def _run_step(self):
        mp = self.master
        mp.state = "CALC"; self.state.loop += 1; self.state.t += self.dt; mp.state = "DONE"

        # use A1 (v0) & A2 (θ) once to compute vx, vy at first step
        if self.state.loop == 1:
            v0 = self.accs[0].value; ang = self.accs[1].value/100.0
            sinv = int(math.sin(math.radians(ang)) * 10000)
            cosv = int(math.cos(math.radians(ang)) * 10000)
            vx = (v0 * cosv) // 10000
            vy = (v0 * sinv) // 10000
            self.accs[8].set(vx)   # A9
            self.accs[9].set(vy)   # A10
            self._pulse(self.accs[0], self.alu, DATA, "v0")
            self._pulse(self.accs[1], self.alu, FUNC, "θ")
            self._pulse(self.alu, self.accs[8], CTRL, "vx")
            self._pulse(self.alu, self.accs[9], CTRL, "vy")
            self.log(f"INIT: vx={vx}, vy={vy}")

        # integrate x,y
        dt = self.dt
        a9, a10, a11, a12 = self.accs[8], self.accs[9], self.accs[10], self.accs[11]
        dx = (a9.value * dt) // 100
        dy = (a10.value * dt) // 100
        a11.set(a11.value + dx)
        a12.set(max(0, a12.value + dy))
        self._pulse(a9, self.alu, DATA, "vx"); self._pulse(self.alu, a11, CTRL, "x+=")
        self._pulse(a10, self.alu, DATA, "vy"); self._pulse(self.alu, a12, CTRL, "y+=")
        self.log(f"INT: x+= {dx}, y+= {dy}")

        # apply gravity (vy -= g*dt)
        g = self.accs[2].value
        gdt = (g * dt) // 100
        a10.set(max(0, a10.value - gdt))
        self._pulse(self.accs[2], self.alu, FUNC, "g")
        self._pulse(self.alu, a10, CTRL, "vy'")
        self.log(f"FORCE: vy-= {gdt}")

        # punch result occasionally
        if self.state.loop % 5 == 0:
            self._pulse(self.accs[10], self.punch, RESULT, "x")
            self._pulse(self.accs[11], self.punch, RESULT, "y")
            self.punch.state = "RECV"; self.punch.state = "DONE"

    # --- update/draw ---
    def update(self, dt):
        for p in self.pulses: p.update(dt)
        self.pulses = [p for p in self.pulses if not p.done]

        if self.running: self._run_step_timer(dt)

    def _run_step_timer(self, dt):
        if not hasattr(self, "_acc_time"): self._acc_time = 0.0
        interval = 0.8 if not self.fast else 0.35
        self._acc_time += dt
        if self._acc_time >= interval:
            self._acc_time = 0.0
            self._run_step()

    def draw(self, screen):
        # wires behind nodes
        for w in self.wires: w.draw(screen, active=False)

        # nodes
        for n in (self.reader, self.tx, self.func, self.master, self.punch): n.draw(screen, self.font)
        for a in self.accs: a.draw(screen, self.font)
        self.alu.draw(screen, self.font)

        # pulses
        for p in self.pulses: p.draw(screen, self.small)

        # HUD
        screen.blit(self.big.render("ENIAC Ballistics – OrCAD Layout", True, TEXT), (28, 18))
        self._draw_hud(screen)
        self._draw_buttons(screen)

    def _draw_hud(self, s):
        r = pygame.Rect(330, WIN_H - 140, WIN_W - 360, 110)
        pygame.draw.rect(s, (36, 40, 50), r, border_radius=10)
        pygame.draw.rect(s, BORDER, r, 2, border_radius=10)
        vals = [("t(s)", f"{self.state.t/100:.2f}"),
                ("loop", str(self.state.loop)),
                ("x(*1e2)", f"{self.accs[10].value:010d}"),
                ("y(*1e2)", f"{self.accs[11].value:010d}"),
                ("vx(*1e2)", f"{self.accs[8].value:010d}"),
                ("vy(*1e2)", f"{self.accs[9].value:010d}")]
        x = r.x + 10; y = r.y + 10
        for k, v in vals:
            s.blit(self.font.render(k, True, MUTED), (x, y))
            s.blit(self.font.render(v, True, TEXT), (x, y + 26))
            x += 170

        legend = [("DATA", DATA), ("CTRL", CTRL), ("FUNC", FUNC), ("CARD", CARD), ("RESULT", RESULT)]
        lx = r.x + 10; ly = r.y + 70
        for name, col in legend:
            pygame.draw.circle(s, col, (lx, ly), 6); s.blit(self.small.render(name, True, MUTED), (lx + 10, ly - 8))
            lx += 90

    def _draw_buttons(self, s):
        self.btn_play.enabled = not self.running
        self.btn_pause.enabled = self.running
        for b in (self.btn_play, self.btn_pause, self.btn_step, self.btn_reset, self.btn_full): b.draw(s, self.font)

    def on_click(self, pos, screen_ref):
        if self.btn_play.hit(pos): self.play()
        elif self.btn_pause.hit(pos): self.pause()
        elif self.btn_step.hit(pos): self.step()
        elif self.btn_reset.hit(pos): self.reset()
        elif self.btn_full.hit(pos):
            # toggled externally in main loop (handled by KEYDOWN F11 for stability)
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))


# ---------------- Main ----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("ENIAC Ballistics – OrCAD Layout")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(FONT_NAME, 18)
    small = pygame.font.SysFont(FONT_NAME, 14)
    big = pygame.font.SysFont(FONT_NAME, 28, bold=True)

    ctx = Context(font, small, big)
    running = True
    fullscreen = False

    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_SPACE:
                    ctx.running = not ctx.running
                elif e.key == pygame.K_n:
                    ctx.step()
                elif e.key == pygame.K_r:
                    ctx.reset()
                elif e.key == pygame.K_f:
                    ctx.fast = not ctx.fast
                elif e.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((WIN_W, WIN_H))
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                ctx.on_click(e.pos, screen)

        ctx.update(dt)
        screen.fill(BG)
        ctx.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
