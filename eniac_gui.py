import pygame
import sys

pygame.init()

# -----------------------
# 초기 설정
# -----------------------
WINDOW_WIDTH, WINDOW_HEIGHT = 1600, 900
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("ENIAC Ballistics - OrCAD Layout")

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 16)

fullscreen = False

# -----------------------
# 색상
# -----------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (80, 80, 80)
LIGHT_GRAY = (150, 150, 150)
BLUE = (0, 150, 255)
GREEN = (0, 200, 0)
YELLOW = (255, 200, 0)
MAGENTA = (255, 0, 255)

# -----------------------
# 블록 클래스
# -----------------------
class Block:
    def __init__(self, name, pos, size=(200, 120), color=GRAY):
        self.name = name
        self.x, self.y = pos
        self.width, self.height = size
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, self.height), border_radius=10)
        pygame.draw.rect(surface, WHITE, (self.x, self.y, self.width, self.height), 2, border_radius=10)
        label = font.render(self.name, True, WHITE)
        surface.blit(label, (self.x + 10, self.y + 10))

    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

# -----------------------
# 직각 배선 함수
# -----------------------
def draw_orthogonal_wire(surface, start, end, color=LIGHT_GRAY, width=2):
    # 중간 x 또는 y를 맞추는 간단한 직각 경로
    mid_x = (start[0] + end[0]) // 2
    pygame.draw.line(surface, color, start, (mid_x, start[1]), width)
    pygame.draw.line(surface, color, (mid_x, start[1]), (mid_x, end[1]), width)
    pygame.draw.line(surface, color, (mid_x, end[1]), end, width)

# -----------------------
# 블록 배치 (OrCAD 스타일)
# -----------------------
blocks = []

# 왼쪽 열
blocks.append(Block("Card Reader", (50, 100)))
blocks.append(Block("Constant Transmitter", (50, 250)))
blocks.append(Block("Function Table", (50, 400)))
blocks.append(Block("Master Programmer", (50, 550)))
blocks.append(Block("Card Punch", (50, 700)))

# 중앙 (Accumulator 3열 × 4행)
accumulators = []
start_x = 350
start_y = 100
gap_x = 230
gap_y = 150
for row in range(4):
    for col in range(3):
        idx = row * 3 + col + 1
        acc = Block(f"A{idx} (Accumulator)", (start_x + col * gap_x, start_y + row * gap_y))
        blocks.append(acc)
        accumulators.append(acc)

# 오른쪽 열 (Arithmetic Units)
blocks.append(Block("Adder / Subtracter", (1100, 200), color=BLUE))
blocks.append(Block("Multiplier", (1100, 380), color=GREEN))
blocks.append(Block("Divider / Sqrt", (1100, 560), color=YELLOW))

# -----------------------
# 배선 연결 정의 (간단 예시)
# -----------------------
connections = [
    ("Card Reader", "A1 (Accumulator)"),
    ("Constant Transmitter", "A5 (Accumulator)"),
    ("Function Table", "A9 (Accumulator)"),
    ("A1 (Accumulator)", "Adder / Subtracter"),
    ("A2 (Accumulator)", "Adder / Subtracter"),
    ("A3 (Accumulator)", "Multiplier"),
    ("A4 (Accumulator)", "Multiplier"),
    ("A7 (Accumulator)", "Divider / Sqrt"),
    ("A8 (Accumulator)", "Divider / Sqrt"),
    ("Adder / Subtracter", "Card Punch")
]

# -----------------------
# 버튼
# -----------------------
class Button:
    def __init__(self, text, pos, size=(80, 30), color=LIGHT_GRAY):
        self.text = text
        self.x, self.y = pos
        self.width, self.height = size
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, self.height), border_radius=5)
        pygame.draw.rect(surface, WHITE, (self.x, self.y, self.width, self.height), 2, border_radius=5)
        label = font.render(self.text, True, WHITE)
        surface.blit(label, (self.x + 10, self.y + 7))

buttons = [
    Button("Play", (1350, 100)),
    Button("Pause", (1350, 140)),
    Button("Step", (1350, 180)),
    Button("Reset", (1350, 220))
]

# -----------------------
# 메인 루프
# -----------------------
running = True
while running:
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    # 블록 그리기
    for block in blocks:
        block.draw(screen)

    # 배선 그리기
    for src_name, dst_name in connections:
        src = next(b for b in blocks if b.name == src_name)
        dst = next(b for b in blocks if b.name == dst_name)
        draw_orthogonal_wire(screen, src.center(), dst.center(), LIGHT_GRAY, 2)

    # 버튼 그리기
    for btn in buttons:
        btn.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
