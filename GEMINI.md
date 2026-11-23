# GEMINI.md: 제미나이 작업 규칙

이 저장소는 **LLM이 관리하는 개인 위키 + 에이전트 코드**다. Claude와 제미나이가 **같은 권한**으로 같이 쓴다(2026-11-23 사용자 결정). 한국어로, 간결하게, 쉬운 말로.

## 기본: `CLAUDE.md`를 똑같이 따른다
- 저장소 규칙(폴더·페이지 형식·index/log·개발 보드·비밀 정보·`private/`·비용·코드 후속 작업)은 **`CLAUDE.md`가 원본**이다. 거기서 "나"는 제미나이에게도 해당한다.
- 공통 협업 규칙: `wiki/_규칙/Claude·Gemini 협업 작업지시서.md`

## 할 수 있는 것
- 볼트 전체 읽기·쓰기(`private/` 등 개인정보 포함, 사용자 허락), 셸 명령, git 커밋.
- 푸시는 안 해도 된다: Obsidian 자동 백업이 5분 안에 푸시한다(셸은 샌드박스라 네트워크가 없음).
- 막혀 있는 것(설정으로 차단): `.env` 키 파일 읽기(읽기 도구·셸 모두), `raw/` 쓰기, 커밋 훅 건너뛰기(`--no-verify`).

## 꼭 지킬 것 (공개 저장소라서)
1. **키·토큰·비밀번호는 어디에도 쓰지 않는다.** 커밋 훅이 막으면 우회하지 말고 값을 `.env`로 옮긴다.
2. **공개 파일(`index.md`·`00_홈`·`log.md`·`README.md`·공개 위키)에서 `private/`를 링크하거나 언급하지 않는다.** `private/` 내용을 바꾸면 백업(`scripts/backup-private.sh`, 네트워크가 필요해 샌드박스에선 안 됨)이 필요하다고 인수인계 메모에 적는다 → Claude가 실행.
3. **커밋은 내가 바꾼 파일만**: `git add <파일>`로 골라서 넣는다(`git add -A`·`git add .` 금지 — Claude가 작업 중인 파일이 섞인다). 메시지 끝에 `Co-Authored-By: Gemini <noreply@google.com>`.
4. **Claude와 같은 파일을 동시에 고치지 않는다.** Claude가 `scripts/gemini.sh`로 부른 일이면 맡긴 범위만 고친다. 사용자가 직접 시킨 일이면 시작 전에 `git status`로 다른 쪽이 고치는 중인 파일이 있는지 보고, 있으면 피한다.
5. 고친 뒤 후속 작업도 내가 한다: `docs/` HTML → `scripts/bump-site-version.sh`, 위키 페이지 → `index.md`·`log.md`, 할 일 → `wiki/개발 보드.md`.
6. 다른 사람의 개인정보(앱 회원 데이터 등)는 다루지 않는다. 사용자가 대신 동의할 수 없다.

## 인수인계 메모: `wiki/_inbox/_인수인계.md` (맨 아래에 추가만)
Claude에게 넘길 일이 있을 때만 쓴다.
```markdown
## [YYYY-MM-DD] gemini → claude
- 한 일:
- 부탁:
- 주의:
```

## Google Workspace
- Drive·Docs·Sheets 자료는 가져와도 된다. 단 개인정보는 `private/`로, 공개 위키엔 공개해도 되는 것만.
- Gmail·Calendar 내용은 공개 폴더에 쓰지 않는다(일정 메모는 `private/일정/`).

## 이 파일 고치기
고치고 싶은 점은 인수인계 메모에 `gemini → claude: GEMINI.md 수정안`으로 남기거나, 사용자가 허락하면 직접 고친다.
