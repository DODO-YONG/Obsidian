"""server.py — 답변 서버 API (가짜 AI로 실제 HTTP 요청을 보내 본다).

약속:
  make_server(host, port, llm, allowed_origins, guest_per_hour=30, daily_limit=300) -> HTTPServer
      port=0 이면 빈 포트를 쓴다. llm 은 stream(system, messages) 를 가진 객체.
  refuse_paid_billing(environ) -> 유료 과금 키(ANTHROPIC_API_KEY 등)가 있으면 SystemExit
  GET  /api/health -> 200 {"ok": true}
  POST /api/chat   -> text/event-stream. 이벤트: token {"text"} · correction {"items"} · risk {"level"} · done {"bubbles"} · error
      body: {"persona", "mode", "settings", "summary", "recent": [{"role","content"}], "message"}
  손님 구분: Cloudflare 터널을 거친 요청은 CF-Connecting-IP 헤더가 있음 → 손님(사용량 제한). 헤더가 없으면 운영자(로컬).
  사용량 초과 → 429 {"error": "limit"} · 허용 안 된 Origin → 403 · 미성년 페르소나·잘못된 메시지 → 400
"""
import contextlib
import io
import json
import threading
import unittest
import urllib.error
import urllib.request

from _helpers import ADULT_PERSONA, FakeLLM, need

ORIGIN = "https://dodo-yong.github.io"


def setUpModule():
    global server
    server = need("server")


def parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        ev, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip() or "{}")
        if ev:
            events.append((ev, data))
    return events


class ServerCase(unittest.TestCase):
    reply = '하루 종일 혼자였구나\n\n나한테는 편하게 말해도 돼<risk level="none"/>'
    guest_per_hour = 3

    def setUp(self):
        self.llm = FakeLLM(self.reply)
        self.srv = server.make_server("127.0.0.1", 0, llm=self.llm, allowed_origins=[ORIGIN],
                                      guest_per_hour=self.guest_per_hour, daily_limit=100)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def request(self, path, body=None, origin=ORIGIN, guest_ip=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                     method="POST" if data else "GET")
        req.add_header("Content-Type", "application/json")
        if origin:
            req.add_header("Origin", origin)
        if guest_ip:
            req.add_header("CF-Connecting-IP", guest_ip)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers, r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.headers, e.read().decode()

    def chat(self, message="오늘 아무랑도 말을 한마디도 안 했어", mode="heart", persona=None, **kw):
        body = {"persona": persona or dict(ADULT_PERSONA), "mode": mode, "settings": {},
                "summary": "", "recent": [], "message": message}
        return self.request("/api/chat", body, **kw)


class Basics(ServerCase):
    def test_health(self):
        status, _, text = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(text)["ok"])

    def test_chat_streams_tokens_then_done(self):
        status, headers, text = self.chat()
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", headers.get("Content-Type", ""))
        events = parse_sse(text)
        kinds = [e[0] for e in events]
        self.assertIn("token", kinds)
        self.assertEqual(kinds[-1], "done")
        self.assertEqual(events[-1][1]["bubbles"], ["하루 종일 혼자였구나", "나한테는 편하게 말해도 돼"])

    def test_tags_never_reach_the_screen(self):
        _, _, text = self.chat()
        shown = "".join(d["text"] for e, d in parse_sse(text) if e == "token")
        self.assertNotIn("<risk", shown)

    def test_system_prompt_starts_with_safety(self):
        self.chat()
        self.assertTrue(self.llm.calls[-1]["system"].lstrip().startswith("### 안전 규칙"))


class EnglishCorrection(ServerCase):
    reply = ('Oh, that sounds peaceful!'
             '<correction>[{"original": "I go to park", "corrected": "I went to the park", "reason": "과거형"}]</correction>'
             '<risk level="none"/>')

    def test_correction_event(self):
        _, _, text = self.chat("I go to park alone yesterday.", mode="english")
        items = [d["items"] for e, d in parse_sse(text) if e == "correction"]
        self.assertTrue(items and items[0][0]["corrected"] == "I went to the park")
        shown = "".join(d["text"] for e, d in parse_sse(text) if e == "token")
        self.assertNotIn("<correction", shown)


class Safety(ServerCase):
    def test_crisis_message_sends_high_risk_even_if_ai_misses(self):
        _, _, text = self.chat("그냥 죽고 싶어")
        levels = [d["level"] for e, d in parse_sse(text) if e == "risk"]
        self.assertIn("high", levels)

    def test_pii_is_masked_before_ai(self):
        self.chat("내 번호 010-1234-5678 이야")
        self.assertNotIn("010-1234-5678", self.llm.last_text)

    def test_minor_persona_rejected(self):
        status, _, _ = self.chat(persona=dict(ADULT_PERSONA, ageGroup="teen"))
        self.assertEqual(status, 400)
        self.assertEqual(self.llm.calls, [])

    def test_too_long_message_rejected(self):
        self.assertEqual(self.chat("가" * 1001)[0], 400)

    def test_message_body_not_logged(self):
        secret = "아무에게도말하지않은비밀문장"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()) as out:
            self.chat(secret)
        self.assertNotIn(secret, err.getvalue() + out.getvalue())


class AccessControl(ServerCase):
    def test_other_origin_rejected(self):
        status, _, _ = self.chat(origin="https://evil.example.com")
        self.assertEqual(status, 403)
        self.assertEqual(self.llm.calls, [])

    def test_guest_rate_limit(self):
        codes = [self.chat(guest_ip="203.0.113.7")[0] for _ in range(self.guest_per_hour + 1)]
        self.assertEqual(codes[:-1], [200] * self.guest_per_hour)
        self.assertEqual(codes[-1], 429)

    def test_other_guest_has_own_limit(self):
        for _ in range(self.guest_per_hour):
            self.chat(guest_ip="203.0.113.7")
        self.assertEqual(self.chat(guest_ip="198.51.100.9")[0], 200)

    def test_local_operator_not_limited(self):
        codes = [self.chat()[0] for _ in range(self.guest_per_hour + 2)]
        self.assertEqual(set(codes), {200})


class Billing(unittest.TestCase):
    def test_refuses_when_paid_key_present(self):
        with self.assertRaises(SystemExit):
            server.refuse_paid_billing({"ANTHROPIC_API_KEY": "sk-test"})

    def test_ok_without_paid_key(self):
        server.refuse_paid_billing({"GOOGLE_API_KEY": "free-tier"})


if __name__ == "__main__":
    unittest.main()
