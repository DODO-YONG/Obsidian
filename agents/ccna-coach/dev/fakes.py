"""가짜 Supabase(메모리 표)·가짜 제미나이·가짜 로그인. 시험과 로컬 화면 확인용 — 실제 서비스·사용량 없음."""
import os, sys, uuid, random, itertools
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "docs" / "api"))
os.environ.update(SUPABASE_URL="x", SUPABASE_SERVICE_ROLE_KEY="x", SUPABASE_ANON_KEY="x", GOOGLE_API_KEY="x",
                  TRACER_OWNER_EMAIL="owner@example.com", TRACER_BANK_MIN="3")
import _db as db, _gemini as gc, _core as core

T = {k: [] for k in ["profiles", "activity_log", "questions", "question_seen", "question_reports", "attempts", "progress", "app_reports"]}
ids = itertools.count(1)
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
        if op == "gte" and k == "at": pass
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
        if t == "profiles": r = {"role": "user", "status": "active", "can_practice": True, "can_explain": True, "daily_limit": 30, "last_seen": None, **r}
        if t == "questions": r = {"id": str(uuid.uuid4()), "status": "active", "served": 0, "graded": 0, "correct": 0, "reports": 0, **r}
        if t == "activity_log": r = {"ai": False, "counted": False, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **r}
        if t == "question_reports": r = {"resolved": False, **r}
        if t == "app_reports": r = {"id": next(ids), "resolved": False, "note": None, "app_version": None, "lang": None, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **r}
        if t == "attempts": r = {"at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **r}
        T[t].append(r); out.append(r)
    return [dict(x) for x in out] if returning else None
db.insert = insert
def update(t, p, f):
    rs = [r for r in T[t] if match(r, p)]
    for r in rs: r.update(f)
    return [dict(r) for r in rs]
db.update = update
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
        return [{"day": str(t - _d.timedelta(days=13 - i)), "visitors": i % 4 + 1, "ai_calls": 12 - i // 2, "bank_serves": i * 2,
                 "new_questions": max(1, 10 - i), "answers": 8 + i} for i in range(14)]
    if name == "bank_buckets":
        from collections import Counter
        c = Counter((q["sub"], q["difficulty"], q["qtype"], q["status"]) for q in T["questions"])
        keys = sorted({k[:3] for k in c})
        return [{"sub": k[0], "difficulty": k[1], "qtype": k[2], "active": c[k + ("active",)], "flagged": c[k + ("flagged",)], "hidden": c[k + ("hidden",)]} for k in keys]
    raise Exception(name)
db.rpc = rpc
calls = {"n": 0}
def ask_json(sys_, prompt, schema=None):
    calls["n"] += 1
    if "Write exactly ONE question" in sys_:
        n = calls["n"]
        return {"question": f"Q{n}: Which protocol {n}?", "choices": ["a", "b", "c", "d"], "answer": "B",
                "explanation": "B because.", "option_notes": ["A no", "B yes", "C no", "D no"], "key_concept": "kc"}, "fake"
    return {"verdict": "partial", "correct_answer": "x", "explanation": "e", "key_concept": "k"}, "fake"
gc.ask_json = ask_json
users = {"o": {"id": "u-owner", "email": "owner@example.com", "user_metadata": {"full_name": "O"}},
         "a": {"id": "u-alice", "email": "alice@example.com", "user_metadata": {}}}
db.auth_user = lambda tok: users.get(tok)

users["b"]={"id":"u-bob","email":"bob@example.com","user_metadata":{"full_name":"Bob"}}
