import directpython as dp
import math
import time

# 초기화
dp.CreateDeviceAndSwapChain()
dp.CreateRenderTargetView()
dp.CreateDepthStencilView()

# 셰이더 로딩
vertex_shader = dp.LoadVertexShader("cube.vs")
pixel_shader = dp.LoadPixelShader("cube.ps")

# 큐브 정점 정의 (간단화된 예시)
vertices = dp.CreateCubeVertices(size=1.0)

# 정점 버퍼 생성
vertex_buffer = dp.CreateVertexBuffer(vertices)

# 회전 변수 초기화
angle = 0.0

# 렌더 루프
while dp.IsRunning():
    # 회전 행렬 계산
    angle += 0.01
    rotation_matrix = dp.MatrixRotationY(angle) @ dp.MatrixRotationX(angle / 2)

    # 뷰 및 프로젝션 행렬
    view_matrix = dp.MatrixLookAtLH(eye=(0, 0, -5), target=(0, 0, 0), up=(0, 1, 0))
    proj_matrix = dp.MatrixPerspectiveFovLH(fov=math.pi/4, aspect=1.0, zn=0.1, zf=100.0)

    # 최종 변환 행렬
    mvp_matrix = rotation_matrix @ view_matrix @ proj_matrix

    # 셰이더에 행렬 전달
    dp.SetShaderConstantBuffer(vertex_shader, "Transform", mvp_matrix)

    # 렌더링
    dp.ClearRenderTargetView((0.1, 0.1, 0.3, 1.0))
    dp.ClearDepthStencilView()
    dp.SetShaders(vertex_shader, pixel_shader)
    dp.SetVertexBuffer(vertex_buffer)
    dp.Draw(len(vertices))
    dp.Present()

    time.sleep(1/60)  # 60FPS