"""제출용: 공개 페이지(PRD·체크리스트·테스트)를 '파일 하나짜리 HTML'로 만든다.

- how.css / how.js 를 페이지 안에 넣는다(다른 파일 없이 더블클릭으로 열림, 인터넷 없이도 동작).
- 사이트 버전 확인 스크립트는 뺀다(파일로 열면 필요 없음).
- 다른 페이지로 가는 링크는 공개 사이트 주소로 바꾼다.
실행: python3 agents/heartline/make-offline-docs.py  → wiki/projects/heartline/output/제출/
"""
import re
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "docs" / "heartline"
OUT = REPO / "wiki" / "projects" / "heartline" / "output" / "제출"
SITE = "https://dodo-yong.github.io/Obsidian/heartline/"
PAGES = {"prd.html": "1_PRD", "checklist.html": "2_체크리스트", "tests.html": "3_테스트목록"}


def build(name):
    s = (WEB / name).read_text(encoding="utf-8")
    # 버전 확인 스크립트(첫 SITE_V 블록) 제거
    s = re.sub(r"<script>\s*(/\*[^*]*\*/\s*)?\(function \(\) \{\s*var SITE_V.*?</script>\n?", "", s, count=1, flags=re.S)
    # how.css / how.js 넣기
    css = (WEB / "how.css").read_text(encoding="utf-8")
    js = (WEB / "how.js").read_text(encoding="utf-8")
    s = re.sub(r'<link rel="stylesheet" href="how\.css\?v=\d+">', lambda m: "<style>\n" + css + "\n</style>", s)
    s = re.sub(r'<script src="how\.js\?v=\d+" defer></script>', lambda m: "<script>\n" + js + "\n</script>", s)
    # 다른 페이지 링크 → 공개 주소
    for page in ("prd.html", "checklist.html", "tests.html", "deck.html"):
        s = s.replace(f'href="{page}', f'href="{SITE}{page}')
    s = s.replace('href="./"', f'href="{SITE}"')
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = date.today().strftime("%Y_%m_%d")
    for name, label in PAGES.items():
        f = OUT / f"{d}_heartline_{label}.html"
        f.write_text(build(name), encoding="utf-8")
        print(f"{f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
