import pygame
import sys
import time

# Pygame initialization
pygame.init()

# Screen settings
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("폰 노이만 컴퓨터 시뮬레이션")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# Fonts
font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 16)

# ==============================================================================
# Computer Component Classes
# ==============================================================================

class ControlUnit:
    def __init__(self):
        self.pc = 0  # Program Counter
        self.ir = "" # Instruction Register
        self.status = "IDLE"
    
    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 200, 150), 2)
        screen.blit(font.render("Control Unit", True, BLACK), (x + 40, y + 10))
        pc_text = f"PC: {self.pc}"
        ir_text = f"IR: {self.ir}"
        status_text = f"Status: {self.status}"
        screen.blit(font.render(pc_text, True, BLACK), (x + 10, y + 40))
        screen.blit(font.render(ir_text, True, BLACK), (x + 10, y + 70))
        screen.blit(font.render(status_text, True, BLACK), (x + 10, y + 100))

class ALU:
    def __init__(self):
        self.accumulator = 0
    
    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 200, 200), 2)
        screen.blit(font.render("Arithmetic Logic Unit", True, BLACK), (x + 10, y + 10))
        
        # Accumulator
        acc_box = pygame.Rect(x + 20, y + 50, 160, 50)
        pygame.draw.rect(screen, (240, 240, 240), acc_box, 2)
        screen.blit(font.render("Accumulator", True, BLACK), (x + 50, y + 60))
        acc_val_text = font.render(str(self.accumulator), True, BLUE)
        screen.blit(acc_val_text, (x + 90 - acc_val_text.get_width() / 2, y + 80))

class Memory:
    def __init__(self, size):
        self.size = size
        self.data = [""] * size

    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 200, 400), 2)
        screen.blit(font.render("Memory", True, BLACK), (x + 65, y + 10))
        
        # Memory content drawing
        mem_y = y + 40
        for i in range(15): # Display a limited number of cells
            mem_text = f"[{i:03d}]: {self.data[i]}"
            text_surf = small_font.render(mem_text, True, BLACK)
            
            # Highlight the current PC cell
            if i == cu.pc:
                pygame.draw.rect(screen, YELLOW, (x + 5, mem_y - 2, 190, 18))
            
            screen.blit(text_surf, (x + 10, mem_y))
            mem_y += 20

# ==============================================================================
# GUI and Animation
# ==============================================================================

class Button:
    def __init__(self, text, x, y, width, height, color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.action = action
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        text_surf = font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()

class BusAnimation:
    def __init__(self):
        self.active = False
        self.step = 0
        self.max_steps = 60
        self.points = []
        self.color = BLUE
    
    def start(self, start_pos, end_pos, color):
        self.active = True
        self.step = 0
        self.points = [start_pos, end_pos]
        self.color = color
    
    def draw(self, screen):
        if not self.active:
            return
        
        if self.step < self.max_steps:
            t = self.step / self.max_steps
            current_pos = (
                self.points[0][0] + (self.points[1][0] - self.points[0][0]) * t,
                self.points[0][1] + (self.points[1][1] - self.points[0][1]) * t
            )
            pygame.draw.line(screen, self.color, self.points[0], current_pos, 3)
            # Arrowhead
            if self.step > 0:
                end_pos_vec = pygame.Vector2(current_pos)
                start_pos_vec = pygame.Vector2(self.points[0])
                direction = (end_pos_vec - start_pos_vec).normalize()
                arrow_points = [
                    end_pos_vec,
                    end_pos_vec - direction.rotate(-30) * 10,
                    end_pos_vec - direction.rotate(30) * 10
                ]
                pygame.draw.polygon(screen, self.color, arrow_points)
            self.step += 1
        else:
            self.active = False
            self.step = 0

# ==============================================================================
# Main Simulation Logic
# ==============================================================================

# Instruction set for 1 + (2 * 3)
instruction_set = [
    "LOAD_ACC 2",
    "MUL 3",
    "ADD 1",
    "HALT"
]

# Create components and initialize memory
cu = ControlUnit()
alu = ALU()
memory = Memory(50)
for i, inst in enumerate(instruction_set):
    memory.data[i] = inst

bus_animation = BusAnimation()
simulation_running = False

def handle_play_button():
    global simulation_running
    if cu.status == "IDLE" or cu.status == "PAUSED":
        simulation_running = True
        cu.status = "RUNNING"
    else:
        simulation_running = False
        cu.status = "PAUSED"

def handle_step_button():
    global simulation_running
    if not simulation_running and not bus_animation.active:
        cu.status = "STEPPING"
        run_simulation_step()
        cu.status = "PAUSED"

def run_simulation_step():
    if cu.pc >= len(instruction_set) or memory.data[cu.pc] == "HALT":
        cu.status = "HALTED"
        return

    # Fetch Cycle
    cu.status = "FETCH"
    instruction = memory.data[cu.pc]
    bus_animation.start((750, 200), (250, 100), RED)
    time.sleep(1) # Visual pause
    cu.ir = instruction
    
    # Decode and Execute
    cu.status = "EXECUTE"
    
    parts = instruction.split(' ')
    op = parts[0]
    val = int(parts[1]) if len(parts) > 1 else None

    if op == "LOAD_ACC":
        alu.accumulator = val
        bus_animation.start((150, 150), (150, 300), GREEN) # CU -> ALU
        
    elif op == "MUL":
        alu.accumulator *= val
        bus_animation.start((150, 300), (150, 400), GREEN) # ALU -> CU (Notional)
        
    elif op == "ADD":
        alu.accumulator += val
        bus_animation.start((150, 300), (150, 400), GREEN) # ALU -> CU (Notional)
    
    cu.pc += 1

# Buttons
play_button = Button("PLAY", 100, 550, 80, 40, GREEN, handle_play_button)
step_button = Button("STEP", 200, 550, 80, 40, BLUE, handle_step_button)

# Main loop
running = True
last_update_time = time.time()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        play_button.handle_event(event)
        step_button.handle_event(event)
    
    # Auto-run mode
    if simulation_running and not bus_animation.active:
        current_time = time.time()
        if current_time - last_update_time > 1: # 1-second interval
            run_simulation_step()
            last_update_time = current_time

    # Drawing
    screen.fill(WHITE)

    # Components
    cu.draw(screen, 50, 50)
    memory.draw(screen, 650, 50)
    alu.draw(screen, 50, 250)
    
    # Connections (Buses)
    pygame.draw.line(screen, BLACK, (250, 100), (650, 100), 2) # CU <-> MEM
    pygame.draw.line(screen, BLACK, (150, 250), (150, 150), 2) # CU -> ALU
    pygame.draw.line(screen, BLACK, (250, 350), (150, 350), 2) # ALU -> CU
    
    # Buttons
    play_button.draw(screen)
    step_button.draw(screen)
    
    # Animation
    bus_animation.draw(screen)
    
    pygame.display.flip()

# Quit
pygame.quit()
sys.exit()