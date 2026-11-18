# 📝 DY-005 PRIMER — 초보자 FAQ 15개 (`beginner-faq`)

> 한 줄 설명: 내 분야에서 초보자가 자주 묻는 질문 15개와 두 줄 답을 Gemini에게 받아 `answer.md`로 저장

- **상태**: 개발중
- **위키 메모**: `wiki/projects/beginner-faq/` (아직 없음)

## 동작
- `ask.py`의 `instruction`(역할·할 일·답 모양)을 **시스템 지시**로, `question`을 질문으로 보낸다.
- 요청은 **한 번만** 보낸다 (재시도 끔: `attempts=1`).
- `answer.md`가 이미 있으면 **새 요청 없이** 저장된 답만 보여 준다. 다시 받으려면 `answer.md`를 지운다.
- 💸 Gemini 무료 등급 키를 쓴다. 개인정보·`private/` 내용은 넣지 않는다(무료 등급은 보낸 내용이 서비스 개선에 쓰일 수 있음).

## 실행 방법
```bash
cd ~/Obsidian/agents/beginner-faq
python3 -m venv .venv                 # 처음 한 번
source .venv/bin/activate             # 가상 환경 켜기
pip install -r requirements.txt       # 처음 한 번
python ask.py
```
`.env`에 `GOOGLE_API_KEY`와 `GEMINI_MODEL`이 있어야 한다 (`.env.example` 참고).
`ask.py`의 `[내 분야]`를 실제 분야로 바꾼 뒤 실행한다.
