---
type: topic
tags: [위키운영, 규칙, 협업]
date: 2026-11-23
상태: 개정(2026-11-27, 중복·이력 정리)
---

# 🤝 Claude·Gemini 협업 작업지시서

상위: [[00_홈]]

> 같은 볼트에서 Claude와 제미나이(agy)가 **같은 권한**으로 같이 일하기 위한 **일 나누기 규칙의 원본**입니다. 저장소 규칙(폴더·형식·비밀 정보·비용·외부 AI 기준)은 `CLAUDE.md`, 제미나이 혼자 지킬 것과 Antigravity 앱 작업 규칙은 `GEMINI.md`가 원본입니다(9번).

---

## 1. 위험 세 가지

- **공개 저장소, 5분마다 자동 커밋·푸시**(Obsidian Git). 볼트에 쓰는 파일은 곧 공개된다고 봅니다. 예외는 `.gitignore` 경로(`private/`, `wiki/_inbox/`, `reports/` 등)뿐입니다.
- **비공개 정보가 같은 폴더에 섞여 있음**: `private/`, `.env`(키), `*.private.*`. 어디로 보내도 되는지는 `CLAUDE.md` "외부 AI로 보내는 기준"(학습에 쓰이는지)을 따릅니다. agy는 Claude와 같은 등급이라 `private/`도 맡길 수 있습니다.
- **같은 폴더를 둘이 씀**: 같은 파일을 동시에 고치면 한쪽 내용이 사라집니다 → 파일 단위로 나눕니다(5·7-5번).

## 2. 각자 잘하는 일

| | Gemini (agy) | Claude |
|---|---|---|
| 강점 | 아주 긴 문맥, 구글 검색으로 최신 정보, 이미지·영상·PDF 직접 읽기, Google Workspace, 넉넉한 사용량 | 여러 파일에 걸친 코드 수정, 규칙을 일관되게 지키기, 브라우저 작업, git 관리 |
| 비용 | Google AI Pro 구독(추가 비용 없음) | Claude 구독(사용량을 아껴야 함) |

토큰이 가장 많이 드는 "많이 읽기"를 agy가 맡고, agy는 초안에서 멈추지 않고 반영·커밋까지 끝내서 Claude가 옮겨 적는 일이 없게 합니다.

## 3. 역할

- **agy**: 자료 ingest(`raw/` → 위키), 큰 PDF·공식 문서 대량 정리와 모순 후보(`> ⚠️ 모순:`) 뽑기, 최신 정보 조사(출처 URL 필수), 외부 API·정책 최신성 점검(요청받을 때), 영상·이미지·스캔 PDF 글로 옮기기, 두 번째 검토, 화면 시험(Playwright) 작성.
- **Claude**: 조각을 잇는 핵심 코드(서버·화면), 비공개 저장소(Tracer-Route 등 볼트 밖), 규칙 문서 수정, lint, 일 나누기·agy 결과 확인, 계정 대시보드 작업(7-6).
- **애매할 때**: 같은 파일을 동시에 고치지 않는 것만 지키면 누가 해도 됩니다. 넘길 일은 인수인계 메모에 남깁니다.

## 4. 개발 보드
"보드 맨 위 거 해줘"라고 하면 Claude가 맨 위 항목을 보고, agy에 맞는 일(3번)은 agy에게 맡깁니다.

## 5. 파일 권한

| 경로 | agy | Claude |
|---|---|---|
| 볼트 전체(`wiki/`·`docs/`·`agents/`·`scripts/`·규칙·`index.md`·`log.md`·보드), `private/` | ✏️ | ✏️ |
| `raw/` | 👀 읽기(쓰기는 설정으로 차단) | 👀 읽기 |
| `.env`·`agents/heartline/server/.env`(키) | 🚫 읽기 도구·셸 모두 차단 | 필요할 때만 |
| 셸·git 커밋 | ✅ OS 샌드박스 안(네트워크 없음), `--no-verify` 차단 | ✅ |
| git 푸시 | 안 함 → Obsidian 자동 백업이 푸시 | ✅ |
| 볼트 밖 | `gemini.sh`의 `REPOS`에 있는 폴더만(`-d`, 6번). Tracer-Route는 안 엶 | 필요할 때만 |

- 커밋은 `git add <내가 바꾼 파일>`로 골라서(`-A`·`.` 금지), 커밋 훅(`.githooks/pre-commit`)은 둘 다 거칩니다.
- Claude가 맡긴 일은 맡긴 범위만, 사용자가 직접 시킨 일은 시작 전에 `git status`로 상대가 고치는 파일을 봅니다.

## 6. 제미나이 부르는 방법 (`scripts/gemini.sh`)

사용자는 Claude에게만 말하면 됩니다. Claude가 필요하다고 판단하면 말하지 않아도 부르고 한 줄로 알립니다. 언제 부르는지·어떤 모델을 쓰는지는 `CLAUDE.md` 협업 칸이 원본입니다(제미나이 모델만, 다른 회사 모델은 스크립트가 막음).

```
scripts/gemini.sh "raw/projects/ccna/ospf.pdf 를 ingest 해서 위키에 반영하고 커밋해 줘"
scripts/gemini.sh -m gemini-4-neon-medium "OSPF hello 간격 기본값을 공식 문서로 확인해 줘"
```

| 옵션 | 뜻 |
|---|---|
| `-m <모델>` | 모델(기본 `gemini-4-neon-high`, 목록은 `agy models`) |
| `-e low\|medium\|high` | 생각 강도 |
| `-w` | 진행을 보이게(`scripts/agy-watch.py`). Claude가 부를 땐 Bash 백그라운드 대신 **터미널 패널 탭**에서 `scripts/gemini.sh -w ... 2>&1 \| tee <로그>`로 돌려 사용자가 볼 수 있게 함 |
| `-d <폴더>` | 볼트 밖 비공개 저장소(`REPOS`: 지금 `~/dating`·`~/midnight-run-korea`). 설정 `scripts/agy-settings-repo.json` = 그 폴더만, `.env`·푸시·볼트 접근 차단. 그 저장소엔 `GEMINI.md`가 없어 스크립트가 핵심 규칙을 프롬프트 앞에 붙임. 푸시는 Claude |

- **안전장치**: 사용자 Google AI Pro 로그인으로만 실행(API 키 변수 지움, `modelProvider` 켜져 있으면 멈춤). 유료 AI 크레딧(`useG1Credits`)이 켜져 있으면 멈추고, 한도가 다 되면 기다립니다. Telemetry 꺼 둠(`agy` `/config`).
- **권한 설정** `scripts/agy-settings.json`: 볼트 전체 읽기·쓰기·셸·커밋, 막는 것은 키 파일 읽기·`raw/` 쓰기·`--no-verify`. 작업 폴더는 볼트 루트라 `GEMINI.md`를 자동으로 읽습니다.

### 6-1. Antigravity 앱에서 일할 때
Claude가 없을 때 사용자가 Antigravity 앱에서 직접 시키는 작업, 그리고 Claude Code와 동시에 일할 때의 구역 나누기는 **`GEMINI.md`가 원본**입니다.
- Claude는 돌아오면 **맨 먼저** `wiki/_inbox/_인수인계.md`에서 마지막 `claude →` 항목 뒤의 `gemini →` 항목을 전부 읽고, 거기 적힌 사용자 결정·피드백·부탁을 할 일로 삼습니다. git 기록만 보고 판단하지 않습니다. 그다음 앱이 쓴 코드·기획을 검토합니다.

## 7. 작업 흐름

### 7-1. 한 번의 작업
Claude가 `gemini.sh`로 맡김 → agy가 위키·코드에 반영하고 링크·index·log·보드 갱신, 자기 파일만 커밋(푸시는 자동) → Claude가 `git log`·결과 확인.

### 7-3. 인수인계 메모: `wiki/_inbox/_인수인계.md`
맨 아래에 **추가만** 합니다. `## [YYYY-MM-DD] gemini → claude` 또는 `claude → gemini` 아래에 "한 일 / 부탁 / 주의". 처리가 끝난 옛 항목은 Claude가 가끔 `wiki/_inbox/_인수인계 보관.md`로 옮깁니다.

### 7-4. 코드 수정
**기본: Claude가 짜고 agy가 검토**합니다. agy가 먼저 짜도 Claude 사용량이 줄지 않았고, agy 검토는 Claude 사용량 0으로 진짜 문제를 찾았습니다([[Claude·agy 코드 작업 비교 실험_261123]]). 검토는 기본 모델로 충분합니다. agy가 코드를 고치면 후속 작업(`docs/` → `scripts/bump-site-version.sh`, README 지도·`docs/map.html`)도 agy가 합니다.

### 7-5. 큰 작업은 병렬로 나누기
목적은 **효율과 정확성**입니다.

| 맡는 쪽 | 일 |
|---|---|
| **agy (동시에, 백그라운드)** | 명세만 있으면 혼자 끝낼 덩어리: DB SQL, 서버 시험·가짜 DB, **화면 시험(기본)**, 문서 초안, 조사, 다 짠 코드 검토 |
| **Claude** | 조각을 잇는 핵심 코드, agy에게 줄 **명세**, agy 결과 검토·수정, 브라우저 작업, 사용자 결정 받기 |

- **agy 먼저 출발**: 순서에 매이지 않는 일은 Claude가 자기 몫을 시작하기 전에 띄웁니다(명세 → agy 실행 → Claude 작업). 명세가 덜 정해졌으면 정해진 부분만 먼저 보냅니다.
- **파일 단위로 겹치지 않게**: agy에게 "이 파일만 고치고 커밋하지 말 것"을 적어 주고, 그 파일은 끝날 때까지 Claude가 손대지 않습니다. 커밋은 Claude가 확인한 뒤 함께 합니다.
- 명세는 바로 코드를 짤 수 있을 만큼 정확하게(예: `admin_report(p_days) → {days, cur, prev, daily…}`).
- agy 결과는 그대로 믿지 않고, 실행해 보고 연결부를 확인합니다.

### 7-6. 계정 대시보드는 Claude가 직접
Supabase·구글 클라우드·Vercel·GitHub 설정은 Claude가 Claude in Chrome으로 직접 합니다. 본인 확인·약관 동의·비밀값 입력만 그 자리에서 사용자에게 부탁하고, 끝나면 API·명령어로 확인합니다(예: `rpc/ping`, `curl -I`). SQL을 붙여 넣을 땐 `LANG=en_US.UTF-8 pbcopy`로 한글 깨짐을 막습니다.

## 8. 내용 기준
비밀 정보·개인정보·`private/`·비용 규칙은 `CLAUDE.md`를 따릅니다. 여기에 더해:
- 저작권 자료는 요약하고, 인용은 짧게 출처와 함께. TRACER 문제은행 원본 문제는 쓰지 않습니다.
- 추측은 `(추정)`, 모순은 `> ⚠️ 모순:`, 검토상태는 사용자가 말하지 않았으면 `미확인`. agy가 새로 쓴 위키 페이지인지는 커밋의 `Co-Authored-By: Gemini`로 구분합니다.
- **Google Workspace**: Drive·Docs·Sheets는 가져와도 됩니다. 개인정보와 Gmail·Calendar 내용은 `private/`에만, 공개 위키엔 공개해도 되는 것만.

## 9. 규칙 파일 나눠 관리하기

| 파일 | 원본인 내용 | 고치는 사람 |
|---|---|---|
| **`CLAUDE.md`** | 저장소 규칙(둘 다 따름), agy 부를 때·모델 | Claude |
| **이 작업지시서** | 일 나누기·권한·부르는 방법 | Claude(사용자가 정했거나 둘이 합의한 것) |
| **`GEMINI.md`** | agy 혼자 지킬 것, Antigravity 앱 작업 규칙 | 사용자가 시키거나 허락하면 agy, 아니면 agy가 수정안을 메모로 → Claude 반영 |

- 같은 내용은 한 파일에만 쓰고 다른 파일엔 한 줄 안내만 둡니다.
- 이 문서가 바뀌면 Claude가 인수인계 메모에 `claude → gemini: N번 바뀜(요약)`을 남깁니다.
- 불편한 점은 인수인계 메모에 제안하고 사용자가 정합니다. 새 저장소를 시작하면 agy에게 열지 따로 정합니다.
- 당분간(~2026-12-07) 여러 단계 작업이 끝날 때마다 [[Claude·agy 분담 기록]]에 한 줄 남기고, 쌓인 기록으로 7-4·7-5를 다시 정합니다.
