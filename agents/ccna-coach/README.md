# 🧠 DY-003 TRACER — CCNA 200-301 시험 대비 코치 (`ccna-coach`)

> 단원·세부 범위를 골라 문제를 받고, 답을 내면 해설을 받는다. 화면은 공개 웹사이트, 답변은 내 Mac.

- **화면**: https://dodo-yong.github.io/Obsidian/ccna/ (코드: `docs/ccna/`)
- **답변 서버**: 이 폴더의 `server.py` — 내 Mac에서 `http://127.0.0.1:8765`로 돈다
- **상태**: 초기 버전
- **위키 메모**: `wiki/projects/ccna-coach/`

## 구조
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
