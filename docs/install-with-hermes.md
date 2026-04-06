# Install Hermes for Web with One Prompt

Repository:
https://github.com/reallygood83/hermes-for-web

## Goal
Let an existing Hermes CLI agent or Hermes bot install this WebUI from a single prompt.

If the user has never installed Hermes Agent before, use the Full Hermes Install path described in `docs/full-install-from-web.md`.

## Copy-paste installer prompt
아래 프롬프트를 Hermes CLI 또는 Hermes 봇에 그대로 넣으면 됩니다.

설치 프롬프트:

reallygood83/hermes-for-web 저장소(https://github.com/reallygood83/hermes-for-web)를 내 환경에 설치해줘.
다음을 자동으로 진행해줘.
1. 저장소를 적절한 작업 디렉터리에 clone 또는 update
2. 필요한 실행 파일/권한 확인
3. WebUI 를 localhost:8788 기준으로 실행 가능하게 준비
4. 가능하면 백그라운드/자동실행 방식까지 제안 또는 설정
5. 설치 후 접속 주소와 재실행 방법을 알려줘
6. 내 Hermes memory 와 config 를 읽어 개인화가 가능한지 점검해줘
7. 오류가 나면 원인과 수정 방법까지 바로 적용해줘
최종적으로는 "어디에 설치되었는지 / 어떻게 실행하는지 / 무엇이 준비되었는지"를 요약해줘.

## Why this works well
This prompt is optimized for Hermes-style agents because it asks for:
- clone or update behavior
- environment detection
- startup preparation
- memory-aware personalization check
- recovery on failure
- final user-facing summary

## Recommended follow-up prompt
설치가 끝났으면 Cherry Blossom 기본 테마, Assistant Name, Setup Packs, Artifact 생성, Telegram Onboarding Pack 까지 확인해줘.

## Full install prompt for complete beginners

Hermes Agent 를 아직 한 번도 설치해본 적이 없다.
https://github.com/NousResearch/hermes-agent 와 https://github.com/reallygood83/hermes-for-web 를 기준으로 내 환경에 Hermes 전체를 처음부터 설치해줘.
다음을 자동으로 진행해줘.
1. Hermes Agent 설치 또는 update
2. 필요한 의존성/실행 환경 점검
3. Hermes 기본 실행 확인
4. 원하면 Telegram 연결에 필요한 준비 항목도 점검
5. hermes-for-web 설치 또는 update
6. localhost:8788 기준 WebUI 실행 준비
7. 설치 후 접속 주소, 재실행 방법, 다음 추천 단계 요약
오류가 나면 가능한 범위에서 직접 수정하고, 남는 수동 단계만 최소한으로 알려줘.
