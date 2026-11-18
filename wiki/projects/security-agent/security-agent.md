---
type: topic
tags: [프로젝트허브, 에이전트, 보안]
project: security-agent
상태: 개발중
date: 2026-11-17
---

# 🛡️ security-agent — DY-001 SENTINEL

> 코드명: [[에이전트 코드명|DY-001 SENTINEL]] · 웹사이트 보안 점검 에이전트

상위: [[00_홈]]

URL을 주면 **비침습(공격 없는) 방식**으로 웹사이트를 점검하고, 발견 항목마다
무엇이 문제인지 · 왜 위험한지 · 얕은 수준의 악용 예시 · 고치는 법을 리포트로 써 주는 대화형 에이전트.

- **코드**: `agents/security-agent/` (Obsidian에선 숨김 — GitHub 또는 터미널에서 확인)
- **기술**: Claude Agent SDK(Python), 커스텀 MCP 도구 7개, 기본 모델 `claude-opus-5-5`
- **원래 저장소**: https://github.com/DODO-YONG/security-agent (2026-11-17 생성, 이 볼트로 이력째 이전, 2026-11-18 보관(Archive) — 읽기 전용)
- **소개 페이지**: https://dodo-yong.github.io/security-agent/ (원래 저장소의 GitHub Pages)

## 점검 항목
| 항목 | 보는 것 |
|---|---|
| 응답 헤더 | `Server`·`X-Powered-By` 등 버전 노출 |
| 보안 헤더 | HSTS, CSP, X-Frame-Options 등 누락 |
| 쿠키 | Secure·HttpOnly·SameSite |
| TLS | HTTPS, 인증서 만료·발급자 |
| 본문 | 에러 메시지, 주석 속 비밀, 디렉터리 목록 |

## 안전장치
- 호스트마다 `authorize_target`으로 **점검 권한을 먼저 묻고**, "예"라고 한 곳만 점검.
- 공격 페이로드(SQLi·XSS 등)는 주입하지 않음 — 일반 GET 요청만.
- 점검 리포트(`reports/`)는 취약점 정보라 **git에 올리지 않음**.

## 지금까지
- 2026-11-17 첫 버전 완성, 테스트용 취약 데모 사이트로 예시 점검 → 높음 2·중간 1·낮음 1 발견.
- 같은 날 Windows+WSL 작업 환경(10분 자동 푸시, 구글 드라이브 백업, 암호화 폴더)과 소개 페이지 제작.
- 2026-11-18 Windows에서 커밋해 둔 이력이 GitHub에 남아 있어, 맥에서 이 볼트의 `agents/`로 이력째 이전. 구글 드라이브 백업은 Windows 시절 것(11-18 08:32 마지막) — [[백업 현황]]

## 다음 할 일
- *(정해지면 추가)*
