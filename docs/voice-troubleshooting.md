# Voice Troubleshooting Guide

## What voice input depends on
Hermes for Web uses the browser's Web Speech API.
That means voice input is affected by:
- browser support
- microphone permission
- HTTPS / localhost security rules
- OS-level microphone access
- language setting used by the browser

## Recommended browsers
Best chance of working:
- Google Chrome
- Microsoft Edge

May be limited or inconsistent:
- Safari
- Firefox
- privacy-focused browsers with speech disabled

## Quick checklist
1. Open the WebUI on `localhost` or `127.0.0.1`
2. Click the microphone icon once
3. If prompted, allow microphone access
4. Check macOS System Settings > Privacy & Security > Microphone
5. Make sure your browser is allowed to use the microphone
6. Try speaking a short Korean phrase

## Common errors
### "마이크 권한이 차단되었습니다"
Meaning:
- the browser blocked microphone access

Fix:
- click the site permission icon in the address bar
- allow microphone
- reload the page

### "음성이 감지되지 않았습니다"
Meaning:
- the recognizer started, but heard nothing usable

Fix:
- speak closer to the mic
- reduce background noise
- try a shorter phrase first

### "마이크를 찾지 못했습니다"
Meaning:
- no audio input device available

Fix:
- connect a microphone
- select the right input device in OS settings

### "음성 인식 서비스를 사용할 수 없습니다"
Meaning:
- browser/service/network support issue

Fix:
- try Chrome
- verify internet connectivity
- retry on localhost instead of a remote tunnel if possible

## Product note
Voice input is a convenience layer, not the primary reliability path.
If speech is unstable on a given browser, the text input path remains the safest fallback.
