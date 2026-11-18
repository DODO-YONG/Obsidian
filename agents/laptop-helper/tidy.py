"""DY-006 SWEEPER 본체 기능 (AI 없이 동작하는 파이썬 코드).

1) 다운로드·데스크탑 정리 보고서    report_folder()
2) 흩어진 문서 찾기 → 위키 raw로 복사  find_documents() / copy_to_raw()
3) 폴더 정리: 종류별 하위 폴더로      plan_organize() / organize()
   + 휴지통 보내기                    trash()

쓰기 작업은 전부 safety.check_writable()을 통과해야 하고, 실행 전에 사람이 터미널에서 y를 입력해야 한다
(확인은 이 파일을 부르는 쪽 — main.py — 에서 한다). 지우기는 휴지통으로만.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import safety
from safety import HOME, VAULT, VAULT_RAW

CATEGORIES = {
    "문서":     {".pdf", ".doc", ".docx", ".hwp", ".hwpx", ".ppt", ".pptx", ".key", ".pages", ".txt", ".md", ".rtf", ".odt"},
    "표":       {".xls", ".xlsx", ".csv", ".numbers", ".tsv"},
    "이미지":   {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp", ".svg", ".bmp", ".tiff", ".psd"},
    "영상·음악": {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".mp3", ".m4a", ".wav", ".flac", ".aac"},
    "압축":     {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"},
    "설치파일": {".dmg", ".pkg", ".app", ".exe", ".msi", ".iso"},
    "Packet Tracer": {".pkt", ".pka", ".pksz"},
    "코드":     {".py", ".js", ".ts", ".html", ".css", ".json", ".ipynb", ".sh", ".java", ".c", ".cpp", ".go", ".rs", ".sql", ".yaml", ".yml"},
}
DOC_EXTS = CATEGORIES["문서"] | CATEGORIES["표"]
OLD_DAYS = 90
INSTALLER_OLD_DAYS = 30


def category(p: Path) -> str:
    if p.is_dir() and p.suffix.lower() != ".app":
        return "폴더"
    ext = p.suffix.lower()
    for name, exts in CATEGORIES.items():
        if ext in exts:
            return name
    return "기타"


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f}{u}" if u in ("B", "KB") else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}GB"


def _size(p: Path, limit_s: float = 3.0) -> int:
    """파일이면 크기, 폴더면 안의 합(너무 오래 걸리면 거기까지)."""
    try:
        if not p.is_dir() or p.is_symlink():
            return p.lstat().st_size
    except OSError:
        return 0
    total, t0 = 0, time.time()
    for root, dirs, files in os.walk(p, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if not safety.is_protected(Path(root) / d)]
        for f in files:
            try:
                total += (Path(root) / f).lstat().st_size
            except OSError:
                pass
        if time.time() - t0 > limit_s:
            break
    return total


def _age_days(p: Path) -> int:
    try:
        return int((time.time() - p.lstat().st_mtime) // 86400)
    except OSError:
        return 0


def _entries(folder: Path) -> tuple[list[Path], str | None]:
    why = safety.check_readable(folder)
    if why:
        return [], why
    try:
        items = [p for p in folder.iterdir() if not p.name.startswith(".") and not safety.is_protected(p)]
    except PermissionError:
        return [], (f"macOS가 {folder} 접근을 막았어요. 시스템 설정 > 개인정보 보호 및 보안 > "
                    "파일 및 폴더(또는 전체 디스크 접근)에서 터미널을 허용해 주세요.")
    except FileNotFoundError:
        return [], f"폴더가 없어요: {folder}"
    return sorted(items, key=lambda p: p.name.lower()), None


# ---- 1) 다운로드·데스크탑 정리 보고서 ----------------------------------------

def report_folder(folder: str | Path) -> dict:
    folder = safety.resolve(folder)
    items, err = _entries(folder)
    if err:
        return {"folder": str(folder), "error": err}
    rows = []
    for p in items:
        rows.append({"name": p.name, "path": str(p), "cat": category(p), "size": _size(p), "age": _age_days(p)})
    by_cat: dict[str, dict] = {}
    for r in rows:
        c = by_cat.setdefault(r["cat"], {"n": 0, "size": 0})
        c["n"] += 1
        c["size"] += r["size"]
    names = {r["name"] for r in rows}
    def why_trash(r: dict) -> str:
        if r["cat"] == "설치파일" and r["age"] >= INSTALLER_OLD_DAYS:
            return "설치 끝난 설치파일"
        if any(t in r["name"] for t in (" (1)", " (2)", " (3)", " 복사본")) or " copy" in r["name"].lower():
            return "중복 이름"
        if r["cat"] == "압축" and Path(r["name"]).stem in names:
            return "이미 압축 푼 폴더가 있음"
        return ""
    trash_cands = []
    for r in rows:
        w = why_trash(r)
        if w:
            trash_cands.append({**r, "why": w})
    old = sorted([r for r in rows if r["age"] >= OLD_DAYS], key=lambda r: -r["size"])
    big = sorted(rows, key=lambda r: -r["size"])[:10]
    return {"folder": str(folder), "total": len(rows), "size": sum(r["size"] for r in rows),
            "by_cat": dict(sorted(by_cat.items(), key=lambda kv: -kv[1]["size"])),
            "old": old, "big": big, "trash_candidates": trash_cands, "rows": rows}


def _tilde(p: str) -> str:
    return p.replace(str(HOME), "~", 1)


def format_report(rep: dict, limit: int = 10) -> str:
    if rep.get("error"):
        return f"## {rep['folder']}\n⚠️ {rep['error']}\n"
    out = [f"## {rep['folder']}", f"항목 {rep['total']}개 · {human(rep['size'])}", "", "| 종류 | 개수 | 용량 |", "|---|---|---|"]
    for c, v in rep["by_cat"].items():
        out.append(f"| {c} | {v['n']} | {human(v['size'])} |")
    if rep["trash_candidates"]:
        out += ["", f"**휴지통 후보** {len(rep['trash_candidates'])}개 (근거: 설치 끝난 지 {INSTALLER_OLD_DAYS}일 넘은 설치파일 · 중복 이름 · 이미 압축 푼 zip):"]
        out += [f"- {_tilde(r['path'])} · {human(r['size'])} · {r['why']}" for r in sorted(rep["trash_candidates"], key=lambda r: -r["size"])[:limit]]
    if rep["old"]:
        out += ["", f"**{OLD_DAYS}일 넘게 안 바뀐 것** {len(rep['old'])}개 (큰 순):"]
        out += [f"- {_tilde(r['path'])} · {human(r['size'])} · {r['age']}일 전" for r in rep["old"][:limit]]
    out += ["", "**가장 큰 것**:"] + [f"- {_tilde(r['path'])} · {human(r['size'])}" for r in rep["big"][:5]]
    return "\n".join(out) + "\n"


# ---- 2) 문서 모으기 -----------------------------------------------------------

DOC_SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "site-packages", ".Trash", "Library", "Applications"}


def find_documents(keyword: str = "", roots: list[str] | None = None, days: int | None = None, limit: int = 200,
                   time_limit: float = 20.0) -> dict:
    """홈 폴더(기본: 데스크탑·문서·다운로드)에서 문서·표 파일을 찾는다. 볼트 안은 이미 정리된 것이라 뺀다."""
    roots_p = [safety.resolve(r) for r in (roots or ["~/Desktop", "~/Documents", "~/Downloads"])]
    kw = keyword.strip().lower()
    found, denied, t0, partial = [], [], time.time(), False
    for root in roots_p:
        if safety.check_readable(root):
            denied.append(str(root))
            continue
        for dirpath, dirs, files in os.walk(root, onerror=lambda e: denied.append(getattr(e, "filename", "?"))):
            dp = Path(dirpath)
            dirs[:] = [d for d in dirs if d not in DOC_SKIP_DIRS and not d.startswith(".")
                       and not safety.is_protected(dp / d) and dp / d != VAULT]
            for f in files:
                p = dp / f
                if p.suffix.lower() not in DOC_EXTS or f.startswith((".", "~$")) or safety.is_protected(p):
                    continue
                if kw and kw not in f.lower() and kw not in dirpath.lower():
                    continue
                try:
                    st = p.stat()
                except OSError:
                    continue
                age = int((time.time() - st.st_mtime) // 86400)
                if days is not None and age > days:
                    continue
                found.append({"path": str(p), "name": f, "folder": str(dp).replace(str(HOME), "~", 1),
                              "size": st.st_size, "age": age, "date": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")})
            if time.time() - t0 > time_limit:
                partial = True
                break
    found.sort(key=lambda r: r["age"])
    return {"keyword": keyword, "total": len(found), "docs": found[:limit], "partial": partial,
            "denied": sorted(set(denied))[:10]}


def format_docs(res: dict, limit: int = 40) -> str:
    out = [f"## 문서 찾기{' — ' + res['keyword'] if res['keyword'] else ''}", f"{res['total']}개 (최근 수정 순)"]
    if res["partial"]:
        out.append("(시간 제한으로 일부만 찾았어요)")
    if res["denied"]:
        out.append("⚠️ macOS가 막은 폴더: " + ", ".join(res["denied"]))
    folder = None
    for r in res["docs"][:limit]:
        if r["folder"] != folder:
            folder = r["folder"]
            out.append(f"\n**{folder}**")
        out.append(f"- {r['name']} · {human(r['size'])} · {r['date']}")
    return "\n".join(out) + "\n"


def raw_projects() -> list[str]:
    try:
        return sorted(p.name for p in VAULT_RAW.iterdir() if p.is_dir() and not p.name.startswith("."))
    except FileNotFoundError:
        return []


def plan_copy_to_raw(paths: list[str], project: str) -> dict:
    if project not in raw_projects():
        return {"error": f"위키에 '{project}' 프로젝트 폴더가 없어요. 있는 것: {', '.join(raw_projects()) or '(없음)'}"}
    dest = VAULT_RAW / project
    ok, skip = [], []
    for s in paths:
        p = safety.resolve(s)
        why = safety.check_readable(p)
        if why or not p.is_file():
            skip.append((s, why or "파일이 아니에요"))
            continue
        if p.suffix.lower() not in DOC_EXTS:
            skip.append((s, "문서·표 파일만 복사해요"))
            continue
        target = dest / p.name
        n = 2
        while target.exists():
            target = dest / f"{p.stem} ({n}){p.suffix}"
            n += 1
        ok.append((str(p), str(target)))
    return {"dest": str(dest), "ok": ok, "skip": skip}


def copy_to_raw(plan: dict) -> list[str]:
    done = []
    for src, dst in plan["ok"]:
        shutil.copy2(src, dst)          # 복사만. 원본은 그대로 둔다.
        done.append(dst)
    return done


# ---- 3) 폴더 정리 ---------------------------------------------------------------

def plan_organize(folder: str | Path, only_older_days: int = 0) -> dict:
    """폴더 바로 아래의 파일을 종류별 하위 폴더(문서/이미지/…)로 옮기는 계획. 폴더는 그대로 둔다."""
    folder = safety.resolve(folder)
    items, err = _entries(folder)
    if err:
        return {"error": err}
    if folder == HOME:
        return {"error": "홈 폴더 자체는 정리하지 않아요. 그 안의 폴더(예: ~/Downloads)를 골라 주세요."}
    if safety._under(folder, VAULT):
        return {"error": "Obsidian 볼트 안은 정리하지 않아요."}
    moves, skip = [], []
    for p in items:
        if p.is_dir() and p.suffix.lower() != ".app":
            continue
        if only_older_days and _age_days(p) < only_older_days:
            continue
        why = safety.check_writable(p)
        if why:
            skip.append((p.name, why))
            continue
        cat = category(p)
        target = folder / cat / p.name
        n = 2
        while target.exists():
            target = folder / cat / f"{p.stem} ({n}){p.suffix}"
            n += 1
        moves.append((str(p), str(target), cat))
    by = {}
    for _, _, c in moves:
        by[c] = by.get(c, 0) + 1
    return {"folder": str(folder), "moves": moves, "by_cat": by, "skip": skip}


def organize(plan: dict) -> list[tuple[str, str]]:
    done = []
    for src, dst, _ in plan["moves"]:
        Path(dst).parent.mkdir(exist_ok=True)
        if Path(dst).exists():
            continue                      # 덮어쓰지 않는다
        shutil.move(src, dst)
        done.append((src, dst))
    return done


def plan_trash(paths: list[str]) -> dict:
    ok, skip = [], []
    for s in paths:
        p = safety.resolve(s)
        why = safety.check_writable(p)
        if why or not p.exists():
            skip.append((s, why or "없는 파일이에요"))
        else:
            ok.append(str(p))
    return {"ok": ok, "skip": skip}


def trash(plan: dict) -> tuple[list[str], str | None]:
    """Finder로 휴지통에 보낸다 → Finder의 '되돌리기'로 원래 자리에 복구 가능."""
    done = []
    for p in plan["ok"]:
        esc = p.replace("\\", "\\\\").replace('"', '\\"')
        r = subprocess.run(["osascript", "-e", f'tell application "Finder" to delete (POSIX file "{esc}" as alias)'],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return done, ("휴지통으로 보내지 못했어요. 처음이면 macOS가 'Finder 제어' 허용을 물을 수 있어요. "
                          f"허용한 뒤 다시 해 주세요. ({r.stderr.strip()[:120]})")
        done.append(p)
    return done, None


# ---- 기록 -----------------------------------------------------------------------

DATA_DIR = VAULT / "private" / "laptop-helper"


def data_dir_is_private() -> bool:
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(DATA_DIR / "_probe")], cwd=VAULT, capture_output=True)
    except FileNotFoundError:
        return True
    return r.returncode in (0, 128)


def log(action: str, items: list) -> None:
    """무엇을 옮기고 지웠는지 private/에만 남긴다(파일 이름은 개인 정보라 공개 저장소에 안 올림)."""
    if not data_dir_is_private():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "작업기록.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "action": action, "items": items},
                           ensure_ascii=False) + "\n")
