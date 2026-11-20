"""예전 풀이 기록(private/ccna-coach/기록.jsonl, 내 Mac) → Supabase attempts 표로 한 번 옮기기.

준비: 새 TRACER 사이트에 주인 계정(TRACER_OWNER_EMAIL)으로 한 번 로그인해서 profiles 에 내 줄이 생긴 뒤 실행.
필요한 값(볼트 루트 .env, git 제외): SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TRACER_OWNER_EMAIL
실행: python3 agents/ccna-coach/migrate_private_log.py          (먼저 몇 건인지 보여 주고 물어본다)
같은 기록을 두 번 넣지 않도록, 이미 옮긴 시각(ts)과 같은 기록은 건너뛴다.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
LOG = VAULT / "private" / "ccna-coach" / "기록.jsonl"
sys.path.insert(0, str(VAULT / "docs" / "api"))


def load_env() -> None:
    env = VAULT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> None:
    load_env()
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY 가 있어 실행하지 않아요(유료 과금 방지).")
    os.environ.setdefault("SUPABASE_ANON_KEY", "unused")
    import _db as db  # noqa: E402

    email = (os.environ.get("TRACER_OWNER_EMAIL") or "").lower()
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY") and email):
        sys.exit(".env 에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TRACER_OWNER_EMAIL 을 넣어 주세요.")
    if not LOG.exists():
        sys.exit(f"옮길 기록이 없어요: {LOG}")
    me = db.one("profiles", {"email": f"eq.{email}", "select": "id,role"})
    if not me:
        sys.exit("주인 계정이 아직 없어요. 새 TRACER 사이트에 주인 이메일로 먼저 로그인해 주세요.")

    kst = timezone(timedelta(hours=9))
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("verdict"):
            continue
        at = datetime.fromisoformat(r["ts"]).replace(tzinfo=kst).isoformat() if r.get("ts") else None
        rows.append({"user_id": me["id"], "mode": r.get("mode") or "practice", "domain_id": r.get("domain_id"),
                     "sub": r.get("sub") or None, "qtype": r.get("qtype"), "difficulty": r.get("difficulty"),
                     "verdict": r["verdict"], "question": (r.get("question") or "")[:500],
                     "user_answer": (r.get("user") or "")[:500], **({"at": at} if at else {})})
    done = {x["at"][:19] for x in db.select("attempts", {"user_id": f"eq.{me['id']}", "select": "at", "limit": "10000"})}
    new = [r for r in rows if not r.get("at") or datetime.fromisoformat(r["at"]).astimezone(timezone.utc).isoformat()[:19] not in done]
    print(f"기록 {len(rows)}건 중 새로 옮길 것 {len(new)}건 → 계정 {email}")
    if not new or input("옮길까요? (y/N) ").strip().lower() != "y":
        return
    db.insert("attempts", new, returning=False)
    print("옮겼어요. 원본 파일은 그대로 둡니다.")


if __name__ == "__main__":
    main()
