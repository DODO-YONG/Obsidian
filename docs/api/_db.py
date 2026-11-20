"""Supabase 접근 (설치할 것 없음, 표준 라이브러리만).

- DB: PostgREST(/rest/v1)를 비밀 키(SUPABASE_SERVICE_ROLE_KEY)로 부른다. 이 키는 Vercel 환경변수에만 있다.
- 로그인 확인: 브라우저가 보낸 토큰으로 /auth/v1/user 를 물어 진짜 사용자인지 확인한다.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class DBError(Exception):
    pass


def _url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


def _svc() -> str:
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def anon_key() -> str:
    return os.environ.get("SUPABASE_ANON_KEY", "")


def configured() -> bool:
    return bool(_url() and _svc() and anon_key())


def _svc_headers() -> dict:
    k = _svc()
    h = {"apikey": k}
    if not k.startswith("sb_"):  # 예전 형식(JWT) 키는 Authorization 에도 넣는다. 새 형식(sb_secret_)은 apikey만.
        h["Authorization"] = "Bearer " + k
    return h


def _call(method: str, url: str, headers: dict, body=None, timeout: int = 10):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return dict(r.headers), (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raise DBError(f"HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise DBError(f"연결 문제 {e}") from None


def _q(params: dict | None) -> str:
    return ("?" + urllib.parse.urlencode(params, safe="(),.*:>=<!")) if params else ""


def select(table: str, params: dict | None = None) -> list:
    _, rows = _call("GET", f"{_url()}/rest/v1/{table}{_q(params)}", _svc_headers())
    return rows or []


def one(table: str, params: dict) -> dict | None:
    rows = select(table, {**params, "limit": "1"})
    return rows[0] if rows else None


def count(table: str, params: dict) -> int:
    h, _ = _call("GET", f"{_url()}/rest/v1/{table}{_q({**params, 'select': 'id', 'limit': '1'})}",
                 {**_svc_headers(), "Prefer": "count=exact"})
    rng = {k.lower(): v for k, v in h.items()}.get("content-range", "*/0")
    try:
        return int(rng.split("/")[-1])
    except ValueError:
        return 0


def insert(table: str, rows, on_conflict: str | None = None, ignore_dupes: bool = False, returning: bool = True):
    prefer = ["return=representation" if returning else "return=minimal"]
    if on_conflict:
        prefer.append("resolution=ignore-duplicates" if ignore_dupes else "resolution=merge-duplicates")
    params = {"on_conflict": on_conflict} if on_conflict else None
    _, out = _call("POST", f"{_url()}/rest/v1/{table}{_q(params)}",
                   {**_svc_headers(), "Prefer": ",".join(prefer)}, rows)
    return out


def update(table: str, params: dict, fields: dict) -> list:
    _, out = _call("PATCH", f"{_url()}/rest/v1/{table}{_q(params)}",
                   {**_svc_headers(), "Prefer": "return=representation"}, fields)
    return out or []


def rpc(name: str, args: dict | None = None):
    _, out = _call("POST", f"{_url()}/rest/v1/rpc/{name}", _svc_headers(), args or {})
    return out


def auth_user(token: str) -> dict | None:
    """브라우저가 보낸 로그인 토큰 → Supabase 사용자(id, email, user_metadata). 아니면 None."""
    if not token or not configured():
        return None
    try:
        _, u = _call("GET", f"{_url()}/auth/v1/user",
                     {"apikey": anon_key(), "Authorization": "Bearer " + token}, timeout=8)
    except DBError:
        return None
    return u if u and u.get("id") else None
