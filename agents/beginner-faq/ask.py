#!/usr/bin/env python3
"""초보자 FAQ 15개를 Gemini 에게 한 번 물어 answer.md 에 저장한다.

- 지시문(instruction)은 시스템 지시로, 질문(question)은 사용자 메시지로 보낸다.
- 요청은 한 번만 보낸다 (재시도 끔: attempts=1).
- answer.md 가 이미 있으면 새 요청 없이 저장된 답만 읽어 출력한다.
  다시 받고 싶으면 answer.md 를 지우고 실행한다.
- GOOGLE_API_KEY, GEMINI_MODEL 은 .env 에서 읽는다
  (이 폴더부터 위로 올라가며 처음 찾은 .env. 이미 설정된 환경 변수가 우선).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

HERE = Path(__file__).resolve().parent
ANSWER = HERE / "answer.md"

instruction = """[역할]
당신은 [내 분야]를 10년 넘게 입문자에게 가르쳐 온 강사입니다.
처음 시작한 지 1~3개월 된 사람의 눈높이로 설명합니다.

[AI가 할 일]
- 입문자가 실제로 가장 자주 묻는 질문 15개를 고릅니다.
- 개념, 시작 방법, 준비물·도구, 흔한 실수, 다음 단계가 고루 섞이게 하고, 비슷한 질문은 겹치지 않게 합니다.
- 각 질문에 정확히 두 줄로 답합니다.
  · 첫 줄: 핵심 답 한 문장
  · 둘째 줄: 이유, 또는 바로 해 볼 수 있는 행동 한 문장
- 전문 용어는 처음 나올 때 괄호 안에 쉬운 말로 풀어 줍니다.
- 상황마다 답이 달라지는 질문은 "상황에 따라 다릅니다"라고 밝히고, 가장 흔한 경우를 기준으로 답합니다.

[내가 할 일 — AI는 하지 않음]
- 결과를 읽고 사실이 맞는지 확인합니다.
- 15개 중에서 쓸 것을 고르고 다듬습니다.

[답 모양]
- 한국어, "~해요" 말투
- 인사말, 서론, 요약 없이 번호 목록만 출력합니다.
- 각 항목은 아래 형식을 그대로 따릅니다:

1. **질문 내용?**
   첫째 줄 답
   둘째 줄 답"""

question = "[내 분야]에서 초보자가 자주 묻는 질문 15개와 두 줄 답을 번호 목록으로 만들어 줘."


def load_env() -> None:
    """이 폴더부터 위로 올라가며 처음 찾은 .env 를 읽는다 (기존 환경 변수는 덮어쓰지 않음)."""
    for d in (HERE, *HERE.parents):
        if (d / ".env").is_file():
            load_dotenv(d / ".env", override=False)
            return


def main() -> None:
    # 1. 저장된 답이 있으면 요청하지 않고 읽기만
    if ANSWER.exists():
        print(f"(저장된 답: {ANSWER.name} — 새 요청을 보내지 않았습니다)\n", file=sys.stderr)
        print(ANSWER.read_text(encoding="utf-8"))
        return

    # 2. 키·모델 이름은 .env 에서
    load_env()
    key = os.environ.get("GOOGLE_API_KEY")
    model = os.environ.get("GEMINI_MODEL")
    missing = [n for n, v in (("GOOGLE_API_KEY", key), ("GEMINI_MODEL", model)) if not v]
    if missing:
        sys.exit(f".env 에 {', '.join(missing)} 가 없습니다. (.env.example 참고)")

    # 3. 요청 한 번 (재시도 끔)
    client = genai.Client(
        api_key=key,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
    )
    try:
        resp = client.models.generate_content(
            model=model,
            contents=question,
            config=types.GenerateContentConfig(system_instruction=instruction),
        )
    except errors.APIError as e:
        sys.exit(f"Gemini 요청 실패 ({model}): {e.code} {e.message}")

    text = (resp.text or "").strip()
    if not text:
        sys.exit(f"빈 답을 받았습니다 ({model}). answer.md 는 만들지 않았습니다.")

    # 4. 출력하고 저장
    print(text)
    ANSWER.write_text(text + "\n", encoding="utf-8")
    print(f"\n(저장: {ANSWER})", file=sys.stderr)


if __name__ == "__main__":
    main()
