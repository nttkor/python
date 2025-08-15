
# ENIAC Demo — V6 Plugboard Editor

**V6 주요 추가점**
- 마우스로 **플러그보드 배선**을 직접 구성(포트→포트 드래그).  
- **저장/로드**: `S`키로 `/mnt/data/plugboard_v6.json` 저장, `L`키로 불러오기.
- **줌/팬**: 휠로 확대/축소, 마우스 가운데 버튼 드래그로 이동.
- 실행은 배선에서 유도된 경로(α/A/S/AS/β/γ, MULT, PUNCH, CCG/RP)에 따라 동작.

**기본 배선**은 V5와 동일한 시나리오(1,2,3 로드 → 2×3 → +1 → −2 → 펀치)를 사전에 연결해 제공합니다.

## 실행
```bash
pip install pygame
python eniac_demo_v6_plugboard_editor.py
```
조작: ENTER=STEP, SPACE=RUN/PAUSE, R=Reset, +/-=속도, S=Save, L=Load, Wheel=Zoom, MMB=Pan

---

향후에는 포트 타입 검사, 배선 충돌 감지, 케이블 스타일(곡선), Divider/√ 유닛 추가, 이니시에이터·프로그램 펄스 라인 확장 등을 계속 붙일 수 있습니다.
