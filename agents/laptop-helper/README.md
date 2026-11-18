# 🧹 DY-006 SWEEPER — 랩탑 정리 도우미 (`laptop-helper`)

> 홈 폴더(`~`)를 대상으로 다운로드·데스크탑 정리, 흩어진 문서 모으기, 폴더 정리를 도와주는 에이전트.
> 스캔은 AI 없이 파이썬 코드가 하고, 대화 모드에서는 Claude가 결과를 설명하고 정리 방법을 제안한다.

- **상태**: 초기 버전
- **위키 메모**: `wiki/projects/laptop-helper/`

## 할 수 있는 일 (첫 버전)
| 기능 | 하는 일 | AI 사용 |
|---|---|---|
| 다운로드·데스크탑 정리 | 종류별 개수·용량, 90일 넘게 안 바뀐 것, 큰 것, **휴지통 후보**(설치 끝난 설치파일 · `(1)`·`복사본` 같은 중복 이름 · 이미 압축 푼 zip) | 보고서는 ❌ |
| 문서 모으기 | 데스크탑·문서·다운로드에서 문서·표(pdf, docx, hwp, pptx, xlsx, csv, md…)를 찾고, 고른 것을 위키 `raw/projects/<프로젝트>/`로 **복사**(원본 유지) | 찾기는 ❌ |
| 폴더 정리 | 폴더 바로 아래 파일을 종류별 하위 폴더(문서·표·이미지·영상·음악·압축·설치파일·Packet Tracer·코드·기타)로 옮김. 하위 폴더는 그대로 | 계획 보기는 ❌ |

## 실행 (맥)
```bash
cd ~/Obsidian/agents/laptop-helper
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 처음 한 번
./run.sh                 # 대화 모드: "다운로드랑 데스크탑 정리해 줘", "CCNA 문서 모아 줘", "~/Documents 정리해 줘"
./run.sh scan            # 다운로드·데스크탑 보고서만 (AI 없음, 사용량 0)
./run.sh docs [키워드]    # 문서 찾기만 (AI 없음)
./run.sh plan ~/Downloads  # 폴더 정리 계획만 보기 (아무것도 안 옮김)
```
- 💸 **추가 요금 없음**: Claude 구독 로그인으로만 실행. `ANTHROPIC_API_KEY`가 있으면 실행을 거부한다. 화면의 "$"는 API 요금 환산 참고치.
- 기본 모델은 사용량을 아끼려고 `claude-sonnet-5-5`(`.env`의 `AGENT_MODEL`로 변경).
- 처음에 macOS가 "데스크탑/문서/다운로드 폴더 접근"이나 "Finder 제어"(휴지통 보내기)를 물으면 허용.

## 🔒 안전장치 (`safety.py`)
- **범위**: 홈 폴더 안만. 그 밖은 읽지도 쓰지도 않는다.
- **보호 구역(목록도 안 봄)**: `~/.ssh` `~/.gnupg` `~/.aws` `~/.config` `~/.claude` `~/Library` `~/.Trash`, 볼트 `private/`, 그리고 `.env`·`*.pem`·`*.key`·`id_rsa*` 같은 비밀 파일.
- **사람이 직접 승인**: 옮기기·복사·휴지통은 실행 직전에 터미널에 목록을 보여 주고 `y`를 쳐야만 실행. AI가 대신 승인할 수 없다.
- **지우기는 휴지통으로만**(Finder 휴지통 → 되돌리기 가능). 영구 삭제 없음. 덮어쓰기 없음(같은 이름이면 ` (2)`를 붙임).
- **Obsidian 볼트 안은 옮기거나 지우지 않음**(git 관리). 위키로는 `raw/projects/`에 복사만.
- 파일 **내용은 읽지 않고** 이름·크기·날짜만 본다. Claude 기본 도구(Bash·Read·Write 등)는 막고 SWEEPER 도구 8개만 허용.
- 무엇을 옮기고 지웠는지는 `private/laptop-helper/작업기록.jsonl`에만 남긴다(파일 이름은 개인 정보 → 공개 저장소 제외). `scan` 보고서도 `private/laptop-helper/보고서/`.

## 도구 (대화 모드)
| 도구 | 하는 일 | 승인 |
|---|---|---|
| `report_downloads_desktop` · `report_folder` | 폴더 현황 보고 | – |
| `find_documents` · `list_wiki_projects` | 문서 찾기, 위키 프로젝트 목록 | – |
| `copy_to_wiki` | 위키 `raw/projects/<프로젝트>/`로 복사 | ✅ y/N |
| `organize_folder` | 종류별 하위 폴더로 옮기기 | ✅ y/N |
| `move_to_trash` | 휴지통으로 | ✅ y/N |
| `current_datetime` | 현재 시각 | – |

## 파일
| 파일 | 설명 |
|---|---|
| `main.py` | 대화 모드(시스템 지시·도구·권한)와 AI 없는 명령(`scan`·`docs`·`plan`) |
| `tidy.py` | 스캔·정리 기능(파이썬만) |
| `safety.py` | 범위·보호 구역·쓰기 허용 검사 |
| `run.sh` | `.env` 읽고 실행 |

## 다음에 해 볼 것
- 디스크 용량 점검(큰 파일·중복 파일), 개발 폴더 정리(안 쓰는 `node_modules`·가상환경) — 첫 버전에서는 범위를 줄여 뺐다.
