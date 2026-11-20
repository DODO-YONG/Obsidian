# LLM Wiki 스키마 (요약판)

이 저장소는 **LLM이 유지보수하는 위키 + 에이전트 코드**다. 사용자는 자료 모으기·질문만 하고, 나머지(읽기·요약·링크·정리·기록)는 내가 한다. 한국어로, 간결하게.

## 어디를 보나 (바로가기)
어디를 볼지 알면 **바로 그 파일로 간다**. 모를 때만 `index.md`(카탈로그)를 먼저 읽는다.

| 질문 대상 | 먼저 볼 곳 |
|---|---|
| 에이전트 기능·사용법 | `agents/<이름>/README.md` (security-agent·interview-coach·ccna-coach·laptop-helper·beginner-faq) |
| 에이전트 설계 결정·남은 일 | `wiki/projects/<이름>/<이름>.md` |
| 코드명 DY-00x | `wiki/shared/에이전트 코드명.md` |
| CCNA 공부 내용 | `wiki/projects/ccna/` |
| 공개 사이트 | `docs/` |
| 백업·제미나이 스크립트 | `wiki/shared/백업 현황.md` · `wiki/shared/gemini-chat.md` |

## 상세 규칙 (해당 작업 때만 읽는다)
- **ingest·질문 저장·lint·첫 세션 세팅·hwp/엑셀/데이터 파일** → `wiki/_규칙/작업 규칙.md`
- **새 페이지·폴더 구조·산출물 위치·파일명·frontmatter·링크 규칙** → `wiki/_규칙/페이지 작성 규칙.md`

## 항상 지킬 핵심
- **`raw/`는 읽기 전용**(수정·삭제·이동 금지). 위키는 `wiki/`, 바이너리 산출물은 `wiki/projects/<프로젝트>/output/YYYY_MM_DD_제목.확장자`.
- 위키 페이지를 만들거나 바꾸면 `index.md` 해당 섹션과 `log.md`(`## [YYYY-MM-DD] ingest|query|lint|output | 제목`)를 갱신한다.
- 검토상태는 사용자가 말한 값만(모르면 `미확인`). 모순은 `> ⚠️ 모순:`으로 표시.

## 에이전트 코드 (`agents/`)
- `agents/<이름>/`, 새 프로젝트는 `agents/_template/` 복사. 설계 메모는 `wiki/projects/<이름>/`에 두고 README ↔ 위키 허브 서로 링크. `agents/`는 Obsidian에서 숨김(git엔 올라감).
- 에이전트를 추가하거나 상태(기획·개발중·완료)가 바뀌면 **루트 `README.md`의 Mermaid 지도(노드+`class` 색)와 목록 표**를 갱신한다.
- **코드명**: 에이전트마다 `DY-00x` + 코드명([[에이전트 코드명]]). 보이는 이름에만 쓰고 폴더 이름은 그대로. 새 에이전트면 다음 번호를 붙이고 목록·README 지도·소개 페이지 갱신.
- **화면 기능을 만들거나 바꾸면** 시험 작성은 서브에이전트 `e2e-test-writer`(Sonnet)에 맡긴다. 매번 브라우저로 직접 눌러 보지 않는다(실행은 GitHub Actions). 현재 대상: TRACER.
- **`docs/` HTML을 고쳤으면** 커밋 전에 `scripts/bump-site-version.sh` 실행(캐시로 옛 화면이 보이는 문제 방지).

## 🔒 비밀 정보 (저장소가 **공개**이고 자동 푸시된다)
- API 키·토큰·비밀번호는 **절대** 코드·md에 쓰지 않는다. `.env`(gitignore)에 두고 변수 이름만 `.env.example`에.
- 올리면 안 되는 문서는 `private/` 또는 `*.private.*`(gitignore). 커밋 훅 `.githooks/pre-commit`이 막으면 우회하지 말고 값을 `.env`로 옮긴다(`--no-verify` 금지).
- 개인정보(실명·연락처 등)를 위키에 쓰기 전엔 공개돼도 되는지 사용자에게 확인한다.

## 🔒 `private/` (git 제외, Obsidian엔 보임)
- 비공개 작업(면접 경험, 비자, 일정 등)은 `private/<주제>/`에, 그 안에 `_<주제> 인덱스.md`.
- **공개 파일(`index.md`·`00_홈`·`log.md`·`README.md`·공개 위키)에서 `private/`를 링크하거나 언급하지 않는다.** log에도 남기지 않는다.
- 새 파일은 `git check-ignore`로 제외되는지 확인. `private/`는 비공개 저장소(`DODO-YONG/Obsidian-private`) → 내용을 바꾸면 작업 끝에 `scripts/backup-private.sh`로 백업. 공개로 바꾸지 않는다.

## 💸 비용 — 추가 요금 절대 없음
- Claude 구독 외 비용 금지. `ANTHROPIC_API_KEY`를 제안·설정하지 않고, 에이전트 코드는 키가 있으면 실행을 거부(`refuse_paid_billing`) — 새 에이전트에도 넣는다.
- 유료 API·클라우드 호스팅·유료 플러그인·유료 GitHub 기능을 제안하지 않는다.
- 구독 사용량도 아낀다: 시험 실행은 짧게, 실행 전 사용량이 든다고 알린다. 화면의 "$"는 API 요금 환산 참고치라고 명시.

## 🔒 외부 AI(제미나이 등)로 보내지 않는 것
- 개인정보, 비자, 면접 경험, `private/` 내용, 키·토큰은 `scripts/gemini.py` 등 외부 AI로 **보내지 않는다**(무료 등급은 서비스 개선에 쓰일 수 있음 — [[gemini-chat]]).
