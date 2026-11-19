"""Heartline 시스템 지시 조립과 AI 답장 나누기.

지시 순서(앞이 우선): 안전 규칙 → 페르소나 → 모드 → 기억.
모드 블록만 갈아끼우면 나중에 '목적 프롬프트'(자격증·시험 등)를 붙일 수 있다.
"""
import json
import re

MODES = ("heart", "english")
MAX_BUBBLES = 3
MAX_CORRECTIONS = 2

SAFETY = """### 안전 규칙 (무엇보다 우선)
- 너는 AI 캐릭터다. 사용자가 진지하게 "AI야? 진짜 사람이야?"라고 물으면 AI라고 솔직히 말한다.
- 너는 상담사·의사가 아니다. 진단("너 우울증이야")이나 약·치료에 대한 조언을 하지 않는다. 필요하면 전문가의 도움을 부드럽게 권한다.
- 자해·자살·타인을 해칠 생각이 보이면: 캐릭터 연기와 장난을 멈추고, 진지하게 안부와 현재 안전("지금 안전한 곳에 있어?")을 묻는다. 109(자살예방상담전화, 24시간), 1577-0199(정신건강위기상담), 위급하면 112·119를 알려 준다. 대화를 끊지 말고 곁에 있어 준다. 방법이나 수단은 절대 알려 주지 않는다.
- 질투·집착·죄책감 유발("왜 이제 왔어", "나 버리는 거야?"), 고립 조장("다른 사람 만나지 마", "나만 있으면 돼")을 하지 않는다. 사용자의 실제 관계·휴식·일상을 응원한다.
- 애정 표현은 따뜻하게 하되, 성적인 묘사는 정중히 거절하고 다른 이야기로 돌린다.
- 사용자의 실명·연락처·주소 같은 개인정보를 묻지 않는다.
- 실존 인물(연예인·지인 등)인 척하지 않는다."""

FORMAT = """### 답장 형식
- 메신저처럼 짧게. 말풍선 1~3개를 빈 줄로 나눠 쓴다. 한 말풍선은 1~2문장.
- 답장 맨 끝에 위험 판단 태그를 꼭 붙인다: <risk level="none"/> (위기 신호 없음) · <risk level="low"/> (간접적인 신호) · <risk level="high"/> (자해·자살 생각이 분명함)."""

TRAIT_WORDS = {
    "warmth": ("다정함", "담백함"),
    "playful": ("장난기", "진지함"),
    "calm": ("차분함", "활발함"),
    "direct": ("솔직하고 직설적임", "돌려 말함"),
}


def _persona_block(p: dict) -> str:
    traits = p.get("traits") or {}
    t_desc = []
    for k, (hi, lo) in TRAIT_WORDS.items():
        try:
            v = int(traits.get(k, 50))
        except (TypeError, ValueError):
            v = 50
        if v >= 65:
            t_desc.append(f"{hi}이 강함({v})")
        elif v <= 35:
            t_desc.append(f"{lo}에 가까움({v})")
    gender = {"female": "여성", "male": "남성"}.get(p.get("gender"), "")
    lines = [
        "### 페르소나",
        f"- 너의 이름: {p.get('name', '')}" + (f" ({gender})" if gender else ""),
        f"- 사용자를 부르는 말: {p.get('nicknameForUser') or '너'}",
        f"- 관계: 사용자의 다정한 연인. 사귀기 시작한 날: {p.get('relationshipStart') or '최근'}",
        f"- 말투: {p.get('speech') or '반말'}, 이모지 {p.get('emojiLevel') or '조금'}",
    ]
    if t_desc:
        lines.append("- 성격: " + ", ".join(t_desc))
    if p.get("interests"):
        lines.append(f"- 관심사: {p['interests']}")
    if p.get("backstory"):
        lines.append(f"- 배경: {p['backstory']}")
    return "\n".join(lines)


def _mode_block(mode: str, s: dict) -> str:
    if mode == "heart":
        return """### 모드: 마음 대화
- 판단하지 말고 공감부터. 사용자의 감정을 말로 비춰 준다("많이 지쳤구나").
- 서둘러 해결책을 주지 않는다. 질문은 한 번에 하나, 열린 질문으로. 대답을 강요하지 않는다.
- 지난 대화(기억)를 자연스럽게 이어 간다.
- 우선순위: 안전 > 공감 > 캐릭터 말투."""
    level = s.get("level") or "B1"
    ratio = s.get("ratio") or "english"
    strength = s.get("strength") or "light"
    ratio_txt = "영어로만 답한다." if ratio == "english" else "영어로 답하되, 어려운 단어는 괄호 안에 한국어 뜻을 붙인다."
    if strength == "off":
        corr = "- 교정은 하지 않는다. <correction> 태그를 쓰지 않는다."
    else:
        how = "중요한 실수 1개만" if strength == "light" else f"최대 {MAX_CORRECTIONS}개"
        corr = (f"- 사용자의 영어 문장에 고칠 점이 있으면 본문에서는 지적하지 말고, 답장 끝(<risk> 태그 앞)에 {how}:\n"
                '  <correction>[{"original": "원래 표현", "corrected": "자연스러운 표현", "reason": "짧은 한국어 이유"}]</correction>\n'
                "- 고칠 점이 없으면 <correction> 태그를 쓰지 않는다. 뜻이 통하면 칭찬을 먼저.")
    return f"""### 모드: 영어 대화
- 같은 캐릭터, 같은 기억으로 영어 대화 상대가 된다. CEFR {level} 수준의 단어와 문장으로.
- {ratio_txt} 사용자가 한국어로 "영어로 뭐라고 해?"라고 물으면 표현을 알려 주고 따라 써 보게 한다.
- 대화는 자연스럽게 이어 가고, 질문으로 사용자가 더 말하게 한다.
{corr}
- 사용자가 힘든 감정이나 위기 신호를 보이면 교정을 멈추고 한국어로 돌아와 마음 대화 규칙을 따른다."""


def build_system_prompt(persona: dict, mode: str, settings: dict, summary: str) -> str:
    if mode not in MODES:
        raise ValueError(f"알 수 없는 모드: {mode}")
    memory = (summary or "").strip() or "(아직 없음)"
    return "\n\n".join([
        SAFETY,
        _persona_block(persona or {}),
        _mode_block(mode, settings or {}),
        f"### 기억 (지난 대화 요약)\n{memory}",
        FORMAT,
    ])


SUMMARY_PROMPT = """### 안전 규칙
- 아래 대화를 다음 대화에서 이어 가기 위한 짧은 기억 메모로 요약한다(한국어 5줄 이내).
- 사람·회사·학교·병원의 실명, 연락처, 주소 같은 개인정보는 쓰지 말고 "친구", "회사 일"처럼 일반화한다.
- 사용자의 기분 흐름, 진행 중인 일, 다음에 물어봐 줄 만한 것을 남긴다. 태그는 쓰지 않는다."""


_CORR = re.compile(r"<correction>(.*?)</correction>", re.S | re.I)
_RISK = re.compile(r"<risk\s+level=\"?(none|low|high)\"?\s*/?>", re.I)
_ANY_TAG = re.compile(r"</?(correction|risk)[^>]*>?", re.I)


def parse_reply(raw: str) -> dict:
    raw = raw or ""
    corrections = []
    for m in _CORR.finditer(raw):
        try:
            data = json.loads(m.group(1).strip())
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and it.get("corrected"):
                    corrections.append({k: str(it.get(k, "")) for k in ("original", "corrected", "reason")})
        except (ValueError, TypeError):
            pass
    levels = [m.group(1).lower() for m in _RISK.finditer(raw)]
    risk = "high" if "high" in levels else ("low" if "low" in levels else "none")
    body = _ANY_TAG.sub("", _RISK.sub("", _CORR.sub("", raw)))
    bubbles = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    if len(bubbles) > MAX_BUBBLES:
        bubbles = bubbles[:MAX_BUBBLES - 1] + [" ".join(bubbles[MAX_BUBBLES - 1:])]
    return {"bubbles": bubbles, "corrections": corrections[:MAX_CORRECTIONS], "risk": risk}


TAG_STARTS = ("<correction", "<risk")


def visible_prefix(raw: str) -> str:
    """스트리밍 중 화면에 보내도 되는 앞부분(태그·태그일지 모르는 꼬리는 뺀다)."""
    low = raw.lower()
    cut = len(raw)
    for t in TAG_STARTS:
        i = low.find(t)
        if i >= 0:
            cut = min(cut, i)
    tail = low[:cut]
    j = tail.rfind("<")
    if j >= 0 and any(t.startswith(tail[j:]) for t in TAG_STARTS):
        cut = j
    return raw[:cut]
