# Hermes Full Auto Install

이 문서는 이 저장소 URL 하나로 Hermes Agent, Hermes Web UI, Telegram Gateway 준비를 최대한 자동화하는 흐름을 설명합니다.

## 목표

초보 사용자가 설치 중 입력해야 하는 값을 두 가지로 제한합니다.

1. 설치 경로
2. Agent 이름 / Hermes profile 이름

그 외 작업은 설치기가 자동으로 처리합니다.

- OS 감지: macOS, Linux, WSL, Windows
- Python/Git 확인
- Hermes Agent 공식 설치기 실행
- Web UI clone/update
- Hermes profile 디렉터리 생성
- Web UI `.env` 생성
- Web UI Python venv 생성 및 requirements 설치
- Web UI 실행 스크립트 생성
- Telegram Gateway `.env` 입력칸 준비
- 기본 health check

## 실행 방법

### macOS / Linux / WSL

```bash
git clone https://github.com/aihubos/ai-hub-os-hermes.git
cd ai-hub-os-hermes
./install.sh
```

### Windows PowerShell

```powershell
git clone https://github.com/aihubos/ai-hub-os-hermes.git
cd ai-hub-os-hermes
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## 비대화형 실행

Codex나 다른 Agent가 기본값으로 자동 실행해야 할 때:

```bash
python3 install.py --yes
```

값을 지정하려면:

```bash
python3 install.py --install-path ~/HermesHub --agent-name my-agent
```

Windows:

```powershell
python install.py --install-path "$env:LOCALAPPDATA\HermesHub" --agent-name my-agent
```

## 설치 후 실행

설치 완료 화면에 생성된 실행 파일이 표시됩니다.

macOS / Linux / WSL 예시:

```bash
~/HermesHub/start-webui.sh
```

Windows 예시:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\HermesHub\start-webui.ps1"
```

기본 접속 주소:

```text
http://localhost:8788
```

## Telegram Gateway 준비

Telegram은 보안상 완전 자동화할 수 없습니다.

자동으로 할 수 있는 것:

- Hermes profile `.env` 생성
- `TELEGRAM_BOT_TOKEN=` 입력칸 준비
- `TELEGRAM_ALLOWED_USERS=` 입력칸 준비
- Gateway 실행 스크립트 생성

사용자가 직접 해야 하는 것:

1. Telegram에서 `@BotFather`로 봇 생성
2. 받은 토큰을 profile `.env`의 `TELEGRAM_BOT_TOKEN=`에 입력
3. `@userinfobot` 등으로 숫자 사용자 ID 확인
4. `TELEGRAM_ALLOWED_USERS=`에 사용자 ID 입력
5. 생성된 `start-gateway` 스크립트 실행

## 설계상 제한

- API Key, Telegram Bot Token, OAuth 로그인은 사용자의 비밀값이므로 자동 생성하지 않습니다.
- Windows native와 WSL은 경로 체계가 다르므로 한쪽에서 설치한 값을 다른 쪽과 섞지 않는 것이 안전합니다.
- Web UI 기본 포트는 `8788`로 통일했습니다.
