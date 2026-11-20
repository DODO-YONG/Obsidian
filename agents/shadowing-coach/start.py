"""DY-008 SHADOW 한 번에 실행하기 — 'SHADOW 실행.command'를 더블클릭하면 이 파일이 실행된다.

1) 유료 키 확인(있으면 거부)  2) 필요한 도구 확인(yt-dlp·ffmpeg·whisper-cli·모델)
3) 빈 포트로 서버 켜기  4) 브라우저 열기.  끄기: 이 창을 닫거나 Ctrl+C
"""
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "server"))

import server  # noqa: E402

MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/" + server.MODEL.name


def check_tools():
    st = server.tool_status()
    missing = [k for k in ("yt-dlp", "ffmpeg", "whisper-cli") if not st[k]]
    if missing:
        names = {"yt-dlp": "yt-dlp", "ffmpeg": "ffmpeg", "whisper-cli": "whisper-cpp"}
        print("필요한 도구가 없어요. 터미널에서 설치한 뒤 다시 실행하세요:")
        print("  brew install " + " ".join(names[k] for k in missing))
        sys.exit(1)
    if not server.DICT_BIN.exists():
        # 맥 내장 영한사전을 읽는 작은 도우미를 한 번만 빌드 (Xcode 명령줄 도구의 swiftc 사용)
        src = server.DICT_BIN.with_name("dict.swift")
        if shutil.which("swiftc") and src.exists():
            print("단어 사전 도우미를 준비하는 중(처음 한 번, 약 10초)...")
            r = subprocess.run(["swiftc", "-O", str(src), "-o", str(server.DICT_BIN)], capture_output=True, text=True)
            print("✅ 단어 사전 준비 완료" if r.returncode == 0 else "⚠️ 단어 사전 준비 실패 — 단어 뜻 보기만 꺼져요.")
        else:
            print("⚠️ swiftc가 없어 단어 뜻 보기가 꺼져요. (xcode-select --install 로 설치 가능)")
    if not st["model"]:
        print(f"Whisper 모델({server.MODEL.name})이 없어 한 번만 내려받아요(약 140MB, 무료)...")
        server.MODEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = server.MODEL.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL, tmp)
        tmp.replace(server.MODEL)
        print("✅ 모델 준비 완료")


def free_port(start=8777):
    for p in range(start, start + 20):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 방금 끈 서버의 포트도 바로 다시 씀
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("빈 포트를 찾지 못했어요.")


def main():
    server.refuse_paid_billing()
    check_tools()
    port = free_port(int(os.environ.get("SHADOW_PORT", "8777")))
    srv = server.make_server("127.0.0.1", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print("─" * 52)
    print("🕶️ DY-008 SHADOW · 영어 섀도잉 코치")
    print(f"   {url}  (이 Mac 안에서만 열려요)")
    print("   끄기: 이 창을 닫거나 Ctrl+C")
    print("─" * 52)
    if not (os.environ.get("SHADOW_NO_BROWSER") or "--no-browser" in sys.argv):
        webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
