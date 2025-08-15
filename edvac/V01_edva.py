import pygame
import sys
import time

# Pygame 초기화
pygame.init()

# 화면 설정
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("폰 노이만 컴퓨터 시뮬레이션")

# 색상 정의
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# 폰트 설정
font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 16)

# 애니메이션을 위한 변수
animation_active = False
animation_step = 0
animation_max_steps = 30
arrow_color = BLUE
arrow_points = []

# ==============================================================================
# 컴퓨터 부품 클래스
# ==============================================================================

class CPU:
    def __init__(self):
        self.pc = 0  # Program Counter
        self.ir = "" # Instruction Register
        self.registers = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0, 'R5': 0}
        self.alu_result = 0

    def draw(self, screen, x, y):
        # CPU 박스
        pygame.draw.rect(screen, GRAY, (x, y, 200, 250), 2)
        screen.blit(font.render("CPU", True, BLACK), (x + 80, y + 10))

        # 레지스터 그리기
        reg_y = y + 40
        for name, value in self.registers.items():
            reg_text = f"{name}: {value}"
            text_surf = font.render(reg_text, True, BLACK)
            screen.blit(text_surf, (x + 10, reg_y))
            reg_y += 25
        
        # PC, IR 그리기
        pc_text = f"PC: {self.pc}"
        ir_text = f"IR: {self.ir}"
        screen.blit(font.render(pc_text, True, BLACK), (x + 10, y + 180))
        screen.blit(font.render(ir_text, True, BLACK), (x + 10, y + 210))


class Memory:
    def __init__(self, size):
        self.size = size
        self.data = [""] * size

    def draw(self, screen, x, y):
        # 메모리 박스
        pygame.draw.rect(screen, GRAY, (x, y, 200, 400), 2)
        screen.blit(font.render("Memory", True, BLACK), (x + 65, y + 10))
        
        # 메모리 내용 그리기
        mem_y = y + 40
        for i in range(15): # 일부만 표시
            mem_text = f"[{i:03d}]: {self.data[i]}"
            text_surf = small_font.render(mem_text, True, BLACK)
            
            # 현재 PC가 가리키는 메모리 셀 강조
            if i == cpu.pc:
                pygame.draw.rect(screen, YELLOW, (x + 5, mem_y - 2, 190, 18))
            
            screen.blit(text_surf, (x + 10, mem_y))
            mem_y += 20

# ==============================================================================
# 애니메이션 함수
# ==============================================================================

def draw_arrow(start_pos, end_pos, color):
    pygame.draw.line(screen, color, start_pos, end_pos, 2)
    # 화살표 머리
    arrow_head_size = 10
    angle = pygame.Vector2(end_pos) - pygame.Vector2(start_pos)
    angle.normalize_ip()
    
    right_vec = angle.rotate(150) * arrow_head_size
    left_vec = angle.rotate(-150) * arrow_head_size
    
    pygame.draw.line(screen, color, end_pos, end_pos + right_vec, 2)
    pygame.draw.line(screen, color, end_pos, end_pos + left_vec, 2)

def animate_bus(start, end):
    global animation_active, animation_step, arrow_points
    
    if not animation_active:
        animation_active = True
        animation_step = 0
        arrow_points = [start, end]
        
    if animation_step < animation_max_steps:
        # 진행률에 따라 화살표 위치 업데이트
        t = animation_step / animation_max_steps
        current_pos = (
            int(arrow_points[0][0] + (arrow_points[1][0] - arrow_points[0][0]) * t),
            int(arrow_points[0][1] + (arrow_points[1][1] - arrow_points[0][1]) * t)
        )
        draw_arrow(arrow_points[0], current_pos, arrow_color)
        animation_step += 1
    else:
        animation_active = False

# ==============================================================================
# 메인 로직 및 시뮬레이션
# ==============================================================================

# 명령어와 데이터 설정
instruction_set = [
    "LOAD R1, #2",
    "LOAD R2, #3",
    "MUL R3, R1, R2",
    "LOAD R4, #1",
    "ADD R5, R3, R4",
    "HALT"
]

# 객체 생성
cpu = CPU()
memory = Memory(50)
for i, inst in enumerate(instruction_set):
    memory.data[i] = inst

# 시뮬레이션 상태 변수
simulation_step = 0
simulation_running = False

# 시뮬레이션 진행 함수
def run_simulation_step():
    global simulation_step, simulation_running
    
    if not simulation_running:
        return

    if cpu.pc >= len(instruction_set) or memory.data[cpu.pc] == "HALT":
        simulation_running = False
        print("시뮬레이션 종료")
        return

    instruction = memory.data[cpu.pc]
    cpu.ir = instruction
    
    # 명령어 실행 로직
    parts = instruction.split(', ')
    op = parts[0].split(' ')[0]

    if op == "LOAD":
        reg = parts[0].split(' ')[1]
        val = int(parts[1].replace('#', ''))
        cpu.registers[reg] = val
        
    elif op == "MUL":
        dest_reg = parts[0].split(' ')[1]
        reg1 = parts[1]
        reg2 = parts[2]
        val1 = cpu.registers[reg1]
        val2 = cpu.registers[reg2]
        cpu.registers[dest_reg] = val1 * val2
        
    elif op == "ADD":
        dest_reg = parts[0].split(' ')[1]
        reg1 = parts[1]
        reg2 = parts[2]
        val1 = cpu.registers[reg1]
        val2 = cpu.registers[reg2]
        cpu.registers[dest_reg] = val1 + val2

    # PC 증가
    cpu.pc += 1
    simulation_step += 1


# 메인 루프
running = True
last_update_time = time.time()
animation_speed = 0.05 # 애니메이션 업데이트 속도

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                simulation_running = not simulation_running
                print("시뮬레이션 시작/정지:", simulation_running)
            if event.key == pygame.K_RIGHT:
                if not simulation_running:
                    run_simulation_step()
                    print("단계 실행")
    
    # 자동 실행 모드
    if simulation_running:
        current_time = time.time()
        if current_time - last_update_time > 1: # 1초마다 한 단계 실행
            run_simulation_step()
            last_update_time = current_time

    # 화면 그리기
    screen.fill(WHITE)
    
    # 블록 그리기
    cpu.draw(screen, 50, 50)
    memory.draw(screen, 650, 50)
    
    # 블록 간 버스 그리기
    bus_y = 300
    pygame.draw.line(screen, BLACK, (50, bus_y), (650, bus_y), 3)
    screen.blit(small_font.render("Bus (주소, 데이터, 제어)", True, BLACK), (300, bus_y + 10))

    # 데이터 흐름 애니메이션 로직
    if cpu.ir:
        parts = cpu.ir.split(', ')
        op = parts[0].split(' ')[0]
        
        # Fetch 단계 애니메이션
        if simulation_step > 0 and not animation_active:
            # CPU -> Memory (주소 전송)
            animate_bus((150, 190), (650, 190))
            # Memory -> CPU (데이터 전송)
            animate_bus((650, 210), (250, 210))
            
    if animation_active:
        animate_bus(arrow_points[0], arrow_points[1])
    
    # 폰트 출력
    pygame.display.flip()
    
# Pygame 종료
pygame.quit()
sys.exit()