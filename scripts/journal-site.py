#!/usr/bin/env python3
"""공개 작업 일지 사이트(docs/journal/)의 데이터를 만든다.

  사용: python3 scripts/journal-site.py backfill        # 첫 커밋 날부터 빠진 날·주 전부
        python3 scripts/journal-site.py day YYYY-MM-DD    # 그날 다시 만들기
        python3 scripts/journal-site.py week YYYY-MM-DD   # 그 날짜가 속한 주(월~일) 다시 만들기
        python3 scripts/journal-site.py auto [--push]     # 매일 밤: 어제(바뀌었으면)·오늘·이번 주 갱신

공개 사이트라서 **공개 저장소(이 볼트) 커밋과 log.md만** 쓴다. 비공개 저장소(~/dating, ~/Tracer-Route)·private/는 읽지 않는다.
요약은 제미나이(agy, 추가 요금 없음). 결과: docs/journal/data.json
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
DATA = VAULT / "docs" / "journal" / "data.json"
SKIP = re.compile(r"^(vault backup|private 백업|Merge |일지:)", re.I)
WD = "월화수목금토일"
PROJECT_HINT = ("프로젝트 이름은 되도록 이 중에서 고른다: TRACER(CCNA 문제·해설 사이트), Tracer Route(안드로이드 앱), "
                "소개팅 앱 say when, Heartline(가상 연인 웹앱), SHADOW(영어 섀도잉 코치), MIRROR(면접 연습), "
                "SENTINEL(보안 점검), SWEEPER(노트북 정리), 작업실·위키(규칙·자동 장치·사이트). 이름 뒤 괄호 설명은 쓰지 않는다.")


def commits(start, end):
    out = subprocess.run(
        ["git", "-C", str(VAULT), "log", "--no-merges", f"--since={start} 00:00", f"--until={end} 23:59:59",
         "--date=format:%m-%d %H:%M", "--format=%ad\t%s"], capture_output=True, text=True).stdout
    rows = [l.split("\t", 1) for l in out.splitlines() if "\t" in l]
    seen, res = set(), []
    for when, subj in reversed(rows):
        if SKIP.match(subj) or subj in seen:
            continue
        seen.add(subj)
        res.append(f"{when} {subj}")
    return res


def log_entries(start, end):
    text = (VAULT / "log.md").read_text(encoding="utf-8")
    return [f"{m.group(1)[5:]} {m.group(2)}"
            for m in re.finditer(r"^## \[(\d{4}-\d{2}-\d{2})\] \S+ \| (.+)$", text, re.M)
            if start <= m.group(1) <= end]


def ask_json(prompt):
    """agy에 JSON만 달라고 하고 꺼낸다. 실패하면 None."""
    for _ in range(2):
        try:
            r = subprocess.run([str(VAULT / "scripts" / "gemini.sh"), "-m", "gemini-3.8-flash-medium", prompt],
                               capture_output=True, text=True, timeout=600, cwd=VAULT)
            t = r.stdout
            i, j = t.find("{"), t.rfind("}")
            if i >= 0 and j > i:
                return json.loads(t[i:j + 1])
        except Exception as e:  # noqa: BLE001
            print("요약 실패:", e, file=sys.stderr)
    return None


RULES = ("이 글은 누구나 보는 공개 사이트에 올라간다. 처음 보는 사람도 이해하게 개발 용어는 쉬운 말로 풀어라. "
         "기록에 없는 일은 지어내지 마라. 비밀값·개인 연락처·실명·비공개 저장소 이름은 쓰지 마라. "
         "파일을 만들거나 고치거나 명령을 실행하지 말고, JSON 하나만 출력하라(코드블록 표시 없이). " + PROJECT_HINT)


def build_day(day):
    raw = commits(day, day)
    logs = log_entries(day, day)
    if not raw and not logs:
        return None
    src = "\n".join(f"- {c}" for c in raw) + ("\n\n위키 로그:\n" + "\n".join(f"- {l}" for l in logs) if logs else "")
    prompt = (f"아래는 {day} 하루의 작업 기록(커밋 메시지)이다. 하루 일지를 만들어라. {RULES}\n"
              'JSON 형식: {"headline": "오늘을 한 문장으로(40자 안팎)", '
              '"projects": [{"name": "프로젝트 이름", "emoji": "이모지 하나", "items": ["한 일, 쉬운 말 한 문장", ...]}], '
              '"learned": "오늘 배운 것이나 인상적인 결정 한 문장(없으면 빈 문자열)"}. '
              "projects는 많이 한 순서로, 프로젝트마다 items 2~5개.\n\n" + src)
    j = ask_json(prompt) or {"headline": f"커밋 {len(raw)}건", "projects": [{"name": "작업 기록", "emoji": "📝", "items": [c[12:] for c in raw[:8]]}], "learned": ""}
    d = dt.date.fromisoformat(day)
    j.update(date=day, weekday=WD[d.weekday()], commits=len(raw))
    return j


def build_week(monday):
    sunday = (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat()
    raw = commits(monday, sunday)
    if not raw:
        return None
    prompt = (f"아래는 {monday} ~ {sunday} 한 주의 작업 기록(커밋 메시지)이다. 주간 회고를 만들어라. {RULES}\n"
              'JSON 형식: {"title": "이번 주를 대표하는 짧은 제목(20자 안팎)", "summary": ["이번 주 요약 3문장"], '
              '"projects": [{"name": "프로젝트 이름", "emoji": "이모지 하나", "outcome": "무엇이 가능해졌나 한 문장", "items": ["주요 성과", ...]}], '
              '"decisions": ["이번 주에 정한 것", ...], "next": ["다음에 할 것", ...]}. '
              "projects마다 items 2~5개, decisions 2~5개, next 최대 3개.\n\n" + "\n".join(f"- {c}" for c in raw))
    j = ask_json(prompt) or {"title": f"커밋 {len(raw)}건", "summary": [], "projects": [], "decisions": [], "next": []}
    j.update(start=monday, end=sunday, commits=len(raw))
    return j


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"days": [], "weeks": []}


def save(data):
    data["days"].sort(key=lambda x: x["date"], reverse=True)
    data["weeks"].sort(key=lambda x: x["start"], reverse=True)
    data["updated"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def put_day(data, day):
    data["days"] = [x for x in data["days"] if x["date"] != day]
    j = build_day(day)
    if j:
        data["days"].append(j)
        print("일:", day, j.get("headline"))
    save(data)


def put_week(data, monday):
    data["weeks"] = [x for x in data["weeks"] if x["start"] != monday]
    j = build_week(monday)
    if j:
        data["weeks"].append(j)
        print("주:", monday, j.get("title"))
    save(data)


def monday_of(d):
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "auto"
    data = load()
    today = dt.date.today()
    if cmd == "backfill":
        first = subprocess.run(["git", "-C", str(VAULT), "log", "--reverse", "--format=%ad", "--date=short"],
                               capture_output=True, text=True).stdout.split()[0]
        d = dt.date.fromisoformat(first)
        have_d = {x["date"] for x in data["days"]}
        have_w = {x["start"] for x in data["weeks"]}
        while d <= today:
            if d.isoformat() not in have_d:
                put_day(data, d.isoformat())
            m = monday_of(d)
            if (d.weekday() == 6 or d == today) and m not in have_w:
                put_week(data, m)
                have_w.add(m)
            d += dt.timedelta(days=1)
    elif cmd == "day":
        put_day(data, a[1])
    elif cmd == "week":
        put_week(data, monday_of(dt.date.fromisoformat(a[1])))
    elif cmd == "auto":
        y = (today - dt.timedelta(days=1)).isoformat()
        old = next((x for x in data["days"] if x["date"] == y), None)
        if len(commits(y, y)) != (old or {}).get("commits", 0):  # 어제 밤 10시 뒤 커밋이 있었으면 다시
            put_day(data, y)
        put_day(data, today.isoformat())
        put_week(data, monday_of(today))
        if "--push" in a:
            push()
    else:
        sys.exit(__doc__)


def push():
    """일지 데이터만 커밋·푸시(다른 작업 중인 파일은 건드리지 않음)."""
    rel = str(DATA.relative_to(VAULT))
    g = ["git", "-C", str(VAULT)]
    subprocess.run(g + ["add", rel])
    if subprocess.run(g + ["diff", "--cached", "--quiet", "--", rel]).returncode == 0:
        return
    subprocess.run(g + ["commit", "-q", "-m", f"일지: {dt.date.today()} 자동 갱신", "--", rel], check=True)
    subprocess.run(g + ["push", "-q"])


if __name__ == "__main__":
    main()
