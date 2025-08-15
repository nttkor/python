import pygame
import sys
import time

# Pygame initialization
pygame.init()

# Screen settings
WIDTH, HEIGHT = 1100, 750
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
BUS_COLOR = (100, 100, 100)

# Fonts
font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 16)

# ==============================================================================
# Computer Component Classes
# ==============================================================================

class ControlUnit:
    def __init__(self):
        self.pc = 0
        self.sp = 0
        self.ir = ""
        self.status = "IDLE"
    
    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 250, 200), 2)
        screen.blit(font.render("Control Unit", True, BLACK), (x + 70, y + 10))
        pc_text = f"PC: {self.pc}"
        sp_text = f"SP: {self.sp}"
        ir_text = f"IR: {self.ir}"
        status_text = f"Status: {self.status}"
        screen.blit(font.render(pc_text, True, BLACK), (x + 10, y + 40))
        screen.blit(font.render(sp_text, True, BLACK), (x + 10, y + 70))
        screen.blit(font.render(ir_text, True, BLACK), (x + 10, y + 100))
        screen.blit(font.render(status_text, True, BLACK), (x + 10, y + 130))

class ALU:
    def __init__(self):
        self.accumulator = 0
    
    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 250, 200), 2)
        screen.blit(font.render("Arithmetic Logic Unit", True, BLACK), (x + 30, y + 10))
        
        acc_box = pygame.Rect(x + 20, y + 50, 210, 50)
        pygame.draw.rect(screen, (240, 240, 240), acc_box, 2)
        screen.blit(font.render("Accumulator", True, BLACK), (x + 75, y + 60))
        acc_val_text = font.render(str(self.accumulator), True, BLUE)
        screen.blit(acc_val_text, (x + 125 - acc_val_text.get_width() / 2, y + 80))

class Memory:
    def __init__(self):
        self.code_section = []
        self.data_section = {'a': 1, 'b': 2, 'c': 0}
        self.stack_section = []
        self.initial_data = self.data_section.copy()
        
    def reset(self):
        self.data_section = self.initial_data.copy()
        self.stack_section.clear()
        
    def get_var(self, var_name):
        return self.data_section.get(var_name)
    
    def set_var(self, var_name, value):
        if var_name in self.data_section:
            self.data_section[var_name] = value

    def push(self, value):
        self.stack_section.append(value)
    
    def pop(self):
        if self.stack_section:
            return self.stack_section.pop()
        return None

    def draw(self, screen, x, y):
        pygame.draw.rect(screen, GRAY, (x, y, 300, 650), 2)
        screen.blit(font.render("Memory", True, BLACK), (x + 120, y + 10))
        
        # Code Section
        code_y = y + 40
        screen.blit(font.render("1. Code Area", True, BLACK), (x + 10, code_y))
        for i, instruction in enumerate(self.code_section):
            code_y += 20
            mem_text = f"[{i:03d}]: {instruction}"
            text_surf = small_font.render(mem_text, True, BLACK)
            if i == cu.pc:
                pygame.draw.rect(screen, YELLOW, (x + 5, code_y - 2, 290, 18))
            screen.blit(text_surf, (x + 10, code_y))
        
        # Data Section
        data_y = code_y + 30
        screen.blit(font.render("2. Data Area", True, BLACK), (x + 10, data_y))
        for name, value in self.data_section.items():
            data_y += 25
            var_text = f"{name} = {value}"
            screen.blit(font.render(var_text, True, BLACK), (x + 20, data_y))
        
        # Stack Section
        stack_y = data_y + 30
        screen.blit(font.render("3. Stack Area", True, BLACK), (x + 10, stack_y))
        for i, value in enumerate(reversed(self.stack_section)):
            stack_y += 25
            stack_text = f"[{cu.sp - (i+1)}]: {value}"
            if i == 0:
                pygame.draw.rect(screen, YELLOW, (x + 5, stack_y - 2, 290, 18))
            screen.blit(font.render(stack_text, True, BLACK), (x + 20, stack_y))
        
        heap_y = stack_y + 30
        screen.blit(font.render("4. Heap Area", True, BLACK), (x + 10, heap_y))

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
            
            # Draw bus as thick dual lines
            offset = 5
            direction = pygame.Vector2(self.points[1]) - pygame.Vector2(self.points[0])
            if direction.length() > 0:
                direction.normalize_ip()
                perp_dir = pygame.Vector2(-direction.y, direction.x)
                
                line1_start = pygame.Vector2(self.points[0]) + perp_dir * offset
                line1_end = pygame.Vector2(current_pos) + perp_dir * offset
                
                line2_start = pygame.Vector2(self.points[0]) - perp_dir * offset
                line2_end = pygame.Vector2(current_pos) - perp_dir * offset
                
                pygame.draw.line(screen, self.color, line1_start, line1_end, 3)
                pygame.draw.line(screen, self.color, line2_start, line2_end, 3)
            
            # Arrowhead
            if self.step > 0:
                end_pos_vec = pygame.Vector2(current_pos)
                start_pos_vec = pygame.Vector2(self.points[0])
                direction = (end_pos_vec - start_pos_vec).normalize()
                arrow_points = [
                    end_pos_vec,
                    end_pos_vec - direction.rotate(-30) * 15,
                    end_pos_vec - direction.rotate(30) * 15
                ]
                pygame.draw.polygon(screen, self.color, arrow_points)
            self.step += 1
        else:
            self.active = False
            self.step = 0

# ==============================================================================
# Main Simulation Logic
# ==============================================================================

# Program logic: c = add(a, b)
instruction_set_main = [
    "LOAD_ACC a",       # 0: Acc = 1
    "PUSH_ACC",         # 1: Stack.push(1)
    "LOAD_ACC b",       # 2: Acc = 2
    "JSR 6",            # 3: Jump to 'add' function (at address 6)
    "STORE c",          # 4: Store result to c
    "HALT",             # 5: End
]
# Function 'add'
instruction_set_add = [
    "ADD_STACK",        # 6: Acc = Acc + Stack.pop()
    "RET",              # 7: Return to caller
]

instruction_set_combined = instruction_set_main + instruction_set_add
cu = ControlUnit()
alu = ALU()
memory = Memory()
memory.code_section = instruction_set_combined

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

def handle_reset_button():
    global simulation_running
    simulation_running = False
    cu.pc = 0
    cu.sp = 0
    cu.ir = ""
    cu.status = "IDLE"
    alu.accumulator = 0
    memory.reset()
    print("시뮬레이션 초기화")

def run_simulation_step():
    global bus_animation
    
    if cu.pc >= len(memory.code_section) or memory.code_section[cu.pc] == "HALT":
        cu.status = "HALTED"
        return

    cu.status = "FETCH"
    instruction = memory.code_section[cu.pc]
    bus_animation.start((mem_x, mem_y + 100), (cu_x + 250, cu_y + 100), YELLOW)
    cu.ir = instruction
    
    time.sleep(1)

    cu.status = "EXECUTE"
    
    parts = instruction.split(' ')
    op = parts[0]
    
    if op == "LOAD_ACC":
        var_name = parts[1]
        val = memory.get_var(var_name)
        alu.accumulator = val
        bus_animation.start((mem_x, mem_y + 250), (alu_x + 250, alu_y + 100), RED)
        
    elif op == "PUSH_ACC":
        memory.push(alu.accumulator)
        cu.sp += 1
        bus_animation.start((alu_x + 250, alu_y + 100), (mem_x + 150, mem_y + 400 + cu.sp * 25), BLUE)
    
    elif op == "STORE":
        var_name = parts[1]
        memory.set_var(var_name, alu.accumulator)
        bus_animation.start((alu_x + 250, alu_y + 100), (mem_x, mem_y + 250), BLUE)
    
    elif op == "JSR":
        ret_addr = cu.pc + 1
        memory.push(ret_addr)
        cu.sp += 1
        cu.pc = int(parts[1])
        bus_animation.start((cu_x + 125, cu_y + 200), (mem_x + 150, mem_y + 400 + cu.sp * 25), GREEN)
        return
    
    elif op == "ADD_STACK":
        operand_a = memory.pop()
        cu.sp -= 1
        alu.accumulator += operand_a
        bus_animation.start((mem_x + 150, mem_y + 400 + cu.sp * 25), (alu_x + 250, alu_y + 100), RED)
    
    elif op == "RET":
        cu.pc = memory.pop()
        cu.sp -= 1
        bus_animation.start((mem_x + 150, mem_y + 400 + cu.sp * 25), (cu_x + 125, cu_y + 200), GREEN)
        return
    
    cu.pc += 1

# Buttons
play_button = Button("PLAY", 100, 650, 80, 40, GREEN, handle_play_button)
step_button = Button("STEP", 200, 650, 80, 40, BLUE, handle_step_button)
reset_button = Button("RESET", 300, 650, 80, 40, RED, handle_reset_button)

# Component positions
cu_x, cu_y = 50, 50
mem_x, mem_y = (WIDTH - 300) / 2, 50
alu_x, alu_y = 50, 350
code_x, code_y = 750, 50

# Main loop
running = True
last_update_time = time.time()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        play_button.handle_event(event)
        step_button.handle_event(event)
        reset_button.handle_event(event)
    
    if simulation_running and not bus_animation.active:
        current_time = time.time()
        if current_time - last_update_time > 1:
            run_simulation_step()
            last_update_time = current_time

    screen.fill(WHITE)

    cu.draw(screen, cu_x, cu_y)
    memory.draw(screen, mem_x, mem_y)
    alu.draw(screen, alu_x, alu_y)
    
    # Draw external code block
    pygame.draw.rect(screen, GRAY, (code_x, code_y, 300, 150), 2)
    screen.blit(font.render("Program Code", True, BLACK), (code_x + 80, code_y + 10))
    code_lines = [
        "def add(a,b):",
        "    tem = a + b",
        "    return tem",
        "a=1",
        "b=2",
        "c=add(a,b)"
    ]
    code_line_y = code_y + 40
    for line in code_lines:
        screen.blit(small_font.render(line, True, BLACK), (code_x + 10, code_line_y))
        code_line_y += 20
    
    # Draw buses
    pygame.draw.line(screen, BUS_COLOR, (cu_x + 250, cu_y + 75), (mem_x, mem_y + 100), 10)
    pygame.draw.line(screen, BUS_COLOR, (alu_x + 250, alu_y + 100), (mem_x, mem_y + 350), 10)
    pygame.draw.line(screen, BUS_COLOR, (cu_x + 125, cu_y + 200), (alu_x + 125, alu_y), 10)
    
    # Buttons
    play_button.draw(screen)
    step_button.draw(screen)
    reset_button.draw(screen)
    
    bus_animation.draw(screen)
    
    pygame.display.flip()

pygame.quit()
sys.exit()