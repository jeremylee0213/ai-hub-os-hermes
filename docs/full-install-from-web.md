# Hermes from Zero: Full Install via hermes-for-web

## Vision
A user who has never used Hermes before should still be able to start from this repository.

Target flow:
1. install Hermes Agent
2. configure or verify credentials
3. connect Telegram if wanted
4. install Hermes for Web
5. launch WebUI
6. personalize with memory / bot name / setup packs

## Two onboarding paths
### A. Full Hermes Install
For total beginners.

Use when:
- Hermes Agent is not installed yet
- Telegram flow is not configured yet
- user wants the whole stack from one entry point

Expected scope:
- clone/install `https://github.com/NousResearch/hermes-agent`
- verify runtime dependencies
- prepare baseline Hermes CLI usage
- optionally guide Telegram setup
- install/update `https://github.com/reallygood83/hermes-for-web`
- prepare localhost:8788 startup
- summarize next steps

### B. WebUI-only Install
For existing Hermes users.

Use when:
- Hermes Agent already works
- user just wants the WebUI
- user wants a lighter onboarding branch

Expected scope:
- install/update hermes-for-web
- verify WebUI startup
- verify theme / naming / setup pack readiness

## Why this matters
Beginners often do not understand where Hermes Agent ends and where the WebUI begins.
This repository should feel like a front door, not just a side extension.

## Recommended copy for agents
If the user says:
- “I have never used Hermes before” → route them to Full Hermes Install
- “I already use Hermes” → route them to WebUI-only Install
