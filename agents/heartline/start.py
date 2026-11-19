"""Heartline 한 번에 실행하기 — 더블클릭 파일(Heartline 실행.command / .bat)이 이 파일을 부른다.

1) 파이썬 버전 확인  2) 제미나이 키 확인(없으면 물어봄, 엔터만 누르면 맛보기 모드)
3) 빈 포트로 서버 켜기  4) 브라우저 자동 열기.  끄기: 이 창을 닫거나 Ctrl+C
설치할 것 없음(파이썬 기본 기능만). 대화는 브라우저에만 저장되고 서버는 저장하지 않는다.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

if sys.version_info < (3, 9):
    print("파이썬 3.9 이상이 필요해요. https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행해 주세요.")
    input("엔터를 누르면 닫혀요...")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server"
sys.path.insert(0, str(SERVER))
os.chdir(SERVER)

import demo  # noqa: E402
import gemini_client as gc  # noqa: E402
import server  # noqa: E402

LINE = "─" * 52


def save_key(key):
    env = SERVER / ".env"
    lines = [l for l in (env.read_text(encoding="utf-8").splitlines() if env.exists() else []) if not l.startswith("GOOGLE_API_KEY=")]
    lines.insert(0, f"GOOGLE_API_KEY={key}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ask_key():
    print(LINE)
    print("💗 Heartline — 내 취향대로 만든, 나만의 가상 연인")
    print(LINE)
    print("진짜 AI로 대화하려면 '제미나이 API 키'(무료)가 필요해요.")
    print("  · 받는 곳: https://aistudio.google.com/apikey  (구글 로그인 → Create API key)")
    print("  · 결제(카드)는 연결하지 마세요. 무료 등급으로 충분해요.")
    print("키가 없으면 그냥 엔터 → '맛보기 모드'(미리 써 둔 답장)로 바로 체험할 수 있어요.\n")
    try:
        key = input("키를 붙여 넣고 엔터 (없으면 그냥 엔터): ").strip()
    except EOFError:
        key = ""
    if key:
        if not (key.startswith("AIza") and len(key) >= 30):
            print("⚠️ 키 모양이 조금 달라 보여요. 일단 저장하고 시도해 볼게요. 안 되면 server/.env 파일을 지우고 다시 실행하세요.")
        save_key(key)
        print("✅ 키를 server/.env 에 저장했어요. 다음부터는 묻지 않아요.\n")


def free_port(start=8766):
    for p in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("빈 포트를 찾지 못했어요. 컴퓨터를 다시 켠 뒤 실행해 주세요.")


def main():
    server.refuse_paid_billing()
    if not gc.env("GOOGLE_API_KEY"):
        if sys.stdin and sys.stdin.isatty() and not os.environ.get("HEARTLINE_NO_PROMPT"):
            ask_key()
        else:
            print("(입력 창이 없어 키를 묻지 않고 맛보기 모드로 시작해요)")
    llm = gc.from_env() or demo.DemoLLM()
    port = free_port(int(gc.env("HEARTLINE_PORT", "8766")))
    srv = server.make_server("127.0.0.1", port, llm, [], 1000, 10000)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    mode = "🎭 맛보기 모드 (미리 써 둔 답장)" if getattr(llm, "demo", False) else "✨ 제미나이 무료 등급 (진짜 AI)"
    print(LINE)
    print(f"✅ Heartline 이 켜졌어요 → {url}")
    print(f"   AI: {mode}")
    print("   브라우저가 안 열리면 위 주소를 직접 열어 주세요.")
    print("   끄기: 이 창을 닫거나 Ctrl+C")
    print(LINE)
    time.sleep(0.6)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n👋 Heartline 을 껐어요. 대화는 브라우저에 남아 있어요.")
        srv.shutdown()


if __name__ == "__main__":
    main()
