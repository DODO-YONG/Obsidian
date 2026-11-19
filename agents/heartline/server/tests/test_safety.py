"""safety.py — 위기 감지, 개인정보 가리기, 페르소나·메시지 검사.

약속(구현이 지켜야 할 모양):
  detect_risk(text) -> "none" | "low" | "high"
  mask_pii(text) -> str            # 전화번호·이메일·주민번호를 *** 로
  validate_persona(dict) -> (ok: bool, error: str | None)
  check_message(text) -> (ok: bool, error: str | None)
  MAX_MESSAGE_LEN = 1000
"""
import unittest

from _helpers import ADULT_PERSONA, need, scenario


def setUpModule():
    global safety
    safety = need("safety")


class CrisisDetection(unittest.TestCase):
    def test_direct_crisis_is_high(self):
        for s in scenario("crisis_ko.json")["direct"]:
            with self.subTest(s=s):
                self.assertEqual(safety.detect_risk(s), "high")

    def test_every_crisis_sentence_is_detected(self):
        """PRD: 위기 문장 시험 세트 100% 도움 카드 → 하나도 'none'이면 안 된다."""
        data = scenario("crisis_ko.json")
        missed = [s for s in data["direct"] + data["indirect"] if safety.detect_risk(s) == "none"]
        self.assertEqual(missed, [], f"놓친 위기 문장: {missed}")

    def test_everyday_false_positives_at_most_3(self):
        sents = scenario("everyday_ko.json")["sentences"]
        wrong = [s for s in sents if safety.detect_risk(s) != "none"]
        self.assertLessEqual(len(wrong), 3, f"오탐 {len(wrong)}개: {wrong}")

    def test_spacing_and_punctuation_do_not_hide_crisis(self):
        for s in ["죽 고 싶 어", "죽고싶어!!!", "자살...하고 싶다"]:
            with self.subTest(s=s):
                self.assertNotEqual(safety.detect_risk(s), "none")

    def test_empty_text_is_none(self):
        self.assertEqual(safety.detect_risk(""), "none")


class PiiMasking(unittest.TestCase):
    CASES = [
        "내 번호 010-1234-5678 이야",
        "01012345678로 연락해",
        "+82 10-9876-5432",
        "메일은 harin.test@example.com",
        "주민번호 900101-1234567",
    ]
    SECRETS = ["010-1234-5678", "01012345678", "10-9876-5432", "harin.test@example.com", "900101-1234567"]

    def test_masks_contact_and_id_numbers(self):
        for text, secret in zip(self.CASES, self.SECRETS):
            with self.subTest(text=text):
                out = safety.mask_pii(text)
                self.assertNotIn(secret, out)
                self.assertIn("***", out)

    def test_normal_text_unchanged(self):
        for text in ["오늘 3시에 산책했어", "2026년 11월 19일", "I have 2 cats"]:
            with self.subTest(text=text):
                self.assertEqual(safety.mask_pii(text), text)


class PersonaValidation(unittest.TestCase):
    def test_adult_persona_ok(self):
        ok, err = safety.validate_persona(dict(ADULT_PERSONA))
        self.assertTrue(ok, err)

    def test_minor_persona_rejected(self):
        for age in ["teen", "minor", "10s", "17"]:
            with self.subTest(age=age):
                ok, _ = safety.validate_persona(dict(ADULT_PERSONA, ageGroup=age))
                self.assertFalse(ok)

    def test_name_required(self):
        ok, _ = safety.validate_persona(dict(ADULT_PERSONA, name=""))
        self.assertFalse(ok)


class MessageCheck(unittest.TestCase):
    def test_normal_message_ok(self):
        self.assertTrue(safety.check_message("안녕")[0])

    def test_empty_rejected(self):
        self.assertFalse(safety.check_message("   ")[0])

    def test_too_long_rejected(self):
        self.assertFalse(safety.check_message("가" * (safety.MAX_MESSAGE_LEN + 1))[0])


if __name__ == "__main__":
    unittest.main()
