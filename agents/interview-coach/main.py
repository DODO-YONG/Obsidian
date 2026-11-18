"""AWS 리더십 원칙(LP) 면접 코치 에이전트 (Claude Agent SDK).

- 내 경험 은행(Obsidian 위키 private 구역)을 읽고, 약한 원칙부터 질문한다.
- 답하면 꼬리 질문으로 파고든 뒤, STAR·본인 행동·수치·원칙 적합도로 평가한다.
- 연습 결과는 private 구역의 `연습기록/`에 남아 다음 연습에 반영된다.

개인 경험 데이터는 코드와 분리되어 git에 올라가지 않는 폴더에만 읽고 쓴다.

실행: python main.py   (종료: exit / 종료)
"""

import asyncio
import os
import re
import subprocess
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

from principles import NAMES, PRINCIPLES

# 코치 도구는 allowed_tools로 자동 승인되고, 그 밖의 도구만 can_use_tool로 막는 것이 의도된 설정
warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
# 개인 데이터 위치: 기본은 볼트의 private 구역 (git 제외)
DATA_DIR = Path(
    os.environ.get("INTERVIEW_DATA_DIR") or BASE_DIR.parents[1] / "private" / "interview-coach"
).resolve()
EXP_DIR = DATA_DIR / "경험"
LOG_DIR = DATA_DIR / "연습기록"


def data_dir_is_private() -> bool:
    """데이터 폴더가 git에서 제외돼 있는지 확인. 공개 저장소로 새는 것을 막는다."""
    probe = LOG_DIR / "_probe.md"
    try:
        r = subprocess.run(
            ["git", "check-ignore", "-q", str(probe)],
            cwd=DATA_DIR if DATA_DIR.exists() else BASE_DIR,
            capture_output=True,
        )
    except FileNotFoundError:
        return True  # git이 없으면 업로드될 일도 없음
    if r.returncode == 128:  # git 저장소 밖
        return True
    return r.returncode == 0


PRIVATE_OK = False  # main()에서 확인 후 설정


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _frontmatter(md: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", md, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r]', " ", name).strip()
    return name[:80] or "제목없음"


def _norm(s: str) -> str:
    """대소문자·쉼표·세미콜론·공백 차이를 무시하고 비교하기 위한 정규화."""
    return re.sub(r"[^0-9a-z가-힣]+", "", s.lower())


def _resolve_principle(name: str) -> str | None:
    key = _norm(name)
    if not key:
        return None
    for p in PRINCIPLES:
        if key in (_norm(p["name"]), _norm(p["ko"])) or _norm(p["name"]).startswith(key):
            return p["name"]
    return None


# ---- 도구 ------------------------------------------------------------------

@tool("current_datetime", "현재 날짜와 시간.", {})
async def current_datetime(args: dict[str, Any]) -> dict[str, Any]:
    return _text(datetime.now().strftime("%Y-%m-%d %H:%M (%A)"))


@tool("list_principles", "16개 리더십 원칙의 이름·한국어 풀이·질문 씨앗 목록.", {})
async def list_principles(args: dict[str, Any]) -> dict[str, Any]:
    lines = []
    for i, p in enumerate(PRINCIPLES, 1):
        qs = " / ".join(p["questions"])
        lines.append(f"{i}. {p['name']} ({p['ko']}) — {p['gist']}\n   질문 예: {qs}")
    return _text("\n".join(lines))


@tool(
    "get_progress",
    "원칙별 연습 횟수·평균 점수·마지막 연습일과, 경험 은행에서 각 원칙에 연결된 경험 수를 보여 준다. "
    "다음에 연습할 원칙을 고를 때 쓴다.",
    {},
)
async def get_progress(args: dict[str, Any]) -> dict[str, Any]:
    stats = {n: {"count": 0, "scores": [], "last": ""} for n in NAMES}
    if LOG_DIR.exists():
        for f in sorted(LOG_DIR.glob("*.md")):
            fm = _frontmatter(f.read_text(encoding="utf-8"))
            lp = _resolve_principle(fm.get("LP", ""))
            if not lp:
                continue
            stats[lp]["count"] += 1
            try:
                stats[lp]["scores"].append(float(fm.get("점수", "")))
            except ValueError:
                pass
            stats[lp]["last"] = max(stats[lp]["last"], fm.get("date", ""))

    exp_cover = {n: 0 for n in NAMES}
    if EXP_DIR.exists():
        for f in EXP_DIR.glob("*.md"):
            fm = _frontmatter(f.read_text(encoding="utf-8"))
            listed = {_resolve_principle(x) for x in fm.get("LP", "").strip("[]").split(",")}
            # "Have Backbone; Disagree and Commit"처럼 쉼표 없는 이름도 통째로 확인
            listed |= {n for n in NAMES if _norm(n) in _norm(fm.get("LP", ""))}
            for n in listed - {None}:
                exp_cover[n] += 1

    rows = ["원칙 | 연습 | 평균(5점) | 마지막 | 연결된 경험"]
    for n in NAMES:
        s = stats[n]
        avg = f"{sum(s['scores']) / len(s['scores']):.1f}" if s["scores"] else "-"
        rows.append(f"{n} | {s['count']} | {avg} | {s['last'] or '-'} | {exp_cover[n]}")
    return _text("\n".join(rows))


@tool("list_experiences", "경험 은행의 경험 목록(파일명·관련 원칙·완성도).", {})
async def list_experiences(args: dict[str, Any]) -> dict[str, Any]:
    if not EXP_DIR.exists():
        return _text("경험 은행이 비어 있습니다.")
    rows = []
    for f in sorted(EXP_DIR.glob("*.md")):
        fm = _frontmatter(f.read_text(encoding="utf-8"))
        rows.append(f"- {f.stem} | LP: {fm.get('LP', '-')} | 완성도: {fm.get('완성도', '-')}")
    return _text("\n".join(rows) or "경험 은행이 비어 있습니다.")


@tool("read_experience", "경험 은행의 경험 하나를 읽는다. name은 list_experiences의 파일명.", {"name": str})
async def read_experience(args: dict[str, Any]) -> dict[str, Any]:
    path = (EXP_DIR / f"{Path(args['name']).stem}.md").resolve()
    if path.parent != EXP_DIR.resolve() or not path.exists():
        return _text("그런 경험이 없습니다. list_experiences로 이름을 확인하세요.")
    return _text(path.read_text(encoding="utf-8"))


@tool(
    "save_session",
    "한 질문의 연습 결과를 연습기록에 저장한다. principle은 원칙 영문명, score는 1~5 종합 점수, "
    "markdown에는 질문·답변 요약·꼬리 질문·항목별 평가·개선 포인트를 담는다.",
    {"principle": str, "score": float, "question": str, "markdown": str},
)
async def save_session(args: dict[str, Any]) -> dict[str, Any]:
    if not PRIVATE_OK:
        return _text("저장 거부: 데이터 폴더가 git 제외 상태가 아닙니다(공개 유출 위험).")
    lp = _resolve_principle(args["principle"])
    if not lp:
        return _text(f"알 수 없는 원칙입니다. 다음 중 하나: {', '.join(NAMES)}")
    score = max(1.0, min(5.0, float(args["score"])))
    now = datetime.now()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z]+", "-", lp).strip("-")
    path = LOG_DIR / f"{now:%Y-%m-%d_%H%M%S}_{slug}.md"
    body = (
        f"---\ntype: topic\ntags: [면접, 연습기록]\nproject: interview-coach\n"
        f"date: {now:%Y-%m-%d}\nLP: {lp}\n점수: {score:g}\n---\n\n"
        f"# {lp} 연습 ({now:%Y-%m-%d %H:%M})\n\n상위: [[_경험은행 인덱스]]\n\n"
        f"**질문**: {args['question']}\n\n{args['markdown'].strip()}\n"
    )
    path.write_text(body, encoding="utf-8")
    return _text(f"저장 완료: 연습기록/{path.name}")


@tool(
    "save_experience",
    "연습 중 사용자가 새로 말한 경험을 경험 은행에 '초안'으로 새 파일로 저장한다(기존 파일은 덮어쓰지 않음). "
    "사용자가 동의했을 때만 호출한다. principles는 쉼표로 구분한 원칙 영문명, markdown은 STAR 초안.",
    {"title": str, "principles": str, "markdown": str},
)
async def save_experience(args: dict[str, Any]) -> dict[str, Any]:
    if not PRIVATE_OK:
        return _text("저장 거부: 데이터 폴더가 git 제외 상태가 아닙니다(공개 유출 위험).")
    lps = [x for x in (_resolve_principle(s) for s in args["principles"].split(",")) if x]
    now = datetime.now()
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    path = EXP_DIR / f"{_safe_name(args['title'])}_{now:%y%m%d}.md"
    if path.exists():
        return _text(f"같은 이름의 경험이 이미 있습니다: {path.stem}. 다른 제목을 쓰세요.")
    body = (
        f"---\ntype: topic\ntags: [경험, 면접]\nproject: interview-coach\n"
        f"date: {now:%Y-%m-%d}\nLP: [{', '.join(lps)}]\n완성도: 초안\n---\n\n"
        f"# {args['title']}\n\n상위: [[_경험은행 인덱스]]\n\n{args['markdown'].strip()}\n"
    )
    path.write_text(body, encoding="utf-8")
    return _text(f"경험 저장 완료: 경험/{path.name}")


coach_tools = create_sdk_mcp_server(
    name="coach",
    version="1.0.0",
    tools=[
        current_datetime,
        list_principles,
        get_progress,
        list_experiences,
        read_experience,
        save_session,
        save_experience,
    ],
)
ALLOWED = [f"mcp__coach__{n}" for n in (
    "current_datetime", "list_principles", "get_progress", "list_experiences",
    "read_experience", "save_session", "save_experience",
)]


SYSTEM_PROMPT = """당신은 Amazon/AWS 인턴십 행동 면접(Leadership Principles, LP)을 준비시키는 면접 코치입니다.
지원자는 AWS 인턴십 과정에 참여 중인 한국인 학습자입니다.

## 시작할 때
1. get_progress와 list_experiences로 현황을 보고, 연습이 없거나 점수가 낮은 원칙을 우선 고릅니다.
   사용자가 원칙을 지정하면 그것을 따릅니다.
2. 왜 그 원칙을 골랐는지 한 줄로 말하고, 관련 경험이 은행에 있으면 "이 경험을 써 볼 수 있어요"라고 힌트만 줍니다.

## 질문과 꼬리 질문
- 한 번에 질문 하나만 합니다. 실제 면접관처럼 정중하지만 날카롭게.
- 답을 들으면 2~3번 꼬리 질문으로 파고듭니다(Dive Deep):
  "그때 *본인이* 직접 한 일은?", "결과를 수치로 말하면?", "다른 선택지는 무엇이었고 왜 버렸나?",
  "다시 한다면 무엇을 바꾸겠나?". 이미 충분히 답한 부분은 다시 묻지 않습니다.
- 지원자의 많은 작업은 AI(Claude Code)와 함께 만든 것입니다. 면접관이 반드시 물을
  "AI가 한 것과 본인이 판단한 것의 구분"을 자연스럽게 확인합니다.

## 평가 (꼬리 질문이 끝나면)
항목별 1~5점과 한 줄 근거:
- STAR 구조 (상황·과제·행동·결과가 분명한가)
- 본인 행동 ("we"가 아니라 "I"로, 구체적 행동인가)
- 결과의 구체성 (수치·전후 비교)
- 원칙 적합도 (이 이야기가 해당 LP를 잘 보여 주는가)
- 전달력 (2~3분 분량, 핵심부터)
그다음 종합 점수(1~5), 가장 중요한 개선점 1~2개, 그리고 **사용자가 말한 사실만으로** 다듬은 답변 뼈대를 줍니다.
사실을 지어내지 않습니다. 빠진 정보는 "[수치 필요]"처럼 표시합니다.
마지막에 save_session으로 저장하고, 다음 질문으로 갈지 묻습니다.

## 경험 은행
- 사용자가 은행에 없는 새 경험을 말하면, 끝난 뒤 "경험 은행에 초안으로 저장할까요?"라고 묻고 동의하면 save_experience.
- 기존 경험 파일은 수정하지 않습니다.

## 언어
- 사용자가 고른 언어 모드를 따릅니다. ko=한국어로 질문·답변, en=영어 질문·영어 답변(피드백은 한국어),
  mix=한국어로 이야기를 다듬은 뒤 같은 질문을 영어로 다시 연습.
- 영어 답변이면 어색한 표현을 2~3개만 골라 더 자연스러운 표현을 제안합니다.

## 주의
- 사용자의 실명·연락처·여권 등 민감정보는 기록에 쓰지 않습니다.
- 답변을 대신 지어 주지 않습니다. 사용자가 자기 경험으로 말하도록 돕습니다.
"""


async def deny_others(
    tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name in ALLOWED:
        return PermissionResultAllow()
    return PermissionResultDeny(message="이 코치는 면접 코치 도구만 사용할 수 있습니다.")


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(DATA_DIR),
        # 기본 claude-opus-5-5. 빠르고 저렴하게: AGENT_MODEL=claude-sonnet-5-5
        model=os.environ.get("AGENT_MODEL") or "claude-opus-5-5",
        allowed_tools=ALLOWED,
        disallowed_tools=["Bash", "Write", "Edit", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "Task"],
        mcp_servers={"coach": coach_tools},
        can_use_tool=deny_others,
        max_turns=60,
    )


async def print_response(client: ClaudeSDKClient) -> None:
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"\n코치: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"  · {block.name.removeprefix('mcp__coach__')}")
        elif isinstance(message, ResultMessage):
            if message.is_error:
                print(f"\n(오류로 끝남: {message.subtype})")
            if message.total_cost_usd:
                print(f"  (이번 응답 비용 약 ${message.total_cost_usd:.4f})")


BANNER = """🎤 AWS 리더십 원칙 면접 코치
- 약한 원칙부터 질문하고, 꼬리 질문으로 파고든 뒤 평가합니다.
- 연습 기록은 private 폴더에만 저장됩니다(git 제외).
종료: exit
"""


async def main() -> None:
    global PRIVATE_OK
    print(BANNER)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE_OK = data_dir_is_private()
    print(f"데이터 폴더: {DATA_DIR}")
    if not PRIVATE_OK:
        print("⚠️  이 폴더는 git 제외 상태가 아닙니다. 연습 기록을 저장하지 않습니다.")

    lang = (await asyncio.to_thread(input, "\n언어 모드 [ko / en / mix] (엔터=ko): ")).strip().lower() or "ko"
    if lang not in ("ko", "en", "mix"):
        lang = "ko"
    focus = (await asyncio.to_thread(input, "연습할 원칙 (엔터=코치가 추천): ")).strip()

    async with ClaudeSDKClient(options=build_options()) as client:
        start = f"면접 연습을 시작해 주세요. 언어 모드: {lang}."
        if focus:
            start += f" 연습할 원칙: {focus}."
        await client.query(start)
        await print_response(client)
        while True:
            user_input = (await asyncio.to_thread(input, "\n나: ")).strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "종료"):
                break
            await client.query(user_input)
            await print_response(client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n종료합니다.")
