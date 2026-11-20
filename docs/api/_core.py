"""TRACER 서버 로직 (Vercel). 화면 요청 → 로그인·권한·한도 확인 → 문제 저장소/제미나이 → 기록.

문제 저장소
- 묶음 = 범위 × 난이도 × 유형. 묶음에 문제가 BANK_MIN(기본 10)개 이상이면 BANK_RATIO(90%)는 저장된 문제에서,
  나머지는 새로 만들어 저장한다. 사용자가 이미 받은 문제는 다시 내지 않는다.
- 객관식은 만들 때 정답·해설·보기별 이유까지 한 번에 받아 저장 → 채점·해설에 제미나이를 쓰지 않는다.
- 주관식은 판정만 제미나이(뜻이 맞는지 봐야 해서).
- 하루 한도를 다 쓰면 저장소에 남은 문제가 있는 한 그걸로 낸다.
- "내 문제 해설"(책·기출 붙여 넣기)은 저장소에 넣지 않는다(저작권·개인 입력).
"""

import hashlib
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _db as db
import _gemini as gc

KST = timezone(timedelta(hours=9))
HERE = Path(__file__).resolve().parent
DOMAINS = json.loads((HERE.parent / "ccna" / "topics.json").read_text(encoding="utf-8"))
SUB_INDEX = {s["id"]: (d, s["name"]) for d in DOMAINS for s in d["subs"]}

BANK_MIN = int(os.environ.get("TRACER_BANK_MIN") or 10)
BANK_RATIO = float(os.environ.get("TRACER_BANK_RATIO") or 0.9)
REPORT_THRESHOLD = int(os.environ.get("TRACER_REPORT_THRESHOLD") or 3)
GLOBAL_DAILY_AI = int(os.environ.get("TRACER_GLOBAL_DAILY_AI") or 300)
NEW_USER_STATUS = os.environ.get("TRACER_NEW_USER_STATUS") or "active"   # active(바로 사용) | pending(승인 후)
DIFFS = ("쉬움", "보통", "어려움")


class ApiError(Exception):
    def __init__(self, code: int, msg: str, extra: dict | None = None):
        super().__init__(msg)
        self.code, self.msg, self.extra = code, msg, extra or {}


def refuse_paid_billing() -> None:
    """Claude API 키가 있으면 실행하지 않는다(구독 외 추가 요금 방지 — 저장소 규칙)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise ApiError(500, "ANTHROPIC_API_KEY 가 설정돼 있어 실행하지 않아요(유료 과금 방지). Vercel 환경변수에서 지워 주세요.")


# ---- 시간·기기 ------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_start_iso() -> str:
    """한국 시간 오늘 0시(UTC로)."""
    k = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return k.astimezone(timezone.utc).isoformat()


def device_of(ua: str) -> str:
    ua = ua or ""
    kind = "모바일" if re.search(r"Mobile|Android|iPhone|iPad", ua) else "데스크톱"
    br = ("Edge" if "Edg/" in ua else "Samsung" if "SamsungBrowser" in ua else "Chrome" if "Chrome/" in ua
          else "Firefox" if "Firefox/" in ua else "Safari" if "Safari/" in ua else "기타")
    os_ = ("iOS" if re.search(r"iPhone|iPad", ua) else "Android" if "Android" in ua else "macOS" if "Mac OS" in ua
           else "Windows" if "Windows" in ua else "Linux" if "Linux" in ua else "")
    return " · ".join(x for x in (kind, os_, br) if x)


# ---- 사용자 ----------------------------------------------------------------------

def current_user(token: str, ua: str = "", required: bool = True) -> dict | None:
    """토큰 → profiles 행(+device). 처음이면 만든다. 오너 이메일이면 owner."""
    u = db.auth_user(token)
    if not u:
        if required:
            raise ApiError(401, "로그인이 필요해요.", {"code": "login"})
        return None
    uid, email = u["id"], (u.get("email") or "").lower()
    meta = u.get("user_metadata") or {}
    p = db.one("profiles", {"id": f"eq.{uid}", "select": "*"})
    owner_email = (os.environ.get("TRACER_OWNER_EMAIL") or "").strip().lower()
    if not p:
        row = {"id": uid, "email": email, "name": meta.get("full_name") or meta.get("name") or "",
               "status": NEW_USER_STATUS if NEW_USER_STATUS in ("active", "pending") else "active"}
        if owner_email and email == owner_email:
            row.update(role="owner", status="active")
        p = (db.insert("profiles", [row], on_conflict="id", ignore_dupes=True) or [None])[0] \
            or db.one("profiles", {"id": f"eq.{uid}", "select": "*"})
        log_activity(p, "signup", {}, device=device_of(ua))
    elif owner_email and email == owner_email and p["role"] != "owner":
        p = db.update("profiles", {"id": f"eq.{uid}"}, {"role": "owner", "status": "active"})[0]
    p["_device"] = device_of(ua)
    return p


def is_admin(p: dict | None) -> bool:
    return bool(p) and p["role"] in ("owner", "admin") and p["status"] == "active"


def require_active(p: dict) -> None:
    if p["status"] == "blocked":
        raise ApiError(403, "이용이 제한된 계정이에요. 관리자에게 문의해 주세요.", {"code": "blocked"})
    if p["status"] == "pending":
        raise ApiError(403, "관리자 승인을 기다리고 있어요. 승인되면 AI 문제를 쓸 수 있어요.", {"code": "pending"})


def log_activity(p: dict | None, action: str, detail: dict, ai: bool = False, device: str | None = None) -> None:
    try:
        db.insert("activity_log", [{
            "user_id": p["id"] if p else None, "action": action, "detail": detail, "ai": ai,
            "counted": bool(ai and p and p["role"] != "owner"),
            "device": device or (p or {}).get("_device"),
        }], returning=False)
    except db.DBError:
        pass  # 기록 실패로 본 기능을 막지 않는다


def ai_left(p: dict) -> int:
    """오늘 이 사용자가 제미나이를 더 부를 수 있는 횟수(owner는 큰 수)."""
    if p["role"] == "owner":
        return 10 ** 6
    since = today_start_iso()
    total = db.count("activity_log", {"counted": "is.true", "at": f"gte.{since}"})
    if total >= GLOBAL_DAILY_AI:
        return 0
    mine = db.count("activity_log", {"user_id": f"eq.{p['id']}", "ai": "is.true", "at": f"gte.{since}"})
    return max(0, min(p["daily_limit"] - mine, GLOBAL_DAILY_AI - total))


def touch(p: dict) -> None:
    """마지막 접속 갱신. 30분 넘게 비었다가 오면 'visit' 기록."""
    last = p.get("last_seen")
    gap = True
    if last:
        try:
            gap = datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00")) > timedelta(minutes=30)
        except ValueError:
            pass
    db.update("profiles", {"id": f"eq.{p['id']}"}, {"last_seen": now_iso()})
    if gap:
        log_activity(p, "visit", {})


# ---- 제미나이 지시문 -------------------------------------------------------------

SYS_QUESTION = """You are a Cisco CCNA 200-301 instructor with 10+ years of experience writing exam-style questions.
Write exactly ONE question from the given exam topic, in ENGLISH, in the style of the real CCNA exam,
and write its full explanation now (it will be stored and shown to many students later).

Rules
- Use precise Cisco terminology and IOS command syntax (e.g. show ip route, OSPF, native VLAN).
- Only write questions with one clearly correct answer. If you are not certain of a fact, choose a different question.
- When useful, include a short IOS config snippet or show-command output (use \\n for new lines).
- Multiple choice: exactly 4 options; "answer" is one letter "A"-"D". Do not prefix options with "A." etc.
  "option_notes": exactly 4 short sentences in the same order as the options, each saying why that option is correct or wrong.
- Short answer: "choices" is an empty array; "answer" is a concise model answer; "option_notes" is an empty array.
- "explanation": why the correct answer is right, in clear, simple English (2-5 sentences).
- "key_concept": the one concept being tested. "cli_example": a relevant IOS example or "". "tip": an exam tip or "".
- Do not repeat or closely paraphrase the existing questions listed by the user."""

SYS_GRADE = """You are a Cisco CCNA 200-301 instructor reviewing a student's answer. Write everything in clear, simple ENGLISH.
- Decide whether the answer is correct first (if a verdict is already given, use it), then explain why.
- If the answer is wrong, point out the likely misconception and correct it.
- Put a relevant IOS command example in "cli_example" when it helps; otherwise use an empty string.
- Do not state uncertain facts as certain; say "verify in the official Cisco documentation" instead.
- verdict must be exactly one of: "correct", "partial", "incorrect".
- If the question is not about networking/CCNA, do not explain it: verdict "incorrect" and explanation "I can only explain CCNA-related questions." """

VERDICT_KO = {"correct": "정답", "partial": "부분 정답", "incorrect": "오답"}
DIFF_EN = {"쉬움": "easy", "보통": "medium", "어려움": "hard"}

Q_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "question": {"type": "STRING"},
        "choices": {"type": "ARRAY", "items": {"type": "STRING"}},
        "answer": {"type": "STRING"},
        "explanation": {"type": "STRING"},
        "option_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "key_concept": {"type": "STRING"},
        "cli_example": {"type": "STRING"},
        "tip": {"type": "STRING"},
    },
    "required": ["question", "choices", "answer", "explanation", "option_notes", "key_concept"],
}
G_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "verdict": {"type": "STRING", "enum": ["correct", "partial", "incorrect"]},
        "correct_answer": {"type": "STRING"},
        "explanation": {"type": "STRING"},
        "why_wrong": {"type": "STRING"},
        "key_concept": {"type": "STRING"},
        "cli_example": {"type": "STRING"},
        "tip": {"type": "STRING"},
    },
    "required": ["verdict", "correct_answer", "explanation", "key_concept"],
}


def _norm_verdict(v) -> str:
    v = str(v or "").strip().lower()
    return VERDICT_KO.get(v) or ("부분 정답" if "부분" in v else "정답" if v == "정답" else "오답")


def norm_hash(text: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return hashlib.sha1(t[:400].encode()).hexdigest()


def public_q(q: dict, source: str) -> dict:
    """화면에 보내는 문제(정답·해설 없음)."""
    d, name = SUB_INDEX.get(q["sub"], ({"name": "", "id": ""}, q["sub"]))
    return {"id": q["id"], "question": q["question"], "choices": q.get("choices") or [], "sub": q["sub"],
            "sub_name": name, "domain": d["name"], "domain_id": d["id"], "qtype": q["qtype"],
            "difficulty": q["difficulty"], "model": q.get("model") or "", "source": source}


# ---- 문제 받기 -------------------------------------------------------------------

def generate(sid: str, difficulty: str, qtype: str, p: dict) -> dict:
    domain, sub_name = SUB_INDEX[sid]
    kind = "multiple choice (4 options)" if qtype == "mcq" else "short answer"
    try:
        recent = [r["question"] for r in db.rpc("recent_in_bucket", {"p_sub": sid, "p_diff": difficulty, "p_qtype": qtype, "p_n": 12}) or []]
    except db.DBError:
        recent = []
    prompt = (f"Exam topic: {domain['en']} / {sub_name} (topic {sid})\nDifficulty: {DIFF_EN[difficulty]}\n"
              f"Format: {kind}\nExisting questions (do not repeat):\n" + ("\n".join(f"- {r}" for r in recent) or "(none)"))
    data, model = gc.ask_json(SYS_QUESTION, prompt, Q_SCHEMA)
    choices = [str(c).strip() for c in data.get("choices") or []][:4] if qtype == "mcq" else []
    answer = str(data.get("answer", "")).strip()
    notes = [str(n).strip() for n in data.get("option_notes") or []][:4] if qtype == "mcq" else []
    if qtype == "mcq":
        answer = answer.upper()[:1]
        if len(choices) != 4 or answer not in "ABCD" or not answer:
            raise gc.GeminiError("보기 4개짜리 문제를 받지 못했어요. 다시 받아 주세요.")
    question = str(data.get("question", "")).strip()
    if not question or not answer:
        raise gc.GeminiError("문제를 제대로 받지 못했어요. 다시 받아 주세요.")
    row = {"sub": sid, "difficulty": difficulty, "qtype": qtype, "question": question, "choices": choices,
           "answer": answer, "explanation": str(data.get("explanation", "")).strip(),
           "option_notes": notes if len(notes) == 4 else [], "key_concept": str(data.get("key_concept", "")).strip(),
           "cli_example": str(data.get("cli_example", "")).strip(), "tip": str(data.get("tip", "")).strip(),
           "model": model, "norm_hash": norm_hash(question), "created_by": p["id"]}
    saved = db.insert("questions", [row], on_conflict="norm_hash", ignore_dupes=True)
    if saved:
        return saved[0]
    # 똑같은 문제가 이미 있으면 그 문제를 쓴다(새로 저장하지 않음)
    return db.one("questions", {"norm_hash": f"eq.{row['norm_hash']}", "select": "*"}) or {**row, "id": None}


def new_question(p: dict, subs: list, difficulty: str, qtype: str) -> dict:
    require_active(p)
    if not p["can_practice"]:
        raise ApiError(403, "AI 문제 권한이 꺼져 있어요. 서브넷 계산 문제는 계속 풀 수 있어요.", {"code": "no_perm"})
    difficulty = difficulty if difficulty in DIFFS else "보통"
    qtype = qtype if qtype in ("mcq", "short") else "mcq"
    pool = [s for s in subs if s in SUB_INDEX] or list(SUB_INDEX)
    sid = random.choice(pool)
    size = db.rpc("bucket_size", {"p_sub": sid, "p_diff": difficulty, "p_qtype": qtype}) or 0
    left = ai_left(p)

    def from_bank():
        rows = db.rpc("pick_question", {"p_user": p["id"], "p_sub": sid, "p_diff": difficulty, "p_qtype": qtype}) or []
        return rows[0] if rows else None

    q, source = None, "new"
    if size >= BANK_MIN and random.random() < BANK_RATIO:
        q, source = from_bank(), "bank"
    if not q and left <= 0:
        q, source = from_bank(), "bank"      # 한도를 다 썼으면 아직 안 받은 저장 문제라도
        if not q:
            raise ApiError(429, "오늘 쓸 수 있는 AI 문제를 모두 썼어요. 내일 다시 이용해 주세요. (서브넷 계산은 계속 쓸 수 있어요)",
                           {"code": "limit"})
    if not q:
        q, source = generate(sid, difficulty, qtype, p), "new"
        if not q.get("id"):
            raise gc.GeminiError("문제를 저장하지 못했어요. 다시 받아 주세요.")
    db.rpc("mark_served", {"p_user": p["id"], "p_qid": q["id"]})
    log_activity(p, "question", {"sub": sid, "difficulty": difficulty, "qtype": qtype, "source": source,
                                 "qid": q["id"], "bucket": size}, ai=(source == "new"))
    return public_q(q, source)


# ---- 채점 ------------------------------------------------------------------------

def grade(p: dict, qid: str, user_answer: str) -> dict:
    require_active(p)
    if not re.fullmatch(r"[0-9a-f-]{36}", qid or ""):
        raise ApiError(400, "문제를 찾을 수 없어요. 새 문제를 받아 주세요.")
    seen = db.one("question_seen", {"user_id": f"eq.{p['id']}", "question_id": f"eq.{qid}", "select": "graded_at"})
    q = db.one("questions", {"id": f"eq.{qid}", "select": "*"})
    if not q or not seen:
        raise ApiError(404, "문제를 찾을 수 없어요. 새 문제를 받아 주세요.")
    used_ai = False
    if q["qtype"] == "mcq":
        letter = user_answer.strip().upper()[:1]
        ok = letter == q["answer"]
        right = q["answer"]
        res = {"verdict": "정답" if ok else "오답",
               "correct_answer": f"{right}. {q['choices']['ABCD'.index(right)]}" if len(q["choices"]) == 4 else right}
        notes = q.get("option_notes") or []
        if q.get("explanation"):
            res.update(explanation=q["explanation"], key_concept=q.get("key_concept") or "",
                       cli_example=q.get("cli_example") or "", tip=q.get("tip") or "",
                       why_wrong=(notes["ABCD".index(letter)] if (not ok and letter in "ABCD" and len(notes) == 4) else ""),
                       model="saved explanation")
        else:  # 예전 문제처럼 해설이 저장돼 있지 않으면 그때만 제미나이
            if ai_left(p) <= 0:
                raise ApiError(429, "오늘 쓸 수 있는 AI 해설을 모두 썼어요.", {"code": "limit"})
            res.update(_ai_grade(q, user_answer, fixed="correct" if ok else "incorrect"))
            res["verdict"] = "정답" if ok else "오답"
            used_ai = True
    else:
        if ai_left(p) <= 0:
            raise ApiError(429, "오늘 쓸 수 있는 AI 채점을 모두 썼어요. 내일 다시 이용해 주세요.", {"code": "limit"})
        res = _ai_grade(q, user_answer)
        res["verdict"] = _norm_verdict(res.get("verdict"))
        if not res.get("correct_answer"):
            res["correct_answer"] = q["answer"]
        used_ai = True
    first = db.rpc("mark_graded", {"p_user": p["id"], "p_qid": qid, "p_ok": res["verdict"] == "정답"})
    if first:
        d = SUB_INDEX.get(q["sub"], ({"id": ""}, ""))[0]
        db.insert("attempts", [{"user_id": p["id"], "question_id": qid, "mode": "practice", "domain_id": d["id"],
                                "sub": q["sub"], "qtype": q["qtype"], "difficulty": q["difficulty"],
                                "verdict": res["verdict"], "question": q["question"][:500],
                                "user_answer": user_answer[:500]}], returning=False)
    res["first"] = bool(first)
    log_activity(p, "grade", {"qid": qid, "sub": q["sub"], "qtype": q["qtype"], "verdict": res["verdict"]}, ai=used_ai)
    return res


def _ai_grade(q: dict, user_answer: str, fixed: str = "") -> dict:
    choices = "\n".join(f"{'ABCD'[i]}. {c}" for i, c in enumerate(q.get("choices") or []))
    prompt = (f"Question:\n{q['question']}\n\nOptions:\n{choices or '(short answer)'}\n\n"
              f"Model answer: {q['answer']}\n" + (f"Reference explanation: {q['explanation']}\n" if q.get("explanation") else "")
              + f"Student's answer: {user_answer}\n"
              + (f"Verdict (already decided): {fixed}" if fixed else "Short answer: correct if the meaning matches, partial if only partly right."))
    res, model = gc.ask_json(SYS_GRADE, prompt, G_SCHEMA)
    res["model"] = model
    return res


def explain_custom(p: dict, question: str, user_answer: str, sub: str) -> dict:
    require_active(p)
    if not p["can_explain"]:
        raise ApiError(403, "내 문제 해설 권한이 꺼져 있어요.", {"code": "no_perm"})
    if ai_left(p) <= 0:
        raise ApiError(429, "오늘 쓸 수 있는 AI 해설을 모두 썼어요. 내일 다시 이용해 주세요.", {"code": "limit"})
    scope = f"{SUB_INDEX[sub][0]['en']} / {SUB_INDEX[sub][1]}" if sub in SUB_INDEX else "not specified"
    prompt = (f"(The student brought this question. No answer key is given; decide the correct answer yourself.)\n"
              f"Topic: {scope}\n\nQuestion:\n{question}\n\nStudent's answer: {user_answer or '(none - explanation only)'}")
    res, model = gc.ask_json(SYS_GRADE, prompt, G_SCHEMA)
    res["verdict"] = _norm_verdict(res.get("verdict"))
    res["model"] = model
    d = SUB_INDEX[sub][0]["id"] if sub in SUB_INDEX else ""
    # 붙여 넣은 문제는 저장소에 넣지 않고, 본인 풀이 기록에만 앞부분을 남긴다
    db.insert("attempts", [{"user_id": p["id"], "mode": "custom", "domain_id": d, "sub": sub or None, "qtype": "custom",
                            "verdict": res["verdict"], "question": question[:300], "user_answer": user_answer[:300]}],
              returning=False)
    log_activity(p, "explain", {"sub": sub}, ai=True)
    return res


def log_subnet(p: dict, body: dict) -> None:
    v = body.get("verdict") if body.get("verdict") in ("정답", "오답") else None
    if not v or p["status"] == "blocked":
        return
    db.insert("attempts", [{"user_id": p["id"], "mode": "practice", "domain_id": "1", "sub": "1.6", "qtype": "subnet",
                            "difficulty": str(body.get("difficulty", ""))[:10], "verdict": v,
                            "question": str(body.get("question", ""))[:300], "user_answer": str(body.get("user", ""))[:100]}],
              returning=False)
    log_activity(p, "subnet", {"verdict": v})


def report(p: dict, qid: str, reason: str) -> dict:
    require_active(p)
    if not db.one("question_seen", {"user_id": f"eq.{p['id']}", "question_id": f"eq.{qid}", "select": "question_id"}):
        raise ApiError(404, "받은 문제만 신고할 수 있어요.")
    n = db.rpc("report_question", {"p_qid": qid, "p_user": p["id"], "p_reason": reason[:500] or "(이유 없음)",
                                   "p_threshold": REPORT_THRESHOLD})
    log_activity(p, "report", {"qid": qid, "reason": reason[:200]})
    return {"ok": True, "reports": n}


# ---- 진도 ------------------------------------------------------------------------

def stats(p: dict) -> dict:
    rows = db.select("attempts", {"user_id": f"eq.{p['id']}", "verdict": "not.is.null",
                                  "select": "sub,verdict,question,at", "order": "at.desc", "limit": "3000"})
    by_sub: dict[str, dict] = {}
    for r in rows:
        s = by_sub.setdefault(r.get("sub") or "", {"n": 0, "ok": 0})
        s["n"] += 1
        s["ok"] += 1 if r["verdict"] == "정답" else 0
    by_domain = []
    for d in DOMAINS:
        n = sum(by_sub.get(s["id"], {}).get("n", 0) for s in d["subs"])
        ok = sum(by_sub.get(s["id"], {}).get("ok", 0) for s in d["subs"])
        by_domain.append({"id": d["id"], "name": d["name"], "n": n, "ok": ok})
    weak = sorted(((s, v) for s, v in by_sub.items() if s in SUB_INDEX and v["n"] >= 2),
                  key=lambda kv: kv[1]["ok"] / kv[1]["n"])[:3]
    recent = [{"sub": r.get("sub"), "verdict": r["verdict"], "question": (r.get("question") or "")[:70]} for r in rows[:8]]
    return {"total": len(rows), "ok": sum(1 for r in rows if r["verdict"] == "정답"), "by_domain": by_domain,
            "weak": [{"sub": s, "name": SUB_INDEX[s][1], "n": v["n"], "ok": v["ok"]} for s, v in weak],
            "recent": recent, "exam_date": os.environ.get("CCNA_EXAM_DATE") if p["role"] == "owner" else None,
            "has_key": gc.has_key()}


def me(p: dict) -> dict:
    touch(p)
    prog = db.one("progress", {"user_id": f"eq.{p['id']}", "select": "data,updated_at"})
    return {"id": p["id"], "email": p["email"], "name": p["name"], "role": p["role"], "status": p["status"],
            "can_practice": p["can_practice"], "can_explain": p["can_explain"], "daily_limit": p["daily_limit"],
            "ai_left": min(ai_left(p), 9999), "progress": (prog or {}).get("data"), "admin": is_admin(p)}


def save_progress(p: dict, data) -> dict:
    if not isinstance(data, dict) or len(json.dumps(data)) > 20000:
        raise ApiError(400, "진행 정보를 저장하지 못했어요.")
    db.insert("progress", [{"user_id": p["id"], "data": data, "updated_at": now_iso()}], on_conflict="user_id",
              returning=False)
    return {"ok": True}


# ---- 관리자 ----------------------------------------------------------------------

def require_admin(p: dict) -> None:
    if not is_admin(p):
        raise ApiError(403, "관리자만 볼 수 있어요.")


def admin_summary(p: dict) -> dict:
    require_admin(p)
    since = today_start_iso()
    return {
        "users": db.count("profiles", {}),
        "blocked": db.count("profiles", {"status": "eq.blocked"}),
        "pending": db.count("profiles", {"status": "eq.pending"}),
        "today_ai": db.count("activity_log", {"ai": "is.true", "at": f"gte.{since}"}),
        "today_counted": db.count("activity_log", {"counted": "is.true", "at": f"gte.{since}"}),
        "global_daily_ai": GLOBAL_DAILY_AI,
        "bank_active": db.count("questions", {"status": "eq.active"}),
        "bank_flagged": db.count("questions", {"status": "eq.flagged"}),
        "open_reports": db.count("question_reports", {"resolved": "is.false"}),
        "bank_min": BANK_MIN, "bank_ratio": BANK_RATIO,
        "daily": db.rpc("admin_daily", {"p_days": 14}) or [],
    }


def admin_users(p: dict) -> list:
    require_admin(p)
    return db.rpc("admin_users") or []


ROLE_FIELDS = {"role", "status", "can_practice", "can_explain", "daily_limit", "note"}


def admin_update_user(p: dict, body: dict) -> dict:
    require_admin(p)
    uid = str(body.get("id", ""))
    target = db.one("profiles", {"id": f"eq.{uid}", "select": "*"})
    if not target:
        raise ApiError(404, "사용자를 찾을 수 없어요.")
    if target["role"] == "owner":
        raise ApiError(403, "주인 계정은 바꿀 수 없어요.")
    if target["role"] == "admin" and p["role"] != "owner":
        raise ApiError(403, "다른 관리자는 주인만 바꿀 수 있어요.")
    fields = {k: body[k] for k in ROLE_FIELDS if k in body}
    if "role" in fields:
        if p["role"] != "owner":
            raise ApiError(403, "관리자 지정은 주인만 할 수 있어요.")
        if fields["role"] not in ("admin", "user"):
            raise ApiError(400, "역할 값이 올바르지 않아요.")
    if "status" in fields and fields["status"] not in ("active", "pending", "blocked"):
        raise ApiError(400, "상태 값이 올바르지 않아요.")
    for k in ("can_practice", "can_explain"):
        if k in fields:
            fields[k] = bool(fields[k])
    if "daily_limit" in fields:
        fields["daily_limit"] = max(0, min(int(fields["daily_limit"]), 1000))
    if "note" in fields:
        fields["note"] = str(fields["note"])[:300]
    if not fields:
        raise ApiError(400, "바꿀 항목이 없어요.")
    out = db.update("profiles", {"id": f"eq.{uid}"}, fields)
    log_activity(p, "admin", {"target": uid, "email": target["email"], "set": fields})
    return out[0] if out else {}


def admin_activity(p: dict, params: dict) -> list:
    require_admin(p)
    days = max(1, min(int(params.get("days") or 7), 90))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q = {"select": "id,action,detail,ai,device,at,user_id,profiles(email,name)", "at": f"gte.{since}",
         "order": "at.desc", "limit": str(max(1, min(int(params.get("limit") or 300), 1000)))}
    if re.fullmatch(r"[0-9a-f-]{36}", params.get("user") or ""):
        q["user_id"] = f"eq.{params['user']}"
    if re.fullmatch(r"[a-z]+", params.get("action") or ""):
        q["action"] = f"eq.{params['action']}"
    return db.select("activity_log", q)


def admin_questions(p: dict, params: dict) -> dict:
    require_admin(p)
    q = {"select": "id,sub,difficulty,qtype,question,choices,answer,explanation,option_notes,key_concept,cli_example,"
                   "tip,model,status,served,graded,correct,reports,created_at",
         "order": "reports.desc,created_at.desc", "limit": str(max(1, min(int(params.get("limit") or 100), 300)))}
    if params.get("status") in ("active", "flagged", "hidden"):
        q["status"] = f"eq.{params['status']}"
    if params.get("sub") in SUB_INDEX:
        q["sub"] = f"eq.{params['sub']}"
    if params.get("low") == "1":  # 정답률이 이상하게 낮은 문제(정답 키 오류 의심)
        q["graded"] = "gte.5"
        q["order"] = "correct.asc"
    rows = db.select("questions", q)
    ids = [r["id"] for r in rows if r["reports"]]
    reasons = db.select("question_reports", {"question_id": f"in.({','.join(ids)})", "resolved": "is.false",
                                             "select": "question_id,reason,at"}) if ids else []
    for r in rows:
        r["report_reasons"] = [x["reason"] for x in reasons if x["question_id"] == r["id"]]
    return {"questions": rows, "buckets": db.rpc("bank_buckets") or [], "bank_min": BANK_MIN}


Q_FIELDS = {"status", "question", "choices", "answer", "explanation", "option_notes", "key_concept", "cli_example", "tip"}


def admin_update_question(p: dict, body: dict) -> dict:
    require_admin(p)
    qid = str(body.get("id", ""))
    if not re.fullmatch(r"[0-9a-f-]{36}", qid):
        raise ApiError(400, "문제 id가 올바르지 않아요.")
    fields = {k: body[k] for k in Q_FIELDS if k in body}
    if "status" in fields and fields["status"] not in ("active", "flagged", "hidden"):
        raise ApiError(400, "상태 값이 올바르지 않아요.")
    if "answer" in fields:
        fields["answer"] = str(fields["answer"]).strip()
    if "question" in fields:
        fields["norm_hash"] = norm_hash(str(fields["question"]))
    if body.get("resolve"):  # 검토 완료: 미해결 신고를 닫고 다시 출제
        db.update("question_reports", {"question_id": f"eq.{qid}", "resolved": "is.false"}, {"resolved": True})
        fields["reports"] = 0
        fields.setdefault("status", "active")
    if not fields:
        raise ApiError(400, "바꿀 항목이 없어요.")
    fields["updated_at"] = now_iso()
    try:
        out = db.update("questions", {"id": f"eq.{qid}"}, fields)
    except db.DBError as e:
        if "23505" in str(e):
            raise ApiError(409, "같은 문제가 이미 저장소에 있어요.")
        raise
    log_activity(p, "admin", {"qid": qid, "set": sorted(k for k in fields if k != "updated_at")})
    return out[0] if out else {}
