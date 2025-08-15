import pygame
import sys

# Pygame 초기화
pygame.init()

# 화면 설정
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ENIAC Simulation")

# 색상 정의
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (0, 100, 255)
RED = (255, 0, 0)

# 폰트 설정
font = pygame.font.Font(None, 36)

# ENIAC 시뮬레이션 변수
eniac_running = False
eniac_step = 0
max_steps = 100

# 버튼 클래스 정의
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = self.color
        self.text_surface = font.render(self.text, True, BLACK)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def draw(self):
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        screen.blit(self.text_surface, self.text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def update(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.color

# 버튼 생성
play_pause_button = Button(50, 500, 150, 50, "Play/Pause", GRAY, DARK_GRAY)
step_button = Button(250, 500, 150, 50, "Step", GRAY, DARK_GRAY)
reset_button = Button(450, 500, 150, 50, "Reset", GRAY, DARK_GRAY)

# ENIAC 튜브 애니메이션
class VacuumTube:
    def __init__(self, x, y, size):
        self.rect = pygame.Rect(x, y, size, size * 2)
        self.color = DARK_GRAY
        self.is_on = False
    
    def draw(self):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        if self.is_on:
            pygame.draw.ellipse(screen, RED, self.rect.inflate(-10, -10))
            pygame.draw.rect(screen, RED, (self.rect.x + 5, self.rect.y + self.rect.height / 2 - 5, self.rect.width - 10, 10))

    def update(self, step):
        # 간단한 로직으로 애니메이션 효과
        if step % 10 == 0:
            self.is_on = not self.is_on

tubes = []
for i in range(10):
    tubes.append(VacuumTube(50 + i * 70, 100, 50))

# 메인 게임 루프
running = True
clock = pygame.time.Clock()
last_step_time = pygame.time.get_ticks()

while running:
    # 1초에 100번 프레임 업데이트
    clock.tick(100)
    
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if play_pause_button.handle_event(event):
            eniac_running = not eniac_running
        if step_button.handle_event(event):
            if not eniac_running:
                eniac_step += 1
                if eniac_step > max_steps:
                    eniac_step = 0
        if reset_button.handle_event(event):
            eniac_running = False
            eniac_step = 0
            
    # 버튼 상태 업데이트
    play_pause_button.update(mouse_pos)
    step_button.update(mouse_pos)
    reset_button.update(mouse_pos)
    
    # 시뮬레이션 로직
    if eniac_running:
        current_time = pygame.time.get_ticks()
        if current_time - last_step_time > 100:  # 100ms마다 스텝 진행
            eniac_step += 1
            if eniac_step > max_steps:
                eniac_step = 0
            last_step_time = current_time
    
    # 애니메이션 업데이트
    for tube in tubes:
        tube.update(eniac_step)

    # 화면 그리기
    screen.fill(WHITE)
    
    # ENIAC 모습 그리기
    pygame.draw.rect(screen, DARK_GRAY, (30, 80, 740, 300), border_radius=20)
    
    for tube in tubes:
        tube.draw()
    
    # 상태 텍스트 그리기
    status_text = "Status: " + ("Running" if eniac_running else "Paused")
    step_text = f"Current Step: {eniac_step}"
    
    status_surface = font.render(status_text, True, BLACK)
    step_surface = font.render(step_text, True, BLACK)
    
    screen.blit(status_surface, (50, 400))
    screen.blit(step_surface, (50, 440))
    
    # 버튼 그리기
    play_pause_button.draw()
    step_button.draw()
    reset_button.draw()
    
    # 화면 업데이트
    pygame.display.flip()

# Pygame 종료
pygame.quit()
sys.exit()