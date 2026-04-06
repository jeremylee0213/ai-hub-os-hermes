# Hermes WebUI 고도화 스펙 v1

작성일: 2026-04-06
대상 저장소: /Users/moon/hermes-webui
배포 채널: GitHub (오픈소스 저장소 기준)

## 1. 목표

Hermes WebUI 를 단순한 웹 채팅창이 아니라, 다음을 지원하는 “작업 운영 콘솔”로 고도화한다.

1. 한국어 친화 UI
2. 멀티 모델 선택과 안정적 라우팅
3. 자연어 기반 예약작업 생성
4. Obsidian / posting / ShareNote 중심 workflow 강화
5. Harness engineering 기반 품질 검증 레이어 추가
6. GitHub 배포에 적합한 문서화, 설정 분리, 회귀 테스트 강화

## 2. 제품 방향

핵심 포지션:
“채팅 UI”보다 “작업 완주율이 높은 개인 AI 작업실”

핵심 사용자:
- Obsidian 중심 지식노동자
- 리서치 / posting / cron 자동화 사용자
- CLI, Telegram, WebUI 를 넘나드는 Hermes 사용자

## 3. 현재 확인된 개선 축

### A. UX / UI
- 한국어 기본 UI 강화
- 테마 확장 (벚꽃, 네오브루탈리즘, 구찌 스타일)
- 브라우저 캐시 무효화 전략 유지
- 파비콘 / 브랜딩 강화
- 레이아웃 안정성 개선

### B. 모델 오케스트레이션
- Darwin, GPT-5.4, GPT-5.4 Mini, Codex Mini 공존
- config 가 local/custom 이어도 인증된 외부 provider 로 라우팅 가능해야 함
- WebUI 드롭다운 = 실제 사용 가능한 모델 집합

### C. Workflow
- 자연어 cron 생성
- Obsidian 결과물 중심 액션
- artifact 중심 흐름 (세션 → 노트 → posting → ShareNote → cron)

### D. Harness Engineering
- preflight checks
- artifact validation
- retry / recovery
- execution transparency

## 4. 요구사항

### 4.1 모델 관련
필수:
- Darwin 과 GPT-5.4 를 모두 선택 가능해야 함
- 선택 모델이 실제 provider 로 올바르게 라우팅되어야 함
- 모델 변경 후 응답 무반응이 없어야 함

검증:
- Darwin / GPT-5.4 / GPT-5.4 Mini / Codex Mini 각각 간단 질문 응답 성공

### 4.2 테마 관련
필수:
- 기본 테마 외에 벚꽃, 네오브루탈리즘, 구찌 스타일 테마 제공
- /theme 명령과 설정 패널 양쪽에서 선택 가능
- 벚꽃 테마는 사이드바 꽃잎 애니메이션 제공

검증:
- 테마 전환 후 새로고침에도 유지
- UI 가 깨지지 않음

### 4.3 예약작업 관련
필수:
- 사용자가 자연어로 cron 의도를 설명하면 schedule / prompt / deliver 를 자동 초안화
- 예시 버튼 제공
- 생성 후 cron panel 에 바로 반영

향후 확장:
- LLM 기반 cron parser
- dry-run 미리보기
- 자연어 → structured cron explain mode

### 4.4 Obsidian / posting 관련
필수:
- 결과물은 Obsidian workflow 를 우선 고려한 액션 구조를 가져야 함
- 향후 다음 quick action 을 추가할 수 있어야 함:
  - 현재 대화 → Obsidian 노트 저장
  - 현재 결과 → ShareNote 생성
  - 현재 자료 → /posting 시작

### 4.5 품질 검증 (Harness)
필수:
- posting / note / cron 생성 전에 preflight 가능 구조 마련
- 결과물 검증 결과를 보여줄 수 있는 상태 모델 정의

초기 validator 대상:
- posting: frontmatter, 시각화, ShareNote 여부
- note: Obsidian markdown 규칙
- cron: schedule / prompt / deliver 최소 유효성

## 5. 아키텍처 제안

### 5.1 프론트엔드
현재 구조 유지:
- static/index.html
- static/style.css
- static/ui.js
- static/messages.js
- static/panels.js
- static/commands.js
- static/boot.js
- static/sessions.js
- static/workspace.js

원칙:
- no framework
- no build step
- 작은 기능 단위 패치
- 캐시 버스팅은 정적 자산 버전 쿼리로 관리

### 5.2 백엔드
현재 구조 유지:
- server.py
- api/config.py
- api/routes.py
- api/streaming.py
- api/models.py
- api/profiles.py
- api/workspace.py

원칙:
- 모델 목록 생성과 모델 라우팅은 api/config.py 가 단일 진실 원천
- route handler 는 얇게 유지
- WebUI 전용 heuristics 는 문서화

### 5.3 배포 / GitHub 고려사항
- README 스크린샷 업데이트 필요
- THEMES.md 에 신규 테마 추가 필요
- ROADMAP.md 에 workflow/harness 항목 추가 필요
- CHANGELOG.md 업데이트 필요
- 테스트 추가 필요

## 6. 단계별 개발 범위

### Phase 1 — 안정화
- 모델 선택/라우팅 안정화
- WebUI 자동실행 안정화
- 캐시 문제 최소화
- 중복 전송 방지

### Phase 2 — UX 강화
- 한국어 테마 및 브랜딩
- 자연어 cron builder
- quick actions

### Phase 3 — Harness layer
- preflight panel
- artifact validators
- retry / recovery UI
- run history 개선

### Phase 4 — Obsidian studio
- 현재 대화 → 노트
- 현재 노트 → posting
- ShareNote generation shortcuts

## 7. GitHub 배포 전 체크리스트
- README 업데이트
- THEMES.md 업데이트
- CHANGELOG.md 업데이트
- ROADMAP.md 업데이트
- 테스트 통과
- 로컬 실행 검증
- 새 테마 스크린샷 추가
- cron 자연어 UX 설명 추가

## 8. 성공 기준
- 문정님이 WebUI 를 매일 작업실처럼 사용할 수 있을 것
- Darwin 과 GPT-5.4 를 자유롭게 전환 가능할 것
- 예약작업 생성이 “말하듯” 가능할 것
- posting / Obsidian workflow 로 연결되기 쉬울 것
- GitHub 에 공개해도 구조와 문서가 납득 가능할 것
