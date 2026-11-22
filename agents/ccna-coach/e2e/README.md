# TRACER 화면 시험 (Playwright)

AI가 매번 브라우저를 눌러 보는 대신, **한 번 써 둔 시험을 GitHub Actions가 푸시마다 자동으로** 돌린다 → Claude 토큰 0.
가짜 로그인·가짜 DB·가짜 제미나이(`../dev/harness.py`)를 띄워서 시험하므로 Supabase·제미나이 사용량도 0.

- 자동 실행: `.github/workflows/tracer-test.yml` — `docs/ccna/`·`docs/api/`·`agents/ccna-coach/`가 바뀐 푸시·PR
- 결과: GitHub 저장소 **Actions → tracer-test** (초록 ✓ / 빨강 ✗). 실패하면 아래 `tracer-test-failures`에 스크린샷·trace(https://trace.playwright.dev 에 끌어다 놓으면 재생)

## 지금 확인하는 것 (49개)
| 영역 | 내용 |
|---|---|
| 공개 페이지 | 선택 화면·소개·개인정보 방침이 열림, 소개/이용 링크, 로그아웃 상태 "Google로 로그인" |
| 로그인 없이 | 출제 범위 목록, AI 문제는 로그인 안내, 서브넷 문제 출제·채점("Calculated by code") |
| 로그인 | 로그인 → 이름 표시 → 로그아웃, 객관식 출제 → B 선택 → Correct·신고 버튼·"다음 문제" |
| 채점→다음 문제 | 채점 전(버튼 비활성·안내)·보기 선택·채점 후(`graded`·"채점 완료"·`#nextBtn2`·선택 고정), "다음 문제"(위 `#gradeBtn`·아래 `#nextBtn2` 둘 다)는 `/api/grade`를 다시 부르지 않고 새 문제로 초기화 |
| 소개 페이지 언어 | 기본 영어(`data-lang-block=en`, "Get Tracer Route", 머리말 `[data-auth]` 숨김), `?lang=ko`·`#ko`면 한국어+로그인 부품 보임, `.lang-sw` 버튼 전환·aria-pressed·새로고침 후 기억, 한국어 처음 화면의 소개 링크 `lang=ko` |
| 상태 버튼 | `#conn` 클릭 → 설명 패널 열기/닫기, 로그인 상태엔 로그인 버튼·개인정보 안내 숨김, 로그아웃이면 표시 |
| 관리자 | 로그아웃이면 로그인 버튼, 주인이면 탭·"로그인됨" |
| 관리자 앱 신고 | 탭에 미처리 3건·이유 라벨·메모, 앱 전용 문제는 "웹 문제은행에는 없는 문제"·stopWeb 없음, "같은 문제 모두 처리"→미처리 감소·전체 보기 reopen 버튼(시험 끝에 되돌림), 대시보드 "앱 신고" 타일 |
| 연결 지연·실패 | `/api/me`를 늦추면 "AI 연결 중…"·설명 패널(로그인 버튼 숨김), 응답 후 "AI 사용 가능"; 계속 실패하면 "AI 연결 늦음", 상태 버튼을 누르면 재연결 |
| 세트 | `#setSeg` 5/10/20(기본 5, localStorage 기억)·"세트 시작", 진행 막대 "세트 i / n", 마지막 문제 버튼 "세트 결과 보기 →", 결과 `#setSummary`(점수·문항 목록)·`#setAgain`·`#setMy`(로그인만); 서브넷(로그아웃)·객관식(로그인) 세트 |
| 마이페이지 | 로그아웃이면 `#myLogin`, 로그인이면 통계(`#myTotal` 등)·옆 패널 숨김(`on-my`), 기록 최신순·"틀린 문제만"·`#histMore`(20개 초과만), 서브넷 풀이가 기록에 나옴 |
| 주관식 중단·틀린 문제 다시 풀기 | `#qtypeSeg`에 short 버튼 없음, 마이페이지 `#retryCard`(개수·버튼), 다시 풀기 세트("다시 풀기 1 / N"·요약·계속 풀기), 맞히면 줄고 `#myTotal` 불변, 기록에 "다시 풀기" 표시, 남은 게 없으면 토스트 |
| 휴대폰·태블릿 | 375px 폭에서 가로 스크롤 없음 (처음·소개·소개 한국어·이용·마이페이지), 820·1024px 문제 풀기 화면 |
| 문제 글 표시(formatQ) | 여러 줄 문제에서 표·출력 줄은 `.q-text .cli` 한 블록, 첫 설명·마지막 질문 줄은 블록 밖; 한 줄짜리 문제는 show 명령이 있어도 `.cli` 없음(시험 안에서 `/api/question` 응답만 바꿔 넣음) |
| 모든 시험 | 자바스크립트 오류가 나면 실패 |

## 내 Mac에서 돌리기 (선택)
```bash
cd ~/Obsidian/agents/ccna-coach/e2e && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m playwright install chromium
```
```bash
cd ~/Obsidian/agents/ccna-coach/e2e && .venv/bin/pytest -q
```
화면을 보면서 돌리려면 `--headed --slowmo 300`을 붙인다.

## 새 기능을 만들 때
1. 기능을 만든 뒤 Claude에게 "이 기능 테스트 추가해 줘" → **시험 작성 도우미**(`.claude/agents/e2e-test-writer.md`, Sonnet)가 `test_tracer.py`에 시험을 추가하고 로컬에서 통과시킨다. 실행은 안 맡긴다(GitHub Actions가 무료로).
2. 가짜 제미나이 답은 `../dev/fakes.py`의 `ask_json` — 객관식 정답은 항상 B.
3. 푸시하면 끝. 실패했을 때만 Claude에게 실패 기록을 보여 주면 된다.

로그인 화면이 바뀌어 가짜 로그인 방식이 달라지면 `../dev/harness.py`의 `FAKE_SB`도 함께 고친다.
