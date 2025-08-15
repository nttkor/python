# eniac_sim.py
# --------------------------------------------------------------
# ENIAC-Style Simulation (Simplified) – Pygame
# - 플레이/포즈, 스텝, 리셋 버튼 포함
# - Space: 재생/일시정지, S: 한 스텝 수행, R: 리셋, F11: 전체화면 토글
# - 슬라이더로 실행 속도 조절(틱/초)
# - 데모 프로그램: 1부터 N까지의 합을 구함 (가산기/루프 계수기 흉내)
# --------------------------------------------------------------
import math
import sys
from dataclasses import dataclass, field
from typing import List, Callable, Optional

import pygame

# ---------------- 기본 설정 ----------------
WIN_W, WIN_H = 1000, 680
FPS = 60

# 색상 팔레트
BG = (18, 18, 22)
PANEL = (28, 28, 34)
CARD = (36, 36, 44)
ACCENT = (92, 175, 255)
ACCENT_DIM = (60, 120, 175)
TEXT = (230, 230, 235)
MUTED = (160, 165, 175)
OK = (90, 200, 140)
WARN = (255, 180, 80)
ERR = (255, 100, 120)

pygame.init()
pygame.display.set_caption("ENIAC Simulation (Simplified)")
screen = pygame.display.set_mode((WIN_W, WIN_H))
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas,malgun gothic,applegothic", 20)
font_small = pygame.font.SysFont("consolas,malgun gothic,applegothic", 16)
font_big = pygame.font.SysFont("consolas,malgun gothic,applegothic", 28)

# ---------------- UI 위젯 ----------------
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    on_click: Callable[[], None]
    enabled: bool = True
    toggled: bool = False

    def draw(self, surf: pygame.Surface):
        color = (70, 70, 80) if self.enabled else (45, 45, 55)
        if self.toggled:
            color = (50, 90, 140)
        pygame.draw.rect(surf, color, self.rect, border_radius=12)
        pygame.draw.rect(surf, (15, 15, 18), self.rect, 2, border_radius=12)
        label = font.render(self.label, True, TEXT if self.enabled else MUTED)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, ev: pygame.event.Event):
        if not self.enabled:
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.on_click()

@dataclass
class Slider:
    # 수평 슬라이더 (값 범위 [min_v, max_v])
    rect: pygame.Rect
    min_v: float
    max_v: float
    value: float
    dragging: bool = False

    def draw(self, surf: pygame.Surface, title: str):
        # 바
        pygame.draw.rect(surf, (55, 55, 65), self.rect, border_radius=8)
        # 채움
        ratio = (self.value - self.min_v) / (self.max_v - self.min_v)
        fill_w = int(self.rect.w * ratio)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.h)
        pygame.draw.rect(surf, (85, 120, 160), fill_rect, border_radius=8)
        pygame.draw.rect(surf, (15, 15, 18), self.rect, 2, border_radius=8)
        # 손잡이
        knob_x = self.rect.x + fill_w
        knob = pygame.Rect(knob_x - 6, self.rect.centery - 10, 12, 20)
        pygame.draw.rect(surf, (200, 205, 215), knob, border_radius=6)

        t = font_small.render(f"{title}: {self.value:.1f}", True, TEXT)
        surf.blit(t, (self.rect.x, self.rect.y - 22))

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.dragging = True
                self._update_by_mouse(ev.pos[0])
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.dragging = False
        elif ev.type == pygame.MOUSEMOTION and self.dragging:
            self._update_by_mouse(ev.pos[0])

    def _update_by_mouse(self, x: int):
        ratio = (x - self.rect.x) / self.rect.w
        ratio = max(0.0, min(1.0, ratio))
        self.value = self.min_v + ratio * (self.max_v - self.min_v)

# ---------------- ENIAC 스타일 구성요소(간소화) ----------------
@dataclass
class Accumulator:
    """10진 가산기 – 정수만 다룸(부호 포함)."""
    value: int = 0
    max_digits: int = 10  # 표시용

    def clear(self):
        self.value = 0

    def add(self, n: int):
        self.value += n

    def sub(self, n: int):
        self.value -= n

    def draw(self, surf: pygame.Surface, rect: pygame.Rect, title="ACCUMULATOR"):
        pygame.draw.rect(surf, CARD, rect, border_radius=16)
        pygame.draw.rect(surf, (15, 15, 18), rect, 2, border_radius=16)
        t = font_big.render(title, True, TEXT)
        surf.blit(t, (rect.x + 16, rect.y + 12))

        # 값 표시(고정 자리수)
        s = f"{self.value:+d}"
        surf.blit(font.render("VALUE", True, MUTED), (rect.x + 16, rect.y + 56))
        val = font_big.render(s, True, OK if self.value >= 0 else ERR)
        surf.blit(val, (rect.x + 16, rect.y + 80))

@dataclass
class LoopCounter:
    """루프 카운터: N부터 1까지 감소, 0이 되면 루프 종료."""
    n: int = 0
    current: int = 0
    active: bool = False

    def load(self, n: int):
        self.n = n
        self.current = n
        self.active = True

    def step(self) -> bool:
        """1 감소. 0이면 False(루프 끝), 그 외 True(계속)."""
        if not self.active:
            return False
        self.current -= 1
        if self.current <= 0:
            self.active = False
            return False
        return True

    def draw(self, surf: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(surf, CARD, rect, border_radius=16)
        pygame.draw.rect(surf, (15, 15, 18), rect, 2, border_radius=16)
        t = font_big.render("LOOP COUNTER", True, TEXT)
        surf.blit(t, (rect.x + 16, rect.y + 12))
        surf.blit(font.render("TARGET N", True, MUTED), (rect.x + 16, rect.y + 56))
        surf.blit(font_big.render(str(self.n), True, TEXT), (rect.x + 16, rect.y + 80))
        surf.blit(font.render("CURRENT", True, MUTED), (rect.x + 16, rect.y + 120))
        surf.blit(font_big.render(str(self.current), True, ACCENT if self.active else MUTED), (rect.x + 16, rect.y + 144))

# ---------------- 시뮬레이터 코어 ----------------
@dataclass
class Instruction:
    """아주 단순한 의사 명령 집합"""
    op: str
    arg: int = 0

@dataclass
class Program:
    """데모 프로그램: 1..N 합산
       의사코드:
         ACC <- 0
         i <- 1
         while i <= N:
             ACC <- ACC + i
             i <- i + 1
       아래는 이를 미시적 '스텝'으로 쪼갠 형태.
    """
    N: int
    pc: int = 0
    steps: List[Instruction] = field(default_factory=list)

    def __post_init__(self):
        # 프로그램 구성
        self.steps = [
            Instruction("CLR_ACC"),        # 0
            Instruction("LOAD_LOOP", self.N), # 1: 루프 카운터 N 로드
            Instruction("SET_I", 1),       # 2: i=1
            # 루프 시작 지점 (pc=3)
            Instruction("ADD_I"),          # 3: ACC += i
            Instruction("INC_I"),          # 4: i += 1
            Instruction("LOOP_CHECK"),     # 5: i<=N ? 계속 : 종료
            Instruction("JMP", 3),         # 6: 루프 본문으로 점프
            Instruction("HALT"),           # 7
        ]

    def reset(self):
        self.pc = 0

@dataclass
class ENIACSim:
    program: Program
    acc: Accumulator = field(default_factory=Accumulator)
    loop: LoopCounter = field(default_factory=LoopCounter)
    i_reg: int = 0
    halted: bool = False

    # 시간 관련
    tick_rate: float = 4.0  # 초당 스텝 수
    _tick_accum: float = 0.0
    playing: bool = False

    def reset(self):
        self.acc.clear()
        self.loop = LoopCounter()
        self.program.reset()
        self.i_reg = 0
        self.halted = False
        self.playing = False
        self._tick_accum = 0.0

    def step_once(self):
        if self.halted:
            return

        if self.program.pc < 0 or self.program.pc >= len(self.program.steps):
            self.halted = True
            return

        ins = self.program.steps[self.program.pc]
        self._exec(ins)

    def _exec(self, ins: Instruction):
        op = ins.op
        # 각 스텝은 하드웨어적 '펄스'처럼 동작한다고 가정
        if op == "CLR_ACC":
            self.acc.clear()
            self.program.pc += 1
        elif op == "LOAD_LOOP":
            self.loop.load(ins.arg)
            self.program.pc += 1
        elif op == "SET_I":
            self.i_reg = ins.arg
            self.program.pc += 1
        elif op == "ADD_I":
            self.acc.add(self.i_reg)
            self.program.pc += 1
        elif op == "INC_I":
            self.i_reg += 1
            self.program.pc += 1
        elif op == "LOOP_CHECK":
            # i <= N 이면 계속, 아니면 다음(HALT)으로
            if self.i_reg <= self.loop.n:
                self.program.pc += 1  # 다음은 JMP
            else:
                self.program.pc = 7   # HALT
        elif op == "JMP":
            self.program.pc = ins.arg
        elif op == "HALT":
            self.halted = True
        else:
            # 알 수 없는 명령: 정지
            self.halted = True

    def update(self, dt: float):
        if not self.playing or self.halted:
            return
        self._tick_accum += dt
        tick_len = 1.0 / max(0.5, self.tick_rate)
        while self._tick_accum >= tick_len and not self.halted:
            self._tick_accum -= tick_len
            self.step_once()

    # ---------------- 렌더링 ----------------
    def draw(self, surf: pygame.Surface):
        surf.fill(BG)

        # 상단 패널(제어)
        top = pygame.Rect(0, 0, WIN_W, 96)
        pygame.draw.rect(surf, PANEL, top)
        title = font_big.render("ENIAC Simulation (Simplified)", True, TEXT)
        surf.blit(title, (16, 16))
        subtitle = font_small.render("데모: 1..N 합 계산 (가산기·루프 계수기·점프)", True, MUTED)
        surf.blit(subtitle, (18, 52))

        # 모듈 카드 위치
        acc_rect = pygame.Rect(24, 120, 380, 200)
        loop_rect = pygame.Rect(420, 120, 260, 200)
        reg_rect = pygame.Rect(700, 120, 276, 200)

        # 모듈 그리기
        self.acc.draw(surf, acc_rect, "ACCUMULATOR")
        self.loop.draw(surf, loop_rect)

        # i 레지스터 카드
        pygame.draw.rect(surf, CARD, reg_rect, border_radius=16)
        pygame.draw.rect(surf, (15, 15, 18), reg_rect, 2, border_radius=16)
        t = font_big.render("I REGISTER", True, TEXT)
        surf.blit(t, (reg_rect.x + 16, reg_rect.y + 12))
        surf.blit(font.render("i", True, MUTED), (reg_rect.x + 16, reg_rect.y + 56))
        surf.blit(font_big.render(str(self.i_reg), True, TEXT), (reg_rect.x + 16, reg_rect.y + 80))

        # 상태 표시
        info_rect = pygame.Rect(24, 340, WIN_W - 48, 148)
        pygame.draw.rect(surf, CARD, info_rect, border_radius=16)
        pygame.draw.rect(surf, (15, 15, 18), info_rect, 2, border_radius=16)

        st = "PLAYING" if self.playing else "PAUSED"
        st_color = OK if self.playing else WARN
        surf.blit(font_big.render("STATUS", True, MUTED), (info_rect.x + 16, info_rect.y + 14))
        surf.blit(font_big.render(st, True, st_color), (info_rect.x + 140, info_rect.y + 14))

        surf.blit(font.render("PC", True, MUTED), (info_rect.x + 16, info_rect.y + 56))
        surf.blit(font.render(str(self.program.pc), True, TEXT), (info_rect.x + 52, info_rect.y + 56))

        # 현재 명령 미리보기
        cur = None
        if 0 <= self.program.pc < len(self.program.steps):
            cur = self.program.steps[self.program.pc]
        cur_str = f"{cur.op} {cur.arg}" if cur else "(none)"
        surf.blit(font.render("CUR INSTR", True, MUTED), (info_rect.x + 120, info_rect.y + 56))
        surf.blit(font.render(cur_str, True, ACCENT), (info_rect.x + 230, info_rect.y + 56))

        surf.blit(font.render("HALTED", True, MUTED), (info_rect.x + 16, info_rect.y + 92))
        surf.blit(font.render(str(self.halted), True, ERR if self.halted else MUTED), (info_rect.x + 86, info_rect.y + 92))

        # 예상 정답(참고): N(N+1)/2
        expected = self.program.N * (self.program.N + 1) // 2
        surf.blit(font.render("EXPECTED SUM", True, MUTED), (info_rect.x + 200, info_rect.y + 92))
        surf.blit(font.render(str(expected), True, OK), (info_rect.x + 340, info_rect.y + 92))

        # 하단: 명령 시퀀스 표시
        seq_rect = pygame.Rect(24, 504, WIN_W - 48, 140)
        pygame.draw.rect(surf, CARD, seq_rect, border_radius=16)
        pygame.draw.rect(surf, (15, 15, 18), seq_rect, 2, border_radius=16)

        surf.blit(font_big.render("PROGRAM STEPS", True, TEXT), (seq_rect.x + 16, seq_rect.y + 10))
        x = seq_rect.x + 16
        y = seq_rect.y + 50
        for idx, ins in enumerate(self.program.steps):
            s = f"[{idx:02}] {ins.op}" + (f" {ins.arg}" if ins.arg else "")
            col = OK if idx == self.program.pc else TEXT
            r = font_small.render(s, True, col)
            surf.blit(r, (x, y))
            y += 24
            if y > seq_rect.bottom - 26:
                x += 240
                y = seq_rect.y + 50

# ---------------- 전역 UI/상태 구성 ----------------
def main():
    N = 20  # 합을 구할 상한
    sim = ENIACSim(Program(N=N))

    # 버튼과 슬라이더
    btn_play = Button(pygame.Rect(720, 18, 88, 48), "▶/⏸", on_click=lambda: toggle_play(sim))
    btn_step = Button(pygame.Rect(814, 18, 78, 48), "STEP", on_click=lambda: sim.step_once())
    btn_reset = Button(pygame.Rect(896, 18, 78, 48), "RESET", on_click=lambda: sim.reset())
    speed = Slider(pygame.Rect(320, 24, 300, 24), 0.5, 20.0, 4.0)

    full = False
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    toggle_play(sim)
                elif ev.key == pygame.K_s:
                    sim.step_once()
                elif ev.key == pygame.K_r:
                    sim.reset()
                elif ev.key == pygame.K_F11:
                    full = not full
                    pygame.display.quit()
                    pygame.display.init()
                    if full:
                        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        pygame.display.set_mode((WIN_W, WIN_H))
            # 위젯 이벤트
            btn_play.handle_event(ev)
            btn_step.handle_event(ev)
            btn_reset.handle_event(ev)
            speed.handle_event(ev)

        # 슬라이더 값 -> tick_rate
        sim.tick_rate = speed.value

        # 업데이트/그리기
        sim.update(dt)
        sim.draw(screen)

        # 버튼 상태/표시
        btn_play.toggled = sim.playing
        btn_play.draw(screen)
        btn_step.draw(screen)
        btn_reset.draw(screen)
        speed.draw(screen, "Speed (steps/s)")

        # 툴팁
        tip = font_small.render("단축키: Space(재생/일시정지)  S(스텝)  R(리셋)  F11(전체화면)", True, MUTED)
        screen.blit(tip, (24, 72))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

def toggle_play(sim: ENIACSim):
    if sim.halted:
        # 정지 상태에서 재생 요청 시 리셋
        sim.reset()
    sim.playing = not sim.playing

if __name__ == "__main__":
    main()
