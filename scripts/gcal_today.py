#!/usr/bin/env python3
"""구글 캘린더 '비공개 iCal 주소'(.ics)로 하루 일정을 읽는다. 표준 라이브러리만 씀.

  사용: python3 scripts/gcal_today.py [YYYY-MM-DD]
주소: 볼트 .env 의 GCAL_ICS_URL (여러 캘린더면 쉼표로). 주소 자체가 비밀번호라 코드·md에 쓰지 않는다.
반복 일정(RRULE: DAILY·WEEKLY·MONTHLY·YEARLY, INTERVAL·BYDAY·BYMONTHDAY·UNTIL·COUNT), 제외 날짜(EXDATE),
옮긴 한 번짜리(RECURRENCE-ID), 취소(STATUS:CANCELLED)를 처리한다.
"""
import datetime as dt
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

LOCAL = dt.datetime.now().astimezone().tzinfo
DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def unescape(v):
    return v.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def parse_dt(params, value):
    """(날짜 또는 시각, 종일 여부). 시각은 현지 시간으로 바꾼다."""
    value = value.strip()
    if "VALUE=DATE" in params or re.fullmatch(r"\d{8}", value):
        return dt.datetime.strptime(value[:8], "%Y%m%d").date(), True
    t = dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        t = t.replace(tzinfo=dt.timezone.utc)
    else:
        m = re.search(r"TZID=([^;:]+)", params)
        try:
            t = t.replace(tzinfo=ZoneInfo(m.group(1)) if m else LOCAL)
        except Exception:  # noqa: BLE001 모르는 시간대면 현지로
            t = t.replace(tzinfo=LOCAL)
    return t.astimezone(LOCAL), False


def events(text):
    res, cur = [], None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {"exdates": set()}
        elif line == "END:VEVENT" and cur is not None:
            if "start" in cur:
                res.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, _, params = head.partition(";")
            if name == "DTSTART":
                cur["start"], cur["allday"] = parse_dt(params, value)
            elif name == "DTEND":
                cur["end"], _ = parse_dt(params, value)
            elif name == "SUMMARY":
                cur["summary"] = unescape(value)
            elif name == "LOCATION":
                cur["location"] = unescape(value)
            elif name == "RRULE":
                cur["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
            elif name == "EXDATE":
                for v in value.split(","):
                    d, _ = parse_dt(params, v)
                    cur["exdates"].add(d if isinstance(d, dt.date) and not isinstance(d, dt.datetime) else d.date())
            elif name == "RECURRENCE-ID":
                d, _ = parse_dt(params, value)
                cur["recurrence_id"] = d if not isinstance(d, dt.datetime) else d.date()
            elif name == "UID":
                cur["uid"] = value
            elif name == "STATUS":
                cur["status"] = value
    return res


def day_of(x):
    return x.date() if isinstance(x, dt.datetime) else x


def nth_weekday_ok(day, spec):
    """BYDAY 항목 하나(예: 'TU', '2TU', '-1FR')가 그 날에 맞나."""
    m = re.fullmatch(r"([+-]?\d+)?([A-Z]{2})", spec)
    if not m or DAYS.index(m.group(2)) != day.weekday():
        return False
    if not m.group(1):
        return True
    n = int(m.group(1))
    if n > 0:
        return (day.day - 1) // 7 + 1 == n
    nxt = day + dt.timedelta(days=7 * (-n))
    return nxt.month != day.month and (day + dt.timedelta(days=7 * (-n - 1))).month == day.month


def rule_hits(rule, start, day):
    """UNTIL·COUNT를 빼고, 반복 규칙이 그 날에 맞는지."""
    freq, iv = rule.get("FREQ"), int(rule.get("INTERVAL", "1"))
    byday = [b for b in rule.get("BYDAY", "").split(",") if b]
    bymd = [int(x) for x in rule.get("BYMONTHDAY", "").split(",") if x]
    if day < start:
        return False
    if freq == "DAILY":
        return (day - start).days % iv == 0 and (not byday or any(nth_weekday_ok(day, b) for b in byday))
    if freq == "WEEKLY":
        weeks = ((day - dt.timedelta(days=day.weekday())) - (start - dt.timedelta(days=start.weekday()))).days // 7
        wanted = [DAYS.index(b[-2:]) for b in byday] or [start.weekday()]
        return weeks % iv == 0 and day.weekday() in wanted
    if freq == "MONTHLY":
        months = (day.year - start.year) * 12 + day.month - start.month
        if months % iv:
            return False
        if byday:
            return any(nth_weekday_ok(day, b) for b in byday)
        return day.day in (bymd or [start.day])
    if freq == "YEARLY":
        return (day.year - start.year) % iv == 0 and (day.month, day.day) == (start.month, start.day)
    return False


def occurs(ev, day):
    start = day_of(ev["start"])
    rule = ev.get("rrule")
    if not rule:
        end = day_of(ev.get("end", ev["start"]))
        if ev["allday"]:  # 종일 일정의 끝 날짜는 포함하지 않는다
            return start <= day < max(end, start + dt.timedelta(days=1))
        return start <= day <= end
    if day in ev["exdates"] or not rule_hits(rule, start, day):
        return False
    if "UNTIL" in rule:
        until, _ = parse_dt("", rule["UNTIL"])
        if day > day_of(until):
            return False
    if "COUNT" in rule:
        n, d = 0, start
        while d <= day:
            if rule_hits(rule, start, d) and d not in ev["exdates"]:
                n += 1
            d += dt.timedelta(days=1)
        if n > int(rule["COUNT"]):
            return False
    return True


def todays(urls, day):
    evs = []
    for url in urls:
        with urllib.request.urlopen(url, timeout=30) as r:
            evs += events(r.read().decode("utf-8", "replace"))
    moved = {(e.get("uid"), e["recurrence_id"]) for e in evs if "recurrence_id" in e}
    out = []
    for e in evs:
        if e.get("status") == "CANCELLED":
            continue
        if "recurrence_id" not in e and e.get("rrule") and (e.get("uid"), day) in moved:
            continue  # 이 날짜 반복분은 따로 옮겨진 일정이 대신한다
        if "recurrence_id" in e:
            if day_of(e["start"]) != day:
                continue
        elif not occurs(e, day):
            continue
        if e["allday"]:
            when, key = "종일", "00:00"
        else:
            t = e["start"]
            if e.get("rrule"):  # 반복이면 그날의 같은 시각
                t = dt.datetime.combine(day, t.timetz())
            end = e.get("end")
            dur = (end - e["start"]) if isinstance(end, dt.datetime) else None
            when = t.strftime("%H:%M") + (f"~{(t + dur).strftime('%H:%M')}" if dur else "")
            key = t.strftime("%H:%M")
        line = f"{when} {e.get('summary', '(제목 없음)')}"
        if e.get("location"):
            line += f" ({e['location']})"
        out.append((key, line))
    return [l for _, l in sorted(set(out))]


def urls_from_env(env):
    return [u.strip() for u in env.get("GCAL_ICS_URL", "").split(",") if u.strip()]


if __name__ == "__main__":
    from pathlib import Path
    env = {}
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    urls = urls_from_env(env)
    if not urls:
        sys.exit(".env에 GCAL_ICS_URL 이 없습니다")
    for line in todays(urls, day) or ["(일정 없음)"]:
        print(line)
