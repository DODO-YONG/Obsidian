"""문제 저장소·권한·한도 로직 시험 (가짜 DB·가짜 제미나이, 네트워크·사용량 없음).  실행: python3 agents/ccna-coach/dev/test_core.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fakes import *  # noqa
ok = lambda c, m: print(("✅ " if c else "❌ ") + m) or (c or sys.exit(1))
o = core.current_user("o"); a = core.current_user("a", "Mozilla/5.0 (iPhone; CPU iPhone OS) Safari/604")
ok(o["role"] == "owner" and a["role"] == "user", "오너 이메일 → owner, 나머지 user")
ok(a["_device"].startswith("모바일 · iOS"), "기기 요약: " + a["_device"])
try: core.current_user("zzz"); ok(False, "")
except core.ApiError as e: ok(e.code == 401, "로그인 안 하면 401")

# 객관식: 문제은행에서만 (제미나이 0번). 문제은행 미리 채우기 = generate 로 3개
try: core.new_question(o, ["2.1"], "보통", "mcq"); ok(False, "")
except core.ApiError as e: ok(e.code == 404 and calls["n"] == 0, "객관식 묶음이 비어 있으면 404 — 제미나이 안 부름")
for _ in range(3): core.generate("2.1", "보통", "mcq", o)
before = calls["n"]
q = core.new_question(a, ["2.1"], "보통", "mcq")
ok(q["source"] == "bank" and calls["n"] == before, "객관식은 문제은행에서 — 제미나이 0번")
ok(all("answer" not in x for x in [core.public_q(T["questions"][0], "x")]), "화면에 정답 안 보냄")
seen_a = [core.new_question(a, ["2.1"], "보통", "mcq")["id"] for _ in range(2)] + [q["id"]]
ok(len(set(seen_a)) == 3, "같은 사람에게 같은 문제를 반복하지 않음")
q4 = core.new_question(a, ["2.1"], "보통", "mcq")
ok(q4["source"] == "bank" and q4["id"] in seen_a and calls["n"] == before, "다 풀었으면 이미 받은 문제를 다시 — 새로 안 만듦")
ok(not any(r["ai"] for r in T["activity_log"] if r.get("action") == "question" and r["detail"].get("qtype") == "mcq"), "객관식 받기는 AI 사용으로 안 셈")

# 채점: 객관식은 저장된 해설로
before = calls["n"]
r = core.grade(a, q["id"], "C")
ok(r["verdict"] == "오답" and r["why_wrong"] == "C no" and r["correct_answer"] == "B. b" and calls["n"] == before, "객관식 채점·보기별 해설 — 제미나이 0번")
r2 = core.grade(a, q["id"], "B")
ok(r2["first"] is False and len([x for x in T["attempts"] if x["user_id"] == "u-alice"]) == 1, "같은 문제 두 번 채점해도 기록은 1번")
try: core.grade(a, T["questions"][-1]["id"] if T["questions"][-1]["id"] not in seen_a + [q4["id"]] else "0"*36, "A"); ok(False, "")
except core.ApiError as e: ok(e.code in (400, 404), "안 받은 문제는 채점 불가")

# 주관식은 잠시 멈춤(기본) → 403, 켜면(TRACER_SHORT=1) 판정만 제미나이
before = calls["n"]
try: core.new_question(a, ["3.4"], "쉬움", "short"); ok(False, "")
except core.ApiError as e: ok(e.code == 403 and e.extra.get("code") == "short_off" and calls["n"] == before, "주관식 멈춤 → 403, 제미나이 안 부름")
core.SHORT_ON = True
core.BANK_RATIO = 0.0
s = core.new_question(a, ["3.4"], "쉬움", "short")
before = calls["n"]; r = core.grade(a, s["id"], "it is OSPF")
ok(r["verdict"] == "부분 정답" and calls["n"] == before + 1, "주관식 판정은 제미나이 1번")

# 한도: daily_limit 0 → 객관식은 계속, 주관식은 저장소에 남은 문제가 있으면 그걸로, 없으면 429
T["profiles"][1]["daily_limit"] = 0; a = core.current_user("a")
ok(core.new_question(a, ["2.1"], "보통", "mcq")["source"] == "bank", "한도 소진해도 객관식은 계속")
core.BANK_RATIO = 0.0
for _ in range(3): core.new_question(o, ["4.1"], "어려움", "short")
q = core.new_question(a, ["4.1"], "어려움", "short")
ok(q["source"] == "bank", "한도 소진 → 주관식 저장소 문제로 대체")
for _ in range(2): core.new_question(a, ["4.1"], "어려움", "short")
try: core.new_question(a, ["4.1"], "어려움", "short"); ok(False, "")
except core.ApiError as e: ok(e.code == 429, "한도 소진 + 주관식 저장소도 다 풂 → 429")
try: core.explain_custom(a, "Q?", "", ""); ok(False, "")
except core.ApiError as e: ok(e.code == 429, "내 문제 해설도 한도 적용")
ok(core.ai_left(o) > 1000, "오너는 한도 없음")

# 권한 회수·차단
T["profiles"][1].update(daily_limit=30, can_practice=False); a = core.current_user("a")
try: core.new_question(a, [], "보통", "mcq"); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "AI 문제 권한 회수 → 403")
core.admin_update_user(o, {"id": "u-alice", "status": "blocked"}); a = core.current_user("a")
try: core.explain_custom(a, "Q", "", ""); ok(False, "")
except core.ApiError as e: ok(e.code == 403 and e.extra.get("code") == "blocked", "차단 → 403")
try: core.admin_summary(a); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "일반 사용자는 관리자 API 403")
try: core.admin_update_user(o, {"id": "u-owner", "status": "blocked"}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "주인 계정은 못 바꿈")

# 신고 3건 → 출제 중지, 검토 완료 → 복구
qid = T["questions"][0]["id"]
for uid in ("u-x", "u-y", "u-z"):
    T["question_seen"].append({"user_id": uid, "question_id": qid, "graded_at": None})
    core.report({"id": uid, "status": "active", "role": "user"}, qid, "answer wrong")
ok(T["questions"][0]["status"] == "flagged", "신고 3건 → 출제 중지(flagged)")
core.admin_update_question(o, {"id": qid, "resolve": True})
ok(T["questions"][0]["status"] == "active" and T["questions"][0]["reports"] == 0, "검토 완료 → 다시 출제")
ok(any(x["action"] == "admin" for x in T["activity_log"]), "관리자 작업도 활동 기록에 남음")
ok(not any("ip" in str(x).lower().split("'")[1::2] for x in T["activity_log"]), "IP 저장 안 함")

# 마이페이지 풀이 기록: 본인 것만, 최신순, 오답만 거르기, 더 보기
T["attempts"].clear()
for i, v in enumerate(["정답", "오답", "부분 정답", "정답", "오답"]):
    T["attempts"].append({"user_id": "u-owner", "mode": "practice", "sub": "3.4", "qtype": "mcq", "difficulty": "보통",
                          "verdict": v, "question": f"Q{i}", "user_answer": "A", "at": f"2026-11-22T10:0{i}:00+00:00"})
T["attempts"].append({"user_id": "u-alice", "mode": "practice", "sub": "1.1", "qtype": "mcq", "verdict": "오답",
                      "question": "남의 기록", "at": "2026-11-22T11:00:00+00:00"})
h = core.history(o, {"limit": "2"})
ok([x["question"] for x in h["items"]] == ["Q4", "Q3"] and h["more"], "풀이 기록: 최신순 · 더 보기 있음")
h2 = core.history(o, {"limit": "2", "offset": "4"})
ok([x["question"] for x in h2["items"]] == ["Q0"] and not h2["more"], "풀이 기록: 다음 쪽")
w = core.history(o, {"only": "wrong"})
ok([x["question"] for x in w["items"]] == ["Q4", "Q2", "Q1"], "틀린 문제만(부분 정답 포함)")
ok(all(x["question"] != "남의 기록" for x in core.history(o, {"limit": "50"})["items"]), "남의 기록은 안 보임")
ok(w["items"][0]["sub_name"].startswith("단일 영역 OSPFv2"), "범위 이름 함께 보냄")
try: core.history(o, {"limit": "x"}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "잘못된 쪽 번호 → 400")
s = core.stats(o)
ok([d["n"] for d in s["by_diff"]] == [0, 5, 0] and s["by_diff"][1]["ok"] == 2, "진도: 난이도별 정답 수")

# 틀린 문제 다시 풀기: 가장 최근 결과가 오답인 문제은행 객관식만, 맞히면 빠짐, 진도 통계엔 안 셈
for _ in range(3): core.generate("1.1", "쉬움", "mcq", o)
q1 = core.new_question(o, ["1.1"], "쉬움", "mcq"); q2 = core.new_question(o, ["1.1"], "쉬움", "mcq")
core.grade(o, q1["id"], "C"); core.grade(o, q2["id"], "B")
ok(core.wrong_summary(o)["count"] == 1, "틀린 문제 1개(맞힌 문제·기록에 문제 번호 없는 것은 제외)")
before = calls["n"]
r = core.retry_question(o, [])
ok(r["id"] == q1["id"] and r["source"] == "retry" and r["left"] == 1 and calls["n"] == before, "다시 풀기: 틀린 문제를 냄 — 제미나이 0번")
try: core.retry_question(o, [q1["id"]]); ok(False, "")
except core.ApiError as e: ok(e.code == 404 and e.extra.get("code") == "no_wrong", "이번 세트에서 낸 문제는 빼고, 없으면 404")
total = core.stats(o)["total"]
g = core.grade(o, q1["id"], "C", retry=True)
ok(g["verdict"] == "오답" and core.wrong_summary(o)["count"] == 1, "다시 틀리면 계속 남음")
core.grade(o, q1["id"], "B", retry=True)
ok(core.wrong_summary(o)["count"] == 0, "다시 풀어 맞히면 목록에서 빠짐")
ok(core.stats(o)["total"] == total, "다시 풀기 기록은 진도 통계에 안 셈")
ok(any(x["mode"] == "retry" for x in core.history(o, {"limit": "50"})["items"]), "풀이 기록에는 다시 풀기도 보임")
T["questions"][[x["id"] for x in T["questions"]].index(q2["id"])]["status"] = "active"
core.grade(o, q2["id"], "C", retry=True)
T["questions"][[x["id"] for x in T["questions"]].index(q2["id"])]["status"] = "hidden"
ok(core.wrong_summary(o)["count"] == 0, "숨긴 문제는 다시 풀기에서 뺌")

# 앱(Tracer Route) 익명 신고: 관리자만 읽고 처리
qb = T["questions"][0]
db.insert("app_reports", [{"app_qid": "abc123", "sub": qb["sub"], "question": qb["question"], "reason": "answer", "note": "x"},
                          {"app_qid": "abc123", "sub": qb["sub"], "question": qb["question"], "reason": "both"},
                          {"app_qid": "zzz999", "sub": "1.1", "question": "Only in the app?", "reason": "typo"}])
try: core.admin_app_reports(a, {}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "앱 신고 목록은 관리자만")
r = core.admin_app_reports(o, {})
ok(r["open"] == 3 and len(r["reports"]) == 3, "미처리 앱 신고 3건")
linked = [x for x in r["reports"] if x["app_qid"] == "abc123"]
ok(all(x["bank"] and x["bank"]["id"] == qb["id"] and x["open_same"] == 2 for x in linked), "웹 문제은행의 같은 문제와 연결, 같은 문제 신고 2건")
ok([x for x in r["reports"] if x["app_qid"] == "zzz999"][0]["bank"] is None, "앱에만 있는 문제는 연결 없음")
one = linked[0]["id"]
ok(core.admin_update_app_report(o, {"id": one, "all_same": True})["updated"] == 2, "같은 문제 신고 한꺼번에 처리 완료")
ok(core.admin_app_reports(o, {})["open"] == 1 and len(core.admin_app_reports(o, {"open": "0"})["reports"]) == 3, "미처리만 / 전체 보기")
ok(core.admin_summary(o)["open_app_reports"] == 1, "대시보드에 미처리 앱 신고 수")
try: core.admin_update_app_report(o, {"id": 999999}); ok(False, "")
except core.ApiError as e: ok(e.code == 404, "없는 신고는 404")

# 관리자 명령창 + 일괄 작업(웹 관리자 전용)
os.environ.pop("TRACER_ADMIN_AI", None)
ok(not core.me(o)["admin_ai"], "실제 관리자 명령창은 기본으로 꺼짐")
for f, b in ((core.admin_users_bulk, {"op": "approve", "ids": ["x"]}), (core.admin_ask, {"prompt": "신고 보여줘"})):
    try: f(o, b); ok(False, "")
    except core.ApiError as e: ok(e.code == 403, "꺼져 있으면 서버도 거부: " + f.__name__)
os.environ["TRACER_ADMIN_AI"] = "1"
ok(core.me(o)["admin_ai"], "TRACER_ADMIN_AI=1이면 켜짐")
ok(core.admin_summary(o, {"days": "30"})["days"] == 30 and len(core.admin_summary(o, {"days": "30"})["daily"]) == 30, "대시보드 기간 30일")
ok(core.admin_summary(o, {"days": "10"})["days"] == 10 and core.admin_summary(o, {"days": "999"})["days"] == 365 and core.admin_summary(o, {"days": "0"})["days"] == 1, "대시보드 기간 1~365(아무 숫자·범위 밖은 끝값)")
_sm = core.admin_summary(o, {"days": "7"})
ok(isinstance(_sm["period"], dict) and set(_sm["period"]) == {"visitors", "answers", "ai_calls", "signups", "graded", "correct", "rate"} and isinstance(_sm["prev"], dict), "대시보드 period·prev 집계 포함")
_orig_rpc = db.rpc
db.rpc = lambda name, a=None: (_ for _ in ()).throw(db.DBError("missing")) if name == "admin_period" else _orig_rpc(name, a)
_sm_no = core.admin_summary(o, {"days": "7"})
db.rpc = _orig_rpc
ok(_sm_no["period"] is None and _sm_no["prev"] is None, "admin_period RPC 없으면 period·prev는 None")
ok(len(core.admin_app_reports(o, {"open": "0", "days": "7"})["reports"]) == 3, "앱 신고 기간 필터")
uid_a = [x for x in T["profiles"] if x["email"] == "alice@example.com"][0]["id"]
uid_o = [x for x in T["profiles"] if x["role"] == "owner"][0]["id"]
try: core.admin_users_bulk(a, {"op": "mark_delete", "ids": [uid_o]}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "일괄 작업은 관리자만")
r = core.admin_users_bulk(o, {"op": "mark_delete", "ids": [uid_a, uid_o]})
ok(r["updated"] == 1 and r["skipped"] == 1, "주인(자기 자신)은 삭제 예정에서 제외")
ok(T["profiles"][[x["id"] for x in T["profiles"]].index(uid_a)]["delete_at"], "삭제 예정 표시됨(지우지 않음)")
ok(len([x for x in T["profiles"] if x["id"] == uid_a]) == 1, "사용자는 그대로 남아 있음")
core.touch(core.current_user("a"))
ok(not T["profiles"][[x["id"] for x in T["profiles"]].index(uid_a)]["delete_at"], "다시 접속하면 삭제 예정 자동 취소")
try: core.admin_users_bulk(o, {"op": "drop_table", "ids": [uid_a]}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "목록 밖 작업은 거부")
c = core.clean_command({"command": "show_users", "args": {"inactive_days": 400, "status": "hacked"}, "confidence": 0.95})
ok(c["args"] == {"status": "", "inactive_days": 400, "joined_days": 0, "sort": "last_desc"} and c["kind"] == "show" and not c["unsure"], "AI 값은 허용 범위 안으로 맞춤(목록 밖 상태는 기본값)")
ok(core.clean_command({"command": "drop_all", "confidence": 1})["command"] == "none", "목록 밖 명령은 none")
c = core.clean_command({"command": "show_app_reports", "args": {"days": 10}, "confidence": 1})
ok(c["args"]["days"] == 10, "기간은 10일처럼 아무 숫자(범위 안)")
ok(core.clean_command({"command": "show_app_reports", "args": {"days": 9999}, "confidence": 1})["args"]["days"] == 365, "범위 밖 기간은 끝값으로")
ok(core.clean_command({"command": "mark_delete_inactive", "args": {}, "confidence": 0.4})["unsure"], "확신 낮으면 실행 전 확인")
ok(core.clean_command({"command": "answer", "args": {"what": "inactive", "days": 300}, "confidence": 1})["kind"] == "answer", "질문은 답변 종류")
c = core.clean_command({"command": "show_bank", "args": {"q": "OSPF<script>", "diff": "hard", "sort": "x"}, "confidence": 1})
ok(c["args"]["q"] == "OSPFscript" and c["args"]["diff"] == "hard" and c["args"]["sort"] == "reports_desc", "주제어는 글자만, 목록 밖 정렬은 기본값")
c = core.clean_command({"command": "select_questions", "args": {"op": "delete", "target": "low"}, "confidence": 1})
ok(c["kind"] == "act" and c["args"]["op"] == "hide", "문제 일괄 작업도 목록 안 작업만")
seen = {}
_orig = gc.ask_json
gc.ask_json = lambda s_, pr, sc=None, temperature=0.7: (seen.update(p=pr, t=temperature) or {"command": "none", "confidence": 1, "reply": "x"}, "f")
core.admin_ask(o, {"prompt": "bob@example.com 계정 차단해줘"})
ok("bob@example.com" not in seen["p"] and seen["t"] == 0.1, "이메일은 제미나이로 보내지 않음, 낮은 온도")
ok(not any("bob@example.com" in str(x.get("detail")) for x in T["activity_log"] if x["action"] == "admin"), "명령 문장은 기록하지 않음")
try: core.admin_ask(a, {"prompt": "x"}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "명령창은 관리자만")
core.DEMO_DAILY_AI = 1
core.demo_ask({"prompt": "신고 보여줘"})
try: core.demo_ask({"prompt": "신고 보여줘"}); ok(False, "")
except core.ApiError as e: ok(e.code == 429, "모의 화면 AI는 하루 횟수 제한")
gc.ask_json = _orig

# 모의 화면 SQL 조회: 읽기 전용만
ok(core.sql_problem("SELECT id FROM users WHERE name LIKE '최%'") == "", "SELECT는 통과")
ok(core.sql_problem("WITH x AS (SELECT 1) SELECT * FROM x;") == "", "WITH … SELECT도 통과")
for bad in ["DELETE FROM users", "SELECT 1; DROP TABLE users", "UPDATE users SET status='blocked'", "PRAGMA table_info(users)", "select * from users -- ok\n; delete from users"]:
    ok(core.sql_problem(bad) != "", "막음: " + bad[:30])
c = core.clean_command({"command": "sql_query", "args": {"sql": "DELETE FROM users", "title": "x"}, "confidence": 1})
ok(c["command"] == "none", "쓰기 SQL은 none")
c = core.clean_command({"command": "sql_query", "args": {"sql": "SELECT id, name FROM users", "title": "<b>사용자</b>", "target": "users"}, "confidence": 0.3})
ok(c["command"] == "sql_query" and not c["unsure"] and c["args"]["title"] == "b사용자/b", "읽기 SQL은 확인 없이, 제목 정리")
gc.ask_json = lambda s_, pr, sc=None, temperature=0.7: ({"command": "sql_query", "args": {"sql": "SELECT id FROM users", "title": "t", "target": "users"}, "confidence": 1, "reply": "r"}, "f")
core.DEMO_DAILY_AI = 100
ok(core.demo_ask({"prompt": "최로 시작하는 사용자"})["command"] == "sql_query", "모의 화면은 SQL 조회 가능")
os.environ["TRACER_ADMIN_AI"] = "1"
_cap = {}
gc.ask_json = lambda s_, pr, sc=None, temperature=0.7: (_cap.update(sys=s_, sc=sc) or {"command": "sql_query", "args": {"sql": "SELECT id FROM users", "title": "t", "target": "users"}, "confidence": 1, "reply": "r"}, "f")
ok(core.admin_ask(o, {"prompt": "최로 시작하는 사용자"})["command"] == "sql_query" and _cap["sys"] == core.DEMO_ASK_SYS and _cap["sc"] == core.DEMO_ASK_SCHEMA, "실제 화면도 DEMO_ASK_SYS/SCHEMA 사용 · sql_query 허용")
ok(core.DEMO_ASK_SCHEMA["properties"]["args"]["properties"].get("download") == {"type": "boolean"}, "DEMO_ASK_SCHEMA args에 download(boolean)")
gc.ask_json = lambda s_, pr, sc=None, temperature=0.7: ({"command": "show_report", "args": {"days": 14, "download": True}, "confidence": 1, "reply": "r"}, "f")
_rep_cmd = core.admin_ask(o, {"prompt": "보고서 파일로 받아줘"})
ok(_rep_cmd["command"] == "show_report" and _rep_cmd["args"]["days"] == 14 and _rep_cmd["args"]["download"] is True, "실제 화면에서도 show_report(download 포함) 허용")
gc.ask_json = lambda s_, pr, sc=None, temperature=0.7: ({"command": "demo_add_users", "args": {"status": "pending", "n": 10}, "confidence": 1, "reply": "r"}, "f")
ok(core.demo_ask({"prompt": "더미 10명"})["command"] == "demo_add_users" and core.admin_ask(o, {"prompt": "더미 10명"})["command"] == "none", "demo_add_users는 모의 화면만 허용, 실제 화면은 none")
try: core.admin_ask(o, {"prompt": "   "}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "빈 명령 문장은 400")
gc.ask_json = _orig

# db.delete: 조건 없으면 DBError, 조건에 맞는 줄만 삭제
try: db.delete("admin_command_log", {}); ok(False, "")
except db.DBError: ok(True, "db.delete 조건 없으면 DBError")
_d1 = db.insert("admin_command_log", [{"admin_id": "u-tmp", "text": "a"}, {"admin_id": "u-keep", "text": "b"}])
ok(db.delete("admin_command_log", {"admin_id": "eq.u-tmp"}) == 1 and len(T["admin_command_log"]) == 1, "db.delete 조건 일치 행만 삭제·건수 반환")
T["admin_command_log"].clear()

# admin_sub_stats · admin_report (정상·권한·경계·RPC 없음)
_ss = core.admin_sub_stats(o, {"days": "500"})
ok(_ss["days"] == 365 and any(r["sub"] == "1.1" and r["name"] and isinstance(r["rate"], float) for r in _ss["subs"]), "admin_sub_stats: 범위명·정답률(float)·days 최대 365")
try: core.admin_sub_stats(a, {}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "admin_sub_stats는 관리자만")
db.rpc = lambda name, a=None: (_ for _ in ()).throw(db.DBError("missing")) if name == "admin_sub_stats" else _orig_rpc(name, a)
ok(core.admin_sub_stats(o, {})["subs"] == [], "admin_sub_stats RPC 없으면 빈 목록")
db.rpc = _orig_rpc
_rp = core.admin_report(o, {"days": "500"})
ok(_rp["days"] == 365 and set(_rp) >= {"days", "cur", "prev", "prev_partial", "top_users", "daily"}, "admin_report: 기간 요약·상위 사용자·일별·days 최대 365")
try: core.admin_report(a, {}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "admin_report는 관리자만")
db.rpc = lambda name, a=None: (_ for _ in ()).throw(db.DBError("missing")) if name == "admin_report" else _orig_rpc(name, a)
try: core.admin_report(o, {}); ok(False, "")
except core.ApiError as e: ok(e.code == 503, "admin_report RPC 없으면 503 ApiError")
db.rpc = _orig_rpc

# admin_users_bulk: block·unblock·restore·권한(주인/본인/다른 관리자)·TRACER_ADMIN_AI
os.environ["TRACER_ADMIN_AI"] = "1"
b = core.current_user("b")
core.admin_update_user(o, {"id": b["id"], "role": "admin", "status": "active"})
b = core.current_user("b")
db.insert("profiles", [{"id": "u-carl", "email": "carl@example.com", "name": "Carl", "role": "admin", "status": "active"}])
core.admin_update_user(o, {"id": uid_a, "status": "active"})
r = core.admin_users_bulk(o, {"op": "block", "ids": [uid_a]})
ok(r["updated"] == 1 and r["skipped"] == 0 and db.one("profiles", {"id": f"eq.{uid_a}"})["status"] == "blocked", "일괄 차단(block): active → blocked")
r = core.admin_users_bulk(o, {"op": "block", "ids": [uid_a]})
ok(r["updated"] == 0 and r["skipped"] == 1, "이미 차단된 사용자 block → skipped")
r = core.admin_users_bulk(o, {"op": "unblock", "ids": [uid_a]})
ok(r["updated"] == 1 and db.one("profiles", {"id": f"eq.{uid_a}"})["status"] == "active", "일괄 해제(unblock): blocked → active")
r = core.admin_users_bulk(o, {"op": "unblock", "ids": [uid_a]})
ok(r["updated"] == 0 and r["skipped"] == 1, "active 사용자 unblock → skipped")
r = core.admin_users_bulk(o, {"op": "restore", "items": [{"id": uid_a, "status": "pending", "delete_at": "2026-12-01T00:00:00+00:00"}]})
_pa = db.one("profiles", {"id": f"eq.{uid_a}"})
ok(r["updated"] == 1 and _pa["status"] == "pending" and _pa["delete_at"] == "2026-12-01T00:00:00+00:00", "일괄 되돌리기(restore): status·delete_at 복원")
r = core.admin_users_bulk(o, {"op": "restore", "items": [{"id": uid_a, "status": "hacked"}]})
ok(r["updated"] == 0 and r["skipped"] == 1, "restore 허용 밖 status → skipped")
r = core.admin_users_bulk(b, {"op": "block", "ids": [uid_o, b["id"], "u-carl"]})
ok(r["updated"] == 0 and r["skipped"] == 3, "일반 관리자는 주인·본인·다른 관리자 block 불가(skipped)")
r = core.admin_users_bulk(o, {"op": "block", "ids": [uid_o, "u-carl"]})
ok(r["updated"] == 1 and r["skipped"] == 1 and db.one("profiles", {"id": "eq.u-carl"})["status"] == "blocked", "주인은 다른 관리자 block 가능(본인은 skipped)")
os.environ.pop("TRACER_ADMIN_AI", None)
try: core.admin_users_bulk(o, {"op": "block", "ids": [uid_a]}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "TRACER_ADMIN_AI 꺼져 있으면 admin_users_bulk(block) 403")
os.environ["TRACER_ADMIN_AI"] = "1"
core.admin_users_bulk(o, {"op": "restore", "items": [{"id": uid_a, "status": "blocked", "delete_at": None}]})

# admin_questions_bulk: hide·flag·resolve·restore·권한·TRACER_ADMIN_AI
_qids = [T["questions"][0]["id"], T["questions"][1]["id"]]
os.environ.pop("TRACER_ADMIN_AI", None)
try: core.admin_questions_bulk(o, {"op": "hide", "ids": _qids}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "TRACER_ADMIN_AI 꺼져 있으면 admin_questions_bulk 403")
os.environ["TRACER_ADMIN_AI"] = "1"
try: core.admin_questions_bulk(a, {"op": "hide", "ids": _qids}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "admin_questions_bulk는 관리자만")
r = core.admin_questions_bulk(o, {"op": "hide", "ids": _qids})
ok(r["updated"] == 2 and all(db.one("questions", {"id": f"eq.{i}"})["status"] == "hidden" for i in _qids), "문제 일괄 숨기기(hide)")
r = core.admin_questions_bulk(o, {"op": "flag", "ids": _qids[:1]})
ok(r["updated"] == 1 and db.one("questions", {"id": f"eq.{_qids[0]}"})["status"] == "flagged", "문제 일괄 출제 중지(flag)")
db.insert("question_reports", [{"question_id": _qids[0], "user_id": "u-x", "reason": "bad", "resolved": False}])
db.update("questions", {"id": f"eq.{_qids[0]}"}, {"reports": 2})
r = core.admin_questions_bulk(o, {"op": "resolve", "ids": _qids[:1]})
ok(r["updated"] == 1 and db.one("questions", {"id": f"eq.{_qids[0]}"})["status"] == "active" and db.one("questions", {"id": f"eq.{_qids[0]}"})["reports"] == 0
   and all(x["resolved"] for x in T["question_reports"] if x["question_id"] == _qids[0]), "문제 일괄 검토 완료(resolve): active·reports=0·신고 닫힘")
r = core.admin_questions_bulk(o, {"op": "restore", "items": [{"id": _qids[0], "status": "flagged", "reports": 3}, {"id": "bad-id", "status": "active"}, {"id": _qids[1], "status": "invalid"}]})
ok(r["updated"] == 1 and db.one("questions", {"id": f"eq.{_qids[0]}"})["status"] == "flagged" and db.one("questions", {"id": f"eq.{_qids[0]}"})["reports"] == 3, "문제 일괄 되돌리기(restore): 유효 항목만 복원")
try: core.admin_questions_bulk(o, {"op": "delete", "ids": _qids}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "문제 일괄 허용 밖 op → 400")
try: core.admin_questions_bulk(o, {"op": "hide", "ids": ["not-uuid"]}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "문제 일괄 유효한 id 없으면 400")

# admin_app_reports_bulk: resolved true/false · op=restore · 권한 · TRACER_ADMIN_AI
_rids = [r["id"] for r in T["app_reports"]]
os.environ.pop("TRACER_ADMIN_AI", None)
try: core.admin_app_reports_bulk(o, {"ids": _rids, "resolved": True}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "TRACER_ADMIN_AI 꺼져 있으면 admin_app_reports_bulk 403")
os.environ["TRACER_ADMIN_AI"] = "1"
try: core.admin_app_reports_bulk(a, {"ids": _rids, "resolved": True}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "admin_app_reports_bulk는 관리자만")
r = core.admin_app_reports_bulk(o, {"ids": _rids, "resolved": True})
ok(r["updated"] == 1 and all(x["resolved"] for x in T["app_reports"]), "앱 신고 일괄 처리 완료: 미처리 건만 변경")
r = core.admin_app_reports_bulk(o, {"ids": _rids[:2], "resolved": False})
ok(r["updated"] == 2 and sum(1 for x in T["app_reports"] if not x["resolved"]) == 2, "앱 신고 일괄 다시 열기(resolved=False)")
r = core.admin_app_reports_bulk(o, {"op": "restore", "items": [{"id": _rids[0], "resolved": True}, {"id": "bad", "resolved": False}]})
ok(r["updated"] == 1 and db.one("app_reports", {"id": f"eq.{_rids[0]}"})["resolved"] is True, "앱 신고 일괄 되돌리기(restore)")
try: core.admin_app_reports_bulk(o, {"ids": ["abc"], "resolved": True}); ok(False, "")
except core.ApiError as e: ok(e.code == 400, "앱 신고 일괄 대상 없으면 400")

# 명령 기록: admin_command_log_save · admin_command_log · admin_command_log_clear
for fn, arg in ((core.admin_command_log_save, {"text": "x"}), (core.admin_command_log, {}), (core.admin_command_log_clear, {})):
    try: fn(a, arg); ok(False, "")
    except core.ApiError as e: ok(e.code == 403, "명령 기록은 관리자만: " + fn.__name__)
_long = "bob@example.com 차단 " + "가" * 320
_s1 = core.admin_command_log_save(o, {"text": _long, "msg": "contact alice@test.co.kr", "st": "bad_st", "path": "bad_path", "command": "show_users!1"})
_row1 = db.one("admin_command_log", {"id": f"eq.{_s1['id']}"})
ok(isinstance(_s1["id"], int) and "(이메일)" in _row1["text"] and "bob@example.com" not in _row1["text"] and len(_row1["text"]) == 300
   and "alice@test.co.kr" not in _row1["msg"] and _row1["st"] is None and _row1["path"] is None and _row1["command"] == "show_users",
   "명령 기록 저장: 이메일 가림·300자 자르기·허용 밖 st/path는 None")
_s1u = core.admin_command_log_save(o, {"id": _s1["id"], "text": "수정됨", "st": "done", "path": "ai"})
ok(_s1u["id"] == _s1["id"] and len(T["admin_command_log"]) == 1 and db.one("admin_command_log", {"id": f"eq.{_s1['id']}"})["st"] == "done" and db.one("admin_command_log", {"id": f"eq.{_s1['id']}"})["path"] == "ai", "명령 기록 본인 줄 update")
_s1_other = core.admin_command_log_save(b, {"id": _s1["id"], "text": "남이 수정"})
ok(_s1_other["id"] is None and db.one("admin_command_log", {"id": f"eq.{_s1['id']}"})["text"] == "수정됨", "다른 관리자는 남의 명령 기록 줄 수정 불가")
_s2 = core.admin_command_log_save(b, {"text": "관리자B 기록", "st": "show", "path": "rules"})
_logs = core.admin_command_log(o, {"limit": "1"})
ok(len(_logs) == 1 and len(core.admin_command_log(o, {})) == 2, "명령 기록 목록 조회·limit 적용")
_cl = core.admin_command_log_clear(o, {})
ok(_cl == {"ok": True, "deleted": 1} and len(T["admin_command_log"]) == 1 and T["admin_command_log"][0]["admin_id"] == b["id"], "명령 기록 비우기: 본인 기록만 삭제")

# admin_activity: days 최대 365 · limit 최대 5000 · 권한
try: core.admin_activity(a, {}); ok(False, "")
except core.ApiError as e: ok(e.code == 403, "admin_activity는 관리자만")
_now = datetime.now(timezone.utc)
T["activity_log"].append({"user_id": uid_o, "action": "visit", "detail": {"tag": "d300"}, "ai": False, "counted": False, "at": (_now - timedelta(days=300)).isoformat()})
T["activity_log"].append({"user_id": uid_o, "action": "visit", "detail": {"tag": "d400"}, "ai": False, "counted": False, "at": (_now - timedelta(days=400)).isoformat()})
_act365 = core.admin_activity(o, {"days": "365", "action": "visit"})
_act999 = core.admin_activity(o, {"days": "999", "action": "visit"})
ok(any((x.get("detail") or {}).get("tag") == "d300" for x in _act365) and not any((x.get("detail") or {}).get("tag") == "d400" for x in _act999), "admin_activity days 최대 365(300일 포함·400일 제외)")
_seen_q = {}
_orig_sel = db.select
db.select = lambda t, p=None: (_seen_q.update(p or {}) or _orig_sel(t, p))
core.admin_activity(o, {"days": "30", "limit": "9999"})
_lim_max = _seen_q.get("limit")
core.admin_activity(o, {"days": "30", "limit": "1200"})
_lim_ok = _seen_q.get("limit")
db.select = _orig_sel
ok(_lim_max == "5000" and _lim_ok == "1200", "admin_activity limit 최대 5000")

print("모두 통과")