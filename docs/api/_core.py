"""TRACER 서버 로직 (Vercel). 화면 요청 → 로그인·권한·한도 확인 → 문제 저장소/제미나이 → 기록.

문제 저장소
- 객관식: 문제은행(미리 채운 1,808문제 + 예전에 만든 문제)에서만 낸다 → 제미나이 0번, 하루 한도에 안 셈.
  안 받은 문제가 없으면 다른 범위를 더 보고, 그래도 없으면 이미 받은 문제를 다시 낸다.
  객관식 생성 코드(generate)는 남겨 두지만 화면 요청으로는 부르지 않는다.
- 주관식: 묶음(범위 × 난이도)에 BANK_MIN(기본 10)개 이상이면 BANK_RATIO(90%)는 저장된 문제에서,
  나머지는 제미나이로 새로 만들어 저장한다. 사용자가 이미 받은 문제는 다시 내지 않는다.
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
# 주관식(제미나이로 출제·판정)은 2026-11-22 사용자 결정으로 잠시 멈춤. 다시 켜려면 환경변수 TRACER_SHORT=1
SHORT_ON = os.environ.get("TRACER_SHORT") == "1"
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
    f = {"last_seen": now_iso()}
    if p.get("delete_at"):  # 삭제 예정이던 사용자가 다시 접속하면 예정을 취소한다
        f["delete_at"] = None
    db.update("profiles", {"id": f"eq.{p['id']}"}, f)
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


def _mcq_from_bank(p: dict, pool: list, difficulty: str):
    """객관식은 문제은행에서만 낸다(AI 0번). 고른 범위에 안 받은 문제가 없으면 다른 범위를 몇 개 더 보고,
    그래도 없으면 이미 받은 문제를 다시 낸다."""
    tries = random.sample(pool, min(len(pool), 6))
    for sid in tries:
        rows = db.rpc("pick_question", {"p_user": p["id"], "p_sub": sid, "p_diff": difficulty, "p_qtype": "mcq"}) or []
        if rows:
            return rows[0], sid, False
    for sid in tries:
        rows = db.select("questions", {"sub": f"eq.{sid}", "difficulty": f"eq.{difficulty}", "qtype": "eq.mcq",
                                       "status": "eq.active", "select": "*", "limit": "50"}) or []
        if rows:
            return random.choice(rows), sid, True
    return None, tries[0], False


def new_question(p: dict, subs: list, difficulty: str, qtype: str) -> dict:
    require_active(p)
    if not p["can_practice"]:
        raise ApiError(403, "AI 문제 권한이 꺼져 있어요. 서브넷 계산 문제는 계속 풀 수 있어요.", {"code": "no_perm"})
    difficulty = difficulty if difficulty in DIFFS else "보통"
    qtype = qtype if qtype in ("mcq", "short") else "mcq"
    if qtype == "short" and not SHORT_ON:
        raise ApiError(403, "주관식은 잠시 쉬고 있어요. 객관식이나 서브넷 계산을 풀어 주세요.", {"code": "short_off"})
    pool = [s for s in subs if s in SUB_INDEX] or list(SUB_INDEX)

    if qtype == "mcq":
        q, sid, repeat = _mcq_from_bank(p, pool, difficulty)
        if not q:
            raise ApiError(404, "이 범위·난이도의 객관식 문제가 아직 없어요. 다른 범위나 난이도를 골라 주세요.", {"code": "empty"})
        db.rpc("mark_served", {"p_user": p["id"], "p_qid": q["id"]})
        log_activity(p, "question", {"sub": sid, "difficulty": difficulty, "qtype": qtype, "source": "bank",
                                     "qid": q["id"], "repeat": repeat}, ai=False)
        return public_q(q, "bank")

    # 주관식: 문제은행이 충분하면 주로 거기서, 아니면 AI가 새로 만들어 저장
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
            raise ApiError(429, "오늘 쓸 수 있는 AI 문제를 모두 썼어요. 객관식은 한도 없이 계속 풀 수 있어요. (서브넷 계산도 계속 쓸 수 있어요)",
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

def _wrong_ids(p: dict) -> list:
    """다시 풀 틀린 문제: 문제은행 객관식 중 '가장 최근 결과'가 정답이 아닌 것(다시 풀어 맞히면 빠진다).
    숨김·신고로 출제가 멈춘 문제는 뺀다. 오래 전에 틀린 것부터."""
    rows = db.select("attempts", {"user_id": f"eq.{p['id']}", "qtype": "eq.mcq", "question_id": "not.is.null",
                                  "verdict": "not.is.null", "select": "question_id,verdict,at", "order": "at.desc",
                                  "limit": "3000"}) or []
    latest: dict[str, dict] = {}
    for r in rows:   # 최신순이라 처음 본 것이 그 문제의 마지막 결과
        latest.setdefault(r["question_id"], r)
    wrong = sorted((r for r in latest.values() if r["verdict"] != "정답"), key=lambda r: str(r.get("at") or ""))
    ids = [r["question_id"] for r in wrong]
    if not ids:
        return []
    active = set()
    for i in range(0, len(ids), 100):
        for q in db.select("questions", {"id": "in.(" + ",".join(ids[i:i + 100]) + ")", "status": "eq.active",
                                         "select": "id"}) or []:
            active.add(q["id"])
    return [i for i in ids if i in active]


def wrong_summary(p: dict) -> dict:
    return {"count": len(_wrong_ids(p))}


def retry_question(p: dict, exclude: list) -> dict:
    """틀린 문제 다시 풀기: 이번 세트에서 이미 낸 문제(exclude)는 빼고 하나를 낸다. AI 0번."""
    require_active(p)
    if not p["can_practice"]:
        raise ApiError(403, "문제 풀기 권한이 꺼져 있어요.", {"code": "no_perm"})
    skip = {str(x) for x in exclude}
    ids = [i for i in _wrong_ids(p) if i not in skip]
    if not ids:
        raise ApiError(404, "다시 풀 틀린 문제가 없어요.", {"code": "no_wrong"})
    q = db.one("questions", {"id": f"eq.{ids[0]}", "select": "*"})
    if not q:
        raise ApiError(404, "다시 풀 틀린 문제가 없어요.", {"code": "no_wrong"})
    log_activity(p, "question", {"sub": q["sub"], "difficulty": q["difficulty"], "qtype": "mcq", "source": "retry",
                                 "qid": q["id"]}, ai=False)
    out = public_q(q, "retry")
    out["left"] = len(ids)
    return out


def grade(p: dict, qid: str, user_answer: str, retry: bool = False) -> dict:
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
    if first or retry:   # 다시 풀기는 매번 기록(가장 최근 결과로 틀린 문제 목록이 바뀐다). 진도 통계에는 안 셈
        d = SUB_INDEX.get(q["sub"], ({"id": ""}, ""))[0]
        db.insert("attempts", [{"user_id": p["id"], "question_id": qid, "mode": "retry" if retry else "practice", "domain_id": d["id"],
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
    rows = db.select("attempts", {"user_id": f"eq.{p['id']}", "verdict": "not.is.null", "mode": "neq.retry",
                                  "select": "sub,verdict,question,difficulty,at", "order": "at.desc", "limit": "3000"})
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
    by_diff = [{"name": d, "n": sum(1 for r in rows if r.get("difficulty") == d),
                "ok": sum(1 for r in rows if r.get("difficulty") == d and r["verdict"] == "정답")} for d in DIFFS]
    return {"total": len(rows), "ok": sum(1 for r in rows if r["verdict"] == "정답"), "by_domain": by_domain,
            "by_diff": by_diff,
            "weak": [{"sub": s, "name": SUB_INDEX[s][1], "n": v["n"], "ok": v["ok"]} for s, v in weak],
            "recent": recent, "exam_date": os.environ.get("CCNA_EXAM_DATE") if p["role"] == "owner" else None,
            "has_key": gc.has_key()}


def history(p: dict, params: dict) -> dict:
    """마이페이지: 내 풀이 기록(최신순). only=wrong 이면 정답이 아닌 것만. 본인 기록만 본다."""
    try:
        offset = max(0, int(params.get("offset") or 0))
        limit = min(50, max(1, int(params.get("limit") or 20)))
    except ValueError:
        raise ApiError(400, "잘못된 요청이에요.")
    q = {"user_id": f"eq.{p['id']}", "verdict": "not.is.null", "order": "at.desc",
         "select": "at,mode,sub,qtype,difficulty,verdict,question,user_answer", "limit": str(limit + 1), "offset": str(offset)}
    if params.get("only") == "wrong":
        q["verdict"] = "neq.정답"
    rows = db.select("attempts", q) or []
    items = [{"at": r.get("at"), "mode": r.get("mode"), "sub": r.get("sub") or "",
              "sub_name": SUB_INDEX[r["sub"]][1] if r.get("sub") in SUB_INDEX else "",
              "qtype": r.get("qtype"), "difficulty": r.get("difficulty") or "", "verdict": r.get("verdict"),
              "question": (r.get("question") or "")[:300], "user_answer": (r.get("user_answer") or "")[:120]}
             for r in rows[:limit]]
    return {"items": items, "more": len(rows) > limit, "offset": offset}


def me(p: dict) -> dict:
    touch(p)
    prog = db.one("progress", {"user_id": f"eq.{p['id']}", "select": "data,updated_at"})
    return {"id": p["id"], "email": p["email"], "name": p["name"], "role": p["role"], "status": p["status"],
            "can_practice": p["can_practice"], "can_explain": p["can_explain"], "daily_limit": p["daily_limit"],
            "ai_left": min(ai_left(p), 9999), "progress": (prog or {}).get("data"), "admin": is_admin(p),
            "admin_ai": is_admin(p) and admin_ai_on()}


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


DASH_DAYS = (7, 14, 30, 90)


def admin_summary(p: dict, params: dict | None = None) -> dict:
    require_admin(p)
    since = today_start_iso()
    days = int((params or {}).get("days") or 14)
    days = days if days in DASH_DAYS else 14
    return {"days": days,
        "users": db.count("profiles", {}),
        "blocked": db.count("profiles", {"status": "eq.blocked"}),
        "pending": db.count("profiles", {"status": "eq.pending"}),
        "today_ai": db.count("activity_log", {"ai": "is.true", "at": f"gte.{since}"}),
        "today_counted": db.count("activity_log", {"counted": "is.true", "at": f"gte.{since}"}),
        "global_daily_ai": GLOBAL_DAILY_AI,
        "bank_active": db.count("questions", {"status": "eq.active"}),
        "bank_flagged": db.count("questions", {"status": "eq.flagged"}),
        "open_reports": db.count("question_reports", {"resolved": "is.false"}),
        "open_app_reports": _safe_count("app_reports", {"resolved": "is.false"}),
        "bank_min": BANK_MIN, "bank_ratio": BANK_RATIO,
        "daily": db.rpc("admin_daily", {"p_days": days}) or [],
    }


def _safe_count(table: str, params: dict) -> int:
    """표가 아직 없어도(SQL 적용 전) 대시보드가 깨지지 않게 0을 돌려준다."""
    try:
        return db.count(table, params)
    except db.DBError:
        return 0


# ── Tracer Route 앱(안드로이드) 익명 오류 신고 — 앱이 공개 키로 app_reports에 넣고, 관리자만 여기서 읽는다
APP_REASONS = {"answer", "both", "explanation", "typo", "other"}


def admin_app_reports(p: dict, params: dict) -> dict:
    require_admin(p)
    q = {"select": "id,app_qid,sub,question,reason,note,app_version,lang,resolved,at", "order": "at.desc",
         "limit": str(max(1, min(int(params.get("limit") or 200), 500)))}
    if params.get("open", "1") == "1":
        q["resolved"] = "is.false"
    days = int(params.get("days") or 0)
    if days > 0:  # 최근 N일만(0 = 기간 제한 없음)
        q["at"] = "gte." + (datetime.now(timezone.utc) - timedelta(days=min(days, 365))).isoformat()
    rows = db.select("app_reports", q)
    # 웹 문제은행(questions)에 같은 문제가 있으면 연결(문제 글 해시로) → 웹에서도 바로 고칠 수 있게
    hashes = sorted({norm_hash(r["question"]) for r in rows})
    found = db.select("questions", {"norm_hash": f"in.({','.join(hashes)})", "select": "id,norm_hash,status,answer"}) if hashes else []
    by = {f["norm_hash"]: f for f in found}
    same = {}
    for r in rows:
        same[r["app_qid"]] = same.get(r["app_qid"], 0) + (0 if r["resolved"] else 1)
    for r in rows:
        m = by.get(norm_hash(r["question"]))
        r["bank"] = {"id": m["id"], "status": m["status"], "answer": m["answer"]} if m else None
        r["open_same"] = same.get(r["app_qid"], 0)
    return {"reports": rows, "open": _safe_count("app_reports", {"resolved": "is.false"})}


def admin_update_app_report(p: dict, body: dict) -> dict:
    """처리 완료/다시 열기. all_same=true면 같은 문제의 미처리 신고를 한꺼번에."""
    require_admin(p)
    rid = int(body.get("id", 0))
    resolved = bool(body.get("resolved", True))
    row = db.one("app_reports", {"id": f"eq.{rid}", "select": "id,app_qid"})
    if not row:
        raise ApiError(404, "신고를 찾을 수 없어요.")
    where = {"app_qid": f"eq.{row['app_qid']}"} if body.get("all_same") else {"id": f"eq.{rid}"}
    out = db.update("app_reports", where, {"resolved": resolved})
    log_activity(p, "admin", {"app_report": rid, "resolved": resolved, "n": len(out)})
    return {"ok": True, "updated": len(out)}


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


# ── 실제 관리자 화면의 명령창·일괄 작업은 기본으로 꺼 둔다(모의 화면에서만 시험). 켜려면 Vercel 환경변수 TRACER_ADMIN_AI=1
def admin_ai_on() -> bool:
    return os.environ.get("TRACER_ADMIN_AI") == "1"


def require_admin_ai() -> None:
    if not admin_ai_on():
        raise ApiError(403, "실제 관리자 화면의 명령창·일괄 작업은 아직 꺼져 있어요(모의 관리자 화면에서 시험해 주세요).")


# ── 여러 사용자 한꺼번에(사용자 탭의 일괄 버튼). 한 명씩 같은 권한 검사를 거친다.
BULK_OPS = {"mark_delete", "unmark_delete", "approve"}


def admin_users_bulk(p: dict, body: dict) -> dict:
    """mark_delete: 삭제 예정 표시(실제로 지우지 않음) · unmark_delete: 예정 취소 · approve: 승인 대기 → 사용 중."""
    require_admin(p)
    require_admin_ai()
    op = str(body.get("op", ""))
    if op not in BULK_OPS:
        raise ApiError(400, "할 수 없는 작업이에요.")
    ids = [str(x) for x in (body.get("ids") or []) if re.fullmatch(r"[0-9a-zA-Z-]{1,36}", str(x))][:500]
    if not ids:
        raise ApiError(400, "대상 사용자가 없어요.")
    rows = db.select("profiles", {"id": f"in.({','.join(ids)})", "select": "*"})
    done, skipped = [], 0
    for t in rows:
        if t["id"] == p["id"] or t["role"] == "owner" or (t["role"] == "admin" and p["role"] != "owner"):
            skipped += 1
            continue
        if op == "approve":
            if t["status"] != "pending":
                skipped += 1
                continue
            fields = {"status": "active"}
        else:
            fields = {"delete_at": now_iso() if op == "mark_delete" else None}
        db.update("profiles", {"id": f"eq.{t['id']}"}, fields)
        done.append(t["id"])
    log_activity(p, "admin", {"bulk": op, "n": len(done)})
    return {"ok": True, "op": op, "updated": len(done), "skipped": skipped + len(ids) - len(rows), "ids": done}


# ── 관리자 명령창(웹 관리자 화면 전용): 말로 한 명령 → '정해진 명령 하나'로 바꾼다. 실행은 화면의 기존 필터·버튼이 한다.
#    자주 쓰는 표현은 화면(admin.html)의 규칙이 먼저 처리하고, 규칙으로 안 되는 말만 여기로 온다.
#    제미나이에는 관리자가 쓴 명령 문장만 보낸다(사용자 이름·이메일·DB 내용은 보내지 않음).
ANSWER_WHAT = ["users_total", "pending", "blocked", "delete_marked", "inactive", "visitors", "today_ai",
               "open_app_reports", "app_reports", "bank_flagged", "bank_active"]
ADMIN_COMMANDS = {
    "show_dashboard":       {"days": ("int", 1, 365, 14)},
    "show_todo":            {},
    "show_users":           {"status": ["", "active", "pending", "blocked", "delete"], "inactive_days": ("int", 0, 3650, 0),
                             "joined_days": ("int", 0, 365, 0),
                             "sort": ["last_desc", "last_asc", "created_desc", "created_asc", "attempts_desc", "ai_desc", "name_asc"]},
    "show_activity":        {"days": ("int", 1, 365, 7), "action": ["", "visit", "signup", "question", "grade", "subnet", "explain", "report", "admin"]},
    "show_bank":            {"status": ["flagged", "", "active", "hidden"], "low": [False, True], "q": "text",
                             "diff": ["", "easy", "medium", "hard"], "sort": ["reports_desc", "rate_asc", "served_desc", "created_desc"]},
    "show_app_reports":     {"open": ["1", "0"], "days": ("int", 0, 365, 0), "reason": ["", "answer", "both", "explanation", "typo", "other"],
                             "sort": ["at_desc", "at_asc", "same_desc"]},
    "answer":               {"what": ANSWER_WHAT, "days": ("int", 1, 3650, 7)},
    "mark_delete_inactive": {"inactive_days": ("int", 1, 3650, 365)},
    "unmark_delete_all":    {},
    "approve_all_pending":  {},
    "resolve_app_reports":  {"days": ("int", 0, 365, 0), "reason": ["", "answer", "both", "explanation", "typo", "other"]},
    "select_users":         {"op": ["approve", "block", "unblock", "mark_delete", "unmark_delete"],
                             "status": ["", "active", "pending", "blocked", "delete"], "inactive_days": ("int", 0, 3650, 0), "joined_days": ("int", 0, 365, 0)},
    "select_questions":     {"op": ["hide", "flag", "resolve"], "target": ["flagged", "low", "hidden", "active"]},
    "undo_last":            {"kind": ["", "approve", "block", "unblock", "mark_delete", "unmark_delete", "questions", "app_reports"], "no": "int"},
    "demo_add_users":       {"status": ["pending", "active", "blocked"], "n": [10, 5, 20, 50]},
    "compare_period":       {"days": ("int", 1, 365, 7)},
    "show_weak_topics":     {"days": ("int", 1, 365, 30)},
    "export_csv":           {"target": ["current", "users", "activity", "bank", "appr"]},
    "show_trace":           {"only_bad": [False, True]},
    "show_report":          {"days": ("int", 1, 365, 30), "download": [False, True]},  # 모의 화면 전용
    "rerun":                {"no": "int"},
    "sql_query":            {"sql": "sql", "title": "title", "target": ["other", "users", "questions", "app_reports", "activity"]},  # 모의 화면 전용
}
COMMAND_KIND = {"answer": "answer", "mark_delete_inactive": "act", "unmark_delete_all": "act", "approve_all_pending": "act",
                "resolve_app_reports": "act", "select_users": "act", "select_questions": "act", "undo_last": "act",
                "export_csv": "act", "demo_add_users": "act", "rerun": "act"}
ADMIN_ASK_SYS = """You turn a Korean admin's request for the TRACER web admin page into exactly ONE command from this fixed list.
You cannot do anything outside this list. Never invent commands or values. Day counts can be any number in range;
convert words to days ("오늘"=1, "며칠/일주일"=7, "열흘"=10, "2주"=14, "한 달"=30, "3달"=90, "반년"=180, "1년/일년"=365).

A) Open a tab with filters (when they say 보여줘/찾아줘/열어줘/목록/확인):
- show_todo {} — the "오늘 할 일" overview (things to check: pending approvals, open reports, stopped questions, deletion candidates).
- show_dashboard {days: 7|14|30|90} — daily visitors (사용자 수·접속자), AI calls, answers.
- show_users {status: ""|active|pending|blocked|delete, inactive_days: 0|30|90|180|365, joined_days: 0|1|7|30|90,
  sort: last_desc|last_asc|created_desc|created_asc|attempts_desc|ai_desc|name_asc} — user list. "delete" = users marked 삭제 예정.
  inactive_days = not visited for more than that many days. joined_days = signed up within that many days. ai_desc = most Gemini use today.
- show_activity {days: 1|7|30|90, action: ""|visit|signup|question|grade|subnet|explain|report|admin} — activity log.
- show_bank {status: flagged|""|active|hidden, low: bool, q: short topic keyword like "OSPF" or "", diff: ""|easy|medium|hard,
  sort: reports_desc|rate_asc|served_desc|created_desc} — question bank. flagged = stopped by reports. low = suspiciously low correct rate.
- show_app_reports {open: "1"|"0", days: 0|1|7|30|90, reason: ""|answer|both|explanation|typo|other, sort: at_desc|at_asc|same_desc}
  — anonymous error reports (신고). open "1" = unresolved only. same_desc = questions with many reports first.
B) Answer a question with a number only, without changing the screen (몇 명/몇 건/얼마나/있어?):
- answer {what, days} — what: users_total | pending | blocked | delete_marked | inactive (not visited for more than `days`) |
  visitors (visitors over the last `days`) | today_ai (Gemini calls today) | open_app_reports | app_reports (reports in last `days`) |
  bank_flagged | bank_active.
C) Change data (the page shows the targets and asks the admin to confirm first):
- mark_delete_inactive {inactive_days: 30|90|180|365} — "지워줘/삭제/정리" for users who haven't visited. Only marks them 삭제 예정.
- unmark_delete_all {} — cancel all 삭제 예정 marks.
- approve_all_pending {} — approve every user waiting for approval.
- resolve_app_reports {days, reason} — mark unresolved reports as handled.
- select_users {op: approve|block|unblock|mark_delete|unmark_delete, status, inactive_days, joined_days} — select every user matching
  the filter and apply op (e.g. "차단된 사람 모두 해제" -> {op:"unblock", status:"blocked"}).
- select_questions {op: hide|flag|resolve, target: flagged|low|hidden|active} — e.g. "출제 중지 문제 다 숨겨" -> {op:"hide", target:"flagged"},
  "정답률 낮은 문제 출제 중지" -> {op:"flag", target:"low"}.
- undo_last {kind: ""|approve|block|unblock|mark_delete|unmark_delete|questions|app_reports} — undo the most recent change,
  or the most recent one of that kind ("방금 거 되돌려" -> "", "승인한 거 되돌려" -> approve), or command-log entry number no ("3번 되돌려" -> no:3).
- demo_add_users {status: pending|active|blocked, n} — mock page only: create fake users ("승인 대기 더미 10명 넣어줘").
- compare_period {days} — compare the last `days` with the period before ("지난주랑 비교", "저번 달보다 늘었어?").
- show_weak_topics {days} — accuracy by exam topic, weakest first ("약한 범위", "범위별 정답률").
- rerun {no} — run command-log entry number `no` again ("3번 다시 실행해줘").
- show_trace {only_bad: bool} — the command log of this page ("명령 기록", "못 알아들은 명령").
- show_report {days, download: bool} — summary report of user activity + admin command log ("보고서", "리포트", "활동 요약").
  download true when they want the report as a file ("받아줘", "다운로드", "파일로").
- export_csv {target: current|users|activity|bank|appr} — download the current filtered list as CSV ("엑셀로 받아줘").
D) none — anything else: a specific person, editing or deleting questions, settings, the Android app, general chat.

Examples:
"최근 며칠 사용자 수 보여줘" -> show_dashboard {days:7}
"한 달 동안 접속 안 한 사람 몇 명이야?" -> answer {what:"inactive", days:30}
"오래 안 들어온 사람들 정리해줘" -> mark_delete_inactive {inactive_days:365}, confidence 0.6
"신고 들어온 거 있어?" -> answer {what:"open_app_reports"}
"정답 이상한 문제" -> show_bank {low:true}
"김철수 차단해줘" -> none

Return JSON: {"command": "...", "args": {...}, "confidence": 0..1 (how sure you are this is what they meant),
"reply": "one short Korean sentence: what you understood"}."""
ADMIN_ASK_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "enum": list(ADMIN_COMMANDS) + ["none"]},
        "args": {"type": "object", "properties": {
            "days": {"type": "integer"}, "inactive_days": {"type": "integer"}, "status": {"type": "string"},
            "action": {"type": "string"}, "open": {"type": "string"}, "low": {"type": "boolean"}, "what": {"type": "string"}}},
        "confidence": {"type": "number"},
        "reply": {"type": "string"},
    },
    "required": ["command", "confidence", "reply"],
}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


def _closest(v, allowed: list):
    if v in allowed:
        return v
    nums = [a for a in allowed if isinstance(a, int) and not isinstance(a, bool)]
    if nums and isinstance(v, (int, float)) and not isinstance(v, bool):
        return min(nums, key=lambda a: abs(a - v))
    return allowed[0]


def clean_command(out: dict) -> dict:
    """제미나이 답을 허용 목록 안으로 맞춘다. 목록 밖이면 none. 확신이 낮으면 unsure(화면이 실행 전에 물어본다)."""
    cmd = str(out.get("command", "none"))
    try:
        conf = max(0.0, min(float(out.get("confidence", 0.5)), 1.0))
    except (TypeError, ValueError):
        conf = 0.5
    reply = str(out.get("reply") or "")[:200]
    if cmd not in ADMIN_COMMANDS:
        return {"command": "none", "kind": "none", "args": {}, "reply": reply or "이 화면에서 할 수 없는 일이에요.",
                "confidence": conf, "unsure": False}
    raw = out.get("args") if isinstance(out.get("args"), dict) else {}
    args = {}
    for k, allowed in ADMIN_COMMANDS[cmd].items():
        if allowed == "int" or isinstance(allowed, tuple):  # 숫자 범위(기간 등). "int" = 0~100000(명령 기록 번호)
            lo, hi, dflt = (0, 100000, 0) if allowed == "int" else allowed[1:]
            try:
                args[k] = max(lo, min(int(raw.get(k) if raw.get(k) is not None else dflt), hi))
            except (TypeError, ValueError):
                args[k] = dflt
        elif allowed == "sql":
            args[k] = str(raw.get(k) or "").strip()[:2000]
        elif allowed == "title":
            args[k] = re.sub(r"[\x00-\x1f<>]", "", str(raw.get(k) or ""))[:60].strip()
        elif allowed == "text":  # 짧은 주제어만(글자·숫자·공백·.-), 사람 이름 같은 건 화면이 거르지 않지만 30자로 제한
            args[k] = re.sub(r"[^\w .\-]", "", str(raw.get(k) or ""))[:30].strip()
        else:
            args[k] = _closest(raw.get(k, allowed[0]), allowed)
    if cmd == "sql_query":  # 읽기 전용 SELECT 하나만. 아니면 실행하지 않는다
        why = sql_problem(args["sql"])
        if why:
            return {"command": "none", "kind": "none", "args": {}, "reply": "조회 SQL을 만들지 못했어요(" + why + ").", "confidence": conf, "unsure": False}
        return {"command": cmd, "kind": "show", "args": args, "reply": reply, "confidence": conf, "unsure": False}  # 읽기만 하므로 확인 없이
    return {"command": cmd, "kind": COMMAND_KIND.get(cmd, "show"), "args": args, "reply": reply,
            "confidence": conf, "unsure": conf < 0.7}


_SQL_BAD = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex|begin|commit|rollback|savepoint|release|analyze|load_extension)\b", re.I)


def sql_problem(sql: str) -> str:
    """읽기 전용 SELECT(또는 WITH … SELECT) 한 문장인지 검사. 문제가 있으면 이유, 없으면 빈 문자열."""
    q = re.sub(r"--[^\n]*|/\*.*?\*/", " ", str(sql or ""), flags=re.S).strip().rstrip(";").strip()
    if not q:
        return "빈 SQL"
    if ";" in q:
        return "여러 문장"
    if not re.match(r"(?is)^(select|with)\b", q):
        return "SELECT가 아님"
    if _SQL_BAD.search(q):
        return "읽기 전용이 아님"
    return ""


# 모의 화면 전용: 조회는 SQL로(브라우저 안 SQLite에서 실행). 제미나이에는 표 구조와 명령 문장만 보낸다(데이터는 안 보냄).
DEMO_SQL_SECTION = """E) sql_query {sql, title, target} — for ANY find / list / count / "who" / "which" question (보여줘, 찾아줘, 몇 명, 누구, 어떤),
  write ONE read-only SQLite SELECT (or WITH ... SELECT). Prefer this over show_* / answer for lookups, especially with names,
  combinations, thresholds or joins. title = short Korean title of the result. target = the table whose rows (with an `id` column) are
  returned: users | questions | app_reports | activity | other. Always include `id` when returning rows of users/questions/app_reports.
  Never write INSERT/UPDATE/DELETE/DDL. Changes are done only by the commands in C).
  Tables (mock data; timestamps are UTC text 'YYYY-MM-DD HH:MM:SS'; compare with datetime('now','-10 days'); booleans are 0/1):
  users(id, name, email, role[owner|admin|user], status[active|pending|blocked], created_at, last_seen NULL=never,
        delete_at NULL=not marked, daily_limit, can_practice, can_explain, today_ai, total_attempts, note)
  questions(id, sub e.g. '3.4', difficulty[easy|medium|hard], status[active|flagged|hidden], question, answer,
            served, graded, correct, correct_rate percent or NULL, reports, created_at)
  app_reports(id, app_qid, sub, question, reason[answer|both|explanation|typo|other], note, app_version, lang[ko|en], resolved, at)
  activity(id, user_id -> users.id, action[visit|signup|question|grade|subnet|explain|report|admin], at, ai, device,
           sub, verdict['정답'|'오답'] for grade, source[bank|new] for question, difficulty)
  Names are Korean like '최민준' or English like 'Alex Kim'. "최로 시작" -> name LIKE '최%'. Limit big lists with ORDER BY.
"""
DEMO_ASK_SYS = ADMIN_ASK_SYS.replace("D) none —", DEMO_SQL_SECTION + "D) none —").replace(
    '"김철수 차단해줘" -> none', '"최로 시작하는 사용자 보여줘" -> sql_query {sql:"SELECT id, name, email, last_seen FROM users WHERE name LIKE \'최%\' ORDER BY name", title:"최로 시작하는 사용자", target:"users"}\n'
    '"지난달 가입했는데 문제 안 푼 사람" -> sql_query {sql:"SELECT id, name, email, created_at FROM users WHERE created_at >= datetime(\'now\',\'-30 days\') AND total_attempts = 0", ...}\n'
    '"김철수 차단해줘" -> none')
DEMO_ASK_SCHEMA = json.loads(json.dumps(ADMIN_ASK_SCHEMA))
DEMO_ASK_SCHEMA["properties"]["args"]["properties"].update({"sql": {"type": "string"}, "title": {"type": "string"}, "target": {"type": "string"}})


def _interpret(text: str, demo: bool = False) -> dict:
    text = _EMAIL.sub("(이메일)", str(text).strip()[:300])  # 혹시 적은 이메일은 제미나이로 보내지 않는다
    if not text:
        raise ApiError(400, "명령을 입력해 주세요.")
    out, _model = gc.ask_json(DEMO_ASK_SYS if demo else ADMIN_ASK_SYS, text, DEMO_ASK_SCHEMA if demo else ADMIN_ASK_SCHEMA, temperature=0.1)
    res = clean_command(out if isinstance(out, dict) else {})
    if res["command"] == "sql_query" and not demo:  # 실제 화면은 SQL 조회를 쓰지 않는다
        res = {"command": "none", "kind": "none", "args": {}, "reply": "SQL 조회는 모의 화면에서만 돼요.", "confidence": res["confidence"], "unsure": False}
    return {**res, "source": "ai"}


def admin_ask(p: dict, body: dict) -> dict:
    require_admin(p)
    require_admin_ai()
    if p["role"] != "owner" and ai_left(p) <= 0:
        raise ApiError(429, "오늘 AI 사용 한도를 다 썼어요.")
    res = _interpret(body.get("prompt", ""))
    log_activity(p, "admin", {"ask": res["command"]}, ai=True)  # 명령 문장 자체는 기록하지 않는다
    return res


DEMO_DAILY_AI = int(os.environ.get("TRACER_DEMO_DAILY_AI", "100"))  # 모의 화면은 제미나이 우선이라 넉넉히(사이트 전체 하루)


def demo_ask(body: dict) -> dict:
    """모의 관리자 화면(로그인 없음)용. 명령 해석만 하고 DB는 건드리지 않는다. 하루 전체 횟수 제한."""
    used = db.count("activity_log", {"action": "eq.demo", "at": f"gte.{today_start_iso()}"})
    if used >= DEMO_DAILY_AI:
        raise ApiError(429, "오늘 모의 화면의 AI 사용 횟수를 다 썼어요.")
    res = _interpret(body.get("prompt", ""), demo=True)
    log_activity(None, "demo", {"ask": res["command"]}, ai=True)
    return res
