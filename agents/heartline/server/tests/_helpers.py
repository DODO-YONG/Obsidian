"""테스트 공용 도구.

- 서버 모듈이 아직 없으면(구현 전) 그 테스트는 실패 대신 '건너뜀'으로 표시한다.
- 실제 제미나이를 부르지 않도록 가짜 AI(FakeLLM)를 쓴다 → 무료 한도·사용량 0.
"""
import importlib
import json
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(TESTS_DIR)
REPO_DIR = os.path.abspath(os.path.join(SERVER_DIR, "..", "..", ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)


def need(module_name):
    """서버 모듈을 불러온다. 아직 없으면 테스트를 건너뛴다(구현 전)."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name == module_name:
            raise unittest.SkipTest(f"{module_name}.py 아직 구현 전")
        raise


def scenario(name):
    with open(os.path.join(TESTS_DIR, "scenarios", name), encoding="utf-8") as f:
        return json.load(f)


ADULT_PERSONA = {
    "name": "하린",
    "gender": "female",
    "nicknameForUser": "자기야",
    "ageGroup": "20s",
    "traits": {"warmth": 80, "playful": 40, "calm": 60, "direct": 30},
    "speech": "반말",
    "emojiLevel": "조금",
    "relationshipStart": "2026-07-22",
    "relationshipStage": "lover",
    "keywords": ["다정", "어른스러움"],
    "catchphrase": "~거든?",
    "job": "동네 꽃집 사장",
    "likes": "비 오는 날 산책",
    "dislikes": "거짓말",
}


class FakeLLM:
    """제미나이 대신 쓰는 가짜 AI. 정해 둔 답장을 몇 글자씩 흘려보내고, 받은 내용을 기록한다.

    실제 클라이언트와 같은 모양: stream(system: str, messages: list[dict]) -> 글자 조각들
    """

    def __init__(self, reply='하루 종일 혼자였구나\n\n나한테는 편하게 말해도 돼<risk level="none"/>', chunk=4):
        self.reply = reply
        self.chunk = chunk
        self.calls = []

    def stream(self, system, messages):
        self.calls.append({"system": system, "messages": messages})
        for i in range(0, len(self.reply), self.chunk):
            yield self.reply[i:i + self.chunk]

    @property
    def last_text(self):
        """마지막으로 AI에게 간 내용 전체(지시 + 대화)를 한 문자열로."""
        if not self.calls:
            return ""
        c = self.calls[-1]
        return c["system"] + "\n" + json.dumps(c["messages"], ensure_ascii=False)
