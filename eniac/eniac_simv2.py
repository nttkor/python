# ENIAC Simulator (Cycle-level, Single-File, Pygame UI)
# -----------------------------------------------------
# 특징
# - 누산기(Accumulator) 기반의 추상 사이클 모델
# - Play / Pause / Step / Reset 버튼
# - 예시 프로그램: (a-b) -> ACC4, (c + 2*b + 359) -> ACC6, 그리고 ACC5 += 359
# - 간단한 "플러그보드 친화형" 미니 DSL 없이, ProgramStep 시퀀스를 통해 동작을 정의
#   (필요시 아래 ProgramBuilder 섹션을 확장하여 DSL 파서를 붙일 수 있음)
# - 숫자 표현: 10진 정수(파이썬 int) 사용. 부호는 정수의 부호로 표현.
# - 20자리 제한 로직 포함(오버플로는 클램핑/표시만 수행)
#
# 실행 방법
#   pip install pygame
#   python eniac_simulator_single_file.py
#
# 조작법
#   - Space: Play/Pause 토글
#   - N: Step 1회
#   - R: Reset
#   - 숫자 편집: 마우스로 누산기 패널 클릭 → 텍스트 입력 → Enter 확정
#   - 속도: 우측 하단 슬라이더(틱 간격)
#
# 주의: 본 구현은 "사이클-추상(Cycle-level)" 모델입니다. 실제 ENIAC의 펄스/페이즈를 단순화했습니다.
#       A/S(정상/보수) 포트는 송신 시 부호(+/-)로 모사합니다(A=+value, S=-value).
# -----------------------------------------------------

import math
import sys
import pygame
from dataclasses import dataclass, field
from typing import Callable, List, Optional

# ------------------------ Config ------------------------
MAX_DIGITS = 20            # ENIAC 누산기 자리수 한계(표현상)
WINDOW_W, WINDOW_H = 1100, 720
FPS = 60
FONT_NAME = "consolas"

# --------------------- Utility funcs --------------------

def clamp_to_digits(value: int, max_digits: int = MAX_DIGITS) -> int:
    """고정 자릿수(10진) 한계를 넘으면 클램핑(표시 목적).
    실제 ENIAC은 자리올림/오버플로 신호가 있었지만 여기선 경고 플래그만 둔다.
    """
    if value == 0:
        return 0
    sign = -1 if value < 0 else 1
    s = str(abs(value))
    if len(s) > max_digits:
        s = s[-max_digits:]  # 최상위 오버플로를 잘라냄(가시화 목적)
    return sign * int(s)


def fmt_value(value: int) -> str:
    s = str(value)
    # 가독성을 위해 천단위 구분은 생략, 단순 부호/숫자
    return s

# ----------------------- Core Model ---------------------

@dataclass
class Accumulator:
    name: str
    value: int = 0
    max_digits: int = MAX_DIGITS
    overflow: bool = False

    def clear(self):
        self.value = 0
        self.overflow = False

    def set(self, v: int):
        self.value = clamp_to_digits(v, self.max_digits)
        self.overflow = len(str(abs(v))) > self.max_digits

    def add(self, v: int):
        raw = self.value + v
        self.overflow = len(str(abs(raw))) > self.max_digits
        self.value = clamp_to_digits(raw, self.max_digits)

    def sub(self, v: int):
        self.add(-v)

    def transmit_A(self) -> int:
        return self.value

    def transmit_S(self) -> int:
        return -self.value

# ---------------- Program / Scheduler -------------------

@dataclass
class ProgramStep:
    """한 사이클에 실행되는 단일 동작.
    func: (state) -> None 를 호출한다. 완료 후 자동으로 다음 스텝으로 진행.
    label: UI 표시에 쓰이는 간단한 설명.
    """
    label: str
    func: Callable[["ENIACState"], None]

@dataclass
class ENIACState:
    accs: dict
    tick_count: int = 0

    def reset(self):
        self.tick_count = 0
        for a in self.accs.values():
            a.clear()

# ---------------- Program Builder (example) --------------

class ProgramBuilder:
    """예시 프로그램을 구성한다.
    - (a-b) -> ACC4
    - (c + 2*b + 359) -> ACC6
    - ACC5 += 359

    실제 ENIAC 플러그보드 동작을 요약/단순화한 사이클 시퀀스로 구성.
    """

    def __init__(self, state: ENIACState):
        self.state = state
        self.steps: List[ProgramStep] = []

    def add_step(self, label: str, func: Callable[[ENIACState], None]):
        self.steps.append(ProgramStep(label, func))

    def build(self):
        acc = self.state.accs

        # --- 예시 스텝 시퀀스 ---
        # 0) 초기화는 외부 Reset에서 실행됨

        # 1) ACC4 <- a
        self.add_step("ACC4 <- a (load)", lambda st: acc["ACC4"].set(acc["ACC2"].transmit_A()))
        # 2) ACC4 -= b
        self.add_step("ACC4 -= b", lambda st: acc["ACC4"].sub(acc["ACC3"].transmit_A()))

        # 3) ACC6 <- c
        self.add_step("ACC6 <- c (load)", lambda st: acc["ACC6"].set(acc["ACC1"].transmit_A()))
        # 4) ACC6 += b
        self.add_step("ACC6 += b", lambda st: acc["ACC6"].add(acc["ACC3"].transmit_A()))
        # 5) ACC6 += b (repeat)
        self.add_step("ACC6 += b (repeat)", lambda st: acc["ACC6"].add(acc["ACC3"].transmit_A()))
        # 6) ACC6 += 359 (CT)
        self.add_step("ACC6 += 359", lambda st: acc["ACC6"].add(359))

        # 7) ACC5 += 359
        self.add_step("ACC5 += 359", lambda st: acc["ACC5"].add(359))

        return self.steps

# ------------------------ UI ----------------------------

class Button:
    def __init__(self, rect, text, on_click: Callable[[], None]):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.hover = False
        self.enabled = True

    def draw(self, surf, font):
        color = (30, 30, 30)
        bg = (200, 200, 200) if self.enabled else (120, 120, 120)
        if self.hover and self.enabled:
            bg = (220, 220, 220)
        pygame.draw.rect(surf, bg, self.rect, border_radius=12)
        pygame.draw.rect(surf, color, self.rect, 2, border_radius=12)
        txt = font.render(self.text, True, color)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, e):
        if not self.enabled:
            return
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                self.on_click()

class Slider:
    def __init__(self, rect, min_v, max_v, value):
        self.rect = pygame.Rect(rect)
        self.min_v, self.max_v = min_v, max_v
        self.value = value
        self.dragging = False

    def draw(self, surf):
        x, y, w, h = self.rect
        pygame.draw.rect(surf, (200, 200, 200), self.rect, border_radius=8)
        # knob position
        t = (self.value - self.min_v) / (self.max_v - self.min_v)
        knob_x = x + int(t * w)
        pygame.draw.circle(surf, (40, 40, 40), (knob_x, y + h // 2), h // 2)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                self.dragging = True
                self._set_from_mouse(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.dragging = False
        elif e.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(e.pos)

    def _set_from_mouse(self, pos):
        x, y = pos
        rx, ry, rw, rh = self.rect
        t = (x - rx) / max(1, rw)
        t = min(max(0.0, t), 1.0)
        self.value = self.min_v + t * (self.max_v - self.min_v)

class InputBox:
    def __init__(self, rect, text=""):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.active = False

    def draw(self, surf, font):
        color = (20, 20, 20)
        bg = (250, 250, 250) if self.active else (235, 235, 235)
        pygame.draw.rect(surf, bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, color, self.rect, 2, border_radius=8)
        txt = font.render(self.text, True, color)
        surf.blit(txt, (self.rect.x + 8, self.rect.y + 6))

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.active = self.rect.collidepoint(e.pos)
        if not self.active:
            return None
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                self.active = False
                try:
                    return int(self.text)
                except ValueError:
                    return None
            elif e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                ch = e.unicode
                if ch in "-0123456789":
                    self.text += ch
        return None

# ---------------------- App -----------------------------

class ENIACSimApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("ENIAC Simulator – Cycle Mode")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 20)
        self.font_small = pygame.font.SysFont(FONT_NAME, 16)
        self.font_big = pygame.font.SysFont(FONT_NAME, 26)

        # Core state
        accs = {
            "ACC1": Accumulator("ACC1"),  # c
            "ACC2": Accumulator("ACC2"),  # a
            "ACC3": Accumulator("ACC3"),  # b
            "ACC4": Accumulator("ACC4"),  # a-b
            "ACC5": Accumulator("ACC5"),  # +=359
            "ACC6": Accumulator("ACC6"),  # c + 2b + 359
        }
        self.state = ENIACState(accs=accs)

        # Default inputs for demo
        accs["ACC1"].set(1000)  # c
        accs["ACC2"].set(12345) # a
        accs["ACC3"].set(678)   # b

        # Program
        self.builder = ProgramBuilder(self.state)
        self.program: List[ProgramStep] = self.builder.build()
        self.pc_index = 0
        self.running = False
        self.ms_per_tick = 500  # 슬로우 디폴트
        self.time_acc = 0

        # UI controls
        self.btn_play = Button((30, 30, 120, 40), "Play", self.toggle_play)
        self.btn_step = Button((160, 30, 120, 40), "Step", self.step_once)
        self.btn_reset = Button((290, 30, 120, 40), "Reset", self.reset)
        self.slider = Slider((WINDOW_W-320, WINDOW_H-60, 280, 20), 80, 1000, self.ms_per_tick)

        # Editable inputs for a,b,c
        self.inputs = {
            "ACC2": InputBox((40, 140, 220, 34), text=str(self.state.accs["ACC2"].value)),
            "ACC3": InputBox((40, 220, 220, 34), text=str(self.state.accs["ACC3"].value)),
            "ACC1": InputBox((40, 300, 220, 34), text=str(self.state.accs["ACC1"].value)),
        }

    # ---- Control logic ----
    def toggle_play(self):
        if self.pc_index >= len(self.program):
            self.pc_index = 0
        self.running = not self.running

    def step_once(self):
        if self.pc_index < len(self.program):
            step = self.program[self.pc_index]
            step.func(self.state)
            self.state.tick_count += 1
            self.pc_index += 1
        else:
            self.running = False

    def reset(self):
        self.state.reset()
        # 입력값은 유지(실기에서 Reset은 레지스터 클리어이므로 입력칸에 다시 세팅)
        for key, box in self.inputs.items():
            try:
                v = int(box.text)
            except ValueError:
                v = 0
            self.state.accs[key].set(v)
        self.pc_index = 0
        self.running = False

    # ---- Main loop ----
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.ms_per_tick = self.slider.value
            if self.running:
                self.time_acc += dt
                if self.time_acc >= self.ms_per_tick:
                    self.time_acc = 0
                    self.step_once()
            self.draw()

    # ---- Event handling ----
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    self.toggle_play()
                elif e.key == pygame.K_n:
                    self.step_once()
                elif e.key == pygame.K_r:
                    self.reset()
            # buttons, slider
            self.btn_play.handle_event(e)
            self.btn_step.handle_event(e)
            self.btn_reset.handle_event(e)
            self.slider.handle_event(e)
            # inputs
            for key, box in self.inputs.items():
                out = box.handle_event(e)
                if out is not None:
                    self.state.accs[key].set(out)

    # ---- Drawing ----
    def draw(self):
        self.screen.fill((248, 248, 248))
        # Title
        title = self.font_big.render("ENIAC Simulator (Cycle Mode)", True, (20, 20, 20))
        self.screen.blit(title, (30, 90))

        # Buttons
        self.btn_play.text = "Pause" if self.running else "Play"
        self.btn_play.draw(self.screen, self.font)
        self.btn_step.draw(self.screen, self.font)
        self.btn_reset.draw(self.screen, self.font)

        # Slider label
        lab = self.font.render(f"Tick: {int(self.ms_per_tick)} ms", True, (40, 40, 40))
        self.screen.blit(lab, (WINDOW_W-320, WINDOW_H-90))
        self.slider.draw(self.screen)

        # Left input panel
        self.draw_input_panel()

        # Accumulator panels
        self.draw_acc_panels()

        # Program panel
        self.draw_program_panel()

        pygame.display.flip()

    def draw_input_panel(self):
        x, y, w, h = 30, 120, 280, 240
        pygame.draw.rect(self.screen, (230, 235, 245), (x, y, w, h), border_radius=16)
        pygame.draw.rect(self.screen, (120, 130, 150), (x, y, w, h), 2, border_radius=16)
        t = self.font.render("Inputs (Editable)", True, (20, 20, 20))
        self.screen.blit(t, (x + 12, y + 10))

        y0 = y + 40
        for key, label in [("ACC2", "a"), ("ACC3", "b"), ("ACC1", "c")]:
            lab = self.font.render(f"{label} -> {key}", True, (20, 20, 20))
            self.screen.blit(lab, (x + 12, y0))
            self.inputs[key].draw(self.screen, self.font)
            y0 += 80

    def draw_acc_panels(self):
        names = ["ACC1", "ACC2", "ACC3", "ACC4", "ACC5", "ACC6"]
        cols = 3
        card_w, card_h = 320, 120
        gap_x, gap_y = 20, 18
        start_x, start_y = 330, 120

        for i, nm in enumerate(names):
            r = pygame.Rect(
                start_x + (i % cols) * (card_w + gap_x),
                start_y + (i // cols) * (card_h + gap_y),
                card_w, card_h,
            )
            self.draw_acc_card(r, self.state.accs[nm])

    def draw_acc_card(self, rect: pygame.Rect, acc: Accumulator):
        pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=16)
        pygame.draw.rect(self.screen, (180, 180, 180), rect, 2, border_radius=16)
        name = self.font.render(acc.name, True, (20, 20, 20))
        self.screen.blit(name, (rect.x + 12, rect.y + 10))

        val = self.font_big.render(fmt_value(acc.value), True, (0, 80, 110))
        self.screen.blit(val, (rect.x + 12, rect.y + 46))

        info = []
        if acc.overflow:
            info.append("OVERFLOW")
        if info:
            tag = self.font_small.render(", ".join(info), True, (160, 40, 40))
            self.screen.blit(tag, (rect.x + 12, rect.y + rect.h - 28))

    def draw_program_panel(self):
        x, y, w, h = 30, 380, WINDOW_W - 60, WINDOW_H - 420
        pygame.draw.rect(self.screen, (235, 245, 235), (x, y, w, h), border_radius=16)
        pygame.draw.rect(self.screen, (120, 150, 120), (x, y, w, h), 2, border_radius=16)
        t = self.font.render("Program (one step per cycle)", True, (20, 20, 20))
        self.screen.blit(t, (x + 12, y + 10))

        # Steps list
        y_line = y + 44
        for i, st in enumerate(self.program):
            mark = ">" if i == self.pc_index else " "
            line = self.font.render(f"{mark} [{i:02}] {st.label}", True, (20, 20, 20))
            self.screen.blit(line, (x + 12, y_line))
            y_line += 28

        # Status
        stat = self.font.render(
            f"Tick={self.state.tick_count} / PC={self.pc_index}/{len(self.program)}", True, (20, 60, 20)
        )
        self.screen.blit(stat, (x + w - 340, y + 10))

# ---------------------- Main ----------------------------

if __name__ == "__main__":
    app = ENIACSimApp()
    app.run()
