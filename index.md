# 📚 위키 카탈로그

> LLM용 전체 카탈로그. 질문에 답할 때 이 파일을 먼저 읽고 관련 페이지로 진입한다.
> 매 ingest마다 해당 프로젝트 섹션을 갱신한다. (페이지 링크 + 한 줄 요약)

# 📁 프로젝트: security-agent

- [[security-agent]] — 허브: 비침습 웹사이트 보안 점검 에이전트 (코드 `agents/security-agent/`)

## sources
*(아직 없음 — 첫 ingest 때 추가)*

## entities
*(아직 없음)*

## topics
*(아직 없음)*

# 📁 프로젝트: interview-coach

- [[interview-coach]] — 허브: AWS 16 LP 면접 코치 에이전트 (코드 `agents/interview-coach/`)

# 📁 프로젝트: ccna-coach

- [[ccna-coach]] — 허브: CCNA 200-301 문제·해설 사이트. 화면은 GitHub Pages, 답변은 개인 서버(내 Mac)가 제미나이로(키는 로컬에만). 작동 방식 그림은 공용 `docs/tracer-how.*`

# 📁 프로젝트: ccna

- [[ccna]] — 허브: CCNA 200-301 공부 노트(개념 정리·자료 요약). 문제 연습은 ccna-coach
- [[_ccna 도메인 메모]] — 시험 형식(120분·약 100문항)과 6개 출제 영역 비중

# 📁 프로젝트: laptop-helper

- [[laptop-helper]] — 허브: DY-006 SWEEPER. 홈 폴더 정리(다운로드·데스크탑 보고, 문서를 raw로 복사, 종류별 폴더 정리). 스캔은 코드, 승인은 터미널 y/N, 지우기는 휴지통만

# 📁 프로젝트: heartline

- [[heartline]] — 허브: DY-007 CUPID(제안) · 기댈 사람 없는 이를 위한 정서 지원 가상 연인 웹앱 Heartline(+영어 모드) (기획)
- [[Heartline PRD_261119]] — PRD v0.5(핵심만): 정서 지원 가상 연인 + 영어 모드, 핵심 기능 4개(페르소나·마음 대화·위기 대응·영어 모드), 메신저 UI, HTML/JS + 서버 + 터널 + 제미나이 무료, MVP 완료 기준. 시각화 페이지: `docs/heartline/prd.html`
- [[Heartline 체크리스트_261119]] — 2단계 개발 체크리스트: 준비·서버·화면(F1~F4)·안전 검증·배포·다음 산출물, 51개(🔒 안전 15). 페이지 `docs/heartline/checklist.html`
- [[Heartline 테스트 계획_261119]] — 3단계: 자동 테스트 46개(안전·지시·서버·제미나이, 가짜 AI) + 시나리오 데이터(위기 30·일상 50·품질) + 수동 시나리오(화면·위기·답장 품질)

# 🔗 공통 (shared)
- [[나]] — 사용자 본인 페이지
- [[에이전트 코드명]] — 007 스타일 코드명 목록: DY-001 SENTINEL · 002 MIRROR · 003 TRACER · 004 TWIN · 005 PRIMER, 본부 Q-BRANCH
- [[백업 현황]] — 공개 저장소·비공개 저장소(private/)·드라이브(Windows 시절, 중단) 백업 범위, 다른 컴퓨터로 옮기는 법
- [[gemini-chat]] — `scripts/gemini.py`: 터미널 제미나이 대화(키는 .env, 기록은 볼트 밖, 모델 자동 전환). 무료 등급, 민감정보 전송 금지
- [[위키 효과 측정]] — 위키 A/B 테스트: 같은 질문을 위키로·위키 없이 답하게 해 토큰·시간 비교(`tools/wiki_ab_test.py`, 결과는 이 페이지에 누적)
- [[작업 규칙]] — ingest·질문·lint·첫 세션·파일 형식별 처리 상세 규칙(`CLAUDE.md`에서 분리, 해당 작업 때만 읽음)
- [[페이지 작성 규칙]] — 폴더 구조·산출물 위치·파일명·frontmatter·링크 규칙(`CLAUDE.md`에서 분리)
