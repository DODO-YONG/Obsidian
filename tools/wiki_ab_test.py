#!/usr/bin/env python3
"""위키 A/B 테스트: 같은 질문을 '위키로'(A)와 '위키 없이'(B) 답하게 해서 토큰·시간을 비교한다.

- A (위키): CLAUDE.md 바로가기 표·wiki/·index.md를 활용해 답한다.
- B (위키 없이): wiki/·index.md·log.md 읽기를 막고, 코드·문서 원본(agents/·docs/·scripts/·raw/)만 보고 답한다.
- 둘 다 읽기 도구(Read·Grep·Glob)만 쓴다. 파일 수정·명령 실행·웹 검색은 막는다. private/는 둘 다 못 읽는다.

실행 (Claude 구독 로그인으로만 돈다. 구독 사용량이 든다):
    python3 tools/wiki_ab_test.py --dry-run        # 무엇을 돌릴지 보기만 (사용량 0)
    python3 tools/wiki_ab_test.py -n 1             # 질문 1개만 시험
    python3 tools/wiki_ab_test.py                  # 전체 (질문 수 × 2회 호출)
    python3 tools/wiki_ab_test.py --model sonnet   # 모델 지정

결과:
    wiki/shared/output/YYYY_MM_DD_위키_AB테스트.csv   (질문·방식별 수치)
    wiki/shared/위키 효과 측정.md 맨 아래에 이번 결과 표 추가
"""
import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
QUESTIONS = VAULT / "tools" / "wiki_ab_questions.txt"
OUT_DIR = VAULT / "wiki" / "shared" / "output"
REPORT = VAULT / "wiki" / "shared" / "위키 효과 측정.md"

COMMON_RULES = (
    "이것은 측정용 실행이다. 질문에 한국어로 3~5줄로만 답하라. "
    "파일을 만들거나 고치지 말고, 위키에 저장하거나 log.md에 기록하지 마라. "
    "답을 못 찾으면 '못 찾음'이라고 답하라."
)
MODES = {
    "A_위키": {
        "prompt": COMMON_RULES + " CLAUDE.md의 바로가기 표와 위키(wiki/·index.md)를 활용해 답을 찾아라.",
        "deny": [],
    },
    "B_위키없이": {
        "prompt": COMMON_RULES + " 이번에는 위키(wiki/ 폴더, index.md, log.md)를 쓰지 않는다고 가정한다. "
        "CLAUDE.md의 'index를 먼저 읽는다' 규칙은 이번 실행에서 무시하고, "
        "agents/·docs/·scripts/·raw/ 등 원본 파일만 찾아 읽어서 답하라.",
        "deny": ["Read(./wiki/**)", "Read(./index.md)", "Read(./log.md)"],
    },
}
ALWAYS_DENY = [
    "Edit", "Write", "NotebookEdit", "Bash", "WebSearch", "WebFetch", "Agent",
    "Read(./private/**)", "Read(./**/.env)", "Read(./**/.env.*)",
]


def refuse_paid_billing():
    """구독 외 비용 금지: API 키가 설정돼 있으면 실행하지 않는다."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY가 설정돼 있어 중단합니다(API 요금이 나갈 수 있음). "
                 "키를 지우고 Claude 구독 로그인으로 실행하세요.")


def find_claude():
    path = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
    if not Path(path).exists():
        sys.exit("claude 명령을 찾지 못했습니다. Claude Code CLI를 설치하거나 PATH에 추가하세요.")
    return path


def load_questions(n):
    qs = [l.strip() for l in QUESTIONS.read_text(encoding="utf-8").splitlines()
          if l.strip() and not l.startswith("#")]
    return qs[:n] if n else qs


def build_cmd(claude, mode, question, model, max_turns):
    cmd = [claude, "-p", question, "--output-format", "json",
           "--no-session-persistence", "--max-turns", str(max_turns),
           "--allowedTools", "Read", "Grep", "Glob",
           "--disallowedTools", *ALWAYS_DENY, *MODES[mode]["deny"],
           "--append-system-prompt", MODES[mode]["prompt"]]
    if model:
        cmd += ["--model", model]
    return cmd


def run_one(cmd, timeout):
    start = dt.datetime.now()
    p = subprocess.run(cmd, cwd=VAULT, capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    wall = (dt.datetime.now() - start).total_seconds()
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"error": (p.stderr or p.stdout)[:300], "wall_s": round(wall, 1)}
    u = d.get("usage") or {}
    fresh = u.get("input_tokens", 0)
    c_new = u.get("cache_creation_input_tokens", 0)
    c_read = u.get("cache_read_input_tokens", 0)
    return {
        "읽은토큰": fresh + c_new + c_read,   # 캐시 여부와 무관한 '실제로 읽은 양'
        "새입력": fresh + c_new,
        "캐시재사용": c_read,
        "출력토큰": u.get("output_tokens", 0),
        "턴수": d.get("num_turns"),
        "시간_s": round((d.get("duration_ms") or wall * 1000) / 1000, 1),
        "API요금환산_usd": d.get("total_cost_usd"),
        "답": (d.get("result") or "").strip(),
        "error": d.get("subtype") if d.get("is_error") else "",
    }


def pct(a, b):
    """A가 B보다 몇 % 적은지(또는 많은지)."""
    if not b:
        return "-"
    d = (1 - a / b) * 100
    return f"{d:.0f}% 적음" if d >= 0 else f"{-d:.0f}% 많음"


def write_report(rows, model, csv_path):
    today = dt.date.today().isoformat()
    ok = [r for r in rows if not r.get("error")]
    def total(mode, key):
        return sum(r[key] or 0 for r in ok if r["방식"] == mode)
    lines = [f"\n## {today} 결과 (질문 {len({r['질문'] for r in rows})}개, 모델: {model or '기본'})\n",
             f"원자료: `{csv_path.relative_to(VAULT)}`\n",
             "| 질문 | A 읽은토큰 | B 읽은토큰 | A 시간 | B 시간 | A 턴 | B 턴 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for q in dict.fromkeys(r["질문"] for r in rows):
        a = next((r for r in ok if r["질문"] == q and r["방식"] == "A_위키"), None)
        b = next((r for r in ok if r["질문"] == q and r["방식"] == "B_위키없이"), None)
        f = lambda r, k: (f"{r[k]:,}" if isinstance(r[k], int) else str(r[k])) if r else "오류"
        lines.append(f"| {q[:30]}… | {f(a,'읽은토큰')} | {f(b,'읽은토큰')} | {f(a,'시간_s')}s | "
                     f"{f(b,'시간_s')}s | {f(a,'턴수')} | {f(b,'턴수')} |")
    at, bt = total("A_위키", "읽은토큰"), total("B_위키없이", "읽은토큰")
    asec, bsec = total("A_위키", "시간_s"), total("B_위키없이", "시간_s")
    lines += [f"| **합계** | **{at:,}** | **{bt:,}** | **{asec:.0f}s** | **{bsec:.0f}s** | | |", "",
              f"- 위키 사용 시 읽은 토큰: B 대비 **{pct(at, bt)}**, 시간: **{pct(asec, bsec)}**",
              "- ⚠️ 답의 정확도는 CSV의 `답` 열에서 직접 비교할 것(토큰이 적어도 틀리면 의미 없음).",
              "- 'API요금환산'은 API 요금 기준 참고치. 구독이라 실제로 청구되지 않음."]
    if len(ok) < len(rows):
        lines.append(f"- 오류 {len(rows) - len(ok)}건: CSV의 `error` 열 참고.")
    with REPORT.open("a", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=0, help="앞에서부터 질문 N개만")
    ap.add_argument("--model", default="", help="예: sonnet, haiku, opus (생략 시 기본 모델)")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=600, help="호출 1회 제한 시간(초)")
    ap.add_argument("--dry-run", action="store_true", help="호출하지 않고 명령만 출력")
    args = ap.parse_args()

    refuse_paid_billing()
    claude = find_claude()
    qs = load_questions(args.n)
    print(f"질문 {len(qs)}개 × 2방식 = 호출 {len(qs) * 2}회 (구독 사용량이 듭니다)")

    rows = []
    for i, q in enumerate(qs, 1):
        # 순서를 번갈아 바꿔 캐시 효과가 한쪽에만 유리하지 않게 한다
        order = list(MODES) if i % 2 else list(reversed(MODES))
        for mode in order:
            cmd = build_cmd(claude, mode, q, args.model, args.max_turns)
            if args.dry_run:
                print(f"\n[{i}/{len(qs)}] {mode}\n  " + " ".join(
                    repr(c) if " " in c else c for c in cmd[1:]))
                continue
            print(f"[{i}/{len(qs)}] {mode} … ", end="", flush=True)
            try:
                r = run_one(cmd, args.timeout)
            except subprocess.TimeoutExpired:
                r = {"error": "timeout"}
            rows.append({"질문": q, "방식": mode, **r})
            print(r.get("error") or f"{r['읽은토큰']:,} 토큰, {r['시간_s']}s, {r['턴수']}턴")

    if args.dry_run or not rows:
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"{dt.date.today():%Y_%m_%d}_위키_AB테스트.csv"
    if csv_path.exists():
        csv_path = csv_path.with_name(csv_path.stem + f"_{dt.datetime.now():%H%M}.csv")
    keys = ["질문", "방식", "읽은토큰", "새입력", "캐시재사용", "출력토큰", "턴수",
            "시간_s", "API요금환산_usd", "error", "답"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    write_report(rows, args.model, csv_path)
    print(f"\n저장: {csv_path.relative_to(VAULT)}\n보고서: {REPORT.relative_to(VAULT)}")


if __name__ == "__main__":
    main()
