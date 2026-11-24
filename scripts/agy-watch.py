#!/usr/bin/env python3
"""agy --output-format stream-json 출력을 사람이 읽기 좋게 보여 준다(gemini.sh -w).
도구를 쓸 때마다 한 줄, 제미나이의 글은 나오는 대로. 실패하면 종료 코드 1."""
import json, sys, time

start = time.time()
def stamp():
    s = int(time.time() - start)
    return f"\033[2m{s // 60:02d}:{s % 60:02d}\033[0m"

def short(params):
    for k in ("Path", "AbsolutePath", "CommandLine", "Query", "Url", "SearchPath", "TargetFile", "DirectoryPath"):
        if k in params and params[k]:
            return str(params[k]).replace("\n", " ")[:110]
    return ""

status = "UNKNOWN"
in_text = False
for line in sys.stdin:
    try:
        ev = json.loads(line)
    except ValueError:
        print(line, end="", flush=True)  # 오류 문구 등은 그대로
        continue
    kind = ev.get("event")
    if kind == "init":
        print(f"{stamp()} 🤖 agy 시작 ({ev['init'].get('model', '')})", flush=True)
    elif kind == "step_update":
        st = ev["step_update"]
        if st.get("step_type") == "tool" and st.get("state") == "ACTIVE":
            if in_text: print(); in_text = False
            info = st.get("tool_info", {})
            print(f"{stamp()} ▶ {info.get('name', st.get('tool_name'))} {short(info.get('parameters', {}))}", flush=True)
        elif st.get("step_type") == "agent_response" and st.get("text_delta"):
            print(st["text_delta"], end="", flush=True); in_text = True
    elif kind == "result":
        r = ev["result"]; status = r.get("status", "UNKNOWN")
        if in_text: print()
        print(f"{stamp()} {'✅' if status == 'SUCCESS' else '⛔'} 끝 ({status}, {int(r.get('duration_seconds', 0))}초)", flush=True)
sys.exit(0 if status == "SUCCESS" else 1)
