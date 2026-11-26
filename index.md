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
  - [[TRACER 고도화 계획]] — 구글 로그인·Supabase DB·Vercel 상시 운영(무료 등급만)·관리자 페이지·문제은행(객관식 해설 미리 저장, AI 호출 절약). 2026-11-20 배포·상시 운영(tracer-eosin.vercel.app)
  - [[관리자 명령창]] — 웹 관리자 페이지에서 말로 명령(보기·숫자 답변·일괄 작업). 규칙 우선 + 제미나이(정해진 명령만), 위험한 작업은 확인창, 결과 5종 구분. 모의 화면 `admin.html?demo=1`(가상 사용자 500명·1년치, 마이페이지 카드로 누구나 체험)에만 새 관리 기능(오늘 할 일·상세 창·선택·일괄·되돌리기·기간 비교·범위별 정답률·CSV·명령 기록·제미나이 우선·AI 조회(SQL, 브라우저 안 SQLite)·보고서(활동+명령 기록 요약, 파일 받기)), 실제 화면은 그대로
  - 자동 화면 시험: Playwright 94개를 푸시마다 GitHub Actions가 실행(가짜 로그인·DB, 토큰 0) — `agents/ccna-coach/e2e/`

# 📁 프로젝트: ccna

- [[ccna]] — 허브: CCNA 200-301 공부 노트(개념 정리·자료 요약). 문제 연습은 ccna-coach
- [[_ccna 도메인 메모]] — 시험 형식(120분·약 100문항)과 6개 출제 영역 비중

# 📁 프로젝트: laptop-helper

- [[laptop-helper]] — 허브: DY-006 SWEEPER. 홈 폴더 정리(다운로드·데스크탑 보고, 문서를 raw로 복사, 종류별 폴더 정리). 스캔은 코드, 승인은 터미널 y/N, 지우기는 휴지통만

# 📁 프로젝트: heartline

- [[heartline]] — 허브: DY-007 CUPID(제안) · 내 취향대로 만드는 나만의 가상 연인 웹앱 Heartline(+영어 모드) (초기 버전, 앱 docs/heartline/index.html)
- [[Heartline PRD_261119]] — PRD v0.6: 1순위 페르소나(프리셋 6종·직접 만들기·미리보기·여러 명 최대 5) + 연인 대화·영어 모드·기본 안전, 메신저 UI, HTML/JS + 서버 + 터널 + 제미나이 무료. 시각화 페이지 `docs/heartline/prd.html`
- [[Heartline 체크리스트_261119]] — 2단계 개발 체크리스트(v0.6): ⭐ 페르소나·여러 명 우선, 45개 중 40개 완료. 페이지 `docs/heartline/checklist.html`
- [[Heartline 테스트 계획_261119]] — 3단계: 자동 테스트 50개(⭐ 페르소나 카드 반영 포함, 모두 통과) + 수동 시나리오 17개(페르소나 7·화면 6·안전 4). 페이지 `docs/heartline/tests.html`
- 발표(5단계): `docs/heartline/deck.html` 10장 — 만든 이유(지방에서 서울로 올라와 외로웠던 경험) · 기능 4장 · 기술 2장(구조·테스트/배포), 발표자 메모 + `output/제출/2026_11_19_heartline_5_발표.pptx`
- 과제 제출 파일: `wiki/projects/heartline/output/제출/` — 1 PRD·2 체크리스트·3 테스트 목록(파일 하나짜리 HTML+md)·4 앱 zip·5 발표 pptx + 전체 묶음 zip

# 📁 프로젝트: shadowing-coach

- [[shadowing-coach]] — 허브: DY-008 SHADOW · 영어 섀도잉 코치(내 Mac 전용). 유튜브 소리 내려받기(yt-dlp) → Whisper(로컬) 문장 나누기 → Space 누르는 동안 녹음·떼면 바로 재생 → 억양 곡선(YIN·DTW)·알아들은 단어 비교, 날짜별 기록, 단어 클릭하면 뜻(맥 내장 영한사전)
  - [[SHADOW 출시 계획_261122]] — 출시 방향: 크롬 확장(유튜브·넷플릭스 위 자동 멈춤·녹음·바로 재생·되감기), 영상 내려받기 없음, 기기 안 처리(서버비 0), 부분 유료(외부 결제), 검토한 대안·저작권 원칙(프렌즈·VOA)·단계

# 📁 프로젝트: dating
- [[dating]] — 💞 소개팅 앱 허브 (1단계 개발중, 코드는 비공개 저장소)
- [[소개팅 앱 기획_261123]] — 초대제 시험판 → 공개 출시 2단계, HTML/JS + Supabase(RLS) + Capacitor, 0원
- [[소개팅 앱 핵심 가설·차별점_261123]] — 여성이 통제하는 앱, Bumble·Hinge에서 배운 것, 첫 시장 서울의 외국인 여성, 목적 표시, "No more Hongdae boys"
- [[소개팅 앱 그룹 미팅 기능_261124]] — 친구끼리 크루로 매칭해 같이 만나는 미팅 모드, 여성 우선 규칙·안전 장치·파티 모드·단계 제안 (브레인스토밍)

# 📁 프로젝트: language-exchange
- [[language-exchange]] — 🗣️ 언어교환 앱 허브 (기획)
- [[언어교환 앱 기획_261126]] — 한국인 ↔ 한국어 배우는 외국인 1:1 자동 짝, 매일 5분 음성 미션·함께 연속 기록, 만남 앱이 되지 않게 하는 원칙, 18+·나이 법 정리, 0원 구조(음성 48시간 삭제)

# 🔗 공통 (shared)
- [[Claude·agy 분담 기록]] — 실제 작업마다 Claude·agy를 어떻게 나눴는지와 결과(줄 수·찾은 문제·다시 고친 것)를 한 줄씩 기록, 2026-12-07에 정리
- [[Claude·agy 코드 작업 비교 실험_261123]] — Claude 먼저 vs agy 먼저: 둘 다 시험 37/37, Claude 사용량 비슷(95k·97k), agy 검토가 문제 8건 발견 → Claude 작성·agy 검토가 기본
- [[개발 보드]] — 모든 프로젝트의 할 일 한 곳(지금·다음·확인 필요·완료)
- [[나]] — 사용자 본인 페이지
- [[에이전트 코드명]] — 007 스타일 코드명 목록: DY-001 SENTINEL · 002 MIRROR · 003 TRACER · 006 SWEEPER · 007 CUPID · 008 SHADOW, 본부 Q-BRANCH (004 TWIN·005 PRIMER는 2026-11-20 삭제, 빈 번호)
- [[백업 현황]] — 공개 저장소·비공개 저장소(private/)·드라이브(Windows 시절, 중단) 백업 범위, 다른 컴퓨터로 옮기는 법
- [[위키 효과 측정]] — 위키 A/B 테스트: 같은 질문을 위키로·위키 없이 답하게 해 토큰·시간 비교(`tools/wiki_ab_test.py`, 결과는 이 페이지에 누적)
- [[작업 규칙]] — ingest·질문·lint·첫 세션·파일 형식별 처리 상세 규칙(`CLAUDE.md`에서 분리, 해당 작업 때만 읽음)
- [[페이지 작성 규칙]] — 폴더 구조·산출물 위치·파일명·frontmatter·링크 규칙(`CLAUDE.md`에서 분리)
- [[Claude·Gemini 협업 작업지시서]] — Claude·Gemini 공통 규칙 원본: 역할·파일 권한·인박스 흐름·`scripts/gemini.sh`로 제미나이 부르기(확정)
