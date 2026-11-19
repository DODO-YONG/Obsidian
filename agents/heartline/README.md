# 💗 DY-007 CUPID — Heartline (`heartline`)

> 내 취향대로 만드는 나만의 가상 연인 웹앱. 성격·말투·호칭·관계를 정하고(프리셋 6종·실시간 미리보기), 최대 5명을 바꿔 가며 메신저처럼 톡한다. 원하면 영어 모드로도.

- **상태**: 초기 버전 (자동 테스트 55/55 통과, 로컬에서 실제 AI·압축 파일 실행 확인)
- **앱**: https://dodo-yong.github.io/Obsidian/heartline/ (답변 서버가 켜져 있을 때 AI가 답함)
- **문서**: [PRD](https://dodo-yong.github.io/Obsidian/heartline/prd.html) · [체크리스트](https://dodo-yong.github.io/Obsidian/heartline/checklist.html) · [테스트](https://dodo-yong.github.io/Obsidian/heartline/tests.html) · 위키 `wiki/projects/heartline/`

## 구조
```
[공개 화면 docs/heartline/]  ──HTTPS──▶  [Cloudflare 임시 터널]  ──▶  [답변 서버 server/]  ──▶  [제미나이 무료 등급]
  대화·페르소나 = 브라우저(IndexedDB)                                    대화 저장 안 함 · 키는 .env
  🆘·위기 감지 = 서버 없이도 동작
```

## 다른 사람에게 주기 (압축 파일)
```bash
./make-zip.sh     # → wiki/projects/heartline/output/YYYY_MM_DD_heartline.zip
```
- 압축을 풀면 `Heartline/` 폴더: **시작하기.html/.txt**(안내서) · **Heartline 실행.command**(맥) · **Heartline 실행.bat**(윈도우) · `start.py` · `server/` · `web/`
- 받은 사람은 파이썬만 있으면 더블클릭 → 키를 물으면 붙여 넣거나 **그냥 엔터 = 맛보기 모드**(미리 써 둔 답장, 인터넷·비용 없음) → 브라우저 자동 열림.
- 키(`.env`)·`start-public.sh`는 넣지 않는다. 한글 파일 이름은 UTF-8 표시로 저장해 윈도우에서도 안 깨진다.

## 실행 (저장소에서, 설치할 것 없음 — 파이썬 3.9+)
```bash
python3 agents/heartline/start.py      # 키 확인 → 빈 포트로 서버 → 브라우저 열기 (키 없으면 맛보기 모드)
cd agents/heartline/server && python3 server.py    # 서버만 (http://127.0.0.1:8766)
./agents/heartline/server/start-public.sh           # 누구나 접속: 터널 주소를 server.json 에 적어 그 파일만 푸시
```
- 💸 유료 과금 키(`ANTHROPIC_API_KEY` 등)가 환경에 있으면 서버가 실행을 거부한다. 제미나이는 **무료 등급 키만**.
- 🔒 대화 본문은 서버 파일·로그에 남지 않는다. 전화번호·이메일·주민번호는 화면과 서버에서 두 번 가린다.

## 테스트
```bash
cd agents/heartline/server && python3 -m unittest discover -s tests -v
```
가짜 AI를 써서 무료 한도를 쓰지 않는다. 수동 시나리오는 테스트 페이지에서 통과/실패를 기록.

## 파일
| 파일 | 하는 일 |
|---|---|
| `server/server.py` | API(`/api/health`·`/api/chat` 스트리밍·`/api/summarize`), CORS, 손님 사용량 제한, 화면 파일 제공 |
| `server/prompts.py` | 지시 조립(안전 → 페르소나 → 모드 → 기억), 답장을 말풍선·교정·위기 신호로 나누기 |
| `server/safety.py` | 위기 감지(화면 `app.js`와 같은 목록), 개인정보 가림, 페르소나·메시지 검사 |
| `server/gemini_client.py` | 제미나이 무료 등급 스트리밍, 바쁘면 다음 모델로 |
| `server/demo.py` | 맛보기 모드: 키 없을 때 페르소나 말투별 대본 답장·영어 교정·🆘 흐름 |
| `start.py` · `Heartline 실행.command/.bat` | 실행기: 키 확인(없으면 맛보기) · 빈 포트 · 브라우저 열기 |
| `make-zip.sh` · `guide/시작하기.*` | 배포용 압축 파일 만들기 · 받는 사람용 안내서 |
| `server/start-public.sh` | 서버 + 터널 + `server.json` 자동 갱신 |
| `../../docs/heartline/index.html` · `app.js` · `app.css` | 앱 화면(입장·대화 목록·페르소나 편집기·대화방·설정) |
