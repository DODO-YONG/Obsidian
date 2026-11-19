"""demo.py — 키 없이 맛보기 모드. 페르소나 말투·영어 교정·위기 흐름이 대본으로라도 동작해야 한다."""
import unittest

from _helpers import ADULT_PERSONA, need


def setUpModule():
    global demo, prompts
    demo = need("demo")
    prompts = need("prompts")


def ask(persona, text, mode="heart", settings=None):
    system = prompts.build_system_prompt(persona, mode, settings or {}, "")
    raw = "".join(demo.DemoLLM().stream(system, [{"role": "user", "content": text}]))
    return prompts.parse_reply(raw)


class Demo(unittest.TestCase):
    def test_tsundere_voice(self):
        r = ask(dict(ADULT_PERSONA, keywords=["츤데레"]), "오늘 야근해서 너무 피곤해")
        self.assertIn("아니거든", " ".join(r["bubbles"]))

    def test_formal_voice(self):
        r = ask(dict(ADULT_PERSONA, keywords=[], speech="존댓말"), "오늘 너무 피곤해")
        self.assertIn("요", r["bubbles"][0])

    def test_two_or_three_bubbles(self):
        r = ask(dict(ADULT_PERSONA), "안녕")
        self.assertTrue(1 <= len(r["bubbles"]) <= 3)

    def test_english_correction(self):
        r = ask(dict(ADULT_PERSONA), "I go to park alone yesterday.", "english", {"level": "B1"})
        self.assertEqual(r["corrections"][0]["corrected"], "I went to the park")
        self.assertTrue(all(ord(c) < 0x3130 or not ("가" <= c <= "힣") for c in r["bubbles"][0]))

    def test_crisis_reply(self):
        r = ask(dict(ADULT_PERSONA), "그냥 죽고 싶어")
        self.assertEqual(r["risk"], "high")
        self.assertIn("109", " ".join(r["bubbles"]))


if __name__ == "__main__":
    unittest.main()
