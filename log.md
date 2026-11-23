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

## [2026-11-19] output | Heartline 작동 방식: 끝나면 처음부터 반복 재생, 장면 바꾸면 자동 재생, ◀ ▶·막대 누르면 멈추고 그 단계 보기

## [2026-11-19] output | Heartline 3단계 테스트: 자동 테스트 46개(agents/heartline/server/tests/, unittest·가짜 AI, 구현 전 skip) + 위기 30·일상 50·품질 시나리오 + 수동 시나리오 → [[Heartline 테스트 계획_261119]]

## [2026-11-19] output | Heartline 테스트 페이지 docs/heartline/tests.html: 자동 테스트 46개 목록, 시나리오 데이터 요약(위기 문장 원문은 비공개), 수동 시나리오 통과/실패 기록 → https://dodo-yong.github.io/Obsidian/heartline/tests.html

## [2026-11-19] output | Heartline 4단계: 서버(safety·prompts·gemini_client·server·start-public.sh)와 앱 화면(docs/heartline/index·app.js·app.css) 구현, 테스트 46/46, 로컬 실제 AI 확인, 압축 파일 output/2026_11_19_heartline.zip → 앱 https://dodo-yong.github.io/Obsidian/heartline/

## [2026-11-19] output | Heartline v0.6 재정렬: 1순위를 페르소나(나만의 연인 만들기·바꾸기·여러 명)로. PRD·PRD 페이지·작동 방식(🎨 페르소나 장면)·체크리스트·테스트(50개, 페르소나 카드 반영 4개 추가)·앱(대화 목록 최대 5명, 프리셋 6종, 다섯 묶음 편집기, 실시간 미리보기) 전부 손봄 → [[Heartline PRD_261119]]

## [2026-11-19] output | Heartline 5단계 발표: deck.html 7장(표지·문제→해결·페르소나·시연·작동 방식·결과·다음), PRD 시연과 작동 방식 그림 재사용, 발표자 메모·타이머 + 2026_11_19_heartline_발표.pptx(이미지+메모) → https://dodo-yong.github.io/Obsidian/heartline/deck.html

## [2026-11-19] output | Heartline 압축 파일을 받는 사람용으로: 더블클릭 실행(맥·윈도우)·start.py(키 입력, 없으면 맛보기 모드)·시작하기 안내서(html·txt)·make-zip.sh, 다른 폴더에 풀어 실제 실행 확인, 테스트 55/55

## [2026-11-19] output | Heartline 발표 11장으로 개편: 만든 이유(서울에 처음 올라와 외로웠던 경험)·기능 4장(페르소나·여러 명·연인 대화/영어·기본 안전)·기술 3장(구조·핵심 구현·테스트/배포), pptx 다시 만듦

## [2026-11-19] output | Heartline 발표 9번 장: 코드 블록을 '답장 한 덩어리 → 말풍선·교정 카드·위기 신호' 그림으로 바꿈, pptx 다시 만듦

## [2026-11-19] output | Heartline 발표 9번 장(핵심 구현) 삭제 → 10장, pptx 다시 만듦

## [2026-11-19] output | Heartline 과제 제출 파일 5종을 output/제출/ 에 모음: PRD·체크리스트·테스트 목록 PDF(공개 페이지 인쇄용 모드)+md, 앱 zip, 발표 pptx, 전체 묶음 zip

## [2026-11-19] output | Heartline 공개 시연: start-public.sh로 서버+Cloudflare 터널 켬(공개 링크에서 실제 AI 답장 확인), 발표 1·6·10번 장에 앱 링크+QR 추가, pptx·제출 묶음 다시 만듦

## [2026-11-19] lint | Heartline output/ 중복 정리: 2026_11_19_heartline.zip·_발표.pptx 삭제(제출/ 4_앱.zip·5_발표.pptx와 동일), 링크·make-zip.sh 출력 위치를 제출/로

## [2026-11-19] output | Heartline 제출 문서 1~3을 PDF(쪽 잘림) → 파일 하나짜리 HTML로 교체(make-offline-docs.py, 더블클릭으로 열림·인터넷 없이 그림 동작), 전체 묶음 다시 만듦

## [2026-11-19] output | Heartline 발표도 파일 하나짜리 HTML(2026_11_19_heartline_5_발표.html)로 제출 폴더에 추가, 전체 묶음 다시 만듦

## [2026-11-19] output | 소개 페이지 갱신: DY-007 CUPID 카드·3일차 작업 기록 추가, git log 상자 자동 생성(scripts/update-site-log.py, 하루 커밋 많으면 축약), 작업 기록 하루 6개 넘으면 핵심만 보이고 접기

## [2026-11-20] query | TRACER 고도화 계획 작성: 구글 로그인·Supabase·Vercel 상시 운영(무료만)·관리자 페이지·문제 저장소(객관식 해설 미리 저장, 30개 이후 90% 재사용) → topics/TRACER 고도화 계획

## [2026-11-20] output | TRACER 상시 운영 코드: Vercel /api(docs/api)·Supabase 스키마(RLS)·구글 로그인·문제은행(30개부터 90% 재사용, 객관식 저장 해설)·신고·관리자 페이지(docs/ccna/admin.html)·깨우기 Actions·SETUP.md. 로직 시험 24개·로컬 화면 확인, 배포는 사용자 계정 준비 후

## [2026-11-20] output | TRACER 배포: https://tracer-eosin.vercel.app/ccna/ (Vercel tracer · Supabase Tracer · 구글 OAuth 테스트 모드). 실제 로그인·출제·저장 해설 채점·관리자 확인, github.io → 새 주소 자동 이동, 깨우기 변수 설정

## [2026-11-20] output | TRACER 소개·이용 분리: /ccna/ 선택 화면 → about.html(핵심만, 새 구조 작동 방식 그림) · app.html(이용), 공용 로그인 부품(로그인/로그아웃 분명하게), Q-BRANCH #how 그림도 새 구조로

## [2026-11-20] output | TRACER 구글 로그인 앱 게시: 개인정보 처리방침(privacy.html) 추가, Branding(홈·방침·허용 도메인) 작성, Publish → In production(심사 불필요). 이제 누구나 로그인

## [2026-11-20] output | 공개 소개 갱신: 루트 README(지도·TRACER 표·쓰는 법)와 Q-BRANCH 소개 페이지(TRACER 카드·버튼을 새 주소로, 4일차 작업 기록)

## [2026-11-20] output | TRACER 소개에 '이렇게 관리하고 있어요'(이용 현황·사용자와 권한·활동 기록·문제 검토) 추가

## [2026-11-20] query | TRACER 예전 풀이 기록(private, 시험 2건)은 Supabase로 옮기지 않기로 결정

## [2026-11-20] output | TRACER 자동 화면 시험: Playwright 15개(agents/ccna-coach/e2e) + GitHub Actions tracer-test(푸시마다, 가짜 로그인·DB·제미나이, 토큰 0)

## [2026-11-20] output | 시험 작성 도우미 e2e-test-writer(.claude/agents, Sonnet): 새 기능의 Playwright 시험만 써 주고 실행은 GitHub Actions. tracer-test 첫 실행 성공

## [2026-11-20] output | 작업실 지도(docs/map.html): 에이전트·만들기 도우미·자동 장치·만드는 사람 네 층, 기능이 나가는 길, 토큰 비교, 추가 규칙. 소개 페이지·README에서 링크

## [2026-11-20] output | DY-008 SHADOW 영어 섀도잉 코치 초기 버전(agents/shadowing-coach): 유튜브 소리 내려받기·Whisper 로컬 문장 나누기·누르는 동안 녹음/떼면 재생·억양 곡선·알아들은 단어 비교·날짜별 기록, 로직 시험 11개 → [[shadowing-coach]]

## [2026-11-20] output | 개발 보드 신설 (wiki/개발 보드.md) — 허브별 할 일을 한 곳으로 모음, CLAUDE.md 바로가기·규칙 추가

## [2026-11-20] output | SHADOW 단어 뜻 보기(맥 내장 뉴에이스 영한사전, Swift 도우미, 클릭하면 품사별 짧은 뜻) + 한글 입력 상태에서도 단축키 동작 → [[shadowing-coach]]

## [2026-11-20] output | SHADOW GitHub 바로가기: docs/shadow/ 'SHADOW 열기' 페이지(→127.0.0.1:8777) + 로그인 때 자동 실행(autostart.sh, LaunchAgent), README·소개 페이지 링크 → [[shadowing-coach]]

## [2026-11-20] output | 소개 페이지 SHADOW 소개 보강: 카드(억양 곡선 예시 그림·핵심 기능 6가지), 맨 위 'SHADOW 열기' 버튼, 4일차 작업 기록 4개, 다음 할 것(소리 단위 발음 점수)

## [2026-11-20] output | DY-004 TWIN·DY-005 PRIMER 삭제 (필요 없어서)
- `scripts/gemini.py`, `agents/beginner-faq/`, `wiki/shared/gemini-chat` 삭제. 번호는 빈 번호로 두고 DY-006~ 그대로
- README 지도·목록, CLAUDE.md, index·홈·코드명, ccna-coach 허브(제미나이 키·무료 등급 메모 옮김), 소개·작업실 지도·터미널 페이지에서 제거

## [2026-11-20] output | TRACER 문제은행 미리 채우기 시작
- `agents/ccna-coach/bank/`: Claude가 직접 쓴 객관식을 `questions/<범위>.json`에 두고 `import_bank.py`로 Supabase에 넣음(형식 검사·중복 건너뜀·정답 위치 섞기). 첫 묶음 1.5(TCP·UDP) 30문제.
- 문제은행 사용 기준 `TRACER_BANK_MIN` 기본값 30 → 10. 목표: 범위 52개 × 난이도 3 × 객관식 10개.

## [2026-11-20] output | TRACER 문제은행 1,560문제 채움
- 52개 범위 × 쉬움·보통·어려움 × 객관식 10문제를 Claude(Sonnet 도우미 6개)가 작성 → `agents/ccna-coach/bank/questions/` → `import_bank.py`로 Supabase에 입력. 표본 검토·불확실 항목 확인, IPv6 보기 1개 수정, 4.8·4.9 해설 보강.
- `import_bank.py`: `--only`/`--skip`, 범위와 파일 이름 일치 검사 추가.

## [2026-11-20] output | TRACER 객관식은 문제은행 전용
- 객관식은 제미나이로 만들지 않고 문제은행에서만 출제(안 받은 문제 우선, 다 받으면 반복), AI 사용·하루 한도에 안 셈. 제미나이는 주관식 생성·판정·내 문제 해설에만. 소개·README·작동 그림 문구 갱신.

## [2026-11-22] output | TRACER IP 연결 단원 문제 248개 보강
- 문제은행 검토 결과 단원 3(IP 연결)이 시험 비중 25% 대비 10%로 부족 → `agents/ccna-coach/bank/questions/3.1~3.5.json`에 248문제 추가(총 1,808). 출력 해석·장애 해결 위주, 정답이 가장 긴 보기인 비율 25%로 맞춤. 형식 검사 통과, DB 입력은 아직.
- 같은 날 DB 입력: `import_bank.py --only 3.1,…,3.5` → 새로 248개. README·소개 페이지·작동 그림 문구 1,560 → 1,808, 사이트 버전 올림.

## [2026-11-22] output | TRACER 문제은행 보기 길이 편향 수정
- 정답이 가장 긴 보기여서 몰라도 맞히던 단서 제거: 572문제 보기 수정, 비율 53% → 23%. 파일·DB(원본 그대로인 행만) 갱신. 앱 이름 traceroute로 정함(보드에 할 일).

## [2026-11-22] lint | TRACER 문제은행 전체 검수
- 자동 검사 + 도우미 6개 단원별 검수(1,808문제). 의심 7건 중 6건 수정, 보기별 설명 어긋남 9건 수정, DB 14행 갱신. 정답 키 오류는 없었음.

## [2026-11-22] query | SHADOW 출시 방향 정리: 크롬 확장(유튜브·넷플릭스 위에서 자동 멈춤·녹음·되감기), 영상 내려받기 없음, 부분 유료 → [[SHADOW 출시 계획_261122]] · 허브의 할 일은 개발 보드로 옮김

## [2026-11-22] output | TRACER 세트 풀기·마이페이지
- 세트(5·10·20문제 연속, 결과 화면)와 마이페이지(정답률·풀이 기록·틀린 문제만) 추가, `/api/history`. 로직 시험 7개 추가, 로컬 화면에서 세트 5문제·마이페이지·화면 폭별 가로 넘침 없음 확인.

## [2026-11-22] output | TRACER 틀린 문제 다시 풀기·주관식 멈춤·출시 체크리스트
- 마이페이지 '틀린 문제 다시 풀기'(맞히면 목록에서 빠짐, 진도 통계 제외), `/api/wrong`. 주관식은 잠시 멈춤(화면 숨김·서버 403). 로직 시험 9개 추가. [[플레이스토어 출시 준비]] 페이지 새로 만듦.

## [2026-11-22] query | 플레이스토어 출시 전 점검
- 개발 도구(JDK·Node·Android Studio) 없음, targetSdk 36 필수, 개인 계정 비공개 테스트 12명·14일, 문제은행 공개 저장소 노출, AdMob은 스토어 연결 후 실광고 — [[플레이스토어 출시 준비]]에 추가.
- 같은 날 Play 요구사항 전체 점검표 추가(계정·앱 콘텐츠 신고·기술·스토어 정보·광고). 핵심 위험: 웹뷰 스팸·최소 기능 정책, 개발자 주소 공개 가능성.
- 추가 검토: 국내 세금·신고(종합소득세 필수, 사업자등록은 상담), 지재권 고지, 운영 위험(내 광고 클릭 시 AdMob 정지, 키 분실, 기기 저장 기록 삭제, 배포 국가 한국 먼저).
- 출시 단계 결정: 1차 광고 없이 출시 → 2차 업데이트로 광고 추가. 체크리스트·보드 반영.
- 앱 이름 **Tracer Route**로 확정(Trace Router는 네트워크 도구처럼 보여 제외). 체크리스트·보드·계획 반영.

## [2026-11-22] output | Tracer Route 비공개 저장소
- `DODO-YONG/Tracer-Route`(비공개, 로컬 `~/Tracer-Route`) 만들고 문제은행 원본·`import_bank.py`·출시 체크리스트를 옮김. 공개 저장소에서는 지우고 `.gitignore`로 다시 못 올라가게 막음. 웹 TRACER·Vercel은 그대로.

## [2026-11-22] output | Tracer Route 앱 1차 화면
- 비공개 저장소 Tracer-Route `app/`: 서버 없는 오프라인 앱 화면(세트 풀기·틀린 문제 복습·내 기록·레벨), 화면 언어 한국어·영어 전환(문제·해설은 영어 원문), Capacitor 8 안드로이드 프로젝트(targetSdk 36). 개발 도구 Node·JDK 21·Android 명령줄 도구 설치.

## [2026-11-22] output | Tracer Route 앱 개인정보 처리방침
- `docs/tracer-route/privacy.html`(한·영, GitHub Pages 공개): 수집하는 개인정보 없음, 기록은 기기 안에만, 이메일 문의·오류 신고만 답장·수정 용도로 1년 내 삭제, 광고 넣기 전 개정 예고. 앱 오류 신고 버튼(메일 앱)·방침 링크 연결.

## [2026-11-22] output | Tracer Route 앱 익명 오류 신고 + 관리자 앱 신고 탭
- 앱: 해설 아래 오류 신고 → 이유·메모 → Supabase `app_reports`(공개 키로 넣기만, 실패 시 기기에 모았다가 재전송). 메일 앱 방식은 뺌.
- Supabase: `agents/ccna-coach/supabase/app_reports.sql` 적용(읽기·수정·삭제 막힘, 1분 30건·하루 500건 제한), 권한 확인·에뮬레이터 실제 전송 확인.
- 웹 TRACER 관리자 페이지 '앱 신고' 탭·대시보드 타일, /api/admin/app-reports. 로직 시험 8개·화면 시험 4개 추가(전체 통과). 개인정보 처리방침 4번을 익명 신고로 개정.

## [2026-11-22] output | TRACER·Tracer Route 문제 출력 표시 개선, 앱 릴리스 AAB
- 문제 글의 장비 출력(프롬프트 없는 표·로그·ipconfig·설정)이 일반 글로 깨지던 문제: 문장만 글로, 나머지 줄은 터미널 블록(웹 app.html·앱 같은 규칙, 출력 있는 134문제 모두 블록). 화면 시험 2개 추가(전체 43 통과).
- Tracer Route: 업로드 키(저장소 밖)로 서명한 릴리스 AAB 빌드, 에뮬레이터 확인.

## [2026-11-22] output | Tracer Route 출시 대상: 영어권 기본(인도 중심) + 한국
- 사용자 결정으로 영어권을 기본 대상으로. Play 기본 언어 en-US·한국어 번역, 영어 스토어 이름 `Tracer Route: Network Practice`(30자). 앱 개인정보 처리방침은 영어가 먼저(한국어 화면에서는 #ko로 연결).

## [2026-11-22] lint | 개발 보드: Tracer Route 앱 이름·칭호 변경 완료 처리
- 앱 코드에 이미 반영돼 있음을 확인(칭호 Route Tracer·Exam Ready). 웹 TRACER 칭호는 그대로.
- 스토어 소개 글(영어 기본·한국어 번역) 작성 — 비공개 저장소 문서. 웹 칭호 변경은 앱 출시 뒤로 보드 다음 칸에.
- Tracer Route Play Console 설문 답안 정리(비공개 저장소). 공개 처리방침 요약 줄의 "서버로 아무것도 안 보냄"을 "오류 신고 말고는"으로 수정(본문 4절과 맞춤).
- Tracer Route 출시 방식 결정: Play 개인 계정으로 바로(비공개 테스트 12명·14일). 조직 계정·다른 스토어는 안 함.
- Play 개발자 계정(개인) 생성: 결제·비판매자 신고·기기 확인 완료, 신원 심사 대기.
- TRACER 소개 페이지를 Tracer Route 앱 소개 + 웹 데모 소개로 개편, 영어 기본·한국어 전환(한 파일). 한국어 웹 화면의 소개 링크는 한국어판으로. QR·스토어 링크 자리는 출시 뒤 채움.
- 소개 페이지 공식 주소를 GitHub Pages로: Vercel 주소로 들어오면 넘김(Vercel 무료=비상업 전용, 2차 광고 대비). Vercel엔 웹 데모만.
- TRACER 화면 시험 8개 실패 원인: 아침에 안 꺼진 가짜 시험 서버(8798 포트)에 새 시험이 붙어 쌓인 데이터로 실패. 서버 끄고 conftest가 매번 빈 포트를 고르게 + 포트가 이미 쓰이면 멈추게 고침 → 49개 전부 통과.
- 소개 페이지 무한 이동 수정: tracer-auth.js의 'github.io → Vercel' 규칙과 about.html의 'Vercel → github.io'가 서로 넘김 → 규칙에서 about.html 제외.
- 소개 페이지 작동 방식 그림 탭(로그인·문제 받기·채점·서브넷) 글자가 사라진 버그 수정: 언어 전환 코드가 [data-t]를 바꾸는데 그림 탭도 data-t를 써서 지워짐 → nav는 data-i18n으로. 회귀 시험 추가.
- TRACER·Tracer Route 웹 페이지 파비콘·머리말 로고를 앱 아이콘으로 교체(docs/ccna/icon.svg, apple-touch-icon.png).

## [2026-11-23] output | 소개팅 앱 기획 v0.1 (새 프로젝트 dating)
- ChatGPT 초안 검토 후 재기획: 초대제 시험판 → 공개 출시 2단계, HTML/JS + Supabase(RLS·RPC) + Capacitor(안드로이드만), 구글 로그인 추천, 사진 인증, 만 19세, 권한 시험 먼저.
- 소개팅 앱 로그인 방식 결정: 구글 로그인.

## [2026-11-23] output | 웹 관리자 명령창 + 모의 관리자 화면
- 관리자 페이지 맨 위 명령창: 말로 명령 → 정해진 명령 하나 → 화면의 기존 필터·버튼으로 실행. 보기 5종·숫자 답변·일괄 작업 4종(삭제 예정 표시/취소, 승인 대기 모두 승인, 앱 신고 처리).
- 잘못 알아듣기 보완: 규칙 먼저(제미나이 안 부름) → 제미나이는 목록 안에서만·낮은 온도·예시 제공 → 확신 70% 미만이면 실행 전 확인 → 해석 결과 항상 표시.
- '지워줘'는 실제 삭제가 아니라 '삭제 예정' 표시(다시 접속하면 자동 취소). 새 SQL `admin_ai.sql`(delete_at) 실행 필요.
- 모의 관리자 화면 `admin.html?demo=1`: 로그인 없이 가상 사용자·신고(브라우저 안 가짜 DB), AI는 하루 30회 제한.

## [2026-11-23] lint | 앱 신고 표 권한 누락 수정
- 운영 DB에서 관리자 API(service_role)가 `app_reports`를 읽지 못해 관리자 '앱 신고' 탭이 권한 오류(42501)였음. 대시보드 숫자는 0으로 가려져 있었음.
- `app_reports.sql`에 service_role 권한 추가, Supabase에서 실행 → 앱 신고 탭·명령창 "미처리 신고 몇 건" 정상(미처리 1건).
- `admin_ai.sql`도 운영 DB에 실행 완료, 관리자 명령창 배포·실제 화면 확인(보기·답변 명령).

## [2026-11-23] output | 모의 관리자 데이터 대량화 + 실제/모의 구분 + 실제 화면 기능 끄기
- 모의 DB를 생성기로: 기본 사용자 300명(100~3,000 선택), 신고·문제·활동을 현실적인 분포로, 씨앗 고정.
- 머리말 [실제 관리자 | 모의 관리자] 전환 칸·표시, 모의 화면은 주황 테마.
- 실제 관리자 화면에서는 명령창·일괄 작업·삭제 예정 버튼을 끔(화면 숨김 + 서버 403). `TRACER_ADMIN_AI=1`로 켬.

## [2026-11-23] output | 모의 관리자 1·2단계 + 명령창 확장
- 새 관리 기능은 모의 화면에만(실제 화면은 그대로). 모의 데이터: 사용자 500명·활동 1년치·문제 460·신고 250.
- 1단계: 정렬·페이지·체크 선택·일괄 작업·10초 되돌리기·필터 주소 저장. 2단계: 오늘 할 일 탭·사용자 상세 창·필터 보강.
- 명령창: 오늘 할 일·정렬·가입 기간·주제어/난이도·신고 이유·조건 일괄(사용자·문제)·되돌리기.

## [2026-11-23] output | 모의 관리자 3단계 + 명령 기록 탭 + 체험 입구
- 대시보드 지난 기간 비교·날짜별 가입자·범위별 정답률, CSV 내보내기, 명령 연결(비교·약한 범위·CSV).
- 명령 기록 탭: 명령별 단계 추적(규칙/AI·확신·확인창·결과·시간), 이 브라우저에만 저장, 못 알아들은 문장 복사.
- 이용 화면 마이페이지에 "관리자 화면 체험해 보기" 카드(로그인 없이도).

## [2026-11-23] output | 모의 관리자: 기록에서 되돌리기 + 더미 사용자 도구 + 탭 한 줄
- 명령 기록 줄마다 번호·되돌리기 버튼, 명령("3번 되돌려줘", "승인한 거 되돌려줘") — 시간 제한 없는 되돌리기 기록, 직접 클릭 작업도 기록.
- 승인 대기 등 가상 사용자 추가(버튼·명령), "처음 상태로". 모의 화면 탭을 머리말 아래 한 줄로.

## [2026-11-23] output | 모의 관리자: 제미나이 우선 + 기간 아무 숫자 + AI 조회(SQL)
- 해석 방식 전환(기본 제미나이 우선, 실패 시 규칙). 기간 10일·45일 등 아무 숫자(직접 입력 옵션).
- 찾기·목록 질문은 제미나이가 읽기 전용 SQL을 만들고 브라우저 안 SQLite(모의 데이터)에서 실행 → 조회 결과 탭, 행 선택 일괄 작업·되돌리기. 표 구조와 문장만 제미나이로.
- 모의 화면 제미나이 한도 하루 100회.

## [2026-11-23] output | 공통 대기 카드(traceroute 콘셉트)
- 이용 화면(문제·채점·해설)과 관리자 명령창에서 AI를 기다리는 동안 화면 아래 카드: 패킷 경로 애니메이션·단계별 터미널 줄·진행 막대·팁·지연 안내. `docs/ccna/tracer-wait.js`.
