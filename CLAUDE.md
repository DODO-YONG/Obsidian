# LLM Wiki 스키마 (요약판)

> **제미나이가 이 파일을 읽고 있다면**: 당신도 이 파일의 규칙을 그대로 따릅니다(같은 권한). 제미나이만의 내용은 `GEMINI.md`, 공통 협업 규칙은 `wiki/_규칙/Claude·Gemini 협업 작업지시서.md`에 있습니다.

이 저장소는 **LLM이 유지보수하는 위키 + 에이전트 코드**다. 사용자는 자료 모으기·질문만 하고, 나머지(읽기·요약·링크·정리·기록)는 내가 한다. 한국어로, 간결하게.

## 어디를 보나 (바로가기)
어디를 볼지 알면 **바로 그 파일로 간다**. 모를 때만 `index.md`(카탈로그)를 먼저 읽는다.

| 질문 대상 | 먼저 볼 곳 |
|---|---|
| 다음에 할 일·"보드 맨 위 거 해줘" | `wiki/개발 보드.md` |
| 에이전트 기능·사용법 | `agents/<이름>/README.md` (security-agent·interview-coach·ccna-coach·laptop-helper·heartline·shadowing-coach) |
| 에이전트 설계 결정·남은 일 | `wiki/projects/<이름>/<이름>.md` |
| 코드명 DY-00x | `wiki/shared/에이전트 코드명.md` |
| CCNA 공부 내용 | `wiki/projects/ccna/` |
| 공개 사이트 | `docs/` |
| 백업 | `wiki/shared/백업 현황.md` |

## 상세 규칙 (해당 작업 때만 읽는다)
- **ingest·질문 저장·lint·첫 세션 세팅·hwp/엑셀/데이터 파일** → `wiki/_규칙/작업 규칙.md`
- **새 페이지·폴더 구조·산출물 위치·파일명·frontmatter·링크 규칙** → `wiki/_규칙/페이지 작성 규칙.md`
- **제미나이와 일 나누기·제미나이 부르기** → `wiki/_규칙/Claude·Gemini 협업 작업지시서.md`

## 🤝 제미나이 협업 (요약)
- 긴 자료 읽기·검색 조사·검토 의견은 `scripts/gemini.sh "할 일"`로 제미나이(Antigravity CLI, 사용자 Pro 로그인)에게 맡겨 Claude 사용량을 아낀다. 제미나이는 나와 **같은 권한**(볼트 전체·`private/`·셸·git 커밋, 푸시는 Obsidian 자동 백업. 키 파일 `.env` 읽기와 `raw/` 쓰기만 차단)이라 맡긴 일을 위키·코드에 직접 반영하고 커밋까지 한다.
- **여러 단계 작업은 겹치지 않는 파일 단위로 agy와 병렬로 나눈다**(명세 주고 백그라운드, 결과는 확인 후 함께 커밋 — 작업지시서 7-5). **순서에 매이지 않는 일은 내 작업보다 agy를 먼저 띄운다**(명세 → agy 실행 → 내 작업). 끝나면 `wiki/shared/Claude·agy 분담 기록.md`에 한 줄(~12-07 비교 중). 코드 검토는 배포 전에.
- **계정 대시보드 화면 조작**(Supabase·구글 클라우드·Vercel·GitHub 설정)은 **내가 Chrome으로 직접** 한다. 본인 확인·동의·비밀값만 사용자에게 부탁하고, 끝나면 API·명령어로 확인(작업지시서 7-6, 2026-11-24 Antigravity 분담안 되돌림).
- **사용자가 말하지 않아도 내가 판단해서 부른다.** 부를 때: 큰 PDF·여러 자료 읽기, 최신 정보 검색(정책·API·버전·가격), 큰 변경 뒤 두 번째 검토, 영·한 글 초안. 부르지 않을 때: 몇 번의 도구 호출로 끝나는 작은 일(부르는 비용이 더 큼), 결과를 바로 이어서 고쳐야 하는 코드 작업. 부르면 "제미나이에게 ○○ 맡김(모델)" 한 줄로 알리고, 결과는 그대로 믿지 말고 확인한 뒤 쓴다. 가벼운 일은 `-m gemini-3.8-flash-medium`.
- 제미나이에게 맡긴 동안 그 범위의 파일은 내가 고치지 않는다. 끝나면 `git log`·`_인수인계.md`로 결과를 확인한다.
- agy(사용자 AI Pro, Telemetry 끔)는 나와 같은 등급으로 본다: `private/` 내용도 맡겨도 된다. 볼트 밖 비공개 저장소는 `scripts/gemini.sh -d <폴더>`(허락된 `REPOS`만: 지금 `~/dating`·`~/midnight-run-korea`, 그 폴더만·`.env` 금지·푸시는 내가).

## 항상 지킬 핵심
- **`raw/`는 읽기 전용**(수정·삭제·이동 금지). 위키는 `wiki/`, 바이너리 산출물은 `wiki/projects/<프로젝트>/output/YYYY_MM_DD_제목.확장자`.
- 위키 페이지를 만들거나 바꾸면 `index.md` 해당 섹션과 `log.md`(`## [YYYY-MM-DD] ingest|query|lint|output | 제목`)를 갱신한다.
- **할 일은 `wiki/개발 보드.md` 한 곳에만** 적는다(허브엔 쓰지 않음). 작업을 끝내면 체크해서 완료 칸으로, 새 할 일은 알맞은 칸에 추가.
- 검토상태는 사용자가 말한 값만(모르면 `미확인`). 모순은 `> ⚠️ 모순:`으로 표시.

## 에이전트 코드 (`agents/`)
- `agents/<이름>/`, 새 프로젝트는 `agents/_template/` 복사. 설계 메모는 `wiki/projects/<이름>/`에 두고 README ↔ 위키 허브 서로 링크. `agents/`는 Obsidian에서 숨김(git엔 올라감).
- 에이전트를 추가하거나 상태(기획·개발중·완료)가 바뀌면 **루트 `README.md`의 Mermaid 지도(노드+`class` 색)와 목록 표**를 갱신한다.
- **코드명**: 에이전트마다 `DY-00x` + 코드명([[에이전트 코드명]]). 보이는 이름에만 쓰고 폴더 이름은 그대로. 새 에이전트면 다음 번호를 붙이고 목록·README 지도·소개 페이지 갱신.
- **만들기 도우미**(`.claude/agents/`)나 **자동 장치**(`.github/workflows/`·`scripts/`)를 추가·변경하면 `docs/map.html`(작업실 지도)도 갱신한다. 도우미는 DY 코드명 없이 하는 일 이름.
- **화면 기능을 만들거나 바꾸면** 시험 작성은 기본 **agy**에 맡긴다(내 작업과 병렬, `wiki/_규칙/Claude·Gemini 협업 작업지시서.md` 7-5). agy 한도가 다 됐을 때만 서브에이전트 `e2e-test-writer`(Sonnet). 매번 브라우저로 직접 눌러 보지 않는다(실행은 GitHub Actions). 현재 대상: TRACER.
- **`docs/` HTML을 고쳤으면** 커밋 전에 `scripts/bump-site-version.sh` 실행(캐시로 옛 화면이 보이는 문제 방지).

## 🔒 비밀 정보 (저장소가 **공개**이고 자동 푸시된다)
- API 키·토큰·비밀번호는 **절대** 코드·md에 쓰지 않는다. `.env`(gitignore)에 두고 변수 이름만 `.env.example`에.
- 올리면 안 되는 문서는 `private/` 또는 `*.private.*`(gitignore). 커밋 훅 `.githooks/pre-commit`이 막으면 우회하지 말고 값을 `.env`로 옮긴다(`--no-verify` 금지).
- 개인정보(실명·연락처 등)를 위키에 쓰기 전엔 공개돼도 되는지 사용자에게 확인한다.

## 🔒 Tracer Route 앱·문제은행 = 비공개 저장소
- 안드로이드 앱 **Tracer Route**(웹 TRACER의 앱판) 코드, **문제은행 원본(문제 JSON)**, 출시 문서는 비공개 저장소 `DODO-YONG/Tracer-Route`(로컬 `~/Tracer-Route`)에만 둔다. 이 볼트(공개)에 문제 파일·앱 코드를 만들거나 올리지 않는다(`.gitignore`에 `agents/ccna-coach/bank/`).
- 웹 TRACER(`agents/ccna-coach`·`docs/ccna`·`docs/api`, Vercel)는 그대로 이 볼트에서 공개 운영. 문제는 Supabase DB에서 읽는다.
- 문제를 DB에 넣을 땐 `python3 ~/Tracer-Route/bank/import_bank.py`. 실제 문제로 로컬 화면 확인은 미리보기 `tracer-real`.

## 🔒 `private/` (git 제외, Obsidian엔 보임)
- 비공개 작업(면접 경험, 비자, 일정 등)은 `private/<주제>/`에, 그 안에 `_<주제> 인덱스.md`.
- **공개 파일(`index.md`·`00_홈`·`log.md`·`README.md`·공개 위키)에서 `private/`를 링크하거나 언급하지 않는다.** log에도 남기지 않는다.
- 새 파일은 `git check-ignore`로 제외되는지 확인. `private/`는 비공개 저장소(`DODO-YONG/Obsidian-private`) → 내용을 바꾸면 작업 끝에 `scripts/backup-private.sh`로 백업. 공개로 바꾸지 않는다.

## 💸 비용 — 추가 요금 절대 없음
- Claude 구독 외 비용 금지. `ANTHROPIC_API_KEY`를 제안·설정하지 않고, 에이전트 코드는 키가 있으면 실행을 거부(`refuse_paid_billing`) — 새 에이전트에도 넣는다.
- 유료 API·클라우드 호스팅·유료 플러그인·유료 GitHub 기능을 제안하지 않는다.
- agy(제미나이)도 추가 요금 없이: 유료 AI 크레딧(`useG1Credits`) 끔, API 키·Cloud 프로젝트 로그인 안 씀, 제미나이 모델만. 한도가 다 되면 기다린다. 예외: Claude가 없을 때 사용자가 **Antigravity 앱**에서 시키는 작업은 Claude Opus 허용(AI Credits 꺼짐, 2026-11-24, 작업지시서 6-1).
- 사용자가 승인한 예외(2026-11-24): 소개팅 앱 미국 출시 때 Apple 개발자 등록비(연 $99). 다른 출시 비용은 매번 먼저 묻는다.
- 구독 사용량도 아낀다: 시험 실행은 짧게, 실행 전 사용량이 든다고 알린다. 화면의 "$"는 API 요금 환산 참고치라고 명시.

## 🔒 외부 AI로 보내는 기준 (2026-11-23 개정)
- 기준은 회사가 아니라 **보낸 내용이 학습에 쓰이는지**다.
- **agy(Antigravity CLI, 사용자 Google AI Pro, Telemetry 끔)** = Claude와 같은 등급. 사용자 본인 정보·`private/`도 된다.
- 볼트 작업에 제미나이가 필요하면 **agy만** 쓴다. 무료 API 키로 직접 부르지 않는다(키는 TRACER·CUPID 앱 전용).
- **제미나이 API 무료 키**(볼트 루트 `.env`의 `GOOGLE_API_KEY`, TRACER·CUPID가 씀)는 학습·사람 검토에 쓰이고 끌 수 없다 → 개인정보·비자·면접·`private/` 내용은 **보내지 않는다**.
- 어디에도 보내지 않는 것: 키·토큰, 다른 사람의 개인정보(앱 회원 데이터 등).
