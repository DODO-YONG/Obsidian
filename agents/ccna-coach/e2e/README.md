# TRACER 화면 시험 (Playwright)

AI가 매번 브라우저를 눌러 보는 대신, **한 번 써 둔 시험을 GitHub Actions가 푸시마다 자동으로** 돌린다 → Claude 토큰 0.
가짜 로그인·가짜 DB·가짜 제미나이(`../dev/harness.py`)를 띄워서 시험하므로 Supabase·제미나이 사용량도 0.

- 자동 실행: `.github/workflows/tracer-test.yml` — `docs/ccna/`·`docs/api/`·`agents/ccna-coach/`가 바뀐 푸시·PR
- 결과: GitHub 저장소 **Actions → tracer-test** (초록 ✓ / 빨강 ✗). 실패하면 아래 `tracer-test-failures`에 스크린샷·trace(https://trace.playwright.dev 에 끌어다 놓으면 재생)

## 지금 확인하는 것 (17개)
| 영역 | 내용 |
|---|---|
| 공개 페이지 | 선택 화면·소개·개인정보 방침이 열림, 소개/이용 링크, 로그아웃 상태 "Google로 로그인" |
| 로그인 없이 | 출제 범위 목록, AI 문제는 로그인 안내, 서브넷 문제 출제·채점("Calculated by code") |
| 로그인 | 로그인 → 이름 표시 → 로그아웃, 객관식 출제 → B 선택 → Correct·신고 버튼·"다음 문제" |
| 상태 버튼 | `#conn` 클릭 → 설명 패널 열기/닫기, 로그인 상태엔 로그인 버튼·개인정보 안내 숨김, 로그아웃이면 표시 |
| 관리자 | 로그아웃이면 로그인 버튼, 주인이면 탭·"로그인됨" |
| 휴대폰 | 375px 폭에서 가로 스크롤 없음 (처음·소개·이용) |
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
