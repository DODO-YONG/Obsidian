---
type: topic
tags: [프로젝트허브, 앱, 가상연인, 정서지원, 영어]
project: heartline
상태: 기획
date: 2026-11-19
---

# 💗 heartline — DY-007 CUPID

> 코드명: [[에이전트 코드명|DY-007 CUPID]] (제안) · 기댈 사람 없는 이에게 곁이 되어 주는 가상 연인 웹앱 **Heartline**(+영어 모드)

상위: [[00_홈]]

일반 사용자가 쓰는 공개 앱. 핵심은 **정서적 지원**(기댈 사람이 없는, 심리적으로 불안정한 사람), 영어 대화는 부가 기능. 실제 메신저로 톡하는 듯한 따뜻한 UI. 이후 '목적 프롬프트'(자격증·시험 등)로 확장.

- **코드**: `agents/heartline/` ([README](../../../agents/heartline/README.md)) — 서버 `server/`(테스트 먼저 작성됨), 화면 `docs/heartline/`
- **기술(예정)**: HTML/JS 정적 화면 + 파이썬 답변 서버 + Cloudflare 임시 터널 — [[ccna-coach|TRACER]]와 같은 방식(Streamlit 안 씀). AI 엔진은 제미나이 무료 등급만
- **문서**: [[Heartline PRD_261119]] — 기본 구성요소·UI·Tech Spec·MVP
- **PRD 보기 좋은 페이지**: [https://dodo-yong.github.io/Obsidian/heartline/prd.html](https://dodo-yong.github.io/Obsidian/heartline/prd.html) (코드 `docs/heartline/prd.html`, 대화방 시연 포함)

## 진행 단계
1. ✅ PRD (2026-11-19 v0.5, 핵심만 남김)
2. ✅ 체크리스트 (2026-11-19) — [[Heartline 체크리스트_261119]] · [보기 좋은 페이지](https://dodo-yong.github.io/Obsidian/heartline/checklist.html), 51개 항목(🔒 안전 15)
3. ✅ 테스트 파일 (2026-11-19) — [[Heartline 테스트 계획_261119]] · [보기 좋은 페이지](https://dodo-yong.github.io/Obsidian/heartline/tests.html): 자동 테스트 46개(`agents/heartline/server/tests/`, 가짜 AI·설치 없음, 구현 전이라 skip) + 수동 시나리오
4. ⏳ 앱 압축 파일 (`output/`)
5. ⏳ 발표 PPT (`output/`)

## 설계 결정
- **공개 웹사이트**(사용자 결정, v0.2): 누구나 링크로 접속, 가입 없음. 대화·페르소나는 방문자 브라우저에만 저장, 서버는 무저장.
- **Claude 구독은 안 씀**: 개인 구독으로 공개 방문자에게 답하는 건 약관 위반 소지. `ANTHROPIC_API_KEY` 있으면 실행 거부.
- **핵심 목적 = 정서적 지원**(사용자 결정, v0.4): 영어는 부가 영어 모드. 공부·시험은 v2 '목적 프롬프트'. 취약 사용자 기준 안전 원칙(위기 대응 2중 감지, 🆘는 서버 없이 동작, 의존 유도 금지).
- **UI = 실제 메신저 대화방 느낌**(사용자 결정): 입력 중 표시·여러 말풍선·읽음·하트 반응, 따뜻한 피치–로즈 톤. AI 표시는 유지.
- **Streamlit 대신 HTML/JS + 서버 + 터널**(사용자 결정): 메신저 연출·서버 없이 도는 안전 도구·가벼움 때문. Streamlit이 과제 필수면 재검토.
- **AI 엔진 = 제미나이 무료 등급만**(사용자 결정): 로컬 모델·섞기 안은 보류. 무료 등급은 입력이 학습·사람 검토에 쓰일 수 있어 입장 동의·자동 가림·서버 무저장을 MVP 필수로. 어댑터 구조로 나중에 교체 가능.
- **제품에 개발자 개인 정보 없음**(사용자 결정): 일반 사용자용 앱이라 코드·화면·프리셋·PRD에 내 정보·내 위키 자료(CCNA 등)를 넣지 않는다.
- **안전 장치는 MVP 필수**: AI 고지, 성인 캐릭터만, 선정적 내용 금지, 고립 조장 금지, 위기 시 도움 안내.
- **PRD는 핵심만**(사용자 요청, v0.5): 핵심 기능 4개(페르소나·마음 대화·위기 대응·영어 모드). 호흡 도구·기분 체크인·표현 노트·목적 프롬프트 등은 '이후'로.

## 남은 일
- 마감일·발표 대상, Streamlit 필수 여부 확인
- 코드명 확정 후 README 지도·소개 페이지 반영
