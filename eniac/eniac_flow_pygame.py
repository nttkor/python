# eniac_flow_pygame.py
# --------------------------------------------
# ENIAC 전체 연산 흐름(입력 → 계수기 → 연산기 → 결과)의
# 개념적 애니메이션 시뮬레이션 (Pygame)
#
# 실행 방법:
#   pip install pygame
#   python eniac_flow_pygame.py
#
# 조작법:
#   SPACE : 시작/일시정지
#   N     : 한 단계(스텝) 진행
#   R     : 리셋
#   1/2/3 : 데모 시나리오 선택 (덧셈/곱셈/혼합)
#   F     : 빠르게 전개(토글)
#   ESC/Q : 종료
#
# 주의:
#  - 실제 ENIAC의 모든 세부 하드웨어 타이밍을 재현하지 않고,
#    "십진 병렬 전송"과 "계수기 중심의 분산 연산" 개념을 시각화하는 데 목적이 있습니다.
#  - 구성 요소: 카드 리더(입력), 20개 계수기(레지스터), 가산/감산, 곱셈기, 나눗셈/제곱근, 펀처(출력), 함수테이블(상수)
#  - 데이터는 10자리 십진수로 표기되며, 자리올림을 단순 모델로 표현합니다.
#
# 제작: ChatGPT (Pygame demo)
# --------------------------------------------

import math
import random
import sys

import pygame

# ---------- 설정 ----------
W, H = 1280, 800
FPS = 60

BG = (20, 22, 26)
PANEL = (32, 36, 44)
TEXT = (230, 232, 240)
MUTED = (150, 154, 165)
ACC_BG = (48, 52, 62)
ACC_HI = (88, 180, 255)
DATA = (44, 188, 110)
CTRL = (255, 196, 66)
ERR = (255, 90, 90)
WIRE = (88, 96, 110)
WIRE_ACTIVE = (255, 255, 255)

FONT_NAME = "consolas"

random.seed(42)


# ---------- 유틸 ----------
def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


# ---------- 그래픽 프리미티브 ----------
class Pulse:
    """배선 위를 이동하는 데이터/제어 펄스(점)."""

    def __init__(self, path, color, speed=300.0, label=""):
        self.path = path  # [ (x,y), (x,y), ... ]
        self.color = color
        self.speed = speed
        self.label = label
        self.seg_index = 0
        self.pos = path[0]
        self.done = False

    def update(self, dt):
        if self.done or self.seg_index >= len(self.path) - 1:
            self.done = True
            return

        x1, y1 = self.path[self.seg_index]
        x2, y2 = self.path[self.seg_index + 1]
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.seg_index += 1
            return

        dirx, diry = dx / dist, dy / dist
        move = self.speed * dt
        nx = self.pos[0] + dirx * move
        ny = self.pos[1] + diry * move

        # 세그먼트 끝 도달 체크
        before = (self.pos[0] - x1) * dx + (self.pos[1] - y1) * dy
        after = (nx - x1) * dx + (ny - y1) * dy
        if after >= dist * dist:
            # 다음 세그먼트로
            self.seg_index += 1
            self.pos = (x2, y2)
            if self.seg_index >= len(self.path) - 1:
                self.done = True
        else:
            self.pos = (nx, ny)

    def draw(self, s, font):
        if self.done:
            return
        pygame.draw.circle(s, self.color, (int(self.pos[0]), int(self.pos[1])), 5)
        if self.label:
            img = font.render(self.label, True, self.color)
            s.blit(img, (self.pos[0] + 8, self.pos[1] - 10))


class Wire:
    """노드 간 연결선을 시각화."""

    def __init__(self, a, b, curvature=0.0, color=WIRE):
        self.a = a
        self.b = b
        self.color = color
        self.curvature = curvature  # 0이면 직선, >0이면 약간 곡선

    def get_path(self):
        ax, ay = self.a.out_pos()
        bx, by = self.b.in_pos()
        if self.curvature == 0.0:
            return [(ax, ay), (bx, by)]
        # 간단한 3점 곡선 경로
        mx = (ax + bx) / 2
        my = (ay + by) / 2 + self.curvature * 80
        return [(ax, ay), (mx, my), (bx, by)]

    def draw(self, s, active=False):
        pts = self.get_path()
        color = WIRE_ACTIVE if active else self.color
        pygame.draw.lines(s, color, False, pts, 2)


# ---------- ENIAC 구성 요소 ----------
class Node:
    """기본 박스(모듈)"""

    def __init__(self, name, x, y, w, h):
        self.name = name
        self.x, self.y, self.w, self.h = x, y, w, h

    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def in_pos(self):
        return (self.x, self.y + self.h / 2)

    def out_pos(self):
        return (self.x + self.w, self.y + self.h / 2)

    def draw_box(self, s, font, color=PANEL, title=None):
        pygame.draw.rect(s, color, self.rect(), border_radius=16)
        pygame.draw.rect(s, (80, 86, 100), self.rect(), 2, border_radius=16)
        t = title if title else self.name
        img = font.render(t, True, TEXT)
        s.blit(img, (self.x + 12, self.y + 10))


class RingDecimal:
    """10자리 십진수 저장(간단 표기). 실제 링 카운터를 원형 눈금으로 표현."""

    def __init__(self, digits=10):
        self.digits = digits
        self.value = 0  # 0~(10^digits - 1)

    def set_value(self, v):
        self.value = int(v) % (10 ** self.digits)

    def add(self, v):
        self.set_value(self.value + v)

    def sub(self, v):
        self.set_value(self.value - v)

    def draw(self, s, cx, cy, r, font):
        # 외곽
        pygame.draw.circle(s, ACC_BG, (cx, cy), r)
        pygame.draw.circle(s, (80, 86, 100), (cx, cy), r, 2)
        # 10개 눈금
        for i in range(10):
            a1 = (i / 10.0) * 2 * math.pi - math.pi / 2
            a2 = ((i + 1) / 10.0) * 2 * math.pi - math.pi / 2
            mid = (a1 + a2) / 2
            # 현재 1의 자리 값 강조
            on = (self.value % 10) == i
            rr = r - 6
            x1 = cx + rr * math.cos(a1)
            y1 = cy + rr * math.sin(a1)
            x2 = cx + rr * math.cos(a2)
            y2 = cy + rr * math.sin(a2)
            col = ACC_HI if on else (70, 74, 86)
            pygame.draw.line(s, col, (x1, y1), (x2, y2), 6)

        # 숫자 표기(최대 10자리)
        txt = f"{self.value:0{self.digits}d}"
        img = font.render(txt, True, TEXT)
        rect = img.get_rect(center=(cx, cy))
        s.blit(img, rect)


class Accumulator(Node):
    """계수기: 10자리 십진 저장 + 덧셈/뺄셈."""

    def __init__(self, name, x, y):
        super().__init__(name, x, y, 200, 120)
        self.reg = RingDecimal(10)

    def draw(self, s, font):
        self.draw_box(s, font, color=(40, 44, 54), title=f"{self.name} (Accumulator)")
        # 링 디스플레이
        cx, cy = int(self.x + self.w * 0.74), int(self.y + self.h * 0.58)
        self.reg.draw(s, cx, cy, 38, font)
        # 레이블
        lbl = font.render("10-digit decimal", True, MUTED)
        s.blit(lbl, (self.x + 12, self.y + self.h - 24))


class ALU(Node):
    """가산/감산, 곱셈, 나눗셈/제곱근 모듈을 하나의 박스에 표현."""

    def __init__(self, x, y):
        super().__init__("Arithmetic Units", x, y, 250, 280)

    def draw(self, s, font):
        self.draw_box(s, font, color=(44, 48, 60))
        # 내부 박스 3개
        names = ["Adder / Subtracter", "Multiplier", "Divider / Sqrt"]
        for i, n in enumerate(names):
            r = pygame.Rect(self.x + 14, self.y + 46 + i * 76, self.w - 28, 64)
            pygame.draw.rect(s, (50, 54, 66), r, border_radius=12)
            pygame.draw.rect(s, (88, 96, 110), r, 2, border_radius=12)
            img = font.render(n, True, TEXT)
            s.blit(img, (r.x + 10, r.y + 18))


class CardReader(Node):
    pass


class CardPunch(Node):
    pass


class FunctionTable(Node):
    pass


# ---------- 시나리오(데모 절차) ----------
class Step:
    """한 단계 동작(펄스, 값 이동, 계산 등)을 기술."""

    def __init__(self, name, action):
        self.name = name
        self.action = action  # def(ctx): -> None


class Context:
    """런타임 컨텍스트: 장치, 와이어, 펄스, 상태, 로그."""

    def __init__(self):
        self.font = None
        self.big = None
        self.small = None

        # 구성 배치
        self.reader = CardReader("Card Reader", 40, 80, 200, 120)
        self.punch = CardPunch("Card Punch", 40, 560, 200, 120)
        self.func = FunctionTable("Function Table", 40, 320, 200, 120)

        self.accs = []
        # 20개 계수기(10 x 2 열 배치)
        ax = 340
        ay = 60
        for r in range(5):
            for c in range(4):
                idx = r * 4 + c + 1
                x = ax + c * 230
                y = ay + r * 140
                self.accs.append(Accumulator(f"A{idx}", x, y))

        self.alu = ALU(W - 290, 220)

        # 와이어(대표 연결만 시각화)
        self.wires = []
        # 입력/함수테이블 → 일부 계수기
        for i in range(4):
            self.wires.append(Wire(self.reader, self.accs[i], curvature=0.3))
            self.wires.append(Wire(self.func, self.accs[i + 4], curvature=-0.2))

        # 계수기 → ALU → 다른 계수기
        for i in range(8):
            self.wires.append(Wire(self.accs[i], self.alu, curvature=0.1))
            self.wires.append(Wire(self.alu, self.accs[i + 8], curvature=-0.15))

        # 결과 → 펀처
        for i in range(8, 12):
            self.wires.append(Wire(self.accs[i], self.punch, curvature=0.1))

        self.pulses = []
        self.logs = []
        self.active_wires = set()
        self.fast = False

        # 데모 값 초기화
        for i, acc in enumerate(self.accs):
            acc.reg.set_value(0)

        # 카드/함수테이블에 있는 값(데모용)
        self.card_data = [1234567890, 3141592653]
        self.func_table_const = [981, 2718]  # 예: 중력가속도*100, e*1000 (임의)

        # 상태
        self.step_index = 0
        self.paused = True

    # ---------- 도우미 ----------
    def log(self, msg):
        self.logs.append(msg)
        self.logs = self.logs[-8:]

    def pulse_wire(self, wire, color, label=""):
        path = wire.get_path()
        self.pulses.append(Pulse(path, color, speed=520 if self.fast else 320, label=label))

    def pulse_between(self, a, b, color, label=""):
        self.pulses.append(Pulse(Wire(a, b).get_path(), color, speed=520 if self.fast else 320, label=label))

    # ---------- 스텝 액션 ----------
    def step_load_from_card(self):
        # 카드 → A1, A2 로드
        a1, a2 = self.accs[0], self.accs[1]
        val1, val2 = self.card_data[0], self.card_data[1]
        self.pulse_between(self.reader, a1, DATA, "DATA")
        self.pulse_between(self.reader, a2, DATA, "DATA")
        a1.reg.set_value(val1)
        a2.reg.set_value(val2)
        self.log(f"[INPUT] Card → A1={val1:010d}, A2={val2:010d}")

    def step_load_from_function_table(self):
        # 함수테이블 상수 → A5, A6
        a5, a6 = self.accs[4], self.accs[5]
        v5, v6 = self.func_table_const
        self.pulse_between(self.func, a5, DATA, "CONST")
        self.pulse_between(self.func, a6, DATA, "CONST")
        a5.reg.set_value(v5)
        a6.reg.set_value(v6)
        self.log(f"[CONST] FuncTable → A5={v5:010d}, A6={v6:010d}")

    def step_add(self):
        # A1 + A5 → A9
        a1, a5, a9 = self.accs[0], self.accs[4], self.accs[8]
        self.pulse_between(a1, self.alu, DATA, "A1")
        self.pulse_between(a5, self.alu, DATA, "A5")
        res = a1.reg.value + a5.reg.value
        self.pulse_between(self.alu, a9, CTRL, "ADD")
        a9.reg.set_value(res)
        self.log(f"[ADD] A1 + A5 → A9 = {res:010d}")

    def step_sub(self):
        # A2 - A6 → A10
        a2, a6, a10 = self.accs[1], self.accs[5], self.accs[9]
        self.pulse_between(a2, self.alu, DATA, "A2")
        self.pulse_between(a6, self.alu, DATA, "A6")
        res = a2.reg.value - a6.reg.value
        self.pulse_between(self.alu, a10, CTRL, "SUB")
        a10.reg.set_value(res)
        self.log(f"[SUB] A2 - A6 → A10 = {res:010d}")

    def step_mul(self):
        # A9 × A10 → A12
        a9, a10, a12 = self.accs[8], self.accs[9], self.accs[11]
        self.pulse_between(a9, self.alu, DATA, "A9")
        self.pulse_between(a10, self.alu, DATA, "A10")
        res = a9.reg.value * a10.reg.value
        self.pulse_between(self.alu, a12, CTRL, "MUL")
        a12.reg.set_value(res % (10 ** 10))  # 10자리 제한 모델
        self.log(f"[MUL] A9 × A10 → A12 = {res:010d} (10자리로 절단)")

    def step_punch_result(self):
        # A12 → 카드 펀치
        a12 = self.accs[11]
        self.pulse_between(a12, self.punch, DATA, "RESULT")
        self.log(f"[OUTPUT] A12 → CardPunch = {a12.reg.value:010d}")

    # 추가 데모: 단일 덧셈/곱셈/혼합 플로우
    def build_scenario(self, mode=3):
        steps = []
        if mode == 1:  # 덧셈 데모
            steps = [
                Step("Load Card", self.step_load_from_card),
                Step("Load Const", self.step_load_from_function_table),
                Step("Add", self.step_add),
                Step("Punch", self.step_punch_result),
            ]
        elif mode == 2:  # 곱셈 데모
            steps = [
                Step("Load Card", self.step_load_from_card),
                Step("Mul (A1 × A2)", lambda: self._mul_a1_a2()),
                Step("Punch", self.step_punch_result),
            ]
        else:  # 혼합
            steps = [
                Step("Load Card", self.step_load_from_card),
                Step("Load Const", self.step_load_from_function_table),
                Step("Add", self.step_add),
                Step("Sub", self.step_sub),
                Step("Mul", self.step_mul),
                Step("Punch", self.step_punch_result),
            ]
        return steps

    def _mul_a1_a2(self):
        a1, a2, a12 = self.accs[0], self.accs[1], self.accs[11]
        self.pulse_between(a1, self.alu, DATA, "A1")
        self.pulse_between(a2, self.alu, DATA, "A2")
        res = a1.reg.value * a2.reg.value
        self.pulse_between(self.alu, a12, CTRL, "MUL")
        a12.reg.set_value(res % (10 ** 10))
        self.log(f"[MUL] A1 × A2 → A12 = {res:010d} (10자리로 절단)")


# ---------- 메인 루프 ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ENIAC Flow (Conceptual Animation)")
    clock = pygame.time.Clock()

    ctx = Context()
    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)
    ctx.small = pygame.font.SysFont(FONT_NAME, 14)

    scenario_mode = 3
    steps = ctx.build_scenario(scenario_mode)

    def run_step(i):
        if 0 <= i < len(steps):
            steps[i].action()

    t = 0.0
    auto_timer = 0.0
    auto_interval = 1.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        t += dt
        if ctx.fast:
            auto_interval = 0.4
        else:
            auto_interval = 1.0

        # 이벤트
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_SPACE:
                    ctx.paused = not ctx.paused
                elif e.key == pygame.K_n:
                    run_step(ctx.step_index)
                    ctx.step_index = min(ctx.step_index + 1, len(steps))
                elif e.key == pygame.K_r:
                    ctx = Context()
                    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
                    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)
                    ctx.small = pygame.font.SysFont(FONT_NAME, 14)
                    steps = ctx.build_scenario(scenario_mode)
                elif e.key == pygame.K_1:
                    scenario_mode = 1
                    ctx = Context()
                    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
                    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)
                    ctx.small = pygame.font.SysFont(FONT_NAME, 14)
                    steps = ctx.build_scenario(scenario_mode)
                elif e.key == pygame.K_2:
                    scenario_mode = 2
                    ctx = Context()
                    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
                    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)
                    ctx.small = pygame.font.SysFont(FONT_NAME, 14)
                    steps = ctx.build_scenario(scenario_mode)
                elif e.key == pygame.K_3:
                    scenario_mode = 3
                    ctx = Context()
                    ctx.font = pygame.font.SysFont(FONT_NAME, 18)
                    ctx.big = pygame.font.SysFont(FONT_NAME, 28, bold=True)
                    ctx.small = pygame.font.SysFont(FONT_NAME, 14)
                    steps = ctx.build_scenario(scenario_mode)
                elif e.key == pygame.K_f:
                    ctx.fast = not ctx.fast

        # 자동 진행
        if not ctx.paused and ctx.step_index < len(steps):
            auto_timer += dt
            if auto_timer >= auto_interval:
                auto_timer = 0.0
                run_step(ctx.step_index)
                ctx.step_index += 1

        # 펄스 업데이트
        for p in ctx.pulses:
            p.update(dt)
        ctx.pulses = [p for p in ctx.pulses if not p.done]

        # ---------- 그리기 ----------
        screen.fill(BG)

        # 좌측 패널: IO/Function
        for node in (ctx.reader, ctx.func, ctx.punch):
            node.draw_box(screen, ctx.font)

        # 계수기들
        for acc in ctx.accs:
            acc.draw(screen, ctx.font)

        # ALU
        ctx.alu.draw(screen, ctx.font)

        # 와이어
        for w in ctx.wires:
            w.draw(screen, active=False)

        # 펄스
        for p in ctx.pulses:
            p.draw(screen, ctx.small)

        # 헤더/도움말
        title = ctx.big.render("ENIAC Conceptual Flow (Decimal, Plugboard-Programmed)", True, TEXT)
        screen.blit(title, (40, 20))
        hint = ctx.small.render("SPACE:재생/일시정지  N:스텝  R:리셋  1/2/3:시나리오  F:빠르게  Q/ESC:종료", True, MUTED)
        screen.blit(hint, (40, 54))

        # 상태 텍스트
        stat = f"Scenario: {scenario_mode}  Step: {ctx.step_index}/{len(steps)}  Fast:{'ON' if ctx.fast else 'OFF'}  {'PAUSED' if ctx.paused else 'RUN'}"
        stimg = ctx.small.render(stat, True, TEXT)
        screen.blit(stimg, (W - stimg.get_width() - 20, 20))

        # 로그
        logx, logy = W - 560, H - 180
        pygame.draw.rect(screen, (36, 40, 50), pygame.Rect(logx - 16, logy - 16, 540, 160), border_radius=12)
        pygame.draw.rect(screen, (80, 86, 100), pygame.Rect(logx - 16, logy - 16, 540, 160), 2, border_radius=12)
        screen.blit(ctx.font.render("Event Log", True, TEXT), (logx, logy - 10))
        for i, line in enumerate(ctx.logs):
            img = ctx.small.render(line, True, (210, 214, 224))
            screen.blit(img, (logx, logy + 18 + i * 18))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
