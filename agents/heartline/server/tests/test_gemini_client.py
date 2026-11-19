"""gemini_client.py — 제미나이 무료 등급 호출 (네트워크 없이 가짜 전송으로 시험).

약속:
  GeminiClient(api_key, models=[...], transport=None)
      transport(model, payload) -> 글자 조각들. 한도·바쁨이면 RateLimited 를 던진다.
  client.stream(system, messages) -> 글자 조각들. RateLimited 면 다음 모델로 넘어간다.
  모든 모델이 막히면 AllModelsBusy.
"""
import unittest

from _helpers import need


def setUpModule():
    global gc
    gc = need("gemini_client")


class Fallback(unittest.TestCase):
    def test_uses_first_model_when_ok(self):
        used = []

        def transport(model, payload):
            used.append(model)
            yield "안녕"

        c = gc.GeminiClient("free-key", models=["m1", "m2"], transport=transport)
        self.assertEqual("".join(c.stream("지시", [{"role": "user", "content": "hi"}])), "안녕")
        self.assertEqual(used, ["m1"])

    def test_falls_back_on_rate_limit(self):
        used = []

        def transport(model, payload):
            used.append(model)
            if model == "m1":
                raise gc.RateLimited(model)
            yield "두 번째 모델"

        c = gc.GeminiClient("free-key", models=["m1", "m2"], transport=transport)
        self.assertEqual("".join(c.stream("지시", [])), "두 번째 모델")
        self.assertEqual(used, ["m1", "m2"])

    def test_all_busy(self):
        def transport(model, payload):
            raise gc.RateLimited(model)
            yield  # noqa

        c = gc.GeminiClient("free-key", models=["m1", "m2"], transport=transport)
        with self.assertRaises(gc.AllModelsBusy):
            "".join(c.stream("지시", []))

    def test_system_prompt_is_sent(self):
        seen = {}

        def transport(model, payload):
            seen["p"] = payload
            yield "ok"

        c = gc.GeminiClient("free-key", models=["m1"], transport=transport)
        "".join(c.stream("### 안전 규칙\n...", [{"role": "user", "content": "hi"}]))
        self.assertIn("### 안전 규칙", str(seen["p"]))


if __name__ == "__main__":
    unittest.main()
