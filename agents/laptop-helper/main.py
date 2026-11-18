"""DY-006 SWEEPER — 내 랩탑(홈 폴더) 정리 도우미 (Claude Agent SDK).

할 수 있는 일 (첫 버전)
  1) 다운로드·데스크탑 정리: 종류별 현황, 오래된 파일, 휴지통 후보
  2) 문서 모으기: 흩어진 문서·표를 찾아 Obsidian 위키 raw/projects/<프로젝트>/ 로 복사
  3) 폴더 정리: 폴더 안 파일을 종류별 하위 폴더(문서·이미지·압축…)로

실행
  ./run.sh                대화 모드 (Claude가 설명·제안, 구독 사용량 듦)
  ./run.sh scan           다운로드·데스크탑 보고서만 (AI 없음, 사용량 0)
  ./run.sh docs [키워드]   문서 찾기만 (AI 없음)
  ./run.sh plan <폴더>     폴더 정리 계획만 보기 (AI 없음, 아무것도 안 옮김)

안전: 홈 폴더 안만, 보호 구역(키·앱 데이터·private/)은 안 봄, 옮기기·휴지통·복사는 터미널에서 y를 쳐야 실행,
지우기는 휴지통으로만, Obsidian 볼트 안은 옮기거나 지우지 않음(raw 로 복사만).
"""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import tidy
from safety import HOME

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def refuse_paid_billing() -> None:
    """API 키가 있으면 사용량만큼 돈이 청구된다. 구독 로그인으로만 실행하도록 막는다."""
    found = [v for v in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN") if os.environ.get(v)]
    if found:
        print(f"⛔ {', '.join(found)} 가 설정돼 있어 실행하지 않습니다(추가 요금 방지).\n"
              "   .env 나 환경 변수에서 지우고, Claude 구독 로그인으로 실행하세요.")
        sys.exit(1)


async def confirm(lines: list[str], question: str) -> bool:
    """사람이 직접 y를 쳐야만 진행. AI가 대신 승인할 수 없다."""
    print("\n" + "\n".join(lines))
    ans = (await asyncio.to_thread(input, f"👉 {question} [y/N] ")).strip().lower()
    return ans in ("y", "yes", "예", "네", "ㅇ")


def _t(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _tl(p: str) -> str:
    return p.replace(str(HOME), "~", 1)


# ---- AI 없이 쓰는 명령 ----------------------------------------------------------

def cli(args: list[str]) -> None:
    cmd = args[0]
    if cmd == "scan":
        text = "".join(tidy.format_report(tidy.report_folder(f)) + "\n" for f in ("~/Downloads", "~/Desktop"))
        print(text)
        if tidy.data_dir_is_private():
            d = tidy.DATA_DIR / "보고서"
            d.mkdir(parents=True, exist_ok=True)
            path = d / f"{datetime.now():%Y_%m_%d}_다운로드·데스크탑.md"
            path.write_text(f"# 다운로드·데스크탑 보고서 ({datetime.now():%Y-%m-%d %H:%M})\n\n" + text, encoding="utf-8")
            print(f"(보고서 저장: {_tl(str(path))} — 비공개 폴더)")
    elif cmd == "docs":
        print(tidy.format_docs(tidy.find_documents(" ".join(args[1:]))))
    elif cmd == "plan":
        if len(args) < 2:
            sys.exit("폴더를 적어 주세요. 예) ./run.sh plan ~/Downloads")
        plan = tidy.plan_organize(args[1])
        if plan.get("error"):
            sys.exit("⚠️ " + plan["error"])
        print(f"{_tl(plan['folder'])} 정리 계획 (아직 아무것도 옮기지 않았어요)")
        print("  " + " · ".join(f"{c} {n}개" for c, n in plan["by_cat"].items()) or "  옮길 파일 없음")
        for src, dst, _ in plan["moves"][:30]:
            print(f"  {os.path.basename(src)}  →  {_tl(os.path.dirname(dst))}/")
        if len(plan["moves"]) > 30:
            print(f"  … 외 {len(plan['moves']) - 30}개")
        print("\n실제로 옮기려면 대화 모드(./run.sh)에서 '이 폴더 정리해 줘'라고 하세요.")
    else:
        sys.exit(__doc__)


# ---- 대화 모드 (Claude Agent SDK) ----------------------------------------------

TOOLS: dict = {}


def build_agent():
    from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool
    from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

    warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")

    @tool("current_datetime", "현재 날짜와 시간.", {})
    async def current_datetime(args):
        return _t(datetime.now().strftime("%Y-%m-%d %H:%M (%A)"))

    @tool("report_downloads_desktop", "다운로드·데스크탑 폴더의 종류별 현황, 휴지통 후보, 오래된 파일, 큰 파일을 보여 준다.", {})
    async def report_downloads_desktop(args):
        return _t("".join(tidy.format_report(tidy.report_folder(f)) + "\n" for f in ("~/Downloads", "~/Desktop")))

    @tool("report_folder", "홈 폴더 안 아무 폴더의 종류별 현황(바로 아래 항목만). path 예: ~/Documents/학교", {"path": str})
    async def report_folder(args):
        return _t(tidy.format_report(tidy.report_folder(args["path"])))

    @tool("find_documents",
          "데스크탑·문서·다운로드에서 문서·표 파일(pdf, docx, hwp, pptx, xlsx, csv, md…)을 찾는다. "
          "keyword(파일·폴더 이름에 포함, 빈 문자열이면 전체), days(최근 며칠 안에 수정된 것만, 0이면 제한 없음).",
          {"keyword": str, "days": int})
    async def find_documents(args):
        days = int(args.get("days") or 0) or None
        res = tidy.find_documents(args.get("keyword", ""), days=days)
        text = tidy.format_docs(res, limit=60)
        # 복사할 때 정확한 경로가 필요하니 전체 경로 목록도 붙인다
        text += "\n(전체 경로)\n" + "\n".join(_tl(r["path"]) for r in res["docs"][:60])
        return _t(text)

    @tool("list_wiki_projects", "문서를 모을 수 있는 Obsidian 위키 프로젝트(raw/projects/ 아래 폴더) 목록.", {})
    async def list_wiki_projects(args):
        return _t(", ".join(tidy.raw_projects()) or "(없음)")

    @tool("copy_to_wiki", "문서 파일들을 위키 raw/projects/<project>/ 로 복사한다(원본은 그대로). "
          "실행 전에 사용자가 터미널에서 직접 승인한다. paths: 경로 목록(~ 사용 가능).",
          {"paths": list, "project": str})
    async def copy_to_wiki(args):
        plan = tidy.plan_copy_to_raw([str(p) for p in args["paths"]], args["project"])
        if plan.get("error"):
            return _t("⚠️ " + plan["error"])
        if not plan["ok"]:
            return _t("복사할 파일이 없어요. 건너뜀: " + "; ".join(f"{s} ({w})" for s, w in plan["skip"]))
        lines = [f"📄 위키로 복사 ({len(plan['ok'])}개 → {_tl(plan['dest'])})"] + \
                [f"  {os.path.basename(s)}" for s, _ in plan["ok"][:30]]
        if not await confirm(lines, "복사할까요? 원본은 그대로 둡니다."):
            return _t("사용자가 복사를 취소했어요.")
        done = tidy.copy_to_raw(plan)
        tidy.log("copy_to_wiki", done)
        return _t(f"{len(done)}개 복사 완료 → {_tl(plan['dest'])}. 위키에 반영하려면 Claude Code에서 'ingest 해줘'라고 하면 돼요."
                  + (f" 건너뜀: {plan['skip']}" if plan["skip"] else ""))

    @tool("organize_folder", "폴더 바로 아래 파일들을 종류별 하위 폴더(문서·표·이미지·영상·음악·압축·설치파일·코드·기타)로 옮긴다. "
          "하위 폴더는 그대로 둔다. only_older_days>0이면 그보다 오래된 파일만. 실행 전에 사용자가 터미널에서 직접 승인한다.",
          {"path": str, "only_older_days": int})
    async def organize_folder(args):
        plan = tidy.plan_organize(args["path"], int(args.get("only_older_days") or 0))
        if plan.get("error"):
            return _t("⚠️ " + plan["error"])
        if not plan["moves"]:
            return _t("옮길 파일이 없어요.")
        lines = [f"🗂️ {_tl(plan['folder'])} 정리: " + " · ".join(f"{c} {n}개" for c, n in plan["by_cat"].items())]
        lines += [f"  {os.path.basename(s)} → {c}/" for s, _, c in plan["moves"][:20]]
        if len(plan["moves"]) > 20:
            lines.append(f"  … 외 {len(plan['moves']) - 20}개")
        if not await confirm(lines, f"{len(plan['moves'])}개를 옮길까요?"):
            return _t("사용자가 정리를 취소했어요.")
        done = tidy.organize(plan)
        tidy.log("organize", done)
        return _t(f"{len(done)}개를 종류별 폴더로 옮겼어요: " + ", ".join(f"{c} {n}개" for c, n in plan["by_cat"].items()))

    @tool("move_to_trash", "파일·폴더를 휴지통으로 보낸다(Finder 휴지통에서 되돌리기 가능, 영구 삭제 아님). "
          "실행 전에 사용자가 터미널에서 직접 승인한다. paths: 경로 목록.", {"paths": list})
    async def move_to_trash(args):
        plan = tidy.plan_trash([str(p) for p in args["paths"]])
        if not plan["ok"]:
            return _t("보낼 수 있는 항목이 없어요: " + "; ".join(f"{s} ({w})" for s, w in plan["skip"]))
        lines = [f"🗑️ 휴지통으로 ({len(plan['ok'])}개, 휴지통에서 되돌릴 수 있어요)"] + \
                [f"  {_tl(p)} · {tidy.human(tidy._size(Path(p)))}" for p in plan["ok"][:30]]
        if not await confirm(lines, "휴지통으로 보낼까요?"):
            return _t("사용자가 취소했어요.")
        done, err = tidy.trash(plan)
        tidy.log("trash", done)
        msg = f"{len(done)}개를 휴지통으로 보냈어요."
        if err:
            msg += " " + err
        if plan["skip"]:
            msg += " 건너뜀: " + "; ".join(f"{s} ({w})" for s, w in plan["skip"])
        return _t(msg)

    tools = [current_datetime, report_downloads_desktop, report_folder, find_documents, list_wiki_projects,
             copy_to_wiki, organize_folder, move_to_trash]
    global TOOLS
    TOOLS = {t.name: t for t in tools}      # 시험용: 도구를 AI 없이 직접 불러 볼 수 있게
    server = create_sdk_mcp_server(name="sweeper", version="1.0.0", tools=tools)
    allowed = [f"mcp__sweeper__{t.name}" for t in tools]

    async def deny_others(tool_name, tool_input, context):
        if tool_name in allowed:
            return PermissionResultAllow()
        return PermissionResultDeny(message="SWEEPER는 자기 정리 도구만 쓸 수 있어요.")

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(HOME),
        model=os.environ.get("AGENT_MODEL") or "claude-sonnet-5-5",
        allowed_tools=allowed,
        disallowed_tools=["Bash", "Write", "Edit", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "Task", "NotebookEdit"],
        mcp_servers={"sweeper": server},
        can_use_tool=deny_others,
        max_turns=40,
    )


SYSTEM_PROMPT = """당신은 DY-006 SWEEPER, 사용자의 맥 랩탑 홈 폴더를 정리해 주는 도우미입니다. 한국어로 짧고 분명하게 말합니다.

## 할 수 있는 일
1. 다운로드·데스크탑 정리 — report_downloads_desktop으로 현황을 보고, 정리 방법을 제안합니다.
2. 문서 모으기 — find_documents로 흩어진 문서를 찾고, 사용자가 고른 것을 copy_to_wiki로 Obsidian 위키 raw/projects/<프로젝트>/에 복사합니다(원본 유지). 프로젝트 이름은 list_wiki_projects로 확인합니다.
3. 폴더 정리 — organize_folder로 파일을 종류별 하위 폴더에 나눕니다. 지울 것은 move_to_trash(휴지통, 되돌리기 가능).

## 일하는 순서
- 먼저 보고(스캔) → 무엇을 왜 할지 3~5줄로 제안 → 사용자가 원하면 실행 도구를 부릅니다.
- 옮기기·복사·휴지통 도구는 실행 전에 터미널에서 사용자에게 직접 y/N을 묻습니다. 당신이 대신 승인할 수 없습니다.
  도구 결과가 "취소"면 다시 시도하지 말고 다른 방법을 물어봅니다.
- 결과는 도구가 돌려준 내용 그대로 보고합니다. 하지 않은 일을 했다고 말하지 않습니다.
- 한 번에 많이 지우자고 하지 않습니다. 휴지통 후보는 설치가 끝난 설치파일, '(1)'·'복사본' 같은 중복 이름처럼 근거가 분명한 것부터.
- 파일 내용은 볼 수 없고 이름·크기·날짜만 봅니다. 내용이 중요해 보이면 사용자에게 확인합니다.

## 지키는 것
- 홈 폴더 밖, 보호 구역(키·인증서, ~/Library 앱 데이터, ~/.config, Obsidian private/), .env 같은 비밀 파일은 보지도 건드리지도 않습니다.
- Obsidian 볼트 안 파일은 옮기거나 지우지 않습니다(raw/로 복사만).
- 영구 삭제는 하지 않습니다.
"""


async def chat() -> None:
    from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock, ToolUseBlock

    print("🧹 DY-006 SWEEPER · 랩탑 정리 도우미\n"
          "- 예) '다운로드랑 데스크탑 정리해 줘', 'CCNA 관련 문서 모아 줘', '~/Documents 폴더 정리해 줘'\n"
          "- 옮기기·지우기는 실행 전에 여기서 y/N을 물어요. 지우기는 휴지통으로만.\n"
          "- 💸 구독 로그인으로 실행(추가 요금 없음). 보고서만 보려면 ./run.sh scan (사용량 0)\n종료: exit\n")
    async with ClaudeSDKClient(options=build_agent()) as client:
        while True:
            q = (await asyncio.to_thread(input, "\n나: ")).strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "종료"):
                break
            await client.query(q)
            async for m in client.receive_response():
                if isinstance(m, AssistantMessage):
                    for b in m.content:
                        if isinstance(b, TextBlock):
                            print(f"\nSWEEPER: {b.text}")
                        elif isinstance(b, ToolUseBlock):
                            print(f"  · {b.name.removeprefix('mcp__sweeper__')}")
                elif isinstance(m, ResultMessage):
                    if m.is_error:
                        print(f"\n(오류로 끝남: {m.subtype})")
                    if m.total_cost_usd:
                        print(f"  (사용량 참고: API 요금 환산 약 ${m.total_cost_usd:.2f} · 구독 로그인이라 실제 청구 없음)")


if __name__ == "__main__":
    refuse_paid_billing()
    try:
        if len(sys.argv) > 1:
            cli(sys.argv[1:])
        else:
            asyncio.run(chat())
    except (KeyboardInterrupt, EOFError):
        print("\n종료합니다.")
