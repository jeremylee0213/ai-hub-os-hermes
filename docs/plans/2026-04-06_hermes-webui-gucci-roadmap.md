# Hermes WebUI Gucci Roadmap Implementation Plan

> For Hermes: use this as the execution guide for incremental development and GitHub-ready rollout.

Goal:
Hermes WebUI 를 문정님용 개인 AI 작업실 수준으로 끌어올리고, 이후 GitHub 에 공개 가능한 수준으로 문서/기능/테스트를 함께 정리한다.

Architecture:
기존의 no-build / vanilla JS / python stdlib 서버 구조는 유지한다. 기능은 작은 패치로 나누고, 모델 라우팅 / cron UX / workflow harness 를 중심으로 점진적으로 확장한다.

Tech stack:
- Python 3.11
- stdlib HTTP server
- Vanilla JS modules
- CSS custom themes
- Hermes backend integration

---

## 현재 반영된 선행 작업
- 한국어 UI 1차 패치
- favicon 추가
- 포트 8788 분리
- GPT-5.4 / Codex 모델 노출
- Darwin + Codex 라우팅 보정
- 자연어 cron 초안 입력 UI 1차 도입
- 벚꽃 / 네오브루탈리즘 / 구찌 스타일 테마 추가

---

## Phase A — 안정화 및 회귀 방지

### Task A1: 메시지 중복 전송 회귀 테스트 추가
Objective: 한글 IME 또는 빠른 전송으로 동일 메시지가 2번 저장되는 버그를 방지한다.

Files:
- Modify: tests/test_regressions.py
- Inspect: static/messages.js, static/boot.js

Steps:
1. 현재 send 중복 방지 로직과 composition 처리 조건 문서화
2. 중복 전송 재현 케이스 테스트 추가
3. 새 세션 첫 메시지에서 중복 저장이 없는지 검증
4. 테스트 명령 정리

Verification:
- pytest tests/test_regressions.py -v

### Task A2: 모델 라우팅 회귀 테스트 추가
Objective: Darwin 기본 설정 상태에서도 GPT-5.4 선택 시 외부 provider 로 정상 라우팅되도록 보장한다.

Files:
- Modify: tests/test_regressions.py or new tests/test_models_routing.py
- Inspect: api/config.py

Steps:
1. auth.json 이 있을 때 provider 감지 케이스 추가
2. custom:darwin 기본 설정 + gpt-5.4 선택 케이스 테스트
3. openai-codex 인증 시 gpt-5.4 가 openai-codex 로 라우팅되는지 확인

Verification:
- pytest tests/ -k routing -v

### Task A3: 자동실행 문서화
Objective: LaunchAgent 기반 자동 실행 구성을 GitHub 배포 관점에서 문서화한다.

Files:
- Modify: README.md
- Modify: ARCHITECTURE.md

Steps:
1. macOS LaunchAgent 사용 방법 정리
2. 포트 변경 방법 정리
3. localhost / 127.0.0.1 차이와 충돌 대응 문서화

---

## Phase B — 테마/브랜딩 완성

### Task B1: THEMES.md 작성 또는 갱신
Objective: 신규 테마 3종을 GitHub 독자가 이해할 수 있게 문서화한다.

Files:
- Modify or Create: THEMES.md

Sections:
- Dark / Light / Slate / Solarized / Monokai / Nord
- Cherry Blossom
- Neo Brutalism
- Gucci
- 사용법 (/theme, Settings)
- 스크린샷 TODO

### Task B2: 벚꽃 테마 시각 효과 안정화
Objective: 꽃잎 애니메이션이 실제로 잘 보이고, 과도하지 않게 유지되도록 조정한다.

Files:
- Modify: static/style.css
- Modify: static/index.html

Steps:
1. 꽃잎 표시 여부 확인
2. 필요 시 개수/크기/속도 보정
3. 모바일에서 과도하면 약화 조건 추가

### Task B3: 구찌 테마 2차 polish
Objective: 구찌 스타일 테마를 더 완성도 있게 만든다.

Files:
- Modify: static/style.css
- Optional: static/favicon.svg, static/favicon.png

Ideas:
- 골드 라인 더 정교화
- 버튼 대비 최적화
- 구찌 테마 전용 아이콘/배지 스타일

---

## Phase C — 자연어 Cron Builder 고도화

### Task C1: 자연어 cron parser 고도화
Objective: 현재 heuristic 기반 parser 를 더 많은 한국어 표현을 이해하도록 확장한다.

Files:
- Modify: static/panels.js

Add support for:
- 매주 금요일 저녁 6시
- 매달 첫째 날 아침 7시
- 격일 / 매주 주말 / 매 영업일
- 오전 8시 반 / 8시 30분

### Task C2: preview 카드 추가
Objective: 자연어 입력 후 실제 해석 결과를 사용자가 만들기 전에 미리 확인하게 한다.

Files:
- Modify: static/index.html
- Modify: static/panels.js
- Modify: static/style.css

Preview fields:
- 해석된 스케줄
- 전달 채널
- 생성될 작업 이름
- 최종 prompt 초안

### Task C3: cron dry-run
Objective: 생성 전에 프롬프트가 자급자족형인지 간단히 점검한다.

Files:
- Modify: api/routes.py
- New: api/cron_preview.py (optional)
- Modify: static/panels.js

---

## Phase D — Harness Engineering Layer

### Task D1: preflight framework 설계
Objective: posting/note/cron 같은 artifact 생성 전에 공통 점검 레이어를 만든다.

Files:
- New: docs/specs/harness-preflight-spec.md
- Optional code later: api/validators.py, static/panels.js

Checks:
- cron: schedule/prompt/deliver
- note: frontmatter/markdown quality
- posting: required sections/visuals/ShareNote

### Task D2: artifact validator panel MVP
Objective: 결과물이 검증되었는지 보여주는 작은 상태 영역을 WebUI 에 도입한다.

Files:
- Modify: static/index.html
- Modify: static/ui.js
- Modify: static/style.css

### Task D3: recovery actions
Objective: 실패 시 one-click retry / reopen / revalidate 를 제공한다.

Files:
- Modify: static/panels.js
- Modify: static/messages.js

---

## Phase E — Obsidian / Posting Studio

### Task E1: quick action buttons 설계
Objective: 세션 결과를 artifact 로 바꾸는 버튼을 넣는다.

Ideas:
- 현재 대화 → Obsidian 노트
- 현재 대화 → /posting 초안
- ShareNote 생성
- 예약작업으로 전환

Files:
- Modify: static/index.html
- Modify: static/ui.js
- Modify: static/style.css

### Task E2: posting studio spec 작성
Objective: posting 을 별도 workflow 로 승격시키기 위한 화면/상태 모델 정의.

Files:
- New: docs/specs/posting-studio-spec.md

### Task E3: Obsidian studio spec 작성
Objective: active note / selected text / save target / ShareNote 를 포함한 Obsidian 중심 작업실 설계.

Files:
- New: docs/specs/obsidian-studio-spec.md

---

## GitHub 배포 준비 체크리스트
- README 기능 설명 갱신
- THEMES.md 갱신
- CHANGELOG.md 갱신
- ROADMAP.md 갱신
- 신규 기능 스크린샷 추가
- 회귀 테스트 추가
- 로컬 실행 / 포트 / LaunchAgent / Docker 설명 확인

---

## 지금 바로 다음 구현 우선순위
1. 회귀 테스트 보강
2. THEMES.md / README 업데이트
3. 자연어 cron preview 추가
4. harness preflight MVP 설계
5. posting / obsidian studio 설계

---

## 참고
이 계획은 GitHub 공개를 전제로 하므로, 기능 구현과 동시에 문서화와 회귀 테스트를 반드시 병행한다.
