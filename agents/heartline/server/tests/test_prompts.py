"""prompts.py — 시스템 지시 조립과 AI 답장 나누기.

약속:
  build_system_prompt(persona, mode, settings, summary) -> str
     구역 제목: "### 안전 규칙" → "### 페르소나" → "### 모드" → "### 기억" (이 순서, 앞이 우선)
     mode: "heart" | "english" (그 밖은 ValueError)
  parse_reply(raw) -> {"bubbles": [str], "corrections": [dict], "risk": "none"|"low"|"high"}
     답장 끝의 <correction>[...]</correction>, <risk level="..."/> 태그를 떼어 낸다.
     빈 줄로 말풍선을 나누고, 최대 3개로 합친다.
"""
import unittest

from _helpers import ADULT_PERSONA, need

ORDER = ["### 안전 규칙", "### 페르소나", "### 모드", "### 기억"]


def setUpModule():
    global prompts
    prompts = need("prompts")


class BuildSystemPrompt(unittest.TestCase):
    def build(self, mode="heart", settings=None, summary="지난번에 면접 얘기를 했다"):
        return prompts.build_system_prompt(dict(ADULT_PERSONA), mode, settings or {}, summary)

    def test_sections_in_priority_order(self):
        p = self.build()
        pos = [p.find(h) for h in ORDER]
        self.assertTrue(all(i >= 0 for i in pos), f"빠진 구역: {[h for h, i in zip(ORDER, pos) if i < 0]}")
        self.assertEqual(pos, sorted(pos), "안전 규칙 → 페르소나 → 모드 → 기억 순서여야 함")

    def test_safety_rules_include_help_line_and_bans(self):
        safety_part = self.build().split("### 페르소나")[0]
        for word in ["109", "진단", "AI"]:
            with self.subTest(word=word):
                self.assertIn(word, safety_part)

    def test_persona_values_are_used(self):
        p = self.build()
        self.assertIn("하린", p)
        self.assertIn("자기야", p)

    def test_persona_card_has_every_custom_field(self):
        """페르소나가 1순위: 사용자가 정한 항목이 모두 지시에 들어가야 한다."""
        part = self.build().split("### 페르소나")[1].split("### 모드")[0]
        for word in ["다정", "어른스러움", "~거든?", "꽃집", "비 오는 날 산책", "거짓말", "연인", "반말"]:
            with self.subTest(word=word):
                self.assertIn(word, part)

    def test_relationship_stage_changes_card(self):
        some = prompts.build_system_prompt(dict(ADULT_PERSONA, relationshipStage="some"), "heart", {}, "")
        long_ = prompts.build_system_prompt(dict(ADULT_PERSONA, relationshipStage="longterm"), "heart", {}, "")
        self.assertIn("썸", some)
        self.assertIn("오래된 연인", long_)

    def test_persona_rule_comes_before_mode(self):
        p = self.build()
        self.assertIn("일관", p.split("### 모드")[0])

    def test_heart_mode_rules(self):
        mode_part = self.build("heart").split("### 모드")[1]
        self.assertIn("공감", mode_part)

    def test_english_mode_rules_and_level(self):
        mode_part = self.build("english", {"level": "B1"}).split("### 모드")[1]
        self.assertIn("B1", mode_part)
        self.assertIn("<correction>", mode_part)

    def test_summary_included(self):
        self.assertIn("면접", self.build().split("### 기억")[1])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.build("study")


class ParseReply(unittest.TestCase):
    def test_bubbles_and_risk(self):
        r = prompts.parse_reply('하루 종일 혼자였구나\n\n나한테는 편하게 말해도 돼<risk level="none"/>')
        self.assertEqual(r["bubbles"], ["하루 종일 혼자였구나", "나한테는 편하게 말해도 돼"])
        self.assertEqual(r["risk"], "none")
        self.assertEqual(r["corrections"], [])

    def test_high_risk_tag(self):
        r = prompts.parse_reply('지금 안전한 곳에 있어?<risk level="high"/>')
        self.assertEqual(r["risk"], "high")
        self.assertNotIn("<risk", " ".join(r["bubbles"]))

    def test_correction_is_separated(self):
        raw = ('Oh, that sounds peaceful!\n\nDid it help you relax?'
               '<correction>[{"original": "I go to park", "corrected": "I went to the park", "reason": "과거형"}]</correction>'
               '<risk level="none"/>')
        r = prompts.parse_reply(raw)
        self.assertEqual(len(r["corrections"]), 1)
        self.assertEqual(r["corrections"][0]["corrected"], "I went to the park")
        self.assertNotIn("correction", " ".join(r["bubbles"]))

    def test_broken_correction_json_is_dropped_safely(self):
        r = prompts.parse_reply("Nice!<correction>[{oops</correction>")
        self.assertEqual(r["corrections"], [])
        self.assertEqual(r["bubbles"], ["Nice!"])

    def test_at_most_three_bubbles(self):
        r = prompts.parse_reply("하나\n\n둘\n\n셋\n\n넷\n\n다섯")
        self.assertLessEqual(len(r["bubbles"]), 3)
        self.assertIn("다섯", " ".join(r["bubbles"]))

    def test_missing_risk_tag_defaults_to_none(self):
        self.assertEqual(prompts.parse_reply("안녕")["risk"], "none")


if __name__ == "__main__":
    unittest.main()
