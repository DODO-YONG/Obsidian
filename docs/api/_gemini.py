"""제미나이 REST 호출 (Vercel용). agents/ccna-coach/gemini_client.py 와 같은 방식, 키는 환경변수에서만 읽는다.

- 키: Vercel 환경변수 GOOGLE_API_KEY (요청 헤더로만 보냄, 브라우저·저장소에 없음)
- 모델: GEMINI_MODEL 이 있으면 그것만, 없으면 아래 순서. 바쁨·한도·없음·시간 초과면 다음 모델로.
- Vercel 함수 최대 60초 안에 끝나도록 대기 시간을 줄였다.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

_cooldown: dict[str, float] = {}  # 모델 → 이 시각까지 건너뜀 (함수 인스턴스가 살아 있는 동안만)
DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite"]


class GeminiError(Exception):
    pass


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


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


def ask_json(system: str, prompt: str, schema: dict | None = None, temperature: float = 0.7) -> tuple[dict, str]:
    """(결과 dict, 사용한 모델) 을 돌려준다."""
    key = _env("GOOGLE_API_KEY")
    if not key:
        raise GeminiError("GOOGLE_API_KEY 가 없습니다. Vercel 환경변수에 넣어 주세요.")
    base = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": temperature},
    }
    # 최근에 한도 초과·무응답이던 모델은 맨 뒤로 보낸다(매번 기다리지 않게). 모두 바쁘면 2초 쉬고 한 번 더.
    t0 = time.time()
    for attempt in range(2):
        try:
            return _ask_once(base, schema, key)
        except GeminiError as e:  # Vercel 함수 시간(60초) 안에서만 한 번 더
            if attempt == 1 or time.time() - t0 > 15 or not any(c in str(e) for c in ("HTTP 503", "HTTP 429", "연결 문제")):
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
                data = _post(model, body, key, 35 if is_last else 12)
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
