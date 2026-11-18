# 웹사이트 보안 점검 에이전트

> 📖 **소개 페이지**: https://dodo-yong.github.io/security-agent/

Claude Agent SDK(Python)로 만든 대화형 보안 점검 에이전트입니다.
URL을 주면 **비침습(non-invasive)** 방식으로 점검하고, 취약점이 있으면
**무엇이 문제인지 · 왜 위험한지 · 얕은 수준에서 어떻게 뚫릴 수 있는지 · 고치는 법**을
리포트로 정리합니다.

## ⚠️ 먼저 꼭 읽어 주세요

- **본인이 소유했거나 서면 허가를 받은 사이트에만** 사용하세요.
- 허가 없이 남의 사이트를 점검·공격하면 한국에서는 **정보통신망법 위반**으로
  처벌받을 수 있습니다.
- 이 에이전트는 호스트마다 실행할 때 **"점검 권한이 있습니까?"**를 물어보고,
  "예"라고 답한 호스트에만 네트워크 점검을 합니다.
- 연습하고 싶다면 일부러 취약하게 만든 실습 사이트를 쓰세요:
  [DVWA](https://github.com/digininja/DVWA),
  [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/).

## 점검 방식 (비침습)

실제 서버에 공격 페이로드(SQL 인젝션, XSS 등)를 **주입하지 않습니다**.
일반 GET 요청을 보내 응답만 분석합니다.

| 점검 항목 | 보는 것 |
|---|---|
| 응답 헤더 | `Server`, `X-Powered-By` 등 버전/구성 정보 노출 |
| 보안 헤더 | HSTS, CSP, X-Frame-Options, X-Content-Type-Options 등 빠진 헤더 |
| 쿠키 플래그 | `Secure` / `HttpOnly` / `SameSite` 설정 여부 |
| TLS/인증서 | HTTPS 연결, 인증서 만료일·발급자·호스트명 일치 |
| 페이지 본문 | 에러 메시지, 주석 속 비밀, 디렉터리 목록 등 눈에 띄는 노출 |

더 정밀한 점검(실제 공격 페이로드 주입)은 본인 소유 사이트에서만 해야 하며,
이 버전에는 넣지 않았습니다.

## 준비 (처음 한 번)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

인증: **Claude 구독 로그인으로만** 실행합니다. 💸 추가 요금을 막기 위해 `ANTHROPIC_API_KEY`가
설정돼 있으면 실행을 거부합니다. 화면의 "$" 금액은 API 요금 환산 참고치일 뿐 실제 청구가 아닙니다.

## 실행

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

예시 요청:
- `https://example.com 보안 점검해 줘`
- `내 사이트 https://mysite.local 의 보안 헤더랑 쿠키 설정 봐 줘`
- `http://localhost:3000 점검하고 리포트 저장해 줘`

실행하면 호스트마다 권한을 한 번 묻습니다. "예"라고 답해야 점검이 진행됩니다.
점검이 끝나면 `reports/` 폴더에 마크다운 리포트가 저장됩니다.

종료하려면 `exit` 또는 `종료`를 입력하세요.

## 구성

| 파일 | 설명 |
|---|---|
| `main.py` | 에이전트 본체 (시스템 프롬프트, 점검 도구, 권한 설정) |
| `reports/` | 점검 리포트가 저장되는 폴더 |

## 도구 목록

| 도구 | 하는 일 |
|---|---|
| `authorize_target` | 점검 전 권한 확인 (네트워크 도구 사용 전 필수) |
| `fetch_headers` | 상태코드·응답 헤더·쿠키 플래그 수집 |
| `check_security_headers` | 권장 보안 헤더 존재 여부 점검 |
| `check_tls` | HTTPS/TLS 인증서 확인 |
| `fetch_page` | 페이지 본문 일부 수집(노출 정보 분석용) |
| `save_report` | 리포트를 마크다운으로 저장 |

## 고쳐 쓰기

- **역할·점검 방침 바꾸기**: `main.py`의 `SYSTEM_PROMPT` 수정.
- **점검 항목 추가**: `@tool(...)`로 함수를 만들고 `create_sdk_mcp_server`의 `tools`와
  `allowed_tools`(`mcp__secrev__<도구이름>`)에 추가.
- **모델 지정**: 기본값은 `claude-opus-5-5`(가장 똑똑함). 구독 사용량을 아끼려면
  `.env`에 `AGENT_MODEL=claude-sonnet-5-5`를 넣으세요.
