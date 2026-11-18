"""웹사이트 보안 점검 에이전트 (Claude Agent SDK).

본인이 소유했거나 서면 허가를 받은 사이트에만 사용하세요.
이 에이전트는 '비침습(non-invasive)' 점검만 합니다.
즉, 일반적인 GET 요청을 보내 응답(헤더/쿠키/노출 정보 등)만 분석하며,
공격 페이로드(SQLi, XSS 등)를 주입하지 않습니다.

실행: python main.py
종료: exit / quit / 종료 입력, 또는 Ctrl+C
"""

import asyncio
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

# allowed_tools의 도구는 자동 승인되고 Bash 등 나머지만 can_use_tool로 확인하는 것이 의도된 설정
warnings.filterwarnings("ignore", message="can_use_tool will not be invoked")

# Windows 콘솔에서 한글이 깨지지 않도록
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "reports"  # 점검 리포트를 저장하는 폴더
WORKSPACE.mkdir(exist_ok=True)

USER_AGENT = "security-review-agent/1.0 (authorized testing only)"
TIMEOUT = 15  # 초

# 이번 실행에서 사용자가 "점검 권한이 있다"고 확인한 호스트 목록(메모리에만 보관)
AUTHORIZED_HOSTS: set[str] = set()

# 보안 관련 응답 헤더와 간단한 설명
SECURITY_HEADERS = {
    "strict-transport-security": "HSTS: HTTPS 강제. 없으면 중간자 공격에 노출될 수 있음",
    "content-security-policy": "CSP: XSS/자원 로딩 제어. 없으면 XSS 피해가 커질 수 있음",
    "x-frame-options": "클릭재킹 방어(iframe 삽입 차단)",
    "x-content-type-options": "nosniff: MIME 스니핑 방어",
    "referrer-policy": "외부로 나가는 Referer 정보 제한",
    "permissions-policy": "카메라/위치 등 브라우저 기능 제한",
}

# 응답 헤더에 그대로 드러나면 버전/구성 정보가 노출되는 헤더
LEAKY_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"]

SYSTEM_PROMPT = f"""당신은 웹사이트의 보안 취약점을 점검하는 보안 리뷰 에이전트입니다.
리포트는 {WORKSPACE} 폴더에 저장합니다.

## 가장 중요한 원칙 (반드시 지킬 것)
- 본인이 소유했거나 명시적 허가를 받은 사이트만 점검합니다.
- 어떤 호스트를 점검하기 전에 반드시 authorize_target 도구로 사용자에게 권한을 확인합니다.
  사용자가 "예"라고 확인하기 전에는 그 호스트로 네트워크 점검 도구를 쓰지 않습니다.
- 이 에이전트는 '비침습' 점검만 합니다. 공격 페이로드(SQL 인젝션, XSS, 명령 주입 등)를
  실제 서버에 주입하지 않습니다. 제공된 도구는 일반 GET 요청으로 응답만 분석합니다.
- 사용자가 다른 사람의 사이트를 무단으로 공격·침투하려 하면 정중히 거절하고,
  허가받은 환경이나 의도적으로 취약하게 만든 실습 사이트(예: DVWA, OWASP Juice Shop)를 권합니다.

## 점검 방식
1. 대상 URL을 받으면 authorize_target으로 권한을 먼저 확인합니다.
2. fetch_headers 로 응답 헤더/쿠키/상태코드를 받아 분석합니다.
3. check_security_headers 로 빠진 보안 헤더를 정리합니다.
4. check_tls 로 HTTPS/인증서 상태를 확인합니다.
5. fetch_page 로 페이지 본문 일부를 받아 눈에 띄는 정보 노출(에러 메시지, 주석 속 비밀,
   디렉터리 목록, 노출된 폼 등)을 살핍니다.

## 리포트 작성
- 사용자가 한국어로 말하면 한국어로 답합니다.
- 발견 항목마다: (1) 무엇이 문제인지 (2) 왜 위험한지 (3) 어떻게 뚫릴 수 있는지 '얕은' 예시
  (4) 고치는 방법. 예시는 개념 설명 수준으로만, 실제 악용 코드를 완성해 주지는 않습니다.
- 위험도를 높음/중간/낮음/정보 로 표시합니다.
- 마지막에 save_report 도구로 리포트를 마크다운 파일로 저장합니다.
- 날짜가 필요하면 current_datetime 도구를 씁니다.
"""


# ---- 공용 함수 -------------------------------------------------------------

def _host_of(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").lower()


def _require_authorized(url: str) -> str | None:
    """권한 확인이 안 된 호스트면 거부 메시지를 돌려준다."""
    host = _host_of(url)
    if not host:
        return "URL에서 호스트를 읽을 수 없습니다."
    if host not in AUTHORIZED_HOSTS:
        return (
            f"'{host}'는 아직 점검 권한이 확인되지 않았습니다. "
            f"먼저 authorize_target 도구로 사용자에게 권한을 확인하세요."
        )
    return None


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")


# ---- 커스텀 도구 -----------------------------------------------------------

@tool("current_datetime", "현재 날짜와 시간을 알려 줍니다.", {})
async def current_datetime(args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
    return {"content": [{"type": "text", "text": now}]}


@tool(
    "authorize_target",
    "점검 대상 호스트에 대해 사용자에게 테스트 권한이 있는지 확인하고 승인 목록에 등록합니다. "
    "네트워크 점검 도구를 쓰기 전에 반드시 먼저 호출하세요.",
    {"url": str},
)
async def authorize_target(args: dict[str, Any]) -> dict[str, Any]:
    host = _host_of(args["url"])
    if not host:
        return {"content": [{"type": "text", "text": "URL에서 호스트를 읽을 수 없습니다."}]}
    if host in AUTHORIZED_HOSTS:
        return {"content": [{"type": "text", "text": f"'{host}'는 이미 이번 실행에서 승인되었습니다."}]}

    prompt = (
        f"\n[권한 확인] '{host}'를 점검하려고 합니다.\n"
        f"  이 사이트를 소유하고 있거나, 점검할 서면 허가를 받았습니까?\n"
        f"  (허가 없는 점검은 법 위반일 수 있습니다.)\n(y/n) > "
    )
    answer = await asyncio.to_thread(input, prompt)
    if answer.strip().lower() in ("y", "yes", "예", "네", "ㅛ"):
        AUTHORIZED_HOSTS.add(host)
        return {"content": [{"type": "text", "text": f"'{host}' 점검 권한 확인됨. 비침습 점검을 진행합니다."}]}
    return {
        "content": [
            {"type": "text", "text": f"'{host}' 점검이 거부되었습니다. 이 호스트는 점검하지 마세요."}
        ]
    }


@tool(
    "fetch_headers",
    "대상 URL에 GET 요청을 보내 상태코드, 응답 헤더, Set-Cookie를 가져옵니다. (비침습)",
    {"url": str},
)
async def fetch_headers(args: dict[str, Any]) -> dict[str, Any]:
    url = args["url"]
    denied = _require_authorized(url)
    if denied:
        return {"content": [{"type": "text", "text": denied}]}

    def _do() -> dict[str, Any]:
        try:
            with urllib.request.urlopen(_build_request(url), timeout=TIMEOUT) as resp:
                status = resp.status
                headers = list(resp.getheaders())
        except urllib.error.HTTPError as e:
            status = e.code
            headers = list(e.headers.items()) if e.headers else []
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}

        lower = {k.lower(): v for k, v in headers}
        cookies = [v for k, v in headers if k.lower() == "set-cookie"]
        cookie_flags = []
        for c in cookies:
            low = c.lower()
            cookie_flags.append(
                {
                    "cookie": c.split(";")[0],
                    "secure": "secure" in low,
                    "httponly": "httponly" in low,
                    "samesite": next(
                        (p.split("=", 1)[1].strip() for p in low.split(";") if "samesite" in p),
                        None,
                    ),
                }
            )
        return {
            "status": status,
            "headers": {k: v for k, v in headers},
            "leaky_headers": {h: lower[h] for h in LEAKY_HEADERS if h in lower},
            "cookies": cookie_flags,
        }

    result = await asyncio.to_thread(_do)
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


@tool(
    "check_security_headers",
    "대상 URL의 응답에서 권장 보안 헤더(HSTS, CSP, X-Frame-Options 등)가 있는지 점검합니다.",
    {"url": str},
)
async def check_security_headers(args: dict[str, Any]) -> dict[str, Any]:
    url = args["url"]
    denied = _require_authorized(url)
    if denied:
        return {"content": [{"type": "text", "text": denied}]}

    def _do() -> dict[str, Any]:
        try:
            with urllib.request.urlopen(_build_request(url), timeout=TIMEOUT) as resp:
                headers = {k.lower(): v for k, v in resp.getheaders()}
        except urllib.error.HTTPError as e:
            headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}

        present, missing = {}, {}
        for name, why in SECURITY_HEADERS.items():
            if name in headers:
                present[name] = headers[name]
            else:
                missing[name] = why
        return {"present": present, "missing": missing}

    result = await asyncio.to_thread(_do)
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


@tool(
    "check_tls",
    "HTTPS 연결과 TLS 인증서 정보(만료일, 발급자, 호스트명 일치)를 확인합니다.",
    {"url": str},
)
async def check_tls(args: dict[str, Any]) -> dict[str, Any]:
    url = args["url"]
    denied = _require_authorized(url)
    if denied:
        return {"content": [{"type": "text", "text": denied}]}
    host = _host_of(url)
    parsed = urlparse(url if "://" in url else f"https://{url}")
    port = parsed.port or 443

    def _do() -> dict[str, Any]:
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    version = ssock.version()
        except Exception as e:  # noqa: BLE001
            return {"https_ok": False, "error": f"{type(e).__name__}: {e}"}

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        return {
            "https_ok": True,
            "tls_version": version,
            "subject": subject.get("commonName"),
            "issuer": issuer.get("organizationName") or issuer.get("commonName"),
            "not_after": cert.get("notAfter"),
            "not_before": cert.get("notBefore"),
        }

    result = await asyncio.to_thread(_do)
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


@tool(
    "fetch_page",
    "대상 URL의 페이지 본문 일부(최대 20000자)를 가져옵니다. 에러 메시지·주석·노출 정보 분석용. (비침습)",
    {"url": str},
)
async def fetch_page(args: dict[str, Any]) -> dict[str, Any]:
    url = args["url"]
    denied = _require_authorized(url)
    if denied:
        return {"content": [{"type": "text", "text": denied}]}

    def _do() -> str:
        try:
            with urllib.request.urlopen(_build_request(url), timeout=TIMEOUT) as resp:
                raw = resp.read(400_000)
                charset = resp.headers.get_content_charset() or "utf-8"
        except urllib.error.HTTPError as e:
            raw = e.read(400_000) if hasattr(e, "read") else b""
            charset = "utf-8"
        except Exception as e:  # noqa: BLE001
            return f"오류: {type(e).__name__}: {e}"
        text = raw.decode(charset, errors="replace")
        return text[:20_000]

    body = await asyncio.to_thread(_do)
    return {"content": [{"type": "text", "text": body}]}


@tool(
    "save_report",
    "보안 점검 리포트를 reports 폴더에 마크다운 파일로 저장합니다.",
    {"filename": str, "markdown": str},
)
async def save_report(args: dict[str, Any]) -> dict[str, Any]:
    name = args["filename"].strip()
    if not name.endswith(".md"):
        name += ".md"
    # 폴더 밖으로 나가지 못하게 파일 이름만 사용
    safe = Path(name).name
    path = WORKSPACE / safe
    path.write_text(args["markdown"], encoding="utf-8")
    return {"content": [{"type": "text", "text": f"리포트 저장 완료: {path}"}]}


security_tools = create_sdk_mcp_server(
    name="secrev",
    version="1.0.0",
    tools=[
        current_datetime,
        authorize_target,
        fetch_headers,
        check_security_headers,
        check_tls,
        fetch_page,
        save_report,
    ],
)


# ---- 권한 확인: 혹시 모델이 Bash를 쓰려 하면 매번 사용자에게 묻기 --------------

async def ask_permission(
    tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        answer = await asyncio.to_thread(
            input, f"\n[확인] 이 명령을 실행할까요?\n  {command}\n(y/n) > "
        )
        if answer.strip().lower() in ("y", "yes", "예", "네"):
            return PermissionResultAllow()
        return PermissionResultDeny(message="사용자가 명령 실행을 거부했습니다.")
    return PermissionResultAllow()


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(WORKSPACE),
        # 기본은 Opus 5.5. 더 빠르고 저렴하게 쓰려면 AGENT_MODEL 환경변수로 바꾸세요.
        # 예: $env:AGENT_MODEL = "claude-sonnet-5-5"
        model=os.environ.get("AGENT_MODEL") or "claude-opus-5-5",
        permission_mode="acceptEdits",
        allowed_tools=[
            "Read", "Write", "Edit", "Glob", "Grep",
            "mcp__secrev__current_datetime",
            "mcp__secrev__authorize_target",
            "mcp__secrev__fetch_headers",
            "mcp__secrev__check_security_headers",
            "mcp__secrev__check_tls",
            "mcp__secrev__fetch_page",
            "mcp__secrev__save_report",
        ],
        mcp_servers={"secrev": security_tools},
        can_use_tool=ask_permission,
        max_turns=40,
    )


async def print_response(client: ClaudeSDKClient) -> None:
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"\n에이전트: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"  · 도구 사용: {block.name}")
        elif isinstance(message, ResultMessage):
            cost = message.total_cost_usd
            if message.is_error:
                print(f"\n(오류로 끝남: {message.subtype})")
            if cost:
                print(f"  (이번 요청 비용 약 ${cost:.4f})")


BANNER = """웹사이트 보안 점검 에이전트입니다.
⚠️  본인이 소유했거나 서면 허가를 받은 사이트에만 사용하세요.
    이 에이전트는 비침습 점검(응답 헤더/쿠키/노출 정보 분석)만 합니다.

점검할 URL과 함께 요청하세요. 예: "https://example.com 보안 점검해 줘"
종료: exit
"""


async def main() -> None:
    print(BANNER)
    print(f"리포트 폴더: {WORKSPACE}\n")
    async with ClaudeSDKClient(options=build_options()) as client:
        while True:
            user_input = (await asyncio.to_thread(input, "\n나: ")).lstrip("﻿").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "종료"):
                break
            await client.query(user_input)
            await print_response(client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n종료합니다.")
