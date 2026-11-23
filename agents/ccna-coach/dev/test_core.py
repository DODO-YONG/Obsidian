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
ok(core.admin_summary(o, {"days": "999"})["days"] == 14, "허용 밖 기간은 14일")
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
ok(c["args"] == {"status": "", "inactive_days": 365} and c["kind"] == "show" and not c["unsure"], "AI 값은 허용 목록 안으로 맞춤")
ok(core.clean_command({"command": "drop_all", "confidence": 1})["command"] == "none", "목록 밖 명령은 none")
ok(core.clean_command({"command": "mark_delete_inactive", "args": {}, "confidence": 0.4})["unsure"], "확신 낮으면 실행 전 확인")
ok(core.clean_command({"command": "answer", "args": {"what": "inactive", "days": 300}, "confidence": 1})["kind"] == "answer", "질문은 답변 종류")
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
print("모두 통과")
