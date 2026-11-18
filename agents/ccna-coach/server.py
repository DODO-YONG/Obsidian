"""CCNA 코치 — 내 Mac에서 도는 '답변 서버' (http://127.0.0.1:8765).

화면은 GitHub Pages(https://dodo-yong.github.io/Obsidian/ccna/)에 공개돼 있고,
그 화면이 문제·해설이 필요할 때만 이 서버에 요청한다. 이 서버가 볼트 .env 의 키로 제미나이를 부른다.

- 키는 이 서버만 읽는다. 브라우저·GitHub로 보내지 않는다.
- 내 GitHub Pages 주소와 로컬 주소에서 온 요청만 받는다(다른 사이트가 내 무료 한도를 쓰지 못하게).
- 풀이 기록은 볼트의 private/ccna-coach/ 에만 저장(공개 저장소에서 제외된 곳인지 검사).
- 이 서버로 직접 들어와도(http://127.0.0.1:8765) 같은 화면을 볼 수 있다.

실행: python3 server.py   (끄기: Ctrl+C)
"""

import json
import random
import subprocess
import sys
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import gemini_client as gc

HOST, PORT = "127.0.0.1", 8765
BASE = Path(__file__).resolve().parent
VAULT = BASE.parents[1]
WEB = VAULT / "docs" / "ccna"                 # 공개 화면과 같은 파일
DATA_DIR = VAULT / "private" / "ccna-coach"
LOG = DATA_DIR / "기록.jsonl"
ALLOWED_ORIGINS = {
    "https://dodo-yong.github.io",
    f"http://{HOST}:{PORT}",
    f"http://localhost:{PORT}",
}

DOMAINS = json.loads((WEB / "topics.json").read_text(encoding="utf-8"))
SUB_INDEX = {s["id"]: (d, s["name"]) for d in DOMAINS for s in d["subs"]}

QUESTIONS: dict[str, dict] = {}  # 출제한 문제(정답 포함)는 서버 메모리에만
RECENT: list[str] = []            # 같은 문제 반복 방지용


def data_is_private() -> bool:
    r = subprocess.run(["git", "check-ignore", "-q", str(LOG)], cwd=BASE, capture_output=True)
    return r.returncode in (0, 128)


PRIVATE_OK = data_is_private()


def log(entry: dict) -> None:
    if not PRIVATE_OK:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry["ts"] = datetime.now().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


# ---- 제미나이 지시문 ---------------------------------------------------------

SYS_QUESTION = """당신은 Cisco CCNA 200-301 시험을 10년 넘게 가르친 강사입니다.
지정된 출제 범위에서 실제 시험과 비슷한 문제를 1개 만듭니다.

규칙
- 한국어로 쓰되, 명령어·프로토콜 이름·용어는 영어 원문을 그대로 씁니다 (예: show ip route, OSPF, native VLAN).
- 정답이 하나로 분명한 문제만 냅니다. 사실이 확실하지 않으면 다른 문제를 냅니다.
- 필요하면 짧은 show 출력이나 설정 일부를 문제에 넣습니다(줄바꿈 \\n 사용).
- 객관식이면 보기 4개, answer는 "A"~"D" 중 하나. 보기 문자열 앞에 A. 같은 기호는 붙이지 않습니다.
- 주관식이면 choices는 빈 배열, answer는 짧은 모범 답안.
- 최근에 낸 문제와 겹치지 않게 합니다."""

SYS_GRADE = """당신은 Cisco CCNA 200-301 강사입니다. 학생의 답을 보고 해설합니다.
- 한국어로, 명령어·용어는 영어 원문 유지. 쉽고 짧게.
- 정답 여부를 먼저 판단하고(주어진 판정이 있으면 그것을 따름), 왜 그런지 설명합니다.
- 틀렸으면 학생이 왜 그렇게 생각했을지 짚고 바로잡습니다.
- 관련 IOS 명령 예시가 도움이 되면 cli_example에 넣고, 아니면 빈 문자열.
- 확실하지 않은 내용은 단정하지 말고 "공식 문서로 확인"이라고 적습니다."""

Q_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "question": {"type": "STRING"},
        "choices": {"type": "ARRAY", "items": {"type": "STRING"}},
        "answer": {"type": "STRING"},
        "key_point": {"type": "STRING"},
    },
    "required": ["question", "choices", "answer"],
}
G_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "verdict": {"type": "STRING", "enum": ["정답", "부분 정답", "오답"]},
        "correct_answer": {"type": "STRING"},
        "explanation": {"type": "STRING"},
        "why_wrong": {"type": "STRING"},
        "key_concept": {"type": "STRING"},
        "cli_example": {"type": "STRING"},
        "tip": {"type": "STRING"},
    },
    "required": ["verdict", "correct_answer", "explanation", "key_concept"],
}


def new_question(sub_ids: list[str], difficulty: str, qtype: str) -> dict:
    subs = [s for s in sub_ids if s in SUB_INDEX] or list(SUB_INDEX)
    sid = random.choice(subs)
    domain, sub_name = SUB_INDEX[sid]
    kind = "객관식(보기 4개)" if qtype == "mcq" else "주관식(짧은 답)"
    recent = "\n".join(f"- {r}" for r in RECENT[-6:]) or "(없음)"
    prompt = (f"출제 범위: {domain['en']} / {sub_name}\n난이도: {difficulty}\n형식: {kind}\n"
              f"최근 낸 문제(겹치지 말 것):\n{recent}")
    data, model = gc.ask_json(SYS_QUESTION, prompt, Q_SCHEMA)
    choices = [str(c) for c in data.get("choices") or []][:4] if qtype == "mcq" else []
    if qtype == "mcq" and len(choices) != 4:
        raise gc.GeminiError("보기 4개짜리 문제를 받지 못했어요. 다시 받아 주세요.")
    qid = uuid.uuid4().hex[:12]
    q = {"id": qid, "question": str(data.get("question", "")).strip(), "choices": choices,
         "answer": str(data.get("answer", "")).strip(), "sub": sid, "sub_name": sub_name,
         "domain": domain["name"], "domain_id": domain["id"], "qtype": qtype,
         "difficulty": difficulty, "model": model}
    QUESTIONS[qid] = q
    RECENT.append(q["question"][:80])
    return {k: q[k] for k in ("id", "question", "choices", "sub", "sub_name", "domain", "domain_id",
                              "qtype", "difficulty", "model")}  # 정답은 보내지 않음


def grade_question(qid: str, user: str) -> dict:
    q = QUESTIONS.get(qid)
    if not q:
        raise gc.GeminiError("문제를 찾을 수 없어요(서버를 다시 켰다면 새 문제를 받아 주세요).")
    fixed = ""
    if q["qtype"] == "mcq":
        fixed = "정답" if user.strip().upper()[:1] == q["answer"].strip().upper()[:1] else "오답"
    choices = "\n".join(f"{'ABCD'[i]}. {c}" for i, c in enumerate(q["choices"]))
    prompt = (f"문제:\n{q['question']}\n\n보기:\n{choices or '(주관식)'}\n\n"
              f"정답: {q['answer']}\n학생의 답: {user}\n"
              f"{'판정(이미 확정): ' + fixed if fixed else '주관식이므로 의미가 맞으면 정답, 일부만 맞으면 부분 정답.'}")
    res, model = gc.ask_json(SYS_GRADE, prompt, G_SCHEMA)
    if fixed:
        res["verdict"] = fixed
        letter = q["answer"].strip().upper()[:1]
        if letter in "ABCD" and len(q["choices"]) == 4:
            res["correct_answer"] = f"{letter}. {q['choices']['ABCD'.index(letter)]}"
    res["model"] = model
    log({"mode": "practice", "domain_id": q["domain_id"], "sub": q["sub"], "qtype": q["qtype"],
         "difficulty": q["difficulty"], "verdict": res.get("verdict"), "question": q["question"],
         "user": user, "answer": q["answer"]})
    return res


def explain_custom(question: str, user: str, sub: str) -> dict:
    scope = f"{SUB_INDEX[sub][0]['en']} / {SUB_INDEX[sub][1]}" if sub in SUB_INDEX else "범위 지정 안 함"
    prompt = (f"(학생이 직접 가져온 문제입니다. 정답은 주어지지 않았으니 직접 판단하세요.)\n"
              f"범위: {scope}\n\n문제:\n{question}\n\n학생의 답: {user or '(답 없음 — 해설만 원함)'}")
    res, model = gc.ask_json(SYS_GRADE, prompt, G_SCHEMA)
    res["model"] = model
    log({"mode": "custom", "domain_id": SUB_INDEX[sub][0]["id"] if sub in SUB_INDEX else "",
         "sub": sub, "qtype": "custom", "verdict": res.get("verdict"), "question": question, "user": user})
    return res


def stats() -> dict:
    rows = [r for r in read_log() if r.get("verdict")]
    by_sub: dict[str, dict] = {}
    for r in rows:
        s = by_sub.setdefault(r.get("sub", ""), {"n": 0, "ok": 0})
        s["n"] += 1
        s["ok"] += 1 if r["verdict"] == "정답" else 0
    by_domain = []
    for d in DOMAINS:
        n = sum(by_sub.get(s["id"], {}).get("n", 0) for s in d["subs"])
        ok = sum(by_sub.get(s["id"], {}).get("ok", 0) for s in d["subs"])
        by_domain.append({"id": d["id"], "name": d["name"], "n": n, "ok": ok})
    weak = sorted(((s, v) for s, v in by_sub.items() if s in SUB_INDEX and v["n"] >= 2),
                  key=lambda kv: kv[1]["ok"] / kv[1]["n"])[:3]
    recent = [{"sub": r.get("sub"), "verdict": r["verdict"], "question": r.get("question", "")[:70]}
              for r in rows[-8:]][::-1]
    return {"total": len(rows), "ok": sum(1 for r in rows if r["verdict"] == "정답"),
            "by_domain": by_domain,
            "weak": [{"sub": s, "name": SUB_INDEX[s][1], "n": v["n"], "ok": v["ok"]} for s, v in weak],
            "recent": recent, "exam_date": gc._env("CCNA_EXAM_DATE"), "private_ok": PRIVATE_OK,
            "has_key": gc.has_key()}


# ---- HTTP ---------------------------------------------------------------------

STATIC = {"/": "index.html", "/index.html": "index.html", "/topics.json": "topics.json"}
CTYPE = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8"}


class Handler(BaseHTTPRequestHandler):
    server_version = "ccna-coach"

    def log_message(self, fmt, *args):  # 내용은 찍지 않고 요청 줄만
        sys.stderr.write(f"  {self.command} {self.path.split('?')[0]}\n")

    def _origin_ok(self) -> bool:
        o = self.headers.get("Origin")
        return o is None or o in ALLOWED_ORIGINS

    def _cors(self):
        o = self.headers.get("Origin")
        if o in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")  # 공개 사이트 → 내 컴퓨터 요청 허용(크롬)

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_OPTIONS(self):  # 브라우저의 사전 확인 요청
        if not self._origin_ok():
            self.send_response(403); self.end_headers(); return
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in STATIC:
            f = WEB / STATIC[path]
            return self._send(200, f.read_bytes(), CTYPE[f.suffix])
        if not self._origin_ok():
            return self._json(403, {"error": "허용되지 않은 사이트"})
        if path == "/api/health":
            self._json(200, {"ok": True, "has_key": gc.has_key(), "private_ok": PRIVATE_OK})
        elif path == "/api/stats":
            self._json(200, stats())
        else:
            self._json(404, {"error": "없는 주소"})

    def do_POST(self):
        if not self._origin_ok():
            return self._json(403, {"error": "허용되지 않은 사이트에서 온 요청이에요."})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "요청을 읽지 못했어요."})
        path = self.path.split("?")[0]
        try:
            if path == "/api/question":
                diff = body.get("difficulty") if body.get("difficulty") in ("쉬움", "보통", "어려움") else "보통"
                qtype = body.get("qtype") if body.get("qtype") in ("mcq", "short") else "mcq"
                self._json(200, new_question(list(body.get("subs") or []), diff, qtype))
            elif path == "/api/grade":
                user = str(body.get("answer", "")).strip()[:2000]
                if not user:
                    return self._json(400, {"error": "답을 입력해 주세요."})
                self._json(200, grade_question(str(body.get("id", "")), user))
            elif path == "/api/explain":
                q = str(body.get("question", "")).strip()[:4000]
                if not q:
                    return self._json(400, {"error": "문제를 입력해 주세요."})
                self._json(200, explain_custom(q, str(body.get("answer", "")).strip()[:2000], str(body.get("sub", ""))))
            elif path == "/api/log":  # 브라우저가 직접 채점한 서브넷 문제 기록
                v = body.get("verdict") if body.get("verdict") in ("정답", "오답") else None
                if v:
                    log({"mode": "practice", "domain_id": "1", "sub": "1.6", "qtype": "subnet",
                         "difficulty": str(body.get("difficulty", ""))[:10], "verdict": v,
                         "question": str(body.get("question", ""))[:300], "user": str(body.get("user", ""))[:100],
                         "answer": str(body.get("answer", ""))[:100]})
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "없는 주소"})
        except gc.GeminiError as e:
            self._json(502, {"error": f"제미나이 요청이 실패했어요. 잠시 뒤 다시 시도해 주세요. ({str(e)[:200]})"})


def main():
    print("🧠 CCNA 코치 답변 서버")
    print("   화면: https://dodo-yong.github.io/Obsidian/ccna/  (또는 http://127.0.0.1:8765)")
    print(f"   키: {'있음' if gc.has_key() else '없음 (.env 에 GOOGLE_API_KEY)'} · 모델: {', '.join(gc.models())}")
    print(f"   기록: {LOG if PRIVATE_OK else '⚠️ 비공개 폴더가 아니라 저장하지 않음'}")
    print("   끄기: Ctrl+C\n")
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
