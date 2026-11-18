"""AWS(Amazon) 16 Leadership Principles — 연습용 요약과 질문 씨앗.

설명은 원문 번역이 아니라 연습용으로 직접 쓴 짧은 풀이다.
공식 원문은 https://www.amazon.jobs/content/en/our-workplace/leadership-principles 참고.
질문은 행동 면접에서 흔히 나오는 유형을 직접 정리한 것이다.
"""

PRINCIPLES: list[dict] = [
    {
        "name": "Customer Obsession",
        "ko": "고객 집착",
        "gist": "고객에서 출발해 거꾸로 일한다. 경쟁사보다 고객을 먼저 본다.",
        "questions": [
            "Tell me about a time you went above and beyond for a customer or user.",
            "Describe a time you used customer feedback to change what you were building.",
        ],
    },
    {
        "name": "Ownership",
        "ko": "주인의식",
        "gist": "장기적으로 생각하고, '내 일이 아니다'라고 말하지 않는다.",
        "questions": [
            "Tell me about a time you took on something outside your responsibilities.",
            "Describe a time you had to make a decision with long-term consequences.",
        ],
    },
    {
        "name": "Invent and Simplify",
        "ko": "발명과 단순화",
        "gist": "새로운 방법을 찾고, 복잡한 것을 단순하게 만든다.",
        "questions": [
            "Tell me about a time you simplified a complex process.",
            "Describe the most innovative thing you have built.",
        ],
    },
    {
        "name": "Are Right, A Lot",
        "ko": "대체로 옳은 판단",
        "gist": "좋은 판단력과 직관, 다양한 관점으로 자기 생각을 검증한다.",
        "questions": [
            "Tell me about a time you made a decision with incomplete information.",
            "Describe a time you were wrong. How did you find out and what did you do?",
        ],
    },
    {
        "name": "Learn and Be Curious",
        "ko": "배우고 호기심 갖기",
        "gist": "계속 배우고 스스로를 개선하며, 새로운 가능성을 탐구한다.",
        "questions": [
            "Tell me about something you learned recently on your own and how you applied it.",
            "Describe a time you failed. What did you learn?",
        ],
    },
    {
        "name": "Hire and Develop the Best",
        "ko": "최고의 인재 채용·육성",
        "gist": "기준을 높이고, 다른 사람의 성장을 돕는다.",
        "questions": [
            "Tell me about a time you helped someone grow or improve.",
            "Describe a time you gave someone difficult feedback.",
        ],
    },
    {
        "name": "Insist on the Highest Standards",
        "ko": "최고 수준 고집",
        "gist": "남들이 지나치다 할 만큼 높은 기준을 유지하고 결함을 넘기지 않는다.",
        "questions": [
            "Tell me about a time you refused to compromise on quality.",
            "Describe a time you raised the bar on something your team was doing.",
        ],
    },
    {
        "name": "Think Big",
        "ko": "크게 생각하기",
        "gist": "작게 생각하면 작게 된다. 대담한 방향을 제시한다.",
        "questions": [
            "Tell me about a time you proposed a bold idea.",
            "Describe a project where you thought beyond the immediate requirements.",
        ],
    },
    {
        "name": "Bias for Action",
        "ko": "실행 우선",
        "gist": "속도가 중요하다. 되돌릴 수 있는 결정은 빠르게 내리고 계산된 위험을 감수한다.",
        "questions": [
            "Tell me about a time you acted quickly without all the information.",
            "Describe a time you took a calculated risk.",
        ],
    },
    {
        "name": "Frugality",
        "ko": "절약",
        "gist": "적은 자원으로 더 많이 해낸다. 제약은 창의성을 낳는다.",
        "questions": [
            "Tell me about a time you accomplished something with limited resources.",
            "Describe a time you saved time or money without hurting quality.",
        ],
    },
    {
        "name": "Earn Trust",
        "ko": "신뢰 얻기",
        "gist": "경청하고 솔직하게 말하며, 자신의 실수도 인정한다.",
        "questions": [
            "Tell me about a time you admitted a mistake.",
            "Describe a time you built trust with someone who doubted you.",
        ],
    },
    {
        "name": "Dive Deep",
        "ko": "깊이 파고들기",
        "gist": "모든 수준에서 세부를 알고, 수치와 사실이 다르면 끝까지 확인한다.",
        "questions": [
            "Tell me about a time you found the root cause of a difficult problem.",
            "Describe a time data told a different story than people expected.",
        ],
    },
    {
        "name": "Have Backbone; Disagree and Commit",
        "ko": "소신 있게 반대하고, 결정되면 전념",
        "gist": "불편해도 이견을 말하고, 결정이 나면 온전히 따른다.",
        "questions": [
            "Tell me about a time you disagreed with a teammate or manager.",
            "Describe a time you committed to a decision you disagreed with.",
        ],
    },
    {
        "name": "Deliver Results",
        "ko": "결과 내기",
        "gist": "핵심 결과에 집중하고, 장애물이 있어도 제때 해낸다.",
        "questions": [
            "Tell me about a time you delivered under a tight deadline.",
            "Describe a time you hit a major obstacle and still delivered.",
        ],
    },
    {
        "name": "Strive to be Earth's Best Employer",
        "ko": "최고의 일터 만들기",
        "gist": "함께 일하는 사람이 안전하고 성장하며 즐겁게 일하도록 돕는다.",
        "questions": [
            "Tell me about a time you made your team a better place to work.",
            "Describe a time you supported a teammate who was struggling.",
        ],
    },
    {
        "name": "Success and Scale Bring Broad Responsibility",
        "ko": "성공과 규모에 따르는 넓은 책임",
        "gist": "내 일이 사회·사용자·환경에 미치는 영향까지 책임진다.",
        "questions": [
            "Tell me about a time you considered the wider impact of your work.",
            "Describe a time you protected users' privacy or safety.",
        ],
    },
]

NAMES = [p["name"] for p in PRINCIPLES]
