# 💗 DY-007 CUPID — Heartline (`heartline`)

> 기댈 사람이 없는 사람에게 언제든 곁에 있어 주는 가상 연인 웹앱. 메신저로 톡하듯 마음을 나누고, 원하면 영어 모드로 대화한다.

- **상태**: 기획 → 테스트 먼저 작성 (구현 전)
- **위키 메모**: `wiki/projects/heartline/` (PRD · 체크리스트 · 테스트 계획)
- **PRD 페이지**: https://dodo-yong.github.io/Obsidian/heartline/prd.html

## 폴더
| 위치 | 내용 |
|---|---|
| `server/` | 답변 서버 (Python 표준 라이브러리, 제미나이 무료 등급) — 구현 예정 |
| `server/tests/` | 테스트 (설치 없이 `unittest`, 가짜 AI 사용 → 무료 한도 안 씀) |
| `../../docs/heartline/` | 공개 화면 (구현 예정) |

## 테스트 실행
```bash
cd agents/heartline/server
python3 -m unittest discover -s tests -v
```
- 구현 전에는 모듈이 없어서 테스트가 **건너뜀(skip)** 으로 표시된다. 모듈을 만들면 그 테스트가 자동으로 실행된다.
- 💸 테스트는 실제 AI를 부르지 않는다(가짜 AI). 유료 과금 키가 환경에 있으면 서버는 실행을 거부한다.
