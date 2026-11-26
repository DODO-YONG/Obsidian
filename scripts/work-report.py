#!/usr/bin/env python3
"""하루·한 주 작업 보고서를 만들어 내 Gmail로 보낸다.

  사용: python3 scripts/work-report.py daily [YYYY-MM-DD] [--no-mail]
        python3 scripts/work-report.py weekly [YYYY-MM-DD] [--no-mail]   # 그 날짜가 속한 주(월~일)
        python3 scripts/work-report.py morning [YYYY-MM-DD] [--no-mail]  # 아침 보고: 어제 한 일 + 오늘 할 일
        python3 scripts/work-report.py auto                              # 매일 밤 자동 실행용: 오늘 일일 + 일요일이면 주간

모으는 것: 볼트·소개팅 앱(~/dating)·Tracer Route(~/Tracer-Route) 커밋, log.md 항목, 개발 보드 다음 할 일.
요약: 제미나이(agy, 사용자 AI Pro 로그인, 추가 요금 없음). 실패하면 목록 그대로 보낸다.
저장: private/보고서/ (비공개 저장소 내용이 들어가서 공개 위키에 두지 않음)
메일: Gmail SMTP + 앱 비밀번호. 값은 볼트 .env 에만(REPORT_GMAIL_USER, REPORT_GMAIL_APP_PASSWORD, REPORT_TO)
"""
import datetime as dt
import html
import os
import re
import smtplib
import subprocess
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
HOME = Path.home()
REPOS = {  # 보고서에 보이는 이름 → 저장소 폴더
    "위키·에이전트(볼트)": VAULT,
    "소개팅 앱": HOME / "dating",
    "Tracer Route 앱": HOME / "Tracer-Route",
}
OUT = VAULT / "private" / "보고서"
SKIP = re.compile(r"^(vault backup|private 백업|Merge )", re.I)  # 자동 백업 커밋은 뺀다


def load_env():
    env = {}
    f = VAULT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def commits(repo, start, end):
    if not (repo / ".git").exists():
        return []
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--all", "--no-merges",
         f"--since={start} 00:00", f"--until={end} 23:59:59",
         "--date=format:%m-%d %H:%M", "--format=%ad\t%s"],
        capture_output=True, text=True).stdout
    rows = [l.split("\t", 1) for l in out.splitlines() if "\t" in l]
    seen, res = set(), []
    for when, subj in reversed(rows):  # 오래된 것부터
        if SKIP.match(subj) or subj in seen:
            continue
        seen.add(subj)
        res.append((when, subj))
    return res


def log_entries(start, end):
    text = (VAULT / "log.md").read_text(encoding="utf-8")
    res = []
    for m in re.finditer(r"^## \[(\d{4}-\d{2}-\d{2})\] (\S+) \| (.+)$", text, re.M):
        if start <= m.group(1) <= end:
            res.append(f"{m.group(1)[5:]} {m.group(3)}")
    return res


def board_next(limit=8):
    f = VAULT / "wiki" / "개발 보드.md"
    if not f.exists():
        return []
    items = re.findall(r"^\s*- \[ \] (.+)$", f.read_text(encoding="utf-8"), re.M)
    return items[:limit]


def collect(start, end):
    parts, total = [], 0
    for name, repo in REPOS.items():
        cs = commits(repo, start, end)
        total += len(cs)
        if cs:
            parts.append(f"### {name} ({len(cs)}건)\n" + "\n".join(f"- {w} {s}" for w, s in cs))
    logs = log_entries(start, end)
    if logs:
        parts.append(f"### 위키 log.md ({len(logs)}건)\n" + "\n".join(f"- {l}" for l in logs))
    nxt = board_next()
    if nxt:
        parts.append("### 개발 보드 남은 할 일(위에서부터)\n" + "\n".join(f"- {n}" for n in nxt))
    return "\n\n".join(parts), total


def summarize(kind, start, end, raw):
    """agy에 요약을 맡긴다. 파일은 건드리지 말고 글만 출력하게 한다."""
    period = start if start == end else f"{start} ~ {end}"
    shape = {
        "daily": "1) 한 줄 요약 2) 프로젝트별로 한 일(쉬운 말, 항목 3~6개씩) 3) 내일 할 만한 일 3개",
        "weekly": "1) 이번 주 세 줄 요약 2) 프로젝트별 성과(무엇이 가능해졌나 중심) "
                  "3) 결정한 것 4) 막혔거나 미룬 것 5) 다음 주 우선순위 3개",
        "morning": "1) 어제 한 일 두세 줄 2) 오늘 할 일 3~5개(할 일 보드 위쪽 우선, "
                   "어제 하다 만 일·기다리는 일(검토·승인·테스터 등)이 있으면 확인할 것으로 넣기, 각 항목 한 줄) "
                   "3) 사용자가 직접 해야 하는 일이 있으면 따로 표시",
    }[kind]
    what = {"daily": "하루 작업 보고서", "weekly": "한 주 작업 보고서", "morning": "아침 보고(어제 정리 + 오늘 할 일)"}[kind]
    prompt = (
        f"아래는 {period} 동안의 작업 기록(커밋·위키 로그·할 일 보드)이다. "
        f"이걸로 {what}를 한국어 마크다운으로 써라. "
        f"형식: {shape}. 개발 용어는 쉬운 말로 풀고, 기록에 없는 일은 지어내지 마라. "
        "파일을 만들거나 고치거나 명령을 실행하지 말고, 보고서 본문만 출력하라. 제목(#)은 쓰지 마라.\n\n"
        + raw)
    try:
        r = subprocess.run([str(VAULT / "scripts" / "gemini.sh"), "-m", "gemini-3.8-flash-medium", prompt],
                           capture_output=True, text=True, timeout=600, cwd=VAULT)
        text = r.stdout.strip()
        if r.returncode == 0 and len(text) > 80:
            return text, True
        print("요약 실패, 목록으로 보냄:", r.stderr[-300:], file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print("요약 실패, 목록으로 보냄:", e, file=sys.stderr)
    return None, False


def md_to_html(md):
    """메일용 아주 간단한 변환(제목·목록·굵게). 다크 배경."""
    out, in_ul = [], False
    for line in md.splitlines():
        s = html.escape(line)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        li = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", s)
        if li:
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{li.group(1)}</li>")
            continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        h = re.match(r"(#{1,4})\s+(.*)", s)
        if h:
            n = min(len(h.group(1)) + 1, 4)
            out.append(f"<h{n}>{h.group(2)}</h{n}>")
        elif s.strip():
            out.append(f"<p>{s}</p>")
    if in_ul:
        out.append("</ul>")
    style = ("body{background:#15161a;color:#e6e6e6;font-family:-apple-system,sans-serif;line-height:1.6;"
             "padding:20px;max-width:680px}h1,h2,h3,h4{color:#fff;margin:18px 0 6px}"
             "code{background:#2a2c33;padding:1px 4px;border-radius:4px}li{margin:3px 0}"
             "hr{border:0;border-top:1px solid #333}")
    return f"<html><head><style>{style}</style></head><body style='background:#15161a;color:#e6e6e6'>{''.join(out)}</body></html>"


def send(subject, md, env):
    user, pw = env.get("REPORT_GMAIL_USER"), env.get("REPORT_GMAIL_APP_PASSWORD", "").replace(" ", "")
    to = env.get("REPORT_TO") or user
    if not (user and pw):
        print("⚠️ .env에 REPORT_GMAIL_USER / REPORT_GMAIL_APP_PASSWORD 가 없어 메일은 건너뜀", file=sys.stderr)
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.attach(MIMEText(md, "plain", "utf-8"))
    msg.attach(MIMEText(md_to_html(md), "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    return True


def report(kind, day, mail=True):
    if kind == "weekly":
        start = day - dt.timedelta(days=day.weekday())
        end = start + dt.timedelta(days=6)
    elif kind == "morning":  # 어제 기록으로 오늘 할 일
        start = end = day - dt.timedelta(days=1)
    else:
        start = end = day
    s, e = start.isoformat(), end.isoformat()
    raw, total = collect(s, e)
    if total == 0 and not log_entries(s, e) and kind != "morning":
        body = "기록된 작업이 없습니다. 쉬어 가는 날도 필요해요."
        summary_ok = False
    else:
        summary, summary_ok = summarize(kind, s, e, raw)
        body = summary or raw
    if kind == "morning":
        title = f"☀️ 아침 보고 {day.isoformat()} ({'월화수목금토일'[day.weekday()]}) — 오늘 할 일"
        fname = f"아침/{day.isoformat()}.md"
    elif kind == "daily":
        title = f"📋 일일 작업 보고 {s} ({'월화수목금토일'[start.weekday()]}) — 커밋 {total}건"
        fname = f"일일/{s}.md"
    else:
        title = f"🗓️ 주간 작업 보고 {s} ~ {e} — 커밋 {total}건"
        fname = f"주간/{s}_주간.md"
    md = f"# {title}\n\n{body}\n"
    if summary_ok:
        md += f"\n---\n\n<details><summary>원본 기록</summary>\n\n{raw}\n\n</details>\n"
        mail_md = f"{body}\n\n---\n## 원본 기록\n\n{raw}\n"
    else:
        mail_md = body + "\n"
    link = "https://dodo-yong.github.io/Obsidian/journal/" + (f"#w-{s}" if kind == "weekly" else f"#d-{s}")
    mail_md = f"📓 공개 작업 일지: {link}\n\n" + mail_md
    path = OUT / fname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    print("저장:", path)
    if mail and send(title, mail_md, load_env()):
        print("메일 보냄:", title)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mail = "--no-mail" not in sys.argv
    kind = args[0] if args else "auto"
    day = dt.date.fromisoformat(args[1]) if len(args) > 1 else dt.date.today()
    if kind == "auto":
        report("daily", day, mail)
        if day.weekday() == 6:  # 일요일 밤엔 주간도
            report("weekly", day, mail)
        # 공개 작업 일지 사이트(docs/journal) 갱신·푸시 — 공개 저장소 기록만 씀
        subprocess.run([sys.executable, str(VAULT / "scripts" / "journal-site.py"), "auto", "--push"])
    elif kind in ("daily", "weekly", "morning"):
        report(kind, day, mail)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
