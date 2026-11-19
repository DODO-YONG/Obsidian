"""Heartline 답변 서버 — 파이썬 표준 라이브러리만 쓴다(설치할 것 없음).

공개 화면(docs/heartline/)이 메시지를 보내면, 안전 검사 → 지시 조립 → 제미나이 무료 등급 → 스트리밍으로 돌려준다.
- 대화 본문은 파일·로그에 남기지 않는다(요청 줄과 오류 종류만).
- 허용한 화면 주소(Origin)에서 온 요청만 받는다. 터널(CF-Connecting-IP)로 온 요청은 '손님' → 사용량 제한.
- 💸 유료 과금 키가 환경에 있으면 실행을 거부한다.
실행: python3 server.py  (공개: ./start-public.sh)
"""
import json
import os
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import gemini_client as gc
import prompts
import safety

HERE = Path(__file__).resolve().parent
WEB_DIR = Path(os.environ.get("HEARTLINE_WEB_DIR") or HERE.parents[2] / "docs" / "heartline")
PAID_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
MAX_BODY = 32 * 1024
MAX_RECENT = 20
LOCAL_ORIGINS = ["http://localhost:8790", "http://127.0.0.1:8790"]
SOFT_FALLBACK = "음… 그 얘기는 내가 조심스럽게 답하고 싶어.\n\n다른 이야기도 편하게 해 줘."
CTYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
          ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}


def refuse_paid_billing(environ=None):
    environ = os.environ if environ is None else environ
    found = [k for k in PAID_KEYS if environ.get(k)]
    if found:
        raise SystemExit(f"💸 유료 과금 키({', '.join(found)})가 설정돼 있어 실행하지 않습니다. 키를 지우고 다시 실행하세요.")


class Limiter:
    def __init__(self, per_hour, per_day):
        self.per_hour, self.per_day = per_hour, per_day
        self.hits = defaultdict(deque)
        self.day = deque()
        self.lock = threading.Lock()

    def allow(self, who):
        now = time.time()
        with self.lock:
            q = self.hits[who]
            while q and now - q[0] > 3600:
                q.popleft()
            while self.day and now - self.day[0] > 86400:
                self.day.popleft()
            if len(q) >= self.per_hour or len(self.day) >= self.per_day:
                return False
            q.append(now)
            self.day.append(now)
            return True

    def remaining(self, who):
        now = time.time()
        with self.lock:
            used = sum(1 for t in self.hits.get(who, ()) if now - t <= 3600)
            return max(0, self.per_hour - used)


class Handler(BaseHTTPRequestHandler):
    server_version = "Heartline/1"

    def log_message(self, fmt, *args):  # 본문은 절대 찍지 않는다
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} {self.command} {self.path.split('?')[0]}\n")

    # ── 출처·손님 ──
    def origin(self):
        return self.headers.get("Origin")

    def self_origin(self):
        return f"http://{self.headers.get('Host', '')}"

    def origin_ok(self):
        o = self.origin()
        return o is None or o in self.server.allowed_origins or o == self.self_origin()

    def guest_id(self):
        return self.headers.get("CF-Connecting-IP") or (
            None if self.client_address[0] in ("127.0.0.1", "::1") else self.client_address[0])

    def cors(self):
        o = self.origin()
        if o and (o in self.server.allowed_origins or o == self.self_origin()):
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204 if self.origin_ok() else 403)
        self.cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            g = self.guest_id()
            return self.send_json(200, {"ok": True, "ai": self.server.llm is not None,
                                        "remaining": self.server.limiter.remaining(g) if g else None})
        self.serve_static(path)

    def serve_static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        f = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in f.parents or not f.is_file():
            return self.send_json(404, {"error": "not found"})
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CTYPES.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # ── POST ──
    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def guard(self, body):
        """문제가 있으면 (코드, 내용)을, 괜찮으면 None을."""
        if not isinstance(body, dict):
            return 400, {"error": "bad_request", "message": "요청 형식이 올바르지 않아요"}
        ok, err = safety.validate_persona(body.get("persona"))
        if not ok:
            return 400, {"error": "persona", "message": err}
        g = self.guest_id()
        if g and not self.server.limiter.allow(g):
            return 429, {"error": "limit", "message": "오늘은 많이 이야기했어요. 조금 쉬고 다시 만나요."}
        if self.server.llm is None:
            return 503, {"error": "no_ai", "message": "AI 키가 설정되지 않았어요"}
        return None

    def do_POST(self):
        path = self.path.split("?")[0]
        if not self.origin_ok():
            return self.send_json(403, {"error": "origin"})
        body = self.read_body()
        if path == "/api/chat":
            if isinstance(body, dict):
                ok, err = safety.check_message(body.get("message"))
                if not ok:
                    return self.send_json(400, {"error": "message", "message": err})
            bad = self.guard(body)
            return self.send_json(*bad) if bad else self.chat(body)
        if path == "/api/summarize":
            bad = self.guard(body)
            return self.send_json(*bad) if bad else self.summarize(body)
        self.send_json(404, {"error": "not found"})

    def clean_recent(self, body):
        out = []
        for m in (body.get("recent") or [])[-MAX_RECENT:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                out.append({"role": m["role"], "content": safety.mask_pii(m["content"][:safety.MAX_MESSAGE_LEN])})
        return out

    def sse(self, event, data):
        self.wfile.write(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()

    def chat(self, body):
        message = safety.mask_pii(body["message"])
        local_risk = safety.detect_risk(body["message"])
        mode = body.get("mode") if body.get("mode") in prompts.MODES else "heart"
        if local_risk != "none":
            mode = "heart"  # 위기 신호면 영어 모드보다 마음이 먼저
        system = prompts.build_system_prompt(body["persona"], mode, body.get("settings") or {},
                                             safety.mask_pii(str(body.get("summary") or ""))[:2000])
        messages = self.clean_recent(body) + [{"role": "user", "content": message}]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.cors()
        self.end_headers()
        if local_risk != "none":
            self.sse("risk", {"level": local_risk, "source": "keyword"})

        raw, sent = "", 0
        try:
            for piece in self.server.llm.stream(system, messages):
                raw += piece
                vis = prompts.visible_prefix(raw)
                if len(vis) > sent:
                    self.sse("token", {"text": vis[sent:]})
                    sent = len(vis)
        except gc.AllModelsBusy:
            return self.sse("error", {"error": "busy", "message": "지금 답하기 어려워요. 잠시 뒤에 다시 말 걸어 줘."})
        except Exception as e:  # 본문은 남기지 않고 종류만
            sys.stderr.write(f"  AI 오류: {type(e).__name__}\n")
            return self.sse("error", {"error": "ai", "message": "지금 답하기 어려워요. 잠시 뒤에 다시 말 걸어 줘."})

        r = prompts.parse_reply(raw)
        if not r["bubbles"]:
            r["bubbles"] = prompts.parse_reply(SOFT_FALLBACK)["bubbles"]
        if r["corrections"] and mode == "english":
            self.sse("correction", {"items": r["corrections"]})
        order = {"none": 0, "low": 1, "high": 2}
        level = max(local_risk, r["risk"], key=order.get)
        self.sse("risk", {"level": level, "source": "combined"})
        self.sse("done", {"bubbles": r["bubbles"]})

    def summarize(self, body):
        recent = self.clean_recent(body)
        prev = safety.mask_pii(str(body.get("summary") or ""))[:2000]
        convo = "\n".join(("나: " if m["role"] == "user" else "상대: ") + m["content"] for m in recent)
        try:
            text = self.server.llm.complete(prompts.SUMMARY_PROMPT,
                                            [{"role": "user", "content": f"이전 기억:\n{prev or '(없음)'}\n\n최근 대화:\n{convo}"}])
        except Exception as e:
            sys.stderr.write(f"  요약 오류: {type(e).__name__}\n")
            return self.send_json(503, {"error": "ai"})
        clean = prompts.parse_reply(text)
        self.send_json(200, {"summary": safety.mask_pii("\n".join(clean["bubbles"]))[:1500]})


def make_server(host, port, llm, allowed_origins, guest_per_hour=30, daily_limit=300):
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    srv.llm = llm
    srv.allowed_origins = set(allowed_origins or []) | set(LOCAL_ORIGINS)
    srv.limiter = Limiter(guest_per_hour, daily_limit)
    return srv


def main():
    refuse_paid_billing()
    port = int(gc.env("HEARTLINE_PORT", "8766"))
    origins = [o.strip() for o in (gc.env("HEARTLINE_ORIGINS") or "").split(",") if o.strip()]
    llm = gc.from_env()
    srv = make_server("127.0.0.1", port, llm, origins,
                      int(gc.env("HEARTLINE_GUEST_PER_HOUR", "30")), int(gc.env("HEARTLINE_DAILY_LIMIT", "300")))
    print(f"💗 Heartline 답변 서버: http://127.0.0.1:{port}")
    print(f"   AI 키: {'있음' if llm else '없음 (.env 에 GOOGLE_API_KEY)'} · 허용 화면: {', '.join(sorted(srv.allowed_origins))}")
    print("   대화 본문은 저장·기록하지 않아요. 끄기: Ctrl+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
