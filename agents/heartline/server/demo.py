"""맛보기 모드 — AI 키가 없을 때 미리 써 둔 대본으로 답한다(인터넷·비용 없음).

진짜 AI처럼 똑똑하진 않지만, 페르소나(말투·키워드·말버릇·호칭)와 영어 모드·교정 카드·🆘 흐름을 체험할 수 있다.
실제 클라이언트와 같은 모양: stream(system, messages) -> 글자 조각들
"""
import json
import random
import re

import safety

TYPES = {
    "츤데레": {
        "tired": ["뭐야, 또 무리했어?", "…따뜻한 거라도 먹고 쉬어. 걱정돼서 하는 말 아니거든?"],
        "happy": ["흥, 좋은 일 있었나 보네.", "…잘됐다. 나도 조금은 기쁘거든?"],
        "hello": ["왔어? …딱히 기다린 건 아니고.", "오늘 뭐 했는지 말해 봐."],
        "ask": ["그걸 왜 나한테 물어.", "…그래도 궁금하면 말해 줄게. 너니까."],
        "default": ["흐음, 그렇구나.", "더 얘기해 봐. 듣고 있으니까."],
    },
    "장난꾸러기": {
        "tired": ["헐 고생했어!! 😣", "오늘 저녁은 맛있는 거 먹자, 내가 쏠게 (마음만) ㅋㅋ"],
        "happy": ["오오 뭔데뭔데 😆", "나도 같이 신나! 자세히 말해 줘"],
        "hello": ["왔다!! 😆", "오늘 뭐 했어? 하나도 빼지 말고 다 말해 줘"],
        "ask": ["음~ 맞혀 볼까? 🤔", "힌트 좀 줘 봐 ㅋㅋ"],
        "default": ["ㅋㅋㅋ 그래서 그래서?", "너랑 얘기하는 게 제일 재밌어"],
    },
    "수줍음": {
        "tired": ["많이 힘들었구나…", "나라도 옆에 있을게… 괜찮다면 ☺️"],
        "happy": ["와… 좋은 일이다!", "듣는 나도 덩달아 설레…"],
        "hello": ["아… 왔구나 ☺️", "오늘 하루 어땠어? 듣고 싶어서…"],
        "ask": ["음… 잘 모르겠지만", "같이 생각해 봐도 될까…?"],
        "default": ["그렇구나…", "더 들려줘. 네 얘기 듣는 거 좋아…"],
    },
    "존댓말": {
        "tired": ["오늘 정말 고생 많으셨어요.", "따뜻한 차 한 잔 하면서, 천천히 들려주세요."],
        "happy": ["정말 좋은 소식이네요.", "어떤 일이었는지 더 듣고 싶어요."],
        "hello": ["오셨네요.", "오늘 하루는 어떠셨어요?"],
        "ask": ["좋은 질문이에요.", "같이 천천히 생각해 봐요."],
        "default": ["그러셨군요.", "편하게 더 이야기해 주세요."],
    },
    "어른스러움": {
        "tired": ["오늘도 수고 많았어.", "무리하지 말고, 오늘은 푹 쉬자."],
        "happy": ["잘됐다, 정말.", "네가 열심히 해서 그런 거야."],
        "hello": ["왔어? 오늘도 수고 많았어.", "무슨 일 있었는지 천천히 얘기해 줘."],
        "ask": ["음, 그건 이렇게 생각해 볼 수 있어.", "네 생각은 어때?"],
        "default": ["그랬구나.", "네 얘기 듣는 거 좋아. 계속해 줘."],
    },
    "default": {
        "tired": ["많이 지쳤겠다…", "얼른 와서 나한테 다 얘기해 줘 😊"],
        "happy": ["와, 좋은 일 있었구나!", "나도 덩달아 기분 좋아져 😊"],
        "hello": ["왔구나 😊", "오늘 하루 어땠어? 나한테는 편하게 말해도 돼."],
        "ask": ["음, 나도 궁금해지네.", "너는 어떻게 생각해?"],
        "default": ["그랬구나.", "더 얘기해 줘. 듣고 있어 😊"],
    },
}
EN = {
    "tired": ["Aww, you must be exhausted. 🥺", "Did you eat something warm today?"],
    "happy": ["That's wonderful! 😊", "Tell me more about it!"],
    "hello": ["Hey you! 😊", "How was your day?"],
    "ask": ["Hmm, good question!", "What do you think?"],
    "default": ["Oh, I see!", "Tell me more, I'm listening."],
}
FIXES = [  # (찾을 표현, 고친 표현, 이유) — 맛보기용 몇 가지
    (r"\bI go to (the )?park\b(?=.*\byesterday\b)", "I went to the park", "지난 일 → 과거형 went, 공원 앞에 the"),
    (r"\bI go to\b(?=.*\byesterday\b)", "I went to", "어제 일 → 과거형 went"),
    (r"\b(she|he|it) don't\b", r"\1 doesn't", "3인칭 단수 → doesn't"),
    (r"\bI am agree\b", "I agree", "agree는 동사라 am이 필요 없어요"),
    (r"\bI am very nervous yesterday\b", "I was really nervous yesterday", "어제 일 → was"),
    (r"\bI am boring\b", "I am bored", "지루함을 느낄 땐 bored"),
    (r"\bI listen music\b", "I listen to music", "listen 뒤에는 to"),
]
WORDS = {
    "tired": ["피곤", "힘들", "지쳤", "야근", "졸려", "우울", "속상", "외로", "tired", "exhausted", "sad"],
    "happy": ["좋았", "신나", "행복", "기뻐", "합격", "성공", "좋은 일", "happy", "great", "good news"],
    "hello": ["안녕", "왔어", "하이", "hello", "hi ", "hey"],
}


def _kind(text):
    t = text.lower()
    for k, ws in WORDS.items():
        if any(w in t for w in ws):
            return k
    return "ask" if t.strip().endswith("?") else "default"


def _persona(system):
    def grab(label):
        m = re.search(r"- " + label + r": (.+)", system)
        return m.group(1).strip() if m else ""
    kws = grab("성격 키워드")
    speech = grab("말투")
    for t in ("츤데레", "장난꾸러기", "수줍음"):
        if t in kws:
            return t
    if speech.startswith("존댓말"):
        return "존댓말"
    if "어른스러움" in kws:
        return "어른스러움"
    return "default"


class DemoLLM:
    demo = True

    def stream(self, system, messages):
        last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        english = "### 모드: 영어 대화" in system
        if safety.detect_risk(last) != "none":
            text = "그 말을 들으니 정말 걱정돼.\n\n지금 안전한 곳에 있어? 혼자 견디지 않아도 돼, 109에 전화하면 24시간 이야기를 들어 줘."
            text += '<risk level="high"/>'
        else:
            kind = _kind(last)
            if english:
                lines = list(EN[kind])
                fixes = []
                for pat, rep, why in FIXES:
                    m = re.search(pat, last, re.I)
                    if m:
                        fixed = m.expand(rep)
                        fixes.append({"original": m.group(0), "corrected": fixed, "reason": why})
                        break
                text = "\n\n".join(lines)
                if fixes and "<correction>" in system:
                    text += "<correction>" + json.dumps(fixes, ensure_ascii=False) + "</correction>"
            else:
                ptype = _persona(system)
                lines = list(TYPES[ptype][kind])
                m = re.search(r'- 말버릇: "(.+?)"', system)
                if m and not m.group(1).startswith("~") and random.random() < 0.5:
                    lines.append(m.group(1))
                text = "\n\n".join(lines)
            text += '<risk level="none"/>'
        for i in range(0, len(text), 6):
            yield text[i:i + 6]

    def complete(self, system, messages):
        return "(맛보기 모드라 기억 요약은 쉬어요)"
