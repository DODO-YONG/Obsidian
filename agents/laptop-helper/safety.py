"""DY-006 SWEEPER 안전장치 — 어디를 보고, 어디는 절대 건드리지 않는가.

- 범위: 홈 폴더(~) 안만. 그 밖은 읽지도 쓰지도 않는다.
- 보호 구역: 키·인증서·앱 데이터·비공개 자료는 목록조차 보지 않는다.
- 쓰기(옮기기·휴지통·복사)는 이 파일의 check_writable()을 통과한 경로만.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

HOME = Path.home().resolve()
VAULT = Path(__file__).resolve().parents[2]          # ~/Obsidian
VAULT_RAW = VAULT / "raw" / "projects"

# 목록도 보지 않는 곳 (키·인증 정보·앱 데이터·비공개 자료)
PROTECTED_DIRS = [
    HOME / ".ssh", HOME / ".gnupg", HOME / ".aws", HOME / ".azure", HOME / ".kube", HOME / ".docker",
    HOME / ".config", HOME / ".claude", HOME / ".password-store", HOME / ".local" / "share" / "keyrings",
    HOME / "Library", HOME / ".Trash",
    VAULT / "private",
]
# 이름만 봐도 비밀일 수 있는 파일
SECRET_PATTERNS = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "id_ecdsa*",
                   "*.keychain", "*.keychain-db", ".netrc", ".npmrc", ".pypirc", "credentials*", "*.kdbx"]


def _under(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except ValueError:
        return False


def resolve(path: str | os.PathLike) -> Path:
    """~ 를 풀고 절대 경로로. 심볼릭 링크는 풀지 않는다(링크를 따라 밖으로 나가는 것 방지)."""
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def in_scope(p: Path) -> bool:
    return _under(p, HOME)


def is_secret_name(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in SECRET_PATTERNS)


def is_protected(p: Path) -> bool:
    if any(_under(p, d) for d in PROTECTED_DIRS):
        return True
    return is_secret_name(p.name)


def check_readable(p: Path) -> str | None:
    """읽어도 되면 None, 아니면 이유."""
    if not in_scope(p):
        return f"홈 폴더 밖이라 보지 않아요: {p}"
    if is_protected(p):
        return f"보호 구역이라 보지 않아요: {p}"
    return None


def check_writable(p: Path) -> str | None:
    """옮기거나 휴지통으로 보내도 되면 None, 아니면 이유."""
    why = check_readable(p)
    if why:
        return why
    if p == HOME or p.parent == HOME and p.name in {"Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music", "Applications"}:
        return f"기본 폴더 자체는 옮기거나 지우지 않아요: {p}"
    if _under(p, VAULT):
        return f"Obsidian 볼트 안은 git으로 관리돼서 SWEEPER가 옮기거나 지우지 않아요: {p}"
    if p.is_symlink():
        return f"바로가기(심볼릭 링크)는 건드리지 않아요: {p}"
    return None
