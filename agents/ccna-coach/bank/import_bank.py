"""TRACER 문제은행 미리 채우기 — bank/questions/*.json 을 Supabase questions 표에 넣는다.

- 문제는 이 저장소에서 Claude가 직접 쓴 객관식(보기 4개). 파일 하나 = 범위(sub) 하나.
- 볼트 루트 .env 의 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 를 읽는다(값은 저장소에 쓰지 않음).
- 똑같은 문제(norm_hash)는 건너뛴다. 여러 번 돌려도 안전하다.
- 넣을 때 보기 순서를 문제마다 정해진 방식(norm_hash 씨앗)으로 섞어 정답 위치가 고르게 퍼지게 한다.

  python3 agents/ccna-coach/bank/import_bank.py --check   # 형식만 검사 (DB 안 건드림)
  python3 agents/ccna-coach/bank/import_bank.py           # 검사 후 DB에 넣기
  python3 agents/ccna-coach/bank/import_bank.py --skip 4.8,4.9   # 일부 범위 빼고
  python3 agents/ccna-coach/bank/import_bank.py --only 4.8,4.9   # 일부 범위만
"""
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parents[2]
sys.path.insert(0, str(VAULT / "docs" / "api"))

DIFFS = ("쉬움", "보통", "어려움")
FIELDS = ("question", "choices", "answer", "explanation", "option_notes", "key_concept", "cli_example", "tip")


def refuse_paid_billing() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY 가 설정돼 있어 실행하지 않아요(유료 과금 방지).")


def load_env() -> None:
    f = VAULT / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        m = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$", line)
        if m and m.group(2) and not os.environ.get(m.group(1)):
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def norm_hash(text: str) -> str:  # docs/api/_core.py 와 같아야 한다
    t = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return hashlib.sha1(t[:400].encode()).hexdigest()


def valid_subs() -> set:
    topics = json.loads((VAULT / "docs" / "ccna" / "topics.json").read_text())
    return {s["id"] for d in topics for s in d["subs"]}


def shuffle(row: dict) -> dict:
    """보기와 보기별 설명을 같은 순서로 섞고 정답 글자를 맞춘다(같은 문제는 늘 같은 결과)."""
    order = list(range(4))
    random.Random(row["norm_hash"]).shuffle(order)
    right = "ABCD".index(row["answer"])
    row["choices"] = [row["choices"][i] for i in order]
    row["option_notes"] = [row["option_notes"][i] for i in order]
    row["answer"] = "ABCD"[order.index(right)]
    return row


def _arg(name: str) -> set:
    if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv):
        return set(sys.argv[sys.argv.index(name) + 1].split(","))
    return set()


def load_rows() -> tuple[list, list]:
    subs, rows, errs, seen = valid_subs(), [], [], set()
    only, skip = _arg("--only"), _arg("--skip")
    for f in sorted((HERE / "questions").glob("*.json")):
        if (only and f.stem not in only) or f.stem in skip:
            continue
        for i, q in enumerate(json.loads(f.read_text())):
            where = f"{f.name}#{i + 1}"
            bad = [k for k in FIELDS if k not in q]
            if q.get("sub") not in subs or q.get("sub") != f.stem: bad.append("sub(파일 이름과 같아야 함)")
            if q.get("difficulty") not in DIFFS: bad.append("difficulty")
            if not isinstance(q.get("choices"), list) or len(q["choices"]) != 4: bad.append("choices(4)")
            if q.get("answer") not in ("A", "B", "C", "D"): bad.append("answer(A-D)")
            if not isinstance(q.get("option_notes"), list) or len(q["option_notes"]) != 4: bad.append("option_notes(4)")
            if not str(q.get("question", "")).strip() or not str(q.get("explanation", "")).strip(): bad.append("빈 문제/해설")
            if any(re.match(r"^[A-D][.)]\s", str(c)) for c in q.get("choices") or []): bad.append("보기 앞 A. 표시")
            h = norm_hash(str(q.get("question", "")))
            if h in seen: bad.append("같은 문제 중복")
            seen.add(h)
            if bad:
                errs.append(f"{where}: {', '.join(bad)}")
                continue
            row = {"sub": q["sub"], "difficulty": q["difficulty"], "qtype": "mcq",
                   **{k: (q[k].strip() if isinstance(q[k], str) else q[k]) for k in FIELDS},
                   "model": "claude-prefill", "norm_hash": h}
            rows.append(shuffle(row))
    return rows, errs


def main() -> None:
    refuse_paid_billing()
    rows, errs = load_rows()
    by = {}
    for r in rows:
        by[(r["sub"], r["difficulty"])] = by.get((r["sub"], r["difficulty"]), 0) + 1
    spread = {c: sum(r["answer"] == c for r in rows) for c in "ABCD"}
    print(f"문제 {len(rows)}개, 묶음 {len(by)}개, 정답 위치 {spread}" + (f", 오류 {len(errs)}개" if errs else ""))
    for e in errs:
        print("  ✗", e)
    if errs or "--check" in sys.argv:
        sys.exit(1 if errs else 0)

    load_env()
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")):
        sys.exit("볼트 루트 .env 에 SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 를 넣어 주세요.")
    import _db as db
    added = 0
    for i in range(0, len(rows), 100):
        out = db.insert("questions", rows[i:i + 100], on_conflict="norm_hash", ignore_dupes=True, returning=True)
        added += len(out or [])
    print(f"새로 넣음 {added}개, 이미 있어서 건너뜀 {len(rows) - added}개")


if __name__ == "__main__":
    main()
