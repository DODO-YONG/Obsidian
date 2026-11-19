"""제미나이 무료 등급 REST 호출 (설치할 것 없음). 답장을 글자 조각으로 흘려보낸다(스트리밍).

- 키: 환경 변수 → server/.env → 저장소 루트 .env 의 GOOGLE_API_KEY. 요청 헤더로만 보낸다.
- 모델: HEARTLINE_MODELS(쉼표)가 있으면 그것, 없으면 아래 순서. 한도·바쁨이면 다음 모델로.
- 💸 무료 등급 키만 쓴다(결제 연결된 키 금지).
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 대화는 빠른 답이 중요해서 가벼운 모델을 먼저. 바쁘거나 15초 안에 답이 없으면 다음 모델로.
DEFAULT_MODELS = ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash"]
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_LOW_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


class RateLimited(Exception):
    """이 모델은 지금 한도·바쁨 → 다음 모델로."""


class AllModelsBusy(Exception):
    pass


def env(name, default=None):
    if os.environ.get(name):
        return os.environ[name]
    files = [HERE / ".env"]
    if (HERE.parents[2] / "docs" / "heartline").exists():  # 저장소 안에서 실행할 때만 루트 .env 도 본다
        files.append(HERE.parents[2] / ".env")
    for f in files:
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
    return default


def http_transport(api_key, timeout=15):
    def transport(model, payload):
        req = urllib.request.Request(
            API.format(model=model), data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (404, 429, 500, 503):
                raise RateLimited(f"{model}: HTTP {e.code}")
            raise
        except (TimeoutError, urllib.error.URLError) as e:
            raise RateLimited(f"{model}: 연결 문제 {e}")
        with resp:
            for line in resp:
                line = line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    continue
                for cand in data.get("candidates") or []:
                    for part in (cand.get("content") or {}).get("parts") or []:
                        if part.get("text"):
                            yield part["text"]
    return transport


class GeminiClient:
    def __init__(self, api_key, models=None, transport=None):
        self.models = list(models or DEFAULT_MODELS)
        self.transport = transport or http_transport(api_key)
        self._cooldown = {}

    def _payload(self, system, messages):
        contents = []
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            text = str(m.get("content") or "")
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"][0]["text"] += "\n" + text
            else:
                contents.append({"role": role, "parts": [{"text": text}]})
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents or [{"role": "user", "parts": [{"text": "안녕"}]}],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 600},
            "safetySettings": SAFETY_SETTINGS,
        }

    def stream(self, system, messages):
        payload = self._payload(system, messages)
        now = time.time()
        order = sorted(self.models, key=lambda m: self._cooldown.get(m, 0) > now)
        for model in order:
            try:
                it = iter(self.transport(model, payload))
                first = next(it, None)
            except RateLimited:
                self._cooldown[model] = time.time() + 300
                continue
            if first is not None:
                yield first
            yield from it
            return
        raise AllModelsBusy("모든 무료 모델이 바빠요")

    def complete(self, system, messages):
        return "".join(self.stream(system, messages))


def from_env():
    key = env("GOOGLE_API_KEY")
    if not key:
        return None
    models = [m.strip() for m in (env("HEARTLINE_MODELS") or "").split(",") if m.strip()]
    return GeminiClient(key, models or None)
