# 🧠 DY-003 TRACER — CCNA 200-301 시험 대비 코치 (`ccna-coach`)

> 단원·세부 범위를 골라 문제를 받고, 답을 내면 해설을 받는다. 화면은 공개 웹사이트, 답변은 내 Mac.

- **화면**: https://dodo-yong.github.io/Obsidian/ccna/ (코드: `docs/ccna/`)
- **답변 서버**: 이 폴더의 `server.py` — 내 Mac에서 `http://127.0.0.1:8765`로 돈다
- **상태**: 상시 운영 (2026-11-20 배포, Vercel 프로젝트 `tracer` · Supabase 프로젝트 `Tracer`)
- **위키 메모**: `wiki/projects/ccna-coach/`

## 🚀 새 구조 (2026-11-20 · 상시 운영 중)
**주소: https://tracer-eosin.vercel.app/ccna/** · 관리자: https://tracer-eosin.vercel.app/ccna/admin.html
내 Mac 없이 항상 동작: **Vercel(화면+/api) + Supabase(DB·구글 로그인)**. 모두 무료 등급, 카드 등록 없음.
**배포 방법(직접 할 일): [SETUP.md](SETUP.md)** · 계획·결정: 위키 `wiki/projects/ccna-coach/topics/TRACER 고도화 계획.md`

```
[브라우저 /ccna/] ─구글 로그인─▶ [Supabase Auth]
      │ 로그인 토큰
      ▼
[Vercel /api (docs/api/index.py)] ─▶ [제미나이 무료 키]   ← 키는 Vercel 환경변수에만
      │ 비밀 키(service_role)
      ▼
[Supabase DB: 사용자·권한·활동 기록·풀이 기록·XP·문제은행]   ← 브라우저는 DB에 직접 못 들어감(RLS)
```
- **로그인**: 구글 계정. 로그인하면 바로 사용(설정으로 승인제 가능). 서브넷 계산은 로그인 없이 누구나.
- **문제은행**: 묶음(범위×난이도×유형)에 30개 이상 쌓이면 90%는 저장된 문제에서, 10%는 새로 만들어 계속 키움. 이미 받은 문제는 다시 안 냄.
  객관식은 만들 때 정답·해설·보기별 이유까지 저장 → **채점·해설에 제미나이 0번**(예전 2번 → 새 문제 1번, 저장 문제 0번). 주관식은 판정만 1번.
  하루 한도를 다 써도 남은 저장 문제는 계속 나옴. "내 문제 해설"은 저장소에 넣지 않음(저작권·개인 입력).
- **품질**: 화면의 "신고하기" → 미해결 신고 3건이면 자동 출제 중지 → 관리자가 검토·수정·숨김. 정답률이 이상하게 낮은 문제 따로 보기.
- **관리자 페이지** `/ccna/admin.html` (주인·관리자만): 대시보드(접속자·제미나이 호출·재사용 비율) · 사용자(권한 켜기/끄기, 하루 한도, 차단, 승인, 관리자 지정은 주인만) · 활동 기록(누가·언제·무엇·기기) · 문제은행.
- **기록 범위**: 이메일·이름·활동(언제·무엇)·기기 종류. IP는 저장 안 함. 한도: 사용자 하루 30회(관리자가 조정), 전체 하루 300회(주인 제외).
- **진도·XP**: 계정에 저장 → 다른 기기에서도 이어짐. 첫 로그인 때 브라우저의 XP를 계정으로 옮김.

| 새 파일 | 설명 |
|---|---|
| `../../docs/api/index.py` | Vercel 함수 하나가 모든 `/api/*`를 받음(라우팅) |
| `../../docs/api/_core.py` | 로그인·권한·한도·문제은행·채점·관리자 로직 |
| `../../docs/api/_db.py` · `_gemini.py` | Supabase REST 호출 · 제미나이 호출(환경변수 키) |
| `../../docs/vercel.json` | Vercel 설정(루트 `docs`, `/api/*` → `index.py`, docs가 바뀔 때만 빌드) |
| `../../docs/ccna/admin.html` | 관리자 페이지 |
| `supabase/schema.sql` | 표·RLS·함수 — Supabase SQL Editor에 붙여 넣기 |
| `SETUP.md` | 계정 준비·배포 순서(직접 할 일) |
| `migrate_private_log.py` | 예전 `private/` 풀이 기록을 내 계정으로 한 번 옮기기 |
| `dev/test_core.py` | 로직 시험 24개(가짜 DB·가짜 제미나이, 사용량 0) |
| `dev/harness.py` | 로컬 화면 시험 서버 http://127.0.0.1:8799/ccna/ (가짜 로그인) |
| `../../.github/workflows/tracer-keepalive.yml` | Supabase 일시정지 방지(하루 한 번 깨우기) |

> 아래는 **예전 방식(내 Mac 서버 + 임시 터널) — 은퇴**. `start-public.sh`를 켜면 `server.json`의 새 주소 안내(home)를 덮어쓰니 쓰지 않는다.

## 구조 (예전)
```
[공개 화면 · GitHub Pages]  ──요청──▶  [내 Mac · server.py]  ──키로 요청──▶  [제미나이 무료 등급]
   docs/ccna/index.html      ◀──답──     127.0.0.1:8765       ◀──────────
   (서브넷 계산은 화면이 직접)            풀이 기록 → private/ccna-coach/
```
- **키는 내 Mac 밖으로 나가지 않는다.** 화면(브라우저)에는 키가 없고, 서버만 볼트 `.env`의 `GOOGLE_API_KEY`를 읽는다.
- **내 사이트에서 온 요청만 받는다.** `https://dodo-yong.github.io`와 로컬 주소 외의 사이트는 403 → 남이 내 무료 한도를 쓰지 못함.
- **정답은 서버에만 둔다.** 화면에는 문제와 보기만 보낸다.
- **서브넷 계산은 AI를 쓰지 않는다.** 화면의 자바스크립트가 직접 만들고 채점 → 서버가 꺼져 있어도, 다른 방문자도 쓸 수 있다.
- 풀이 기록은 `private/ccna-coach/기록.jsonl`에만(공개 저장소 제외 확인 후 저장).

## 실행
```bash
cd ~/Obsidian/agents/ccna-coach && python3 server.py
```
그다음 https://dodo-yong.github.io/Obsidian/ccna/ 를 열면 오른쪽 위가 **"내 서버 연결됨"**으로 바뀐다.
(처음에 브라우저가 "로컬 네트워크 접근"을 물으면 허용. 크롬 권장. 서버로 직접 http://127.0.0.1:8765 를 열어도 같은 화면)

설치할 것 없음(파이썬 기본 기능만). 끄기: `Ctrl+C`.

## 누구나 쓰게 열기 (다른 네트워크에서 접속)
`127.0.0.1`은 '그 기기 자신'이라 다른 사람의 컴퓨터에서는 내 서버를 찾지 못한다.
그래서 내 Mac 서버에 Cloudflare 임시 터널(무료, 가입 불필요)로 공개 주소를 붙인다. 키는 여전히 내 Mac에만 있다.

```bash
cd ~/Obsidian/agents/ccna-coach && ./start-public.sh
```
- 켜지면 현재 서버 주소를 `docs/ccna/server.json`에 적어 GitHub에 올린다 → **방문자는 https://dodo-yong.github.io/Obsidian/ccna/ 만 열면 자동 연결**(1~2분 뒤부터). 접속 코드 없음.
- `Ctrl+C`로 끄면 서버·터널이 꺼지고 `server.json`을 "꺼짐"으로 올린다 → 화면은 "AI 꺼짐 · 서브넷만".
- 켤 때마다 터널 주소가 바뀌지만 `server.json`이 알아서 갱신한다.
- **무료 한도 보호**: 방문자 1명당 시간당 30번 · 방문자 전체 하루 300번(나는 제한 없음). 방문자에게 내 진도·기록 안 보임, 방문자 풀이는 기록 안 함. "내 문제 해설"은 CCNA와 관련 없는 질문엔 답하지 않음.
- **내 진도**는 이 Mac에서 http://127.0.0.1:8765 로 열면 보인다(공개 주소로 열면 방문자 모드).
- 내 Mac이 켜져 있고 이 창이 열려 있을 때만 AI가 동작한다.
- 설정(볼트 `.env`, 선택): `CCNA_GUEST_PER_HOUR`, `CCNA_DAILY_LIMIT`, `CCNA_ACCESS_CODE`(넣으면 다시 코드가 필요해짐).
- 필요: `brew install cloudflared` (한 번). 모델은 한도에 걸린 것을 잠시 뒤로 미뤄 빠르게 응답한다.

## 기능
| 기능 | 제미나이 사용 |
|---|---|
| 단원(6개)·세부 범위(52개) 선택, 난이도(쉬움·보통·어려움) | – |
| 객관식·주관식 문제 받기 → 답 입력 → 정답 여부와 해설 (**문제·해설 모두 영어**, 실제 시험처럼) | ✅ (문제 1번 + 해설 1번) |
| 서브넷 계산 문제와 해설 (영어) | ❌ 화면이 직접 계산 |
| 내 문제 해설: 책·기출 문제와 내 답을 붙여 넣으면 영어 해설 | ✅ |
| 진도: 단원별 정답률, 약한 범위, 최근 풀이 (주인만) | ❌ (내 Mac 기록) |
| 🎮 게임: XP·레벨·칭호·오늘의 퀘스트·업적 배지 (방문자 각자 브라우저에 저장) | ❌ |

### 화면 구성
- **맨 앞 소개**: 예시 문제 카드, 3단계 사용법, 단원별 출제 비중, 칭호 10단계 사다리, 안내 문구(비공식 학습 도구 고지 포함).
  처음 온 사람에게는 펼쳐 보이고, 문제를 풀어 본 사람에게는 **"다시 오셨네요" 안내 카드**(소개 펼치기 · 이어서 풀기)로 접힌다. 직접 펼치거나 접으면 그 선택을 기억.
- **소개 안 "HOW IT WORKS"**: 재생형 구성도(패킷이 브라우저·임시 터널·개인 서버·제미나이·주소 안내판을 오감, AI 문제 10단계 / 서브넷 문제 5단계), 역할 트리, 설계 이유 4개.
  소개 페이지(`docs/index.html#how`)와 같은 공용 파일 `docs/tracer-how.js`·`docs/tracer-how.css`를 쓴다.
- **바로가기 주소**: `…/ccna/#intro`(소개 처음부터) · `…/ccna/#how`(작동 방식). 소개가 접혀 있어도 펼쳐서 보여 주고, 접힘 설정은 그대로.
- **왼쪽** 출제 범위 · **가운데** 문제·답·해설 · **오른쪽** 내 레벨·오늘의 퀘스트·업적 배지·진도.
- 상단: Lv 칩, AI 연결 상태(AI 연결됨 / AI 꺼짐 · 서브넷만), 밝게·어둡게.
- 새 버전이 배포되면 열린 화면이 한 번 자동 새로고침(`scripts/bump-site-version.sh`).

### 🎮 게임 규칙
- **XP**: 정답 쉬움 10 · 보통 15 · 어려움 25, 부분 정답 7, 오답 3, 내 문제 해설 5. 3연속 정답부터 보너스(+2씩, 최대 +10).
- **레벨·칭호 (10단계)**: Cable Rookie → Patch Panel Apprentice → MAC Learner → VLAN Wrangler → Subnet Slicer →
  Trunk Master → OSPF Navigator → ACL Gatekeeper → Packet Tracer → **CCNA Ready**. Lv n에 필요한 누적 XP = 50·n·(n−1).
- **오늘의 퀘스트**: 날짜마다 3개(문제 5개 풀기, 3연속 정답, 특정 단원 2개 정답 등). 완료하면 보너스 XP.
- **업적 배지 14개**: First Ping, Link Up, Full Duplex, STP Survivor, Subnet Sniper, Uptime 100, Daily Driver, Full Topology, 단원별 마스터 6개.
- 저장은 각자 브라우저(localStorage). 서버·GitHub에 올라가지 않음. 패널의 "진행 초기화"로 리셋.

## 💸 비용·개인정보
- 제미나이 **무료 등급** 키만 쓴다. 바쁘거나 한도에 걸리면 다음 모델로 넘어간다(`gemini-3.8-flash` → `3.7-flash` → `3.1-flash-lite`).
- 제미나이에는 단원 이름·문제·내 답만 보낸다. 개인정보는 넣지 않는다.
- 선택: `.env`에 `CCNA_EXAM_DATE=YYYY-MM-DD`를 넣으면 화면에 D-day가 나온다(내 서버에 연결됐을 때만, 공개 화면 코드에는 날짜가 없음).

## 파일
| 파일 | 설명 |
|---|---|
| `server.py` | 답변 서버(제미나이 지시문, 채점, 기록, CORS, 방문자 사용량 제한) |
| `start-public.sh` | 서버 + Cloudflare 임시 터널을 켜고 현재 주소를 `docs/ccna/server.json`으로 공개 |
| `../../docs/ccna/server.json` | 지금 켜진 서버 주소(꺼지면 null) — 화면이 읽어 자동 연결 |
| `gemini_client.py` | 제미나이 REST 호출(모델 자동 전환, JSON 응답) |
| `../../docs/ccna/index.html` | 공개 화면 |
| `../../docs/ccna/topics.json` | 출제 범위(단원·세부 범위) — 화면과 서버가 함께 씀 |
| `../../docs/tracer-how.js` · `.css` | 작동 방식 그림(구성도·트리) — 소개 페이지와 TRACER 소개가 함께 씀 |
