"""가짜 Supabase(메모리 표)·가짜 제미나이·가짜 로그인. 시험과 로컬 화면 확인용 — 실제 서비스·사용량 없음."""
import os, sys, uuid, random, itertools
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "docs" / "api"))
os.environ.update(SUPABASE_URL="x", SUPABASE_SERVICE_ROLE_KEY="x", SUPABASE_ANON_KEY="x", GOOGLE_API_KEY="x",
                  TRACER_OWNER_EMAIL="owner@example.com", TRACER_BANK_MIN="3")
import _db as db, _gemini as gc, _core as core

T = {k: [] for k in ["profiles", "activity_log", "questions", "question_seen", "question_reports", "attempts", "progress", "app_reports", "admin_command_log"]}
ids = itertools.count(1)
def _ts(v):
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
def match(r, params):
    for k, v in params.items():
        if k in ("select", "order", "limit", "offset", "on_conflict"): continue
        op, _, val = v.partition(".")
        x = r.get(k)
        if op == "eq" and str(x) != val: return False
        if op == "neq" and (x is None or str(x) == val): return False
        if op == "is" and val == "true" and x is not True: return False
        if op == "is" and val == "false" and x is not False: return False
        if op == "is" and val == "null" and x is not None: return False
        if op == "not" and val == "is.null" and x is None: return False
        if op == "gte" and k == "at":
            if x is None or _ts(x) < _ts(val): return False
        if op == "gte" and k != "at" and not (x >= int(val)): return False
        if op == "in" and str(x) not in val.strip("()").split(","): return False
    return True
def _select(t, p=None):
    p = p or {}
    rows = [dict(r) for r in T[t] if match(r, p)]
    if t == "activity_log":
        for r in rows:
            r.setdefault("at", "2026-11-20T10:00:00+00:00")
            pr = [x for x in T["profiles"] if x["id"] == r.get("user_id")]
            r["profiles"] = {"email": pr[0]["email"], "name": pr[0]["name"]} if pr else None
        rows.reverse()
    o = p.get("order", "")
    if t != "activity_log" and o.endswith(".desc"):
        rows.sort(key=lambda r: str(r.get(o[:-5]) or ""), reverse=True)
    off = int(p.get("offset", 0))
    return rows[off: off + int(p.get("limit", 10**9))]
db.select = _select
db.one = lambda t, p: (db.select(t, p) or [None])[0]
db.count = lambda t, p: len([r for r in T[t] if match(r, p)])
def insert(t, rows, on_conflict=None, ignore_dupes=False, returning=True):
    out = []
    for r in rows:
        r = dict(r)
        if on_conflict and any(x.get(on_conflict) == r.get(on_conflict) for x in T[t]):
            if ignore_dupes: continue
            ex = [x for x in T[t] if x[on_conflict] == r[on_conflict]][0]; ex.update(r); out.append(ex); continue
        if t == "profiles": r = {"role": "user", "status": "active", "can_practice": True, "can_explain": True, "daily_limit": 30, "last_seen": None, "delete_at": None, "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **r}
        if t == "questions": r = {"id": str(uuid.uuid4()), "status": "active", "served": 0, "graded": 0, "correct": 0, "reports": 0, **r}
        if t == "activity_log": r = {"ai": False, "counted": False, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **r}
        if t == "question_reports": r = {"resolved": False, **r}
        if t == "app_reports": r = {"id": next(ids), "resolved": False, "note": None, "app_version": None, "lang": None, "at": datetime.now(timezone.utc).isoformat(), **r}
        if t == "admin_command_log": r = {"id": next(ids), "at": datetime.now(timezone.utc).isoformat(), **r}
        if t == "attempts": r = {"at": datetime.now(timezone.utc).isoformat(), **r}
        T[t].append(r); out.append(r)
    return [dict(x) for x in out] if returning else None
db.insert = insert
def update(t, p, f):
    rs = [r for r in T[t] if match(r, p)]
    for r in rs: r.update(f)
    return [dict(r) for r in rs]
db.update = update
def delete(t, p):
    if not p: raise db.DBError("삭제 조건이 없어요")
    kept = [r for r in T[t] if not match(r, p)]
    n = len(T[t]) - len(kept)
    T[t][:] = kept
    return n
db.delete = delete
def rpc(name, a=None):
    a = a or {}
    if name == "bucket_size": return len([q for q in T["questions"] if (q["sub"], q["difficulty"], q["qtype"], q["status"]) == (a["p_sub"], a["p_diff"], a["p_qtype"], "active")])
    if name == "pick_question":
        seen = {s["question_id"] for s in T["question_seen"] if s["user_id"] == a["p_user"]}
        c = [q for q in T["questions"] if (q["sub"], q["difficulty"], q["qtype"], q["status"]) == (a["p_sub"], a["p_diff"], a["p_qtype"], "active") and q["id"] not in seen]
        return [dict(random.choice(c))] if c else []
    if name == "recent_in_bucket": return []
    if name == "mark_served":
        if not any(s["user_id"] == a["p_user"] and s["question_id"] == a["p_qid"] for s in T["question_seen"]):
            T["question_seen"].append({"user_id": a["p_user"], "question_id": a["p_qid"], "graded_at": None})
        return None
    if name == "mark_graded":
        s = [s for s in T["question_seen"] if s["user_id"] == a["p_user"] and s["question_id"] == a["p_qid"] and s["graded_at"] is None]
        if not s: return False
        s[0]["graded_at"] = "now"; return True
    if name == "report_question":
        T["question_reports"].append({"question_id": a["p_qid"], "user_id": a["p_user"], "reason": a["p_reason"], "resolved": False})
        n = len([r for r in T["question_reports"] if r["question_id"] == a["p_qid"] and not r["resolved"]])
        for q in T["questions"]:
            if q["id"] == a["p_qid"]:
                q["reports"] = n
                if n >= a["p_threshold"]: q["status"] = "flagged"
        return n
    if name == "admin_users":
        return [{**p, "today_ai": len([x for x in T["activity_log"] if x.get("user_id") == p["id"] and x["ai"]]),
                 "today_actions": 0, "total_attempts": len([x for x in T["attempts"] if x["user_id"] == p["id"]])} for p in T["profiles"]]
    if name == "admin_daily":
        import datetime as _d
        t = _d.date.today()
        n = a.get("p_days", 14)
        return [{"day": str(t - _d.timedelta(days=n - 1 - i)), "visitors": i % 4 + 1, "ai_calls": max(0, 12 - i // 2), "bank_serves": i * 2,
                 "new_questions": max(1, 10 - i), "answers": 8 + i} for i in range(n)]
    if name == "bank_buckets":
        from collections import Counter
        c = Counter((q["sub"], q["difficulty"], q["qtype"], q["status"]) for q in T["questions"])
        keys = sorted({k[:3] for k in c})
        return [{"sub": k[0], "difficulty": k[1], "qtype": k[2], "active": c[k + ("active",)], "flagged": c[k + ("flagged",)], "hidden": c[k + ("hidden",)]} for k in keys]
    if name == "admin_period":
        f, to = _ts(a["p_from"]), _ts(a["p_to"])
        rows = [r for r in T["activity_log"] if r.get("at") and f <= _ts(r["at"]) < to]
        graded = [r for r in rows if r.get("action") == "grade"]
        correct = sum(1 for r in graded if (r.get("detail") or {}).get("verdict") == "정답")
        return {
            "visitors": len({r["user_id"] for r in rows if r.get("user_id")}),
            "answers": sum(1 for r in rows if r.get("action") in ("grade", "subnet")),
            "ai_calls": sum(1 for r in rows if r.get("ai")),
            "signups": sum(1 for r in rows if r.get("action") == "signup"),
            "graded": len(graded), "correct": correct,
            "rate": round(correct * 100 / len(graded), 1) if graded else None,
        }
    if name == "admin_sub_stats":
        since = datetime.now(timezone.utc) - timedelta(days=a.get("p_days", 30))
        by = {}
        for r in T["activity_log"]:
            if r.get("action") != "grade" or not r.get("at") or _ts(r["at"]) < since: continue
            sub = (r.get("detail") or {}).get("sub")
            if not sub: continue
            s = by.setdefault(sub, {"graded": 0, "correct": 0, "users": set()})
            s["graded"] += 1
            s["correct"] += 1 if (r.get("detail") or {}).get("verdict") == "정답" else 0
            if r.get("user_id"): s["users"].add(r["user_id"])
        out = [{"sub": sub, "graded": s["graded"], "correct": s["correct"], "users": len(s["users"]),
                "rate": round(s["correct"] * 100 / s["graded"], 1) if s["graded"] else None} for sub, s in by.items()]
        return sorted(out, key=lambda r: (r["rate"] if r["rate"] is not None else 101, -r["graded"]))
    if name == "admin_report":  # 실제 SQL(admin_full.sql)과 같은 모양: cur/prev = total·ai·active_users·signups·graded·correct·rate·by_action·by_device·by_hour
        days = max(1, min(int(a.get("p_days") or 1), 365))
        now = datetime.now(timezone.utc)
        today = now.date()
        def agg(t0, t1):
            logs = [r for r in T["activity_log"] if r.get("at") and t0 <= _ts(r["at"]) < t1]
            g = [r for r in logs if r.get("action") == "grade"]
            ok_ = [r for r in g if (r.get("detail") or {}).get("verdict") == "정답"]
            by_a, by_d, hr = {}, {}, [0] * 24
            for r in logs:
                by_a[r.get("action")] = by_a.get(r.get("action"), 0) + 1
                dv = r.get("device") or "알 수 없음"; by_d[dv] = by_d.get(dv, 0) + 1
                hr[(_ts(r["at"]) + timedelta(hours=9)).hour] += 1
            return {"total": len(logs), "ai": sum(1 for r in logs if r.get("ai")), "active_users": len({r.get("user_id") for r in logs}),
                    "signups": sum(1 for p_ in T["profiles"] if p_.get("created_at") and t0 <= _ts(p_["created_at"]) < t1),
                    "graded": len(g), "correct": len(ok_), "rate": round(len(ok_) * 100 / len(g), 1) if g else None,
                    "by_action": by_a, "by_device": by_d, "by_hour": hr}
        since = now - timedelta(days=days)
        cnt = {}
        for r in T["activity_log"]:
            if r.get("user_id") and r.get("at") and _ts(r["at"]) >= since and r.get("action") != "admin":
                cnt[r["user_id"]] = cnt.get(r["user_id"], 0) + 1
        pmap = {p_["id"]: p_ for p_ in T["profiles"]}
        top_users = [{"id": uid, "email": pmap.get(uid, {}).get("email", ""), "name": pmap.get(uid, {}).get("name", ""), "n": n}
                     for uid, n in sorted(cnt.items(), key=lambda kv: -kv[1])[:5]]
        daily = []
        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            rs = [r for r in T["activity_log"] if r.get("at") and _ts(r["at"]).date() == d]
            daily.append({"day": d.isoformat(), "total": len(rs), "users": len({r.get("user_id") for r in rs})})
        return {"days": days, "cur": agg(since, now + timedelta(seconds=1)), "prev": agg(now - timedelta(days=2 * days), since),
                "prev_partial": False, "top_users": top_users, "daily": daily}
    raise db.DBError(name)
db.rpc = rpc
calls = {"n": 0}
def ask_json(sys_, prompt, schema=None, temperature=0.7):
    calls["n"] += 1
    if "Write exactly ONE question" in sys_:
        n = calls["n"]
        return {"question": f"Q{n}: Which protocol {n}?", "choices": ["a", "b", "c", "d"], "answer": "B",
                "explanation": "B because.", "option_notes": ["A no", "B yes", "C no", "D no"], "key_concept": "kc"}, "fake"
    if "TRACER web admin page" in sys_:  # 관리자 명령창: 낱말로 대충 고른다(가짜)
        t = prompt
        if "시작" in t and "최" in t:
            return {"command": "sql_query", "args": {"sql": "SELECT id, name, email, last_seen FROM users WHERE name LIKE '최%' ORDER BY name", "title": "최로 시작하는 사용자", "target": "users"}, "confidence": 0.95, "reply": "이름이 최로 시작하는 사용자를 찾을게요."}, "fake"
        if "SQL로" in t:
            return {"command": "sql_query", "args": {"sql": "DELETE FROM users", "title": "x", "target": "users"}, "confidence": 1, "reply": "x"}, "fake"
        days = 365 if "1년" in t or "일년" in t else 90 if "3달" in t or "90" in t else 30 if "30" in t or "한 달" in t else 1 if "오늘" in t else 7
        if "접속" in t and ("안 한" in t or "않은" in t or "안한" in t):
            if any(w in t for w in ("지워", "삭제")): return {"command": "mark_delete_inactive", "args": {"inactive_days": days}, "confidence": 0.9, "reply": f"{days}일 넘게 접속하지 않은 사용자를 삭제 예정으로 표시할게요."}, "fake"
            return {"command": "show_users", "args": {"inactive_days": days}, "reply": f"{days}일 넘게 접속하지 않은 사용자를 보여 드릴게요."}, "fake"
        if "삭제 예정" in t and "취소" in t: return {"command": "unmark_delete_all", "args": {}, "reply": "삭제 예정을 모두 취소할게요."}, "fake"
        if "승인" in t: return {"command": "approve_all_pending", "args": {}, "reply": "승인 대기 사용자를 모두 승인할게요."}, "fake"
        if "신고" in t and "처리" in t: return {"command": "resolve_app_reports", "args": {"days": days}, "reply": "미처리 신고를 처리 완료로 바꿀게요."}, "fake"
        if "신고" in t: return {"command": "show_app_reports", "args": {"open": "0", "days": days}, "reply": f"최근 {days}일 앱 신고를 보여 드릴게요."}, "fake"
        if "사용자 수" in t or "접속자" in t: return {"command": "show_dashboard", "args": {"days": days}, "reply": f"최근 {days}일 접속자를 보여 드릴게요."}, "fake"
        if "오래" in t: return {"command": "show_users", "args": {"inactive_days": 180}, "confidence": 0.5, "reply": "오래 접속하지 않은 사용자를 보려는 것 같아요."}, "fake"
        return {"command": "none", "args": {}, "confidence": 0.9, "reply": "그 명령은 이 화면에서 할 수 없어요."}, "fake"
    return {"verdict": "partial", "correct_answer": "x", "explanation": "e", "key_concept": "k"}, "fake"
gc.ask_json = ask_json
users = {"o": {"id": "u-owner", "email": "owner@example.com", "user_metadata": {"full_name": "O"}},
         "a": {"id": "u-alice", "email": "alice@example.com", "user_metadata": {}}}
db.auth_user = lambda tok: users.get(tok)

users["b"]={"id":"u-bob","email":"bob@example.com","user_metadata":{"full_name":"Bob"}}
