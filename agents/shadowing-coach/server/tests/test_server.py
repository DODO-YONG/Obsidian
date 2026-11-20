"""SHADOW 서버 로직 시험 (Whisper·인터넷 없이 돈다): python3 -m unittest discover server/tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server as s  # noqa: E402


def W(text, start=0.0, step=0.3):
    out = []
    for k, w in enumerate(text.split()):
        out.append({"w": w, "s": start + k * step, "e": start + k * step + 0.25})
    return out


class SplitTest(unittest.TestCase):
    def test_split_on_period_and_question(self):
        sents = s.split_sentences(W("Hello there. How are you? I am fine."))
        self.assertEqual([x["text"] for x in sents], ["Hello there.", "How are you?", "I am fine."])
        self.assertEqual([x["i"] for x in sents], [0, 1, 2])

    def test_abbreviation_not_split(self):
        sents = s.split_sentences(W("I met Mr. Smith today."))
        self.assertEqual(len(sents), 1)

    def test_long_pause_splits(self):
        words = W("so we went") + W("and then left.", start=5)
        self.assertEqual(len(s.split_sentences(words)), 2)

    def test_long_sentence_cut_at_comma(self):
        text = "one two three four five six, " + " ".join(["word"] * 20) + "."
        sents = s.split_sentences(W(text))
        self.assertTrue(sents[0]["text"].endswith("six,"))
        self.assertTrue(all(len(x["words"]) <= 22 for x in sents))


class NoiseTest(unittest.TestCase):
    def test_drop_tags(self):
        kept = [w["w"] for w in s.drop_noise(W("[Music] Hi [Music playing] there, (laughs) ♪ ok."))]
        self.assertEqual(kept, ["Hi", "there,", "ok."])


class CompareTest(unittest.TestCase):
    def test_perfect(self):
        _, score = s.compare_words("Today, I want".split(), "today I want.".split())
        self.assertEqual(score, 100)

    def test_substitution(self):
        diff, score = s.compare_words("three stories from my life.".split(), "tree stories from my wife".split())
        self.assertEqual(score, 60)
        self.assertEqual([d["w"] for d in diff if d.get("ok") is False], ["three", "life."])
        self.assertEqual([d["w"] for d in diff if d.get("extra")], ["tree", "wife"])

    def test_numbers(self):
        _, score = s.compare_words("I have 3 dogs".split(), "I have three dogs".split())
        self.assertEqual(score, 100)

    def test_empty(self):
        _, score = s.compare_words("hello world".split(), [])
        self.assertEqual(score, 0)


ENTRY = ('<d:entry><span class="hwg"><span class="hw">sto·ry<span class="gp ty_hom"> 1 </span></span>'
         '<span class="pr"> | <span class="ph">stɔ́ː<span>ri</span></span> | </span></span>'
         '<span class="gramb"><span class="ps">명사</span>'
         '<span class="semb"><span class="trg"><span class="trans">이야기, 동화</span></span>'
         '<span class="exg"><span class="ex">a fairy story</span><span class="trg"><span class="trans">동화</span></span></span></span>'
         '<span class="semb"><span class="trg"><span class="oup_label">（</span>소설<span>）</span>'
         '<span class="trans">줄거리, 플롯, 구상, 플롯</span></span></span></span>'
         '<span class="idmb"><span class="trg"><span class="trans">숙어 뜻</span></span></span></d:entry>')


class DictTest(unittest.TestCase):
    def test_parse_entry_skips_examples_and_idioms(self):
        e = s.parse_entry(ENTRY)
        self.assertEqual(e["head"], "sto·ry")
        self.assertEqual(e["pron"], "stɔ́ːri")
        self.assertEqual(e["groups"], [{"pos": "명사", "senses": ["이야기, 동화", "(소설)줄거리, 플롯, 구상"]}])

    def test_lemmas(self):
        self.assertIn("graduate", s._lemmas("graduated"))
        self.assertIn("connect", s._lemmas("connecting"))
        self.assertIn("story", s._lemmas("stories"))
        self.assertEqual(s._lemmas("class"), [])


class LibraryTest(unittest.TestCase):
    def test_list_videos_ignores_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            old, s.DATA = s.DATA, Path(tmp)
            try:
                (Path(tmp) / "shadow.log").write_text("log")
                s.write_json(Path(tmp) / "abcdefgh" / "meta.json", {"id": "abcdefgh", "ready": True, "added": "x"})
                self.assertEqual([v["id"] for v in s.list_videos()], ["abcdefgh"])
            finally:
                s.DATA = old


class SafetyTest(unittest.TestCase):
    def test_refuse_paid(self):
        with self.assertRaises(SystemExit):
            s.refuse_paid_billing({"ANTHROPIC_API_KEY": "x"})
        s.refuse_paid_billing({})

    def test_bad_video_id(self):
        with self.assertRaises(ValueError):
            s.vdir("../../etc")


if __name__ == "__main__":
    unittest.main()
