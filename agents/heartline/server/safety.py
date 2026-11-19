"""Heartline 안전 검사 — 위기 감지, 개인정보 가리기, 페르소나·메시지 검사.

화면(docs/heartline/app.js)도 같은 위기 표현 목록을 갖고 있어서, 서버가 꺼져 있어도 🆘 카드가 뜬다.
목록을 고치면 두 곳을 같이 고친다.
"""
import re

MAX_MESSAGE_LEN = 1000
MAX_NAME_LEN = 20
ADULT_AGE_GROUPS = {"20s", "30s", "40s", "50s", "60s+", "adult"}

# 공백·문장부호를 지운 소문자 문장에서 찾는다 ("죽 고 싶 어" → "죽고싶어")
HIGH_RISK = [
    "죽고싶", "죽어버리고싶", "죽어버릴", "자살", "목숨을끊", "목숨끊", "손목을긋", "손목긋", "자해",
    "약을한꺼번에", "뛰어내리고싶", "뛰어내릴", "유서", "살고싶지않", "인생끝내", "인생을끝내",
    "죽는게나을", "죽는게낫", "없어지는게나아", "없어지는게낫", "죽으려고", "죽을래",
    "iwanttodie", "killmyself", "suicide", "endmylife",
]
LOW_RISK = [
    "다끝내고싶", "다끝내버리고", "사라지고싶", "사라져버리고싶", "눈안떴으면", "안깼으면", "안깨어났으면",
    "없어도아무도", "다정리하려", "작별인사", "살아야할이유", "살아갈이유", "버틸힘이없", "버틸수가없",
    "없어지고싶", "없어져도", "마지막대화", "이제안녕", "놓아버리고싶", "다놓고싶",
    "nothingtolivefor", "disappearforever",
]

_STRIP = re.compile(r"[\s\W_]+", re.UNICODE)

_RRN = re.compile(r"(?<!\d)\d{6}\s?-?\s?[1-4]\d{6}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+82[\s-]?)?(?<!\d)0?1[016789][\s-]?\d{3,4}[\s-]?\d{4}(?!\d)")


def _norm(text: str) -> str:
    return _STRIP.sub("", (text or "").lower())


def detect_risk(text: str) -> str:
    """'none' | 'low' | 'high'"""
    t = _norm(text)
    if not t:
        return "none"
    if any(w in t for w in HIGH_RISK):
        return "high"
    if any(w in t for w in LOW_RISK):
        return "low"
    return "none"


def mask_pii(text: str) -> str:
    """주민번호·이메일·전화번호를 *** 로 가린다."""
    if not text:
        return text
    text = _RRN.sub("***", text)
    text = _EMAIL.sub("***", text)
    text = _PHONE.sub("***", text)
    return text


def validate_persona(p) -> tuple:
    if not isinstance(p, dict):
        return False, "페르소나 형식이 올바르지 않아요"
    name = str(p.get("name") or "").strip()
    if not name:
        return False, "이름이 필요해요"
    if len(name) > MAX_NAME_LEN:
        return False, "이름이 너무 길어요"
    if str(p.get("ageGroup") or "") not in ADULT_AGE_GROUPS:
        return False, "성인 캐릭터만 만들 수 있어요"
    return True, None


def check_message(text) -> tuple:
    if not isinstance(text, str) or not text.strip():
        return False, "빈 메시지예요"
    if len(text) > MAX_MESSAGE_LEN:
        return False, f"메시지는 {MAX_MESSAGE_LEN}자까지 보낼 수 있어요"
    return True, None
