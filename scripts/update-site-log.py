#!/usr/bin/env python3
"""소개 페이지(docs/index.html) 맨 위 'git log' 상자를 실제 커밋 기록으로 다시 만든다.

하루 커밋이 많으면 축약한다:
  - 서버 주소 갱신·자동 저장 같은 잡음 커밋은 빼고 센다
  - 하루에 MAX_PER_DAY개까지만 보여 주고, 나머지는 '… 외 N개'로 접는다
    고르는 순서: docs/gitlog-highlights.txt에 적힌 커밋(문구도 그걸로) →
    DY-00x·첫 버전·N단계·vX.Y 같은 이정표 커밋 → 나머지 시간 순
  - 최근 SHOW_DAYS일만 펼치고, 그보다 오래된 날은 한 줄로 묶는다

bump-site-version.sh가 자동으로 부른다. 직접 실행:  python3 scripts/update-site-log.py
"""
import html
import re
import subprocess
from collections import OrderedDict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "index.html"
HIGHLIGHTS = ROOT / "docs" / "gitlog-highlights.txt"
START, END = "<!-- gitlog:start -->", "<!-- gitlog:end -->"

MAX_PER_DAY = 4   # 하루에 보여 줄 커밋 수
SHOW_DAYS = 3     # 펼쳐 보여 줄 최근 날짜 수
MAX_LEN = 60      # 메시지 길이(넘으면 …, 좁은 화면은 CSS가 더 자름)

NOISE = re.compile(r"서버 주소 갱신|^auto:|자동 저장|^Merge ")
MILESTONE = re.compile(r"DY-00\d|첫 버전|\d단계|v\d+\.\d+")


def highlights():
    hl = {}
    if HIGHLIGHTS.exists():
        for line in HIGHLIGHTS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                h, _, label = line.partition(" ")
                hl[h[:7]] = label.strip()
    return hl


def commits():
    out = subprocess.run(
        ["git", "log", "--reverse", "--date=format:%Y-%m-%d %H:%M", "--format=%h\t%ad\t%s"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        h, when, subj = line.split("\t", 2)
        d, t = when.split(" ")
        yield h, d, t, subj


def short(subj):
    s = re.split(r" \(|: https?://", subj)[0].strip()
    return s if len(s) <= MAX_LEN else s[: MAX_LEN - 1].rstrip() + "…"


def pick(items, hl):
    """강조 목록 → 이정표 순으로 MAX_PER_DAY개 고르고, 시간 순서는 유지."""
    if len(items) <= MAX_PER_DAY:
        return items
    rank = lambda i: (items[i][0][:7] not in hl, not MILESTONE.search(items[i][3]), i)
    ranked = sorted(range(len(items)), key=rank)
    keep = sorted(ranked[:MAX_PER_DAY])
    return [items[i] for i in keep]


def build():
    hl = highlights()
    days = OrderedDict()
    total = 0
    for c in commits():
        total += 1
        days.setdefault(c[1], []).append(c)
    first = date.fromisoformat(next(iter(days)))
    e = html.escape
    lines = []
    keys = list(days)
    old, recent = keys[:-SHOW_DAYS], keys[-SHOW_DAYS:]
    if old:
        n = sum(len(days[k]) for k in old)
        lines.append(f'<li class="day"># {old[0][5:]} ~ {old[-1][5:]} · {len(old)}일 · {n} commits (접음)</li>')
    for d in recent:
        all_items = days[d]
        real = [c for c in all_items if not NOISE.search(c[3])]
        shown = pick(real, hl)
        nth = (date.fromisoformat(d) - first).days + 1
        lines.append(f'<li class="day"># {nth}일차 · {d[5:]} · {len(all_items)} commits</li>')
        for h, _, t, s in shown:
            lines.append(f'<li><span class="h">{e(h)}</span><span class="t">{t}</span><span class="m">{e(hl.get(h[:7]) or short(s))}</span></li>')
        rest = len(all_items) - len(shown)
        if rest > 0:
            lines.append(f'<li class="more">… 외 {rest}개 (잡음·작은 수정 포함)</li>')
    body = "\n".join("          " + l for l in lines)
    tail = f'{total} commits · {len(days)} days'
    return (
        f'{START}\n        <ol>\n{body}\n        </ol>\n'
        f'        <div class="tail">{tail}<span class="cursor" aria-hidden="true"></span></div>\n        {END}'
    ), tail


def main():
    text = PAGE.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(f"{PAGE.name}에 {START} … {END} 표시가 없습니다.")
    block, tail = build()
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        PAGE.write_text(new, encoding="utf-8")
    print(f"git log 상자: {tail}")


if __name__ == "__main__":
    main()
