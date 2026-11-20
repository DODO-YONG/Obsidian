"""TRACER 화면 시험 준비: dev/harness.py(가짜 로그인·가짜 DB·가짜 제미나이)를 띄우고 시험이 끝나면 끈다.
실제 Supabase·제미나이·Claude 사용량 0."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / "dev" / "harness.py"
PORT = int(os.environ.get("TRACER_E2E_PORT", "8798"))
BASE = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="session")
def base_url():
    env = {**os.environ, "TRACER_HARNESS_PORT": str(PORT)}
    for k in ("GOOGLE_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "ANTHROPIC_API_KEY"):
        env.pop(k, None)  # 진짜 키가 섞여 들어가지 않게
    proc = subprocess.Popen([sys.executable, str(HARNESS)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
            break
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError("시험 서버가 바로 꺼짐:\n" + proc.stdout.read())
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("시험 서버가 10초 안에 뜨지 않음")
    yield BASE
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def errors(page):
    """페이지의 자바스크립트 오류를 모은다. 시험 끝에 비어 있어야 통과."""
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    yield errs
    assert not errs, "자바스크립트 오류: " + " | ".join(errs)


@pytest.fixture
def logged_in(page):
    """가짜 로그인(주인 계정 owner@example.com). 실제 구글 로그인 없음."""
    page.add_init_script("localStorage.setItem('fake-tok', 'a')")
    return page
