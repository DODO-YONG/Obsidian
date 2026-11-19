# 작업 로그 (append-only)

> 형식: `## [YYYY-MM-DD] ingest|query|lint|output | 제목` — grep 가능하게 유지.
> 아래에 시간순으로만 추가한다. 기존 항목 수정·삭제 금지.

## [2026-11-18] output | 에이전트 프로젝트 구조·README 시각화·비밀정보 보호 세팅
- `agents/`(+`_template`), 루트 `README.md`(Mermaid 지도), `.gitignore` 비밀 규칙, `.githooks/pre-commit` 키 검사 추가

## [2026-11-18] output | security-agent 이전 (DODO-YONG/security-agent → agents/security-agent, 이력 보존) + 위키 허브·README 등록

## [2026-11-18] output | interview-coach 에이전트 첫 버전 (agents/interview-coach) + 위키 허브·README 등록

## [2026-11-18] output | 작업 소개 페이지(docs/index.html, GitHub Pages) + README 대표 이미지

## [2026-11-18] output | 소개 페이지 톤 낮춤 + gemini-chat 도구 정리(wiki/shared/gemini-chat)

## [2026-11-18] output | 백업 현황 정리(드라이브 백업 11-18 08:32 이후 중단 확인), Windows→맥 이전 내용 추가

## [2026-11-18] output | private/ 비공개 저장소(DODO-YONG/Obsidian-private) 백업 + scripts/backup-private.sh

## [2026-11-18] output | 터미널 작업 기록 페이지(docs/terminal.html) + 공용 스타일(docs/style.css)

## [2026-11-18] output | ccna-coach: CCNA 문제·해설 사이트(docs/ccna, GitHub Pages) + 내 Mac 답변 서버(agents/ccna-coach)

## [2026-11-18] output | 에이전트 코드명(007 스타일) 적용: DY-001 SENTINEL · 002 MIRROR · 003 TRACER · 004 TWIN · 005 PRIMER, 본부 Q-BRANCH

## [2026-11-18] output | TRACER 손님 공개: 접속 코드·사용량 제한·손님 모드 + start-public.sh(Cloudflare 임시 터널). 시험 통과, 문서화는 다음에

## [2026-11-18] output | TRACER 누구나 사용(코드 없음): server.json 자동 연결, 방문자 한도, 모델 쿨다운으로 응답 1~2초

## [2026-11-18] output | TRACER: 문제·해설 영어로, 게임(XP·레벨·칭호·퀘스트·배지) 추가

## [2026-11-18] output | 소개 페이지 갱신: TRACER 카드, 커밋 로그·작업 기록(비공개 저장소·코드명·누구나 접속·영어+게임), 다음 할 일

## [2026-11-18] output | TRACER 사이트 맨 앞에 소개 영역(예시 카드·3단계·출제 비중·칭호 사다리), 재방문자는 한 줄로 접힘

## [2026-11-18] output | 공개 사이트 자동 새 버전 확인(docs/version.json + scripts/bump-site-version.sh)

## [2026-11-18] output | README 갱신: TRACER(영어·누구나 접속·게임·소개), 공개 사이트 표, 스크립트 표, 비용 원칙

## [2026-11-18] output | ccna 공부 프로젝트 생성 (wiki/projects/ccna 허브 + 도메인 메모, raw/projects/ccna)

## [2026-11-18] output | 소개 페이지에 "TRACER 원리" 섹션(docs/index.html #how): 구조도(서버 켜짐/꺼짐 전환)·문제 하나 풀리는 순서(스윔레인)·설계 이유 4개

## [2026-11-18] output | "TRACER 원리" 섹션 개편: 재생형 토폴로지(패킷이 단계별로 이동, AI 문제/서브넷 문제 탭) + 역할 트리(어디서 무엇을)

## [2026-11-18] output | "TRACER 원리" 디자인 다시: 큰 카드 노드·꺾인 연결선·선 이름표(HTTPS·터널·API), 다크모드 전용 색, 진행 막대, 트리 아이콘 통일 (사용자 피드백: 다크모드에서 안 보이고 허접함)

## [2026-11-18] output | TRACER 사이트 소개에도 작동 방식(구성도·트리) 추가 — 공용 docs/tracer-how.{js,css}로 분리해 두 페이지가 함께 씀. 공개 문구 "제 Mac" → "개인 서버·개인 컴퓨터 환경"

## [2026-11-18] output | TRACER 바로가기 주소: /ccna/#intro(소개 처음부터) · /ccna/#how(작동 방식) — 접힘 설정과 상관없이 펼쳐서 보여 줌

## [2026-11-18] output | 문서 정리: README(TRACER 작동 방식 링크·공용 파일·공식 표현), TRACER README(HOW IT WORKS·바로가기), index, 소개 페이지 작업 기록(14:23·14:43) + 미리보기 설정(.claude/launch.json)

## [2026-11-18] output | DY-006 SWEEPER 첫 버전(agents/laptop-helper): 다운로드·데스크탑 정리·문서 모으기(raw로 복사)·폴더 정리, 스캔은 코드·승인은 터미널 y/N·휴지통만 + 코드명·README·홈·index·소개 페이지 등록

## [2026-11-18] output | 위키 효과 측정 도구: tools/wiki_ab_test.py(A 위키 vs B 위키 없이, 읽기 도구만·구독 로그인만) + 질문 목록 + [[위키 효과 측정]] 페이지. 실제 측정은 아직

## [2026-11-18] query | 위키 A/B 첫 측정(질문 2개, sonnet): 위키 쪽이 읽은 토큰 56%·시간 15% 더 많음. 코드엔 README가 이미 요약 역할 → [[위키 효과 측정]]

## [2026-11-18] output | CLAUDE.md 요약판(16KB→4.4KB): 상세 규칙을 [[작업 규칙]]·[[페이지 작성 규칙]](wiki/_규칙/)으로 분리, "index 먼저" → 바로가기 표

## [2026-11-18] query | 위키 A/B 재측정: 위키 방식 −57%(324k→138k), 위키 없이 −33%, 이제 두 방식 거의 같음 → [[위키 효과 측정]]

## [2026-11-18] output | 문서 정리: 소개 페이지(커밋 목록·17:28 토큰 측정 기록·지키는 것), README(폴더 구조·tools 표), 00_홈(위키 효과 측정·규칙 페이지) 반영

## [2026-11-19] output | Heartline(DY-007 CUPID 제안) 1단계 PRD v0.1: 구성요소·UI·Tech Spec·MVP → [[Heartline PRD_261119]], 허브 [[heartline]]

## [2026-11-19] output | Heartline PRD v0.2: 공개 웹사이트 + 제미나이 무료(TRACER 방식)로 Tech Spec 재작성, 19세 확인·개인정보 가림·사용량 제한 추가, 예시 자료 CCNA → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline PRD v0.3: MVP를 영어 회화로 한정(공부·시험 모드는 v2 목적 프롬프트로), 개발자 개인 정보·CCNA 의존 제거 → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline PRD v0.4: 핵심 목적을 정서 지원으로(영어는 부가 모드), 메신저 같은 따뜻한 UI, 위기 대응·의존 방지 강화, 기술은 Streamlit 대신 HTML/JS+서버+Cloudflare 터널, AI 엔진(민감정보) 결정 대기 → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline AI 엔진 결정: C 섞기(마음 대화 = 로컬 모델 Ollama, 영어 모드 = 제미나이 무료), 운영 규칙 추가 → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline AI 엔진 정정: 제미나이 무료 등급만(섞기 안 철회), 민감정보 보완책(입장 동의·자동 가림·요약 일반화·서버 무저장) MVP 필수 → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline PRD v0.5: 핵심 기능 4개 중심으로 압축(부가 기능은 '이후'로, 세부 표·지표·데이터 모델 제거) → [[Heartline PRD_261119]]

## [2026-11-19] lint | Heartline 재확인: PRD에 성적 묘사 거절·개인정보 가림 완료 기준 복원, 허브·README에서 v0.5에서 뺀 기능(호흡·노트·사용량 숫자) 언급 정리

## [2026-11-19] output | Heartline PRD 시각화 페이지 `docs/heartline/prd.html`(대화방 시연·기능 카드·구조도·MVP 체크) → 공개 링크 https://dodo-yong.github.io/Obsidian/heartline/prd.html

## [2026-11-19] output | Heartline PRD 페이지에 재생형 '작동 방식' 추가(마음 대화·위기 대응·영어 모드 통신 흐름 + 역할 트리 + 설계 이유, docs/heartline/how.*), 페이지 기본 다크 모드

## [2026-11-19] output | Heartline 2단계 체크리스트 → [[Heartline 체크리스트_261119]], 페이지 https://dodo-yong.github.io/Obsidian/heartline/checklist.html (진행률·안전만 보기, 체크는 브라우저 저장)

## [2026-11-19] output | Heartline 작동 방식에 '🔌 서버 켜기' 장면 추가: start-public.sh → 서버 켜기 → Cloudflare 임시 주소 받기 → server.json에 적어 그 파일만 푸시 → 화면이 읽어 연결 → 끄면 '꺼짐' 푸시
