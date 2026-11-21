"""TRACER API (Vercel 파이썬 함수 하나로 모든 /api/* 를 받는다 — vercel.json 의 rewrites 참고).

화면(같은 주소의 /ccna/)만 부른다. 다른 사이트에서 온 요청은 403.
로그인: 브라우저가 Supabase 구글 로그인으로 받은 토큰을 Authorization: Bearer 로 보낸다.
"""

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _core as core  # noqa: E402
import _db as db  # noqa: E402
import _gemini as gc  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 요청 내용은 로그에 남기지 않는다
        pass

    # ---- 공통
    def _route(self) -> tuple[str, dict]:
        u = urllib.parse.urlparse(self.path)
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        route = qs.pop("route", None) or u.path.removeprefix("/api/").removeprefix("/api")
        return route.strip("/"), qs

    def _origin_ok(self) -> bool:
        o = self.headers.get("Origin")
        if not o:
            return True
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or ""
        return urllib.parse.urlparse(o).netloc == host

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _token(self) -> str:
        a = self.headers.get("Authorization") or ""
        return a[7:] if a.startswith("Bearer ") else ""

    def _user(self, required: bool = True):
        return core.current_user(self._token(), self.headers.get("User-Agent", ""), required)

    def _run(self, fn) -> None:
        try:
            core.refuse_paid_billing()
            if not self._origin_ok():
                return self._json(403, {"error": "허용되지 않은 사이트에서 온 요청이에요."})
            self._json(200, fn())
        except core.ApiError as e:
            self._json(e.code, {"error": e.msg, **e.extra})
        except gc.GeminiError as e:
            self._json(502, {"error": f"제미나이 요청이 실패했어요. 잠시 뒤 다시 시도해 주세요. ({str(e)[:160]})"})
        except db.DBError as e:
            self._json(503, {"error": f"데이터베이스 요청이 실패했어요. 잠시 뒤 다시 시도해 주세요. ({str(e)[:160]})"})
        except (ValueError, TypeError, KeyError) as e:
            self._json(400, {"error": f"요청을 처리하지 못했어요. ({type(e).__name__})"})

    # ---- GET
    def do_GET(self):
        route, qs = self._route()

        def go():
            if route == "config":  # 공개해도 되는 값만(Supabase 주소·공개 키). 비밀 키는 절대 아님
                return {"supabase_url": os.environ.get("SUPABASE_URL", ""), "anon_key": db.anon_key(),
                        "ready": db.configured() and gc.has_key()}
            if route == "health":  # 무료 프로젝트 일시정지 방지용 깨우기도 겸한다(DB를 한 번 읽음)
                ok_db = False
                if db.configured():
                    try:
                        db.count("questions", {"status": "eq.active"})
                        ok_db = True
                    except db.DBError:
                        pass
                return {"ok": True, "db": ok_db, "has_key": gc.has_key()}
            p = self._user()
            if route == "me":
                return core.me(p)
            if route == "stats":
                return core.stats(p)
            if route == "history":
                return core.history(p, qs)
            if route == "wrong":
                return core.wrong_summary(p)
            if route == "admin/summary":
                return core.admin_summary(p)
            if route == "admin/users":
                return core.admin_users(p)
            if route == "admin/activity":
                return core.admin_activity(p, qs)
            if route == "admin/questions":
                return core.admin_questions(p, qs)
            if route == "admin/app-reports":
                return core.admin_app_reports(p, qs)
            raise core.ApiError(404, "없는 주소")

        self._run(go)

    # ---- POST
    def do_POST(self):
        route, _ = self._route()
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(min(n, 30000)) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "요청을 읽지 못했어요."})

        def go():
            p = self._user()
            if route == "question" and body.get("retry"):
                return core.retry_question(p, [str(x) for x in (body.get("exclude") or [])][:100])
            if route == "question":
                return core.new_question(p, list(body.get("subs") or [])[:60], str(body.get("difficulty", "")),
                                         str(body.get("qtype", "")))
            if route == "grade":
                ans = str(body.get("answer", "")).strip()[:2000]
                if not ans:
                    raise core.ApiError(400, "답을 입력해 주세요.")
                return core.grade(p, str(body.get("id", "")), ans, retry=bool(body.get("retry")))
            if route == "explain":
                q = str(body.get("question", "")).strip()[:4000]
                if not q:
                    raise core.ApiError(400, "문제를 입력해 주세요.")
                return core.explain_custom(p, q, str(body.get("answer", "")).strip()[:2000], str(body.get("sub", "")))
            if route == "log":
                core.log_subnet(p, body)
                return {"ok": True}
            if route == "progress":
                return core.save_progress(p, body.get("data"))
            if route == "report":
                return core.report(p, str(body.get("id", "")), str(body.get("reason", "")).strip())
            if route == "admin/user":
                return core.admin_update_user(p, body)
            if route == "admin/question":
                return core.admin_update_question(p, body)
            if route == "admin/app-report":
                return core.admin_update_app_report(p, body)
            raise core.ApiError(404, "없는 주소")

        self._run(go)
