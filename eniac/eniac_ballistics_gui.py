# eniac_ballistics_gui.py (fixed)
# ------------------------------------------------------------------
# ENIAC 탄도계산 흐름 애니메이션 (확장판, Pygame)
# - Fix: Context.dt_units 초기화 순서 버그 수정 (set_preset 이전에 설정)
# - Cleanup: RingDecimal.draw 텍스트 렌더 중복 호출 제거
# ------------------------------------------------------------------

import math
import sys
import pygame
from dataclasses import dataclass

# ---------- 화면/색상 ----------
W, H = 1500, 940
FPS = 60

BG = (18, 20, 24)
PANEL = (35, 39, 48)
TEXT = (235, 238, 245)
MUTED = (160, 165, 178)
BORDER = (80, 86, 102)

DATA = (76, 201, 137)       # 데이터(초록)
CTRL = (255, 200, 84)       # 제어(노랑)
FUNC = (160, 120, 255)      # 함수/상수(보라)
CARD = (80, 180, 255)       # 카드(하늘)
RESULT = (255, 120, 160)    # 결과(분홍)
WIRE = (90, 98, 115)
WIRE_ACTIVE = (240, 244, 255)

ACC_BG = (44, 49, 60)
ACC_HI = (90, 180, 255)

FONT_NAME = "consolas"


# ---------- 펄스/와이어 ----------
class Pulse:
    def __init__(self, path, color, speed, label=""):
        self.path = path
        self.color = color
        self.speed = speed
        self.label = label
        self.idx = 0
        self.pos = path[0]
        self.done = False

    def update(self, dt):
        if self.done or self.idx >= len(self.path) - 1:
            self.done = True
            return
        x1, y1 = self.path[self.idx]
        x2, y2 = self.path[self.idx + 1]
        dx, dy = x2 - x1, y2 - y1
        dist = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        step = self.speed * dt
        if step >= dist:
            self.idx += 1
            self.pos = (x2, y2)
            if self.idx >= len(self.path) - 1:
                self.done = True
        else:
            self.pos = (self.pos[0] + step * dx / dist, self.pos[1] + step * dy / dist)

    def draw(self, s, font):
        if self.done:
            return
        pygame.draw.circle(s, self.color, (int(self.pos[0]), int(self.pos[1])), 5)
        if self.label:
            s.blit(font.render(self.label, True, self.color), (self.pos[0] + 8, self.pos[1] - 10))


class Wire:
    def __init__(self, a, b, color=WIRE, curvature=0.0):
        self.a, self.b = a, b
        self.color = color
        self.curvature = curvature

    def path(self):
        ax, ay = self.a.out_pos()
        bx, by = self.b.in_pos()
        if abs(self.curvature) < 1e-6:
            return [(ax, ay), (bx, by)]
        mx = (ax + bx) / 2
        my = (ay + by) / 2 + self.curvature * 80
        return [(ax, ay), (mx, my), (bx, by)]

    def draw(self, s, active=False):
        pygame.draw.lines(s, WIRE_ACTIVE if active else self.color, False, self.path(), 2)


# ---------- 노드/장치 ----------
class Node:
    def __init__(self, name, x, y, w, h):
        self.name, self.x, self.y, self.w, self.h = name, x, y, w, h
        self.state = "IDLE"  # IDLE/RECV/CALC/SEND/DONE

    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def in_pos(self):
        return (self.x, self.y + self.h / 2)

    def out_pos(self):
        return (self.x + self.w, self.y + self.h / 2)

    def draw_box(self, s, font, title=None, color=PANEL):
        pygame.draw.rect(s, color, self.rect(), border_radius=16)
        pygame.draw.rect(s, BORDER, self.rect(), 2, border_radius=16)
        s.blit(font.render(title or self.name, True, TEXT), (self.x + 12, self.y + 10))
        stc = {"IDLE": MUTED, "RECV": CARD, "CALC": CTRL, "SEND": DATA, "DONE": RESULT}.get(self.state, MUTED)
        pygame.draw.circle(s, stc, (int(self.x + self.w - 20), int(self.y + 20)), 6)


class CardReader(Node): ...
class CardPunch(Node): ...
class ConstantTransmitter(Node): ...
class FunctionTable(Node): ...
class MasterProgrammer(Node): ...


class RingDecimal:
    def __init__(self, digits=10):
        self.digits = digits
        self.value = 0

    def set(self, v): self.value = int(v) % (10 ** self.digits)
    def add(self, v): self.set(self.value + int(v))
    def sub(self, v): self.set(self.value - int(v))

    def draw(self, s, cx, cy, r, font):
        pygame.draw.circle(s, ACC_BG, (cx, cy), r)
        pygame.draw.circle(s, BORDER, (cx, cy), r, 2)
        for i in range(10):
            ang = -math.pi / 2 + (i / 10.0) * 2 * math.pi
            rr = r - 8
            px = cx + rr * math.cos(ang)
            py = cy + rr * math.sin(ang)
            on = (self.value % 10) == i
            pygame.draw.circle(s, ACC_HI if on else (70, 74, 86), (int(px), int(py)), 6)
        txt = f"{self.value:0{self.digits}d}"
        img = font.render(txt, True, TEXT)
        rc = img.get_rect(center=(cx, cy))
        s.blit(img, rc)


class Accumulator(Node):
    def __init__(self, name, x, y):
        super().__init__(name, x, y, 230, 140)
        self.reg = RingDecimal(10)
        self.ports_in = ["α", "β", "γ", "δ", "ε"]
        self.ports_out = ["A", "S"]

    def draw(self, s, font):
        self.draw_box(s, font, title=f"{self.name}  (Accumulator)", color=(42, 47, 58))
        for i, p in enumerate(self.ports_in):
            s.blit(font.render(p, True, FUNC), (self.x + 8, self.y + 34 + i * 16))
        for i, p in enumerate(self.ports_out):
            s.blit(font.render(p, True, DATA), (self.x + self.w - 22, self.y + 34 + i * 16))
        cx, cy = int(self.x + self.w * 0.73), int(self.y + self.h * 0.62)
        self.reg.draw(s, cx, cy, 42, font)
        s.blit(font.render("10-digit decimal", True, MUTED), (self.x + 10, self.y + self.h - 20))


class ALU(Node):
    def __init__(self, x, y):
        super().__init__("Arithmetic Units", x, y, 300, 330)

    def draw(self, s, font):
        self.draw_box(s, font, color=(46, 52, 66))
        names = [("Adder / Subtracter", DATA), ("Multiplier", CTRL), ("Divider / Sqrt", FUNC)]
        for i, (n, col) in enumerate(names):
            r = pygame.Rect(self.x + 14, self.y + 50 + i * 90, self.w - 28, 78)
            pygame.draw.rect(s, (52, 58, 72), r, border_radius=12)
            pygame.draw.rect(s, BORDER, r, 2, border_radius=12)
            s.blit(font.render(n, True, col), (r.x + 10, r.y + 24))


# ---------- GUI 버튼 ----------
class Button:
    def __init__(self, x, y, w, h, label, key=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.key = key
        self.enabled = True

    def draw(self, s, font, active=False):
        color = (58, 64, 80) if not self.enabled else (56, 120, 96) if active else (52, 58, 72)
        pygame.draw.rect(s, color, self.rect, border_radius=10)
        pygame.draw.rect(s, BORDER, self.rect, 2, border_radius=10)
        s.blit(font.render(self.label, True, TEXT), (self.rect.x + 12, self.rect.y + 10))

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


# ---------- 상태/컨텍스트 ----------
@dataclass
class BallisticState:
    x: int = 0
    y: int = 0
    vx: int = 0   # *100
    vy: int = 0
    t: int = 0    # 0.01s 단위
    step: int = 0
    loop: int = 0
    apex_y: int = 0
    apex_x: int = 0
    done: bool = False
    range_x: int = 0


class Context:
    def __init__(self):
        # 폰트(런타임에 주입)
        self.font = None
        self.small = None
        self.big = None

        # --- 먼저 시간 스텝 초기화 (버그 수정 포인트) ---
        self.dt_units = 10   # 0.10 s per step (set_preset에서 사용)

        # 장치 배치
        self.reader = CardReader("Card Reader", 30, 60, 240, 120)
        self.tx = ConstantTransmitter("Constant Transmitter", 30, 210, 240, 110)
        self.func = FunctionTable("Function Table", 30, 350, 240, 140)
        self.master = MasterProgrammer("Master Programmer", 30, 520, 240, 110)
        self.punch = CardPunch("Card Punch", 30, 660, 240, 120)

        # 계수기 (12개 표시)
        self.accs = []
        ax, ay = 310, 60
        for r in range(3):
            for c in range(4):
                self.accs.append(Accumulator(f"A{r*4+c+1}", ax + c * 255, ay + r * 155))

        self.alu = ALU(W - 340, 240)

        # 초기화
        for a in self.accs: a.reg.set(0)

        # 입력 프리셋 (dt_units 이미 준비됨)
        self.set_preset(45.0, 250.0)

        # 와이어(시각화용)
        self.wires = []
        self.wires.append(Wire(self.reader, self.tx, curvature=0.2))
        for i in range(4):
            self.wires.append(Wire(self.tx, self.accs[i], curvature=(-1)**i * 0.25))
        for i in range(2):
            self.wires.append(Wire(self.func, self.accs[4 + i], curvature=(1 if i == 0 else -1) * 0.2))
        for i in range(8):
            self.wires.append(Wire(self.accs[i], self.alu, curvature=0.15))
        for i in range(8, 12):
            self.wires.append(Wire(self.alu, self.accs[i], curvature=-0.18))
        self.wires.append(Wire(self.accs[11], self.punch, curvature=0.1))

        self.pulses = []
        self.fast = False

        # 실행 상태
        self.logs = []
        self.state = BallisticState()
        self.func_table_note = ""

        # Function Table 내부 데이터(보정용)
        self.drag_c0 = 0
        self.drag_c2 = 6

        # 시나리오
        self.scenario = self._build_scenario()
        self.step_index = 0

        # GUI 버튼
        by = H - 90
        bx = 30
        self.btn_play = Button(bx, by, 110, 40, "▶ Play")
        self.btn_pause = Button(bx + 120, by, 110, 40, "⏸ Pause")
        self.btn_step = Button(bx + 240, by, 120, 40, "⏩ Step (N)")
        self.btn_reset = Button(bx + 370, by, 110, 40, "↺ Reset")
        self.btn_p1 = Button(bx + 500, by, 110, 40, "Preset 1")
        self.btn_p2 = Button(bx + 620, by, 110, 40, "Preset 2")
        self.btn_p3 = Button(bx + 740, by, 110, 40, "Preset 3")
        self.auto = False

    # ----- 도우미 -----
    def log(self, msg):
        self.logs.append(msg)
        self.logs = self.logs[-10:]

    def pulse_path(self, a, b, color, label, speed=None):
        p = Pulse(Wire(a, b).path(), color, speed if speed else (740 if self.fast else 460), label)
        self.pulses.append(p)

    def set_preset(self, angle_deg, v0):
        g = 9.81
        self.inputs = {
            "v0": int(v0 * 100),
            "angle_deg": int(angle_deg * 100),
            "sinθ": int(math.sin(math.radians(angle_deg)) * 10000),
            "cosθ": int(math.cos(math.radians(angle_deg)) * 10000),
            "g": int(g * 100),
            "k": 15,
            "Δt": self.dt_units,   # <-- dt_units가 이제 보장됨
        }

    # ----- 시나리오 구성 -----
    def _build_scenario(self):
        return [
            ("Card→TX", self._st_card_tx),
            ("TX→Acc Init", self._st_tx_to_acc),
            ("FuncTable trig", self._st_func_trig),
            ("Init Vectors", self._st_init_vec),
            ("Loop Start", self._st_loop_start),
            ("Integrate XY", self._st_integrate_xy),
            ("Apply Forces", self._st_apply_forces),
            ("Update VX", self._st_update_vx),
            ("Check Ground", self._st_check_ground),
            ("Punch Result", self._st_punch),
        ]

    # ----- 스텝 구현 -----
    def _st_card_tx(self):
        self.reader.state = "SEND"
        self.tx.state = "RECV"
        self.pulse_path(self.reader, self.tx, CARD, "CARD")
        self.log("[CARD] Read v0, angle, g, k, Δt")
        self.reader.state = "DONE"
        self.tx.state = "DONE"

    def _st_tx_to_acc(self):
        self.tx.state = "SEND"
        mapping = [
            (self.accs[0], "v0", self.inputs["v0"]),
            (self.accs[1], "θ*100", self.inputs["angle_deg"]),
            (self.accs[2], "g*100", self.inputs["g"]),
            (self.accs[3], "k", self.inputs["k"]),
            (self.accs[7], "Δt", self.inputs["Δt"]),
        ]
        for acc, lbl, val in mapping:
            self.pulse_path(self.tx, acc, DATA, lbl)
            acc.reg.set(val)
            acc.state = "RECV"
        self.tx.state = "DONE"
        self.log("[TX] A1..A4,A8 loaded")

    def _func_table_drag_coeff(self, v100):
        v = v100 / 100.0
        val = self.drag_c0 + self.drag_c2 * (v * v)
        return int(val * 10000)

    def _st_func_trig(self):
        self.func.state = "SEND"
        a5, a6 = self.accs[4], self.accs[5]

        self.func_table_note = f"lookup: sin/cos({self.inputs['angle_deg']/100:.2f}°)"
        self.pulse_path(self.func, a5, FUNC, "sinθ")
        self.pulse_path(self.func, a6, FUNC, "cosθ")
        a5.reg.set(self.inputs["sinθ"])
        a6.reg.set(self.inputs["cosθ"])

        v0 = self.inputs["v0"]
        dragK = self._func_table_drag_coeff(v0)
        self.func_table_note += f" | dragK≈{dragK}(*1e4)"
        self.accs[6].reg.set(dragK)
        self.pulse_path(self.func, self.accs[6], FUNC, "dragK")

        self.func.state = "DONE"
        self.log("[FUNC] sinθ, cosθ, dragK → A5/A6/A7")

    def _st_init_vec(self):
        self.alu.state = "CALC"
        a1, a5, a6, a9, a10 = self.accs[0], self.accs[4], self.accs[5], self.accs[8], self.accs[9]

        vx0 = (a1.reg.value * a6.reg.value) // 10000
        vy0 = (a1.reg.value * a5.reg.value) // 10000
        self.pulse_path(a1, self.alu, DATA, "v0")
        self.pulse_path(a6, self.alu, FUNC, "cosθ")
        self.pulse_path(self.alu, a9, CTRL, "MUL→A9")
        self.pulse_path(a1, self.alu, DATA, "v0")
        self.pulse_path(a5, self.alu, FUNC, "sinθ")
        self.pulse_path(self.alu, a10, CTRL, "MUL→A10")
        a9.reg.set(vx0); a10.reg.set(vy0)

        self.accs[10].reg.set(0)  # x
        self.accs[11].reg.set(0)  # y
        self.state.apex_y = 0
        self.state.apex_x = 0

        self.alu.state = "DONE"
        self.log(f"[INIT] vx0={vx0:010d}, vy0={vy0:010d}")

    def _st_loop_start(self):
        self.master.state = "CALC"
        self.state.loop += 1
        self.state.step += 1
        self.state.t += self.inputs["Δt"]
        self.master.state = "DONE"
        self.log(f"[MP] loop={self.state.loop}, t={self.state.t/100:.2f}s")

    def _st_integrate_xy(self):
        dt = self.accs[7].reg.value
        a9, a10, a11, a12 = self.accs[8], self.accs[9], self.accs[10], self.accs[11]
        self.alu.state = "CALC"
        dx = (a9.reg.value * dt) // 100
        a11.reg.set(a11.reg.value + dx)
        self.pulse_path(a9, self.alu, DATA, "vx")
        self.pulse_path(self.alu, a11, CTRL, "Δx")
        dy = (a10.reg.value * dt) // 100
        a12.reg.set(a12.reg.value + dy)
        self.pulse_path(a10, self.alu, DATA, "vy")
        self.pulse_path(self.alu, a12, CTRL, "Δy")
        if a12.reg.value > self.state.apex_y:
            self.state.apex_y = a12.reg.value
            self.state.apex_x = a11.reg.value
        self.alu.state = "DONE"
        self.log(f"[INT] x+= {dx:010d}, y+= {dy:010d}")

    def _st_apply_forces(self):
        dt = self.accs[7].reg.value
        g = self.accs[2].reg.value
        a9, a10 = self.accs[8], self.accs[9]
        Ktab = self.accs[6].reg.value

        self.alu.state = "CALC"
        speed = int((a9.reg.value**2 + a10.reg.value**2) ** 0.5)
        K = (Ktab * speed) // 10000
        gdt = (g * dt) // 100
        drag = (K * dt) // 100
        vy_new = a10.reg.value - gdt - drag

        self.pulse_path(self.accs[2], self.alu, FUNC, "g")
        self.pulse_path(self.accs[6], self.alu, FUNC, "dragK")
        self.pulse_path(self.alu, a10, CTRL, "vy'")
        a10.reg.set(vy_new)

        self.alu.state = "DONE"
        self.log(f"[FORCE] vy-= gΔt({gdt}) + drag({drag})")

    def _st_update_vx(self):
        dt = self.accs[7].reg.value
        a9, a10 = self.accs[8], self.accs[9]
        Ktab = self.accs[6].reg.value
        speed = int((a9.reg.value**2 + a10.reg.value**2) ** 0.5)
        K = (Ktab * speed) // 10000
        dv = (K * dt) // 100
        vx_new = a9.reg.value - dv

        self.alu.state = "CALC"
        self.pulse_path(self.accs[6], self.alu, FUNC, "dragK")
        self.pulse_path(self.alu, a9, CTRL, "vx'")
        a9.reg.set(vx_new)
        self.alu.state = "DONE"
        self.log(f"[DRAG] vx-= {dv}")

    def _st_check_ground(self):
        y = self.accs[11].reg.value
        if y <= 0 and self.state.loop > 1:
            last_y = y - ((self.accs[9].reg.value * self.accs[7].reg.value) // 100)
            if y != last_y:
                frac = abs(last_y) / (abs(y) + abs(last_y))
            else:
                frac = 0.5
            dx_step = (self.accs[8].reg.value * self.accs[7].reg.value) // 100
            self.state.range_x = self.accs[10].reg.value - dx_step + int(dx_step * frac)
            self.state.done = True
            self.log("[MP] Ground reached → Punch")
            self.step_index = 9
        else:
            self.log("[MP] Continue loop")

    def _st_punch(self):
        self.punch.state = "RECV"
        self.pulse_path(self.accs[10], self.punch, RESULT, "x")
        self.pulse_path(self.accs[11], self.punch, RESULT, "y")
        self.log(f"[PUNCH] x={self.accs[10].reg.value:010d}, y={self.accs[11].reg.value:010d}")
        if self.state.done:
            self.log(f"[RESULT] Range≈{self.state.range_x:010d}, ApexY={self.state.apex_y:010d}")
        self.punch.state = "DONE"

    # ----- 실행/렌더 -----
    def run_step(self):
        if self.step_index >= len(self.scenario):
            self.step_index = 4
        _, fn = self.scenario[self.step_index]
        fn()
        if self.step_index == 9:
            if not self.state.done:
                self.step_index = 4
        else:
            self.step_index += 1

    def update(self, dt):
        for p in self.pulses:
            p.update(dt)
        self.pulses = [p for p in self.pulses if not p.done]

    def draw(self, screen):
        for node in (self.reader, self.tx, self.func, self.master, self.punch):
            node.draw_box(screen, self.font)
        for a in self.accs: a.draw(screen, self.font)
        self.alu.draw(screen, self.font)
        for w in self.wires: w.draw(screen, active=False)
        for p in self.pulses: p.draw(screen, self.small)
        screen.blit(self.big.render("ENIAC Ballistics – Expanded (fixed)", True, TEXT), (30, 18))
        screen.blit(self.small.render("Play/Pause/Step/Reset & Presets; Colored pulses: DATA/CTRL/FUNC/CARD/RESULT", True, MUTED), (30, 46))
        self._draw_hud(screen)
        self._draw_buttons(screen)

    def _draw_hud(self, screen):
        r = pygame.Rect(300, H - 220, W - 330, 190)
        pygame.draw.rect(screen, (36, 40, 50), r, border_radius=12)
        pygame.draw.rect(screen, BORDER, r, 2, border_radius=12)

        a9, a10, a11, a12 = self.accs[8], self.accs[9], self.accs[10], self.accs[11]
        headers = ["t(s)", "loop", "x(*1e2)", "y(*1e2)", "vx(*1e2)", "vy(*1e2)", "range(*1e2)", "apexY(*1e2)"]
        values = [
            f"{self.state.t/100:.2f}", f"{self.state.loop}",
            f"{a11.reg.value:010d}", f"{a12.reg.value:010d}",
            f"{a9.reg.value:010d}", f"{a10.reg.value:010d}",
            f"{self.state.range_x:010d}", f"{self.state.apex_y:010d}"
        ]
        x0, y0 = r.x + 16, r.y + 16
        for i, h in enumerate(headers):
            screen.blit(self.font.render(h, True, FUNC if i < 2 else TEXT), (x0 + i * 145, y0))
        for i, v in enumerate(values):
            screen.blit(self.font.render(v, True, TEXT), (x0 + i * 145, y0 + 28))

        legend = [("DATA", DATA), ("CTRL", CTRL), ("FUNC", FUNC), ("CARD", CARD), ("RESULT", RESULT)]
        lx = x0
        for name, col in legend:
            pygame.draw.circle(screen, col, (lx, y0 + 72), 6)
            screen.blit(self.small.render(name, True, MUTED), (lx + 12, y0 + 62))
            lx += 92
        ports = "Accumulator Ports: inputs α..ε  | outputs A/S"
        screen.blit(self.small.render(ports, True, MUTED), (x0, y0 + 100))
        if self.func_table_note:
            screen.blit(self.small.render(f"FunctionTable: {self.func_table_note}", True, (210, 214, 224)), (x0, y0 + 122))

        # 로그
        lx2, ly2 = 30, H - 220
        logr = pygame.Rect(lx2, ly2, 240, 190)
        pygame.draw.rect(screen, (36, 40, 50), logr, border_radius=12)
        pygame.draw.rect(screen, BORDER, logr, 2, border_radius=12)
        screen.blit(self.font.render("Event Log", True, TEXT), (lx2 + 10, ly2 + 8))
        for i, line in enumerate(self.logs[-9:]):
            screen.blit(self.small.render(line, True, (210, 214, 224)), (lx2 + 10, ly2 + 34 + i * 18))

    def _draw_buttons(self, screen):
        self.btn_play.enabled = not self.auto
        self.btn_pause.enabled = self.auto
        self.btn_play.draw(screen, self.font, active=False)
        self.btn_pause.draw(screen, self.font, active=False)
        self.btn_step.draw(screen, self.font, active=False)
        self.btn_reset.draw(screen, self.font, active=False)
        self.btn_p1.draw(screen, self.font, active=False)
        self.btn_p2.draw(screen, self.font, active=False)
        self.btn_p3.draw(screen, self.font, active=False)

    # ----- 제어 -----
    def on_click(self, pos):
        if self.btn_play.hit(pos): self.auto = True
        elif self.btn_pause.hit(pos): self.auto = False
        elif self.btn_step.hit(pos): self.run_step()
        elif self.btn_reset.hit(pos): self.reset()
        elif self.btn_p1.hit(pos): self.preset_select(1)
        elif self.btn_p2.hit(pos): self.preset_select(2)
        elif self.btn_p3.hit(pos): self.preset_select(3)

    def preset_select(self, idx):
        if idx == 1: self.set_preset(45.0, 250.0)
        elif idx == 2: self.set_preset(30.0, 300.0)
        elif idx == 3: self.set_preset(60.0, 220.0)
        self.reset()

    def reset(self):
        for a in self.accs:
            a.reg.set(0); a.state = "IDLE"
        for n in (self.reader, self.tx, self.func, self.master, self.punch): n.state = "IDLE"
        self.alu.state = "IDLE"
        self.pulses.clear()
        self.logs.clear()
        self.state = BallisticState()
        self.func_table_note = ""
        self.scenario = self._build_scenario()
        self.step_index = 0
        # 입력 재적용
        self._st_card_tx(); self._st_tx_to_acc(); self._st_func_trig(); self._st_init_vec()
        self.step_index = 4  # 루프 시작 직전으로 위치

# ---------- 메인 ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ENIAC Ballistics – Expanded (fixed)")
    clock = pygame.time.Clock()

    ctx = Context()
    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
    ctx.small = pygame.font.SysFont(FONT_NAME, 14)
    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)

    auto_timer = 0.0
    interval = 0.9
    running = True

    # 가시성: 초기 입력/상수/벡터 초기화 후 루프 준비
    ctx._st_card_tx(); ctx._st_tx_to_acc(); ctx._st_func_trig(); ctx._st_init_vec()
    ctx.step_index = 4  # Loop Start부터

    while running:
        dt = clock.tick(FPS) / 1000.0
        interval = 0.38 if ctx.fast else 0.9

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q): running = False
                elif e.key == pygame.K_SPACE: ctx.auto = not ctx.auto
                elif e.key == pygame.K_n: ctx.run_step()
                elif e.key == pygame.K_r: ctx.reset()
                elif e.key == pygame.K_f: ctx.fast = not ctx.fast
                elif e.key == pygame.K_1: ctx.preset_select(1)
                elif e.key == pygame.K_2: ctx.preset_select(2)
                elif e.key == pygame.K_3: ctx.preset_select(3)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                ctx.on_click(e.pos)

        if ctx.auto and not ctx.state.done:
            auto_timer += dt
            if auto_timer >= interval:
                auto_timer = 0.0
                ctx.run_step()

        ctx.update(dt)
        screen.fill(BG)
        ctx.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
