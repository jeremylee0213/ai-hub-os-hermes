# Private Release Checklist

Repository target:
- https://github.com/reallygood83/hermes-for-web

Purpose:
Validate this fork in private before sharing it broadly.

## Product checks
- [ ] Cherry Blossom is the default theme on first launch
- [ ] personalization card appears when Hermes memory exists
- [ ] personalization card fails gracefully when memory is empty
- [ ] Darwin works from WebUI
- [ ] GPT-5.4 works from WebUI
- [ ] Artifact modal creates real files
- [ ] Artifact shelf can open and delete files
- [ ] Share / Telegram / Memory artifact actions trigger the right prompts
- [ ] Setup Packs render and run
- [ ] Setup Pack history updates correctly
- [ ] Preflight Validator renders in sidebar tools
- [ ] sidebar icons are visually distinct and non-duplicative

## Docs checks
- [ ] README is understandable for a new Hermes user
- [ ] setup packs are explained in human language
- [ ] examples do not leak personal/private machine assumptions
- [ ] YouTube / X links work
- [ ] repo URL points to the private fork

## Release checks
- [ ] git status clean enough to review
- [ ] screenshots updated if needed
- [ ] obvious debug logs removed
- [ ] startup path/port instructions match actual default behavior
- [ ] local/private-only assumptions are documented clearly
