#!/usr/bin/env python3
"""구글 제미나이에게 질문하기.

사용:
  python3 scripts/gemini.py                 대화 모드 (계속 묻고 답하기, 앞 대화 기억)
  python3 scripts/gemini.py "질문"           한 번만 묻기
  python3 scripts/gemini.py -c "질문"        지난 대화에 이어서 묻기 (앞 대화 기억)
  python3 scripts/gemini.py --new           저장된 대화 기록 지우기
  GEMINI_MODEL=gemini-3.1-flash-lite python3 scripts/gemini.py ...   모델 지정

대화 모드에서: /new 새 대화, /exit 또는 Ctrl+D 끝내기
키는 볼트 루트의 .env 에 있는 GOOGLE_API_KEY 를 읽는다 (.env 는 git 제외).
대화 기록은 ~/.local/state/gemini-chat.json (볼트 밖, git 에 안 올라감).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1]
HISTORY = Path.home() / ".local/state/gemini-chat.json"
# 앞에서부터 시도. 바쁨(503)·한도 초과(429)·시간 초과면 다음 모델로 넘어감
MODELS = [os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else [
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite",
]


def load_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY")
    env = VAULT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GOOGLE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("GOOGLE_API_KEY 가 없습니다. 볼트 루트 .env 에 넣어 주세요.")
    return key


def call(model: str, contents: list, key: str, timeout: int) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({"contents": contents}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return text or json.dumps(data, ensure_ascii=False)[:500]


class GeminiError(Exception):
    pass


def ask(contents: list, key: str) -> str:
    for model in MODELS:
        last = model == MODELS[-1]
        try:
            text = call(model, contents, key, 120 if last else 30)  # 앞 모델은 30초만 기다림
            print(f"[{model}]", file=sys.stderr)
            return text
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            if e.code in (429, 503, 404) and not last:
                print(f"[{model}: {e.code}, 다음 모델 시도]", file=sys.stderr)
                continue
            raise GeminiError(f"오류 {e.code} ({model}): {msg[:500]}")
        except (TimeoutError, urllib.error.URLError) as e:
            if not last:
                print(f"[{model}: 연결 문제({e}), 다음 모델 시도]", file=sys.stderr)
                continue
            raise GeminiError(f"연결 실패 ({model}): {e}")
    raise GeminiError("모든 모델 실패")


def load_history() -> list:
    try:
        return json.loads(HISTORY.read_text())
    except (OSError, ValueError):
        return []


def save_history(contents: list) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(contents, ensure_ascii=False, indent=1))
    HISTORY.chmod(0o600)


def turn(contents: list, question: str, key: str) -> str:
    """질문을 보내고, 성공하면 질문·답변을 contents 에 추가."""
    msg = {"role": "user", "parts": [{"text": question}]}
    answer = ask(contents + [msg], key)
    contents += [msg, {"role": "model", "parts": [{"text": answer}]}]
    return answer


def chat(key: str) -> None:
    contents = load_history()
    if contents:
        print(f"(지난 대화 {len(contents) // 2}개에 이어서 합니다. 새로 시작: /new)")
    print("제미나이와 대화합니다. 끝내기: /exit 또는 Ctrl+D\n")
    while True:
        try:
            q = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("/exit", "/quit", "exit", "quit"):
            break
        if q == "/new":
            contents = []
            save_history(contents)
            print("(새 대화를 시작합니다)\n")
            continue
        try:
            print(f"\n제미나이> {turn(contents, q, key)}\n")
            save_history(contents)
        except GeminiError as e:
            print(f"\n⚠ {e}\n(다시 질문해 보세요)\n")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if args and args[0] == "--new":
        save_history([])
        print("대화 기록을 지웠습니다.")
        return
    key = load_key()
    if not args and sys.stdin.isatty():
        chat(key)
        return
    cont = bool(args) and args[0] in ("-c", "--continue")
    if cont:
        args = args[1:]
    q = " ".join(args) or sys.stdin.read()
    if not q.strip():
        sys.exit(__doc__)
    contents = load_history() if cont else []
    try:
        print(turn(contents, q, key))
    except GeminiError as e:
        sys.exit(str(e))
    save_history(contents)   # 한 번 묻기도 기록 → 다음에 -c 로 이어 묻기 가능


if __name__ == "__main__":
    main()
