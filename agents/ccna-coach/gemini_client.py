"""Gemini REST API를 직접 호출한다 (설치할 것 없음).

- 키: 환경 변수 또는 볼트 루트 .env 의 GOOGLE_API_KEY (요청 헤더로만 보냄, URL·브라우저에 노출 안 함)
- 모델: GEMINI_MODEL 이 있으면 그것만, 없으면 아래 순서로 시도하고 바쁨(503)·한도(429)·없음(404)·시간 초과면 다음 모델로.
- 답은 JSON으로 받는다(responseMimeType). 스키마를 못 받는 모델이면 스키마 없이 다시 시도.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]
_cooldown: dict[str, float] = {}  # 모델 → 이 시각까지 건너뜀
DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite"]


class GeminiError(Exception):
    pass


def _env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    env = VAULT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def models() -> list[str]:
    m = _env("GEMINI_MODEL")
    return [m] if m else DEFAULT_MODELS


def has_key() -> bool:
    return bool(_env("GOOGLE_API_KEY"))


def _post(model: str, body: dict, key: str, timeout: int) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON 없음")
    return json.loads(m.group(0))


def ask_json(system: str, prompt: str, schema: dict | None = None) -> tuple[dict, str]:
    """(결과 dict, 사용한 모델) 을 돌려준다."""
    key = _env("GOOGLE_API_KEY")
    if not key:
        raise GeminiError("GOOGLE_API_KEY 가 없습니다. 볼트 루트 .env 에 넣어 주세요.")
    base = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    # 최근에 한도 초과·무응답이던 모델은 맨 뒤로 보낸다(매번 기다리지 않게). 모두 바쁘면 2초 쉬고 한 번 더.
    for attempt in range(2):
        try:
            return _ask_once(base, schema, key)
        except GeminiError as e:
            if attempt == 1 or not any(c in str(e) for c in ("HTTP 503", "HTTP 429", "연결 문제")):
                raise
            time.sleep(2)
    raise GeminiError("모든 모델 실패")


def _ask_once(base: dict, schema: dict | None, key: str) -> tuple[dict, str]:
    now = time.time()
    order = sorted(models(), key=lambda m: _cooldown.get(m, 0) > now)
    last_err = "모든 모델 실패"
    for i, model in enumerate(order):
        is_last = i == len(order) - 1
        for use_schema in ([True, False] if schema else [False]):
            body = json.loads(json.dumps(base))
            if use_schema:
                body["generationConfig"]["responseSchema"] = schema
            try:
                data = _post(model, body, key, 90 if is_last else 15)
                cand = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                if not text:
                    raise GeminiError(f"빈 답 ({model}, {cand.get('finishReason', '?')})")
                return _parse_json(text), model
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:300]
                if e.code == 400 and use_schema:
                    continue  # 스키마를 못 받는 모델 → 스키마 없이 재시도
                last_err = f"{model}: HTTP {e.code} {msg}"
                if e.code in (429, 503, 404):
                    _cooldown[model] = time.time() + (3600 if e.code == 404 else 600)
                if e.code in (429, 503, 404, 500) and not is_last:
                    break  # 다음 모델
                raise GeminiError(last_err)
            except (TimeoutError, urllib.error.URLError) as e:
                last_err = f"{model}: 연결 문제 {e}"
                _cooldown[model] = time.time() + 120
                if not is_last:
                    break
                raise GeminiError(last_err)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = f"{model}: 답을 JSON으로 읽지 못함 ({e})"
                if not is_last:
                    break
                raise GeminiError(last_err)
    raise GeminiError(last_err)
