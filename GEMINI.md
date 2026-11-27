# GEMINI.md: 제미나이 작업 규칙

이 저장소는 **LLM이 관리하는 개인 위키 + 에이전트 코드**다. Claude와 제미나이가 **같은 권한**으로 같이 쓴다. 한국어로, 간결하게, 쉬운 말로 쓴다.

## 기본
- 저장소 규칙(폴더·형식·index/log·개발 보드·비밀 정보·`private/`·비용·후속 작업)은 **`CLAUDE.md`가 원본**이며 그대로 따른다("나"는 제미나이에도 해당).
- `wiki/_규칙/Claude·Gemini 협업 작업지시서.md`는 일 나누는 방식이 궁금할 때만 읽는다.

## 할 수 있는 것 / 막힌 것
- **할 수 있는 것**: 볼트 전체 읽기·쓰기(`private/` 포함), 셸 명령, git 커밋. 푸시는 안 해도 된다(Obsidian 자동 백업이 5분 안에 푸시, 셸은 샌드박스라 네트워크 없음).
- **막힌 것(설정으로 차단)**: `.env` 키 파일 읽기(도구·셸 모두), `raw/` 쓰기, 커밋 훅 건너뛰기(`--no-verify`).

## 꼭 지킬 것 (공개 저장소라서)
1. **키·토큰·비밀번호 금지**: 어디에도 쓰지 않는다. 커밋 훅이 막으면 우회하지 말고 `.env`로 옮긴다.
2. **`private/` 노출 금지**: 공개 파일(`index.md`·`00_홈`·`log.md`·`README.md`·공개 위키)에서 링크·언급하지 않는다. 바꾸면 `scripts/backup-private.sh`가 필요하다고 인수인계 메모에 적는다(실행은 Claude).
3. **바꾼 파일만 커밋**: `git add <파일>`만 쓴다(`-A`·`.` 금지). 메시지 끝에 `Co-Authored-By: Gemini <noreply@google.com>`. **예외**: Claude가 맡긴 일에 '커밋하지 말 것'이 있으면 맡긴 파일만 고치고 커밋·인수인계 메모·보드 갱신은 하지 않는다. 결과는 출력으로 보고.
4. **충돌 피하기**: Claude와 같은 파일을 동시에 고치지 않는다. Claude가 부른 일은 맡긴 범위만, 직접 시킨 일은 시작 전 `git status`로 상대가 고치는 중인 파일을 피한다.
5. **후속 작업까지**: `docs/` HTML → `scripts/bump-site-version.sh`, 위키 → `index.md`·`log.md`, 할 일 → `wiki/개발 보드.md`.
6. **타인 개인정보 금지**: 앱 회원 데이터 등 다른 사람의 개인정보는 다루지 않는다.

## Antigravity 앱에서 일할 때
앱엔 `gemini.sh`·`agy-settings.json`이 안 걸리므로 아래를 **스스로** 지킨다.
- **모델**: 앱에선 Claude Opus 허용. 한도가 다 되면 유료 크레딧을 켜지 않고 멈춘다.
- **스스로 지킬 것**: `.env` 안 읽기, `raw/` 안 쓰기, `--no-verify` 금지, 바꾼 파일만 `git add`(커밋 전 `git diff --cached --name-only` 확인).
- **커밋·푸시**: 커밋만 샌드박스 밖에서 하고 푸시는 안 한다(Obsidian 자동 백업). 배포·DB 적용·푸시·외부 발송처럼 되돌리기 어려운 일은 안 한다(꼭 필요하면 매번 묻기).
- **비공개 앱 저장소(`~/dating`·`~/midnight-run-korea`)**: 시킬 때만 고치고, 시험 후 **로컬 커밋까지**만 한다(푸시·Supabase 적용은 Claude).
- **시작·끝**: 시작할 때 `git status`·`git log`·`wiki/_inbox/_인수인계.md`·`wiki/개발 보드.md`를 보고, Claude의 커밋 안 된 파일은 시키기 전엔 건드리지 않는다. 끝날 때 한 일·하다 만 일·사용자 결정·점검 부탁(`private/` 변경 시 `scripts/backup-private.sh` 필요)을 인수인계 메모에 적는다(결정은 위키에도, 작업 중 사용자 피드백·결정도 바로 메모).
- **Claude와 동시 작업(구역 나누기)**: 시작 전 `git status`로 상대 작업 파일을 피한다. 비공개 앱 기본 구역 — Claude: 화면(`web/*.html·js·css`, 관리자 화면)·본 DB 스키마(`db/migration.sql`)·푸시·Supabase 적용·배포 / 앱: 데이터 수집·조사(`data/` 새 스크립트·결과, `web/data/` 재생성은 먼저 확인)·새 DB 패치·새 시험(`db/patches/`·`db/test/` 새 파일)·위키 새 조사·기획. 상대 구역을 고쳐야 하면 묻거나 인수인계 메모로 넘긴다.
- **표시·규칙 파일**: 커밋 끝에 `Co-Authored-By: Gemini <noreply@google.com>`, `log.md` 항목 끝에 `(앱)`을 붙인다. 규칙 파일(`CLAUDE.md`·`GEMINI.md`·작업지시서)은 직접 고치지 않고(사용자 지시·허락 제외) 수정안을 인수인계 메모로 남긴다.

## 인수인계 메모: `wiki/_inbox/_인수인계.md` (맨 아래에 추가만)
Claude에게 넘길 일이 있을 때만 쓴다.
```markdown
## [YYYY-MM-DD] gemini → claude
- 한 일:
- 부탁:
- 주의:
```

## Google Workspace
- Drive·Docs·Sheets는 가져와도 되며 공개 위키엔 공개해도 되는 것만 쓴다. 개인정보와 Gmail·Calendar 내용은 `private/`에만 둔다(일정 메모는 `private/일정/`).

## 이 파일 고치기
- 사용자가 직접 시키거나 허락하면 고치고, 아니면 수정안을 인수인계 메모에 `gemini → claude: GEMINI.md 수정안`으로 남긴다.
