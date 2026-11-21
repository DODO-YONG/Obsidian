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
print("모두 통과")
