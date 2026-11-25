#!/usr/bin/env python3
"""GitHub 프로필(DODO-YONG/DODO-YONG) README를 영문 이력서 원본 + 최근 작업 일지(영어)로 만들어 올린다.

  사용: python3 scripts/profile-readme.py            # 만들어서 바뀌었으면 올림
        python3 scripts/profile-readme.py --dry-run  # 올리지 않고 결과만 출력

원본: scripts/profile/README.template.md (이력서 부분은 여기서 고친다)
최근 작업: docs/journal/data.json 의 영어(en) — 이번 주 요약 + 최근 5일
올리기: gh api (저장소를 내려받지 않음). 매일 밤 journal-site.py auto --push 뒤에 자동 실행.
"""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
TEMPLATE = VAULT / "scripts" / "profile" / "README.template.md"
DATA = VAULT / "docs" / "journal" / "data.json"
REPO = "DODO-YONG/DODO-YONG"
JOURNAL = "https://dodo-yong.github.io/Obsidian/journal/"
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def nice(d):
    return f"{MON[int(d[5:7]) - 1]} {int(d[8:10])}"


def en(x):
    return {**x, **(x.get("en") or {})}


def recent():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    out = []
    weeks = data.get("weeks") or []
    if weeks:
        w = en(weeks[0])
        out.append(f"**Week of {nice(w['start'])} – {nice(w['end'])}: {w.get('title', '')}** "
                   f"· [weekly review]({JOURNAL}?lang=en#w-{w['start']})")
        out += [f"> {s}  " for s in (w.get("summary") or [])]
        out.append("")
    out.append("| Date | Highlights | Commits |")
    out.append("|---|---|---|")
    for d in (data.get("days") or [])[:5]:
        d = en(d)
        names = ", ".join(p["name"] for p in (d.get("projects") or [])[:3])
        cell = f"{d.get('headline', '')}<br><sub>{names}</sub>".replace("|", "/")
        out.append(f"| [{nice(d['date'])}]({JOURNAL}?lang=en#d-{d['date']}) | {cell} | {d.get('commits', 0)} |")
    out.append("")
    out.append(f"<sub>Updated automatically every night from my commit history · "
               f"[full journal →]({JOURNAL}?lang=en)</sub>")
    return "\n".join(out)


def build():
    t = TEMPLATE.read_text(encoding="utf-8")
    t = re.sub(r"\A<!--.*?-->\n", "", t, flags=re.S)  # 작업 메모(한국어)는 올리지 않음
    return re.sub(r"(<!-- journal:start -->).*?(<!-- journal:end -->)",
                  lambda m: f"{m.group(1)}\n{recent()}\n{m.group(2)}", t, flags=re.S)


def main():
    readme = build()
    if "--dry-run" in sys.argv:
        print(readme)
        return
    cur = json.loads(subprocess.run(["gh", "api", f"repos/{REPO}/contents/README.md"],
                                    capture_output=True, text=True, check=True).stdout)
    if base64.b64decode(cur["content"]).decode("utf-8") == readme:
        print("프로필: 바뀐 것 없음")
        return
    body = json.dumps({"message": "Update profile README (resume + recent work)",
                       "content": base64.b64encode(readme.encode("utf-8")).decode(), "sha": cur["sha"]})
    subprocess.run(["gh", "api", "-X", "PUT", f"repos/{REPO}/contents/README.md", "--input", "-"],
                   input=body, text=True, capture_output=True, check=True)
    print("프로필 README 올림: https://github.com/DODO-YONG")


if __name__ == "__main__":
    main()
