"""TRACER 화면 시험 (Playwright). 실행: agents/ccna-coach/e2e/README.md 참고.
새 기능을 만들면 여기에 시험을 하나 추가한다 → 그다음부턴 푸시할 때마다 GitHub Actions가 자동 확인(토큰 0)."""
import re

import pytest
from playwright.sync_api import expect

AUTH = "[data-auth]"


# ---------- 공개 페이지 ----------
@pytest.mark.parametrize("path,text", [
    ("/ccna/", "TRACER"),
    ("/ccna/about.html", "TRACER"),
    ("/ccna/privacy.html", "개인정보"),
])
def test_public_pages_load(page, errors, base_url, path, text):
    r = page.goto(base_url + path)
    assert r.ok
    expect(page.locator("body")).to_contain_text(text)


def test_home_links_to_about_and_app(page, errors, base_url):
    page.goto(base_url + "/ccna/")
    expect(page.locator('a[href*="about.html"]').first).to_be_visible()
    expect(page.locator('a[href*="app.html"]').first).to_be_visible()


def test_logged_out_shows_google_login(page, errors, base_url):
    page.goto(base_url + "/ccna/")
    expect(page.locator(AUTH).first).to_contain_text("로그인")
    expect(page.locator(f"{AUTH} [data-auth-act=in]").first).to_be_visible()


# ---------- 이용 화면: 로그인 없이 ----------
def test_app_scope_list_loads(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#scopeList .dom-head").first).to_be_visible()


def test_ai_question_needs_login(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#connText")).to_have_text(re.compile("로그인"))
    page.click("#newQ")
    expect(page.locator("#connHelp")).to_be_visible()


def test_subnet_works_without_login(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.click('#qtypeSeg [data-v="subnet"]')
    page.click("#newQ")
    expect(page.locator("#qCard .q-text")).to_contain_text("What is the")
    page.fill("#ansIn", "0")
    page.click("#gradeBtn")
    expect(page.locator("#expBox .verdict")).to_be_visible()
    expect(page.locator("#expBox")).to_contain_text("Calculated by code")


# ---------- 로그인 흐름 ----------
def test_login_button_logs_in(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.locator(f"{AUTH} [data-auth-act=in]").first.click()
    expect(page.locator(f"{AUTH} .auth-user").first).to_contain_text("Test Owner")
    page.locator(f"{AUTH} [data-auth-act=out]").first.click()
    expect(page.locator(f"{AUTH} [data-auth-act=in]").first).to_be_visible()


def test_mcq_question_and_grade(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#adminLink")).to_be_visible()   # 주인이면 관리자 링크
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    expect(page.locator("#qCard .choice")).to_have_count(4)
    page.click('#qCard .choice[data-l="B"]')               # 가짜 제미나이의 정답은 항상 B
    page.click("#gradeBtn")
    expect(page.locator("#expBox .verdict")).to_contain_text("Correct")
    expect(page.locator('#qCard .choice[data-l="B"]')).to_have_class(re.compile("correct"))
    expect(page.locator("#reportBtn")).to_be_visible()
    expect(page.locator("#gradeBtn")).to_contain_text("다음 문제")


def _open_mcq(page, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    expect(page.locator("#qCard .choice")).to_have_count(4)


def test_mcq_grade_button_states_before_and_after(logged_in, errors, base_url):
    page = logged_in
    _open_mcq(page, base_url)
    expect(page.locator("#gradeBtn")).to_have_text("채점하기")
    expect(page.locator("#gradeBtn")).to_be_disabled()
    expect(page.locator("#gradeHint")).to_contain_text("보기를 하나 고르세요")
    page.click('#qCard .choice[data-l="C"]')
    expect(page.locator("#gradeBtn")).to_be_enabled()
    expect(page.locator("#gradeHint")).to_contain_text("C를 골랐어요")
    page.click("#gradeBtn")
    expect(page.locator("#gradeBtn")).to_contain_text("다음 문제")
    expect(page.locator("#gradeBtn")).to_have_class(re.compile("next"))
    expect(page.locator("#qCard")).to_have_class(re.compile("graded"))
    expect(page.locator("#gradeHint")).to_contain_text("채점 완료")
    expect(page.locator("#nextBtn2")).to_be_visible()
    expect(page.locator("#nextBtn2")).to_contain_text("다음 문제")
    # 채점 후에는 다른 보기를 눌러도 선택이 바뀌지 않는다
    expect(page.locator('#qCard .choice[data-l="C"]')).to_have_attribute("aria-pressed", "true")
    page.click('#qCard .choice[data-l="A"]', force=True)
    expect(page.locator('#qCard .choice[data-l="A"]')).to_have_attribute("aria-pressed", "false")
    expect(page.locator('#qCard .choice[data-l="C"]')).to_have_attribute("aria-pressed", "true")


@pytest.mark.parametrize("btn", ["#gradeBtn", "#nextBtn2"])
def test_mcq_next_does_not_regrade(btn, logged_in, errors, base_url):
    page = logged_in
    grades = []
    page.on("request", lambda r: grades.append(r.url) if "/api/grade" in r.url else None)
    _open_mcq(page, base_url)
    page.click('#qCard .choice[data-l="B"]')
    page.click("#gradeBtn")
    expect(page.locator("#nextBtn2")).to_be_visible()
    assert len(grades) == 1
    page.click(btn)                                         # 다음 문제
    expect(page.locator("#gradeBtn")).to_have_text("채점하기")
    expect(page.locator("#qCard")).not_to_have_class(re.compile("graded"))
    expect(page.locator("#nextBtn2")).to_have_count(0)
    expect(page.locator("#qCard .choice")).to_have_count(4)
    assert len(grades) == 1, "다음 문제를 눌렀는데 /api/grade가 다시 호출됨"


def test_conn_help_logged_in_has_no_login_button(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#connText")).to_contain_text("AI 사용 가능")
    page.locator("#conn").click()
    expect(page.locator("#connHelp")).to_be_visible()
    expect(page.locator("#helpMsg")).to_contain_text("로그인되어 있어요")
    expect(page.locator("#helpLogin")).to_be_hidden()
    expect(page.locator("#helpNote")).to_be_hidden()
    page.locator("#conn").click()
    expect(page.locator("#connHelp")).to_be_hidden()


def test_conn_help_logged_out_shows_login(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#connText")).to_contain_text("로그인")
    page.locator("#conn").click()
    expect(page.locator("#connHelp")).to_be_visible()
    expect(page.locator("#helpLogin")).to_be_visible()
    expect(page.locator("#helpNote")).to_be_visible()
    page.locator("#conn").click()
    expect(page.locator("#connHelp")).to_be_hidden()


def test_conn_waiting_for_me_shows_linking(logged_in, errors, base_url):
    page = logged_in
    held = []
    page.route("**/api/me", lambda route: held.append(route))   # 응답을 붙잡아 '연결 중' 상태를 만든다
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#connText")).to_contain_text("AI 연결 중")
    expect(page.locator("#conn")).to_have_class(re.compile(r"\bwait\b"))
    page.locator("#conn").click()
    expect(page.locator("#connHelp")).to_be_visible()
    expect(page.locator("#helpMsg")).to_contain_text("AI 서버에 연결하는 중")
    expect(page.locator("#helpLogin")).to_be_hidden()
    expect(page.locator("#connHelp")).to_have_class(re.compile(r"\bok\b"))
    for r in held:
        r.continue_()                                           # 이제 응답이 온다
    expect(page.locator("#connText")).to_contain_text("AI 사용 가능")
    expect(page.locator("#conn")).to_have_class(re.compile(r"\bon\b"))
    expect(page.locator("#connHelp")).to_be_hidden()


def test_conn_me_failure_then_retry_on_click(logged_in, errors, base_url):
    page = logged_in
    page.route("**/api/me", lambda route: route.abort())        # 계속 실패 (자동 재시도 2번, 1.5초 간격)
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#connText")).to_contain_text("AI 연결 늦음", timeout=10000)
    expect(page.locator("#helpLogin")).to_be_hidden()
    page.unroute("**/api/me")                                   # 서버가 살아남
    page.locator("#conn").click()                               # 누르면 다시 연결
    expect(page.locator("#connText")).to_contain_text("AI 사용 가능")
    expect(page.locator("#helpLogin")).to_be_hidden()


# ---------- 세트 ----------
def _finish_set(page, n, answer="0"):
    """서브넷 세트를 끝까지 푼다(로그인 불필요). 마지막 문제에서 버튼 문구를 확인."""
    for i in range(1, n + 1):
        expect(page.locator("#setBar")).to_contain_text(f"세트 {i} / {n}")
        page.fill("#ansIn", answer)
        page.click("#gradeBtn")
        expect(page.locator("#expBox .verdict")).to_be_visible()
        if i < n:
            expect(page.locator("#gradeBtn")).to_contain_text("다음 문제 →")
            expect(page.locator("#nextBtn2")).to_contain_text("다음 문제 →")
            page.click("#nextBtn2")
        else:
            expect(page.locator("#gradeBtn")).to_contain_text("세트 결과 보기 →")
            expect(page.locator("#nextBtn2")).to_contain_text("세트 결과 보기 →")
            page.click("#nextBtn2")


def test_set_size_control_default_and_remembered(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("#newQ")).to_have_text("세트 시작")
    expect(page.locator('#setSeg [data-v="5"]')).to_have_attribute("aria-pressed", "true")
    page.click('#setSeg [data-v="10"]')
    expect(page.locator('#setSeg [data-v="10"]')).to_have_attribute("aria-pressed", "true")
    assert page.evaluate("localStorage.getItem('ccna-setsize')") == "10"
    page.reload()
    expect(page.locator('#setSeg [data-v="10"]')).to_have_attribute("aria-pressed", "true")
    page.click('#qtypeSeg [data-v="subnet"]')
    page.click("#newQ")
    expect(page.locator("#setBar")).to_contain_text("세트 1 / 10")


def test_subnet_set_of_5_summary_logged_out(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.click('#qtypeSeg [data-v="subnet"]')
    page.click("#newQ")
    expect(page.locator("#qCard .pill", has_text="서브넷 계산")).to_be_visible()
    _finish_set(page, 5)
    expect(page.locator("#setSummary")).to_be_visible()
    expect(page.locator("#setSummary")).to_contain_text("세트 완료")
    expect(page.locator("#setSummary .score")).to_have_text(re.compile(r"^\d / 5$"))
    expect(page.locator("#setSummary li")).to_have_count(5)
    expect(page.locator("#setMy")).to_have_count(0)          # 로그아웃이면 마이페이지 버튼 없음
    page.click("#setAgain")                                  # 새 세트
    expect(page.locator("#setBar")).to_contain_text("세트 1 / 5")
    expect(page.locator("#setSummary")).to_have_count(0)


def test_mcq_set_logged_in_summary_and_go_mypage(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    page.click('#setSeg [data-v="5"]')
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    for i in range(1, 6):
        expect(page.locator("#setBar")).to_contain_text(f"세트 {i} / 5")
        expect(page.locator("#qCard .choice")).to_have_count(4)
        page.click('#qCard .choice[data-l="B"]')            # 가짜 정답은 항상 B
        page.click("#gradeBtn")
        expect(page.locator("#nextBtn2")).to_be_visible()
        expect(page.locator("#gradeBtn")).to_contain_text("세트 결과 보기" if i == 5 else "다음 문제")
        page.click("#nextBtn2")
    expect(page.locator("#setSummary")).to_contain_text("세트 완료")
    expect(page.locator("#setSummary .score")).to_have_text("5 / 5")
    expect(page.locator("#setSummary li")).to_have_count(5)
    page.click("#setMy")
    expect(page.locator("#view-mypage")).to_be_visible()
    expect(page.locator("#tab-mypage")).to_have_attribute("aria-selected", "true")


# ---------- 마이페이지 ----------
def test_mypage_logged_out_shows_login(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.click("#tab-mypage")
    expect(page.locator("#view-mypage")).to_be_visible()
    expect(page.locator("#myLogin")).to_be_visible()
    expect(page.locator("#myLoginBtn")).to_be_visible()
    expect(page.locator("#myBody")).to_be_hidden()
    expect(page.locator("body")).to_have_class(re.compile(r"\bon-my\b"))
    page.click("#myLoginBtn")                                # 가짜 로그인
    expect(page.locator("#myBody")).to_be_visible()


def test_mypage_logged_in_stats_and_side_panels_hidden(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator("aside.scope")).to_be_visible()
    page.click("#tab-mypage")
    expect(page.locator("#myBody")).to_be_visible()
    expect(page.locator("#myLogin")).to_be_hidden()
    expect(page.locator("body")).to_have_class(re.compile(r"\bon-my\b"))
    expect(page.locator("aside.scope")).to_be_hidden()
    expect(page.locator("aside.side")).to_be_hidden()
    expect(page.locator("#myTotal")).to_have_text(re.compile(r"^\d+$"))
    expect(page.locator("#myRate")).not_to_be_empty()
    expect(page.locator("#myLv")).to_contain_text("Lv")
    expect(page.locator("#myDomains .rate").first).to_be_visible()
    expect(page.locator("#myDiffs .rate").first).to_be_visible()
    page.click("#tab-practice")                              # 돌아오면 옆 패널이 다시 보임
    expect(page.locator("aside.scope")).to_be_visible()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\bon-my\b"))


def _fake_hist(total):
    """최신순으로 total개. 3개마다 하나는 오답."""
    items = [{"at": f"2026-11-20T10:{59 - i % 60:02d}:00+00:00", "mode": "practice", "sub": "1.1", "sub_name": "",
              "qtype": "mcq", "difficulty": "중", "verdict": "오답" if i % 3 == 0 else "정답",
              "question": f"Q{i}", "user_answer": "B"} for i in range(total)]

    def handler(route):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(route.request.url).query)
        rows = [x for x in items if x["verdict"] != "정답"] if q.get("only") == ["wrong"] else items
        off, lim = int(q.get("offset", ["0"])[0]), int(q.get("limit", ["20"])[0])
        route.fulfill(json={"items": rows[off:off + lim], "more": len(rows) > off + lim, "offset": off})
    return handler


def test_mypage_history_newest_first_wrong_filter_and_more(logged_in, errors, base_url):
    page = logged_in
    page.route("**/api/history*", _fake_hist(45))
    page.goto(base_url + "/ccna/app.html")
    page.click("#tab-mypage")
    expect(page.locator("#histList li")).to_have_count(20)
    expect(page.locator("#histList li").first).to_contain_text("Q0")      # 최신 먼저
    expect(page.locator("#histMore")).to_be_visible()
    page.click("#histMore")
    expect(page.locator("#histList li")).to_have_count(40)
    page.click("#histMore")
    expect(page.locator("#histList li")).to_have_count(45)
    expect(page.locator("#histMore")).to_be_hidden()
    page.click('#histSeg [data-v="wrong"]')                  # 틀린 문제만: 45개 중 15개
    expect(page.locator("#histList li")).to_have_count(15)
    expect(page.locator("#histList .vb")).to_have_count(15)
    expect(page.locator("#histList .vb.ok")).to_have_count(0)
    expect(page.locator("#histMore")).to_be_hidden()
    page.click('#histSeg [data-v=""]')
    expect(page.locator("#histList li")).to_have_count(20)


def test_mypage_history_no_more_button_for_20_or_less(logged_in, errors, base_url):
    page = logged_in
    page.route("**/api/history*", _fake_hist(20))
    page.goto(base_url + "/ccna/app.html")
    page.click("#tab-mypage")
    expect(page.locator("#histList li")).to_have_count(20)
    expect(page.locator("#histMore")).to_be_hidden()


def test_mypage_real_history_records_solved_subnet(logged_in, errors, base_url):
    """가짜 DB까지 이어서: 서브넷 문제를 풀면(로그 저장) 마이페이지 기록 맨 위에 나온다."""
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    page.click('#qtypeSeg [data-v="subnet"]')
    page.click("#newQ")
    page.fill("#ansIn", "zzz-wrong")
    with page.expect_response(lambda r: "/api/log" in r.url):
        page.click("#gradeBtn")
    page.click("#tab-mypage")
    expect(page.locator("#histList li .vb").first).to_be_visible()
    expect(page.locator("#histList li").first).to_contain_text("zzz-wrong")
    page.click('#histSeg [data-v="wrong"]')
    expect(page.locator("#histList li").first).to_contain_text("zzz-wrong")
    expect(page.locator("#histList .vb.ok")).to_have_count(0)


# ---------- 관리자 ----------
def test_admin_requires_login(page, errors, base_url):
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#loginBtn")).to_be_visible()
    expect(page.locator("#tabs")).to_be_hidden()


def test_admin_dashboard_for_owner(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#tabs")).to_be_visible()
    expect(page.locator("#gate")).to_be_hidden()
    expect(page.locator("#who")).to_contain_text("로그인됨")


# ---------- 관리자: 앱 신고 탭 (가짜 DB는 서버 하나를 같이 쓰므로, 상태를 바꾼 시험은 끝에서 되돌린다) ----------
def _open_app_reports(page, base_url):
    page.goto(base_url + "/ccna/admin.html#appr")
    expect(page.locator("#arCount")).to_contain_text("미처리")


def test_admin_app_reports_list_shows_open_with_reason_and_note(logged_in, errors, base_url):
    page = logged_in
    _open_app_reports(page, base_url)
    expect(page.locator("#arCount")).to_contain_text("미처리 3건")
    cards = page.locator("#arList .qc")
    expect(cards).to_have_count(3)
    expect(cards.filter(has_text="정답이 틀림")).to_have_count(1)
    expect(cards.filter(has_text="해설이 틀림")).to_have_count(1)
    expect(cards.filter(has_text="오타·표현")).to_have_count(1)
    expect(page.locator("#arList")).to_contain_text("정답이 C 같아요")
    expect(page.locator("#arList")).to_contain_text("Typo in choice B")


def test_admin_app_reports_app_only_question_has_no_stop_web(logged_in, errors, base_url):
    page = logged_in
    _open_app_reports(page, base_url)
    app_only = page.locator("#arList .qc").filter(has_text="ffff000011")
    expect(app_only).to_have_count(1)
    expect(app_only).to_contain_text("웹 문제은행에는 없는 문제")
    expect(app_only.locator("[data-a=stopWeb]")).to_have_count(0)
    # 웹 문제와 연결된 신고에는 출제 중지 버튼이 있다
    linked = page.locator("#arList .qc").filter(has_text="a1b2c3d4e5")
    expect(linked.first).to_contain_text("웹 문제은행에도 있음")
    expect(linked.first.locator("[data-a=stopWeb]")).to_have_count(1)


def test_admin_app_reports_done_all_same_then_reopen(logged_in, errors, base_url):
    page = logged_in
    _open_app_reports(page, base_url)
    expect(page.locator("#arList [data-a=doneAll]")).to_have_count(2)
    page.locator("#arList .qc").filter(has_text="a1b2c3d4e5").first.locator("[data-a=doneAll]").click()
    expect(page.locator("#arCount")).to_contain_text("미처리 1건")
    expect(page.locator("#arList .qc")).to_have_count(1)
    # 전체 보기: 처리된 2건에 다시 열기 버튼
    page.select_option("#arOpen", "0")
    expect(page.locator("#arList [data-a=reopen]")).to_have_count(2)
    # 상태 되돌리기(다른 시험에 영향 없게)
    page.locator("#arList [data-a=reopen]").first.click()
    expect(page.locator("#arCount")).to_contain_text("미처리 2건")
    page.locator("#arList [data-a=reopen]").first.click()
    expect(page.locator("#arCount")).to_contain_text("미처리 3건")


def test_admin_dashboard_app_report_tile(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    tile = page.locator("#tiles .tile").filter(has_text="앱 신고")
    expect(tile).to_have_count(1)
    expect(tile.locator(".v")).to_have_text("3")


# ---------- 소개 페이지 (영어/한국어) ----------
EN = '[data-lang-block="en"]'
KO = '[data-lang-block="ko"]'


def test_about_default_english(page, errors, base_url):
    page.goto(base_url + "/ccna/about.html")
    expect(page.locator(EN)).to_be_visible()
    expect(page.locator(KO)).to_be_hidden()
    expect(page.locator(EN)).to_contain_text("Get Tracer Route")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator(".top " + AUTH)).to_be_hidden()
    expect(page.locator("[data-tracer-how]")).to_have_count(1)
    expect(page.locator(EN + " [data-tracer-how]")).to_have_count(0)


@pytest.mark.parametrize("suffix", ["?lang=ko", "#ko"])
def test_about_korean_by_url(page, errors, base_url, suffix):
    page.goto(base_url + "/ccna/about.html" + suffix)
    expect(page.locator(KO)).to_be_visible()
    expect(page.locator(EN)).to_be_hidden()
    expect(page.locator("html")).to_have_attribute("lang", "ko")
    expect(page.locator(".top " + AUTH).first).to_be_visible()


def test_about_lang_switch_is_remembered(page, errors, base_url):
    page.goto(base_url + "/ccna/about.html")
    page.click('.lang-sw [data-lang="ko"]')
    expect(page.locator(KO)).to_be_visible()
    expect(page.locator(EN)).to_be_hidden()
    expect(page.locator('.lang-sw [data-lang="ko"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator('.lang-sw [data-lang="en"]')).to_have_attribute("aria-pressed", "false")
    page.reload()
    expect(page.locator(KO)).to_be_visible()
    expect(page.locator("html")).to_have_attribute("lang", "ko")
    page.click('.lang-sw [data-lang="en"]')
    expect(page.locator(EN)).to_be_visible()
    expect(page.locator(".top " + AUTH)).to_be_hidden()
    page.reload()
    expect(page.locator(EN)).to_be_visible()


def _check_how_tabs(page):
    tabs = page.locator("#how .tq-tabs button")
    expect(tabs).to_have_count(4)
    for i, t in enumerate(["로그인", "문제 받기", "채점", "서브넷"]):
        expect(tabs.nth(i)).to_contain_text(t)


def test_about_how_tabs_keep_text_ko(page, errors, base_url):
    page.goto(base_url + "/ccna/about.html?lang=ko")
    _check_how_tabs(page)


def test_about_how_tabs_keep_text_after_switch(page, errors, base_url):
    page.goto(base_url + "/ccna/about.html")
    page.click('.lang-sw [data-lang="ko"]')
    expect(page.locator(KO)).to_be_visible()
    _check_how_tabs(page)


def test_about_favicon_is_app_icon(page, errors, base_url):
    page.goto(base_url + "/ccna/about.html")
    href = page.locator("link[rel=icon]").first.get_attribute("href")
    assert href.endswith("icon.svg")
    r = page.request.get(page.evaluate("document.querySelector('link[rel=icon]').href"))
    assert r.status == 200


def test_korean_home_about_link_uses_lang_ko(page, errors, base_url):
    page.goto(base_url + "/ccna/")
    links = page.locator('a[href*="about.html"]')
    assert links.count() >= 1
    for i in range(links.count()):
        assert "lang=ko" in links.nth(i).get_attribute("href")


# ---------- 휴대폰 화면 ----------
@pytest.mark.parametrize("path", ["/ccna/", "/ccna/about.html", "/ccna/about.html?lang=ko", "/ccna/app.html"])
def test_no_horizontal_scroll_on_phone(browser, base_url, path):
    ctx = browser.new_context(viewport={"width": 375, "height": 812})
    page = ctx.new_page()
    page.goto(base_url + path)
    page.wait_for_load_state("networkidle")
    over = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    ctx.close()
    assert over <= 1, f"{path}: 휴대폰 폭에서 가로로 {over}px 넘침"


def _overflow(browser, base_url, width, logged, click_mypage):
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    if logged:
        ctx.add_init_script("localStorage.setItem('fake-tok', 'a')")
    page = ctx.new_page()
    page.goto(base_url + "/ccna/app.html")
    if click_mypage:
        page.click("#tab-mypage")
        expect(page.locator("#view-mypage")).to_be_visible()
        if logged:
            expect(page.locator("#myDomains .rate").first).to_be_visible()
            expect(page.locator("#histList li").first).to_be_visible()
    else:
        expect(page.locator("#scopeList .dom-head").first).to_be_visible()
    over = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    ctx.close()
    return over


@pytest.mark.parametrize("logged", [False, True])
def test_no_horizontal_scroll_mypage_phone(browser, base_url, logged):
    over = _overflow(browser, base_url, 375, logged, True)
    assert over <= 1, f"마이페이지 375px: 가로로 {over}px 넘침"


@pytest.mark.parametrize("width", [820, 1024])
def test_no_horizontal_scroll_practice_tablet(browser, base_url, width):
    over = _overflow(browser, base_url, width, False, False)
    assert over <= 1, f"문제 풀기 {width}px: 가로로 {over}px 넘침"


# ---------- 주관식 중단 / 틀린 문제 다시 풀기 ----------
def test_short_answer_button_removed(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    expect(page.locator('#qtypeSeg [data-v="mcq"]')).to_be_visible()
    expect(page.locator('#qtypeSeg [data-v="subnet"]')).to_be_visible()
    expect(page.locator('#qtypeSeg [data-v="short"]')).to_have_count(0)


def _drain_wrong(page, base_url):
    """공유 가짜 DB에 앞선 시험이 남긴 틀린 문제를 모두 맞혀 0으로 만든다(API 직접 호출)."""
    h = {"Authorization": "Bearer a"}
    for _ in range(200):
        r = page.request.post(base_url + "/api/question", data={"retry": True, "exclude": []}, headers=h)
        q = r.json()
        if not r.ok or not q.get("id"):
            break
        page.request.post(base_url + "/api/grade", data={"id": q["id"], "answer": "B", "retry": True}, headers=h)
    assert page.request.get(base_url + "/api/wrong", headers=h).json()["count"] == 0


def _play_set(page, answers, last_text):
    """진행 중인 세트를 answers(보기 글자 목록)대로 끝까지 풀고 결과 화면까지 간다."""
    n = len(answers)
    for i, a in enumerate(answers, 1):
        expect(page.locator("#setBar")).to_contain_text(f"/ {n}")
        expect(page.locator("#qCard .choice")).to_have_count(4)
        page.click(f'#qCard .choice[data-l="{a}"]')
        page.click("#gradeBtn")
        expect(page.locator("#nextBtn2")).to_be_visible()
        page.click("#nextBtn2")
    expect(page.locator("#setSummary")).to_contain_text(last_text)


def test_retry_wrong_questions_flow(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    _drain_wrong(page, base_url)
    page.click('#setSeg [data-v="5"]')
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    _play_set(page, ["A", "A", "A", "B", "B"], "세트 완료")   # 앞 3개 오답
    page.click("#setMy")
    expect(page.locator("#retryInfo")).to_contain_text("틀린 문제 3개가 남았어요")
    expect(page.locator("#retryBtn")).to_be_enabled()
    total = page.locator("#myTotal").inner_text()

    page.click("#retryBtn")                                   # 다시 풀기 세트(3문제)
    expect(page.locator("#tab-practice")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#setBar")).to_contain_text("다시 풀기 1 / 3")
    _play_set(page, ["A", "B", "B"], "다시 풀기 완료")
    expect(page.locator("#setSummary .score")).to_have_text("2 / 3")
    expect(page.locator("#setAgain")).to_have_text("틀린 문제 계속 풀기")
    page.click("#setMy")
    expect(page.locator("#retryInfo")).to_contain_text("틀린 문제 1개가 남았어요")
    expect(page.locator("#myTotal")).to_have_text(total)       # 다시 풀기는 통계에 안 셈
    expect(page.locator("#histList li").first.locator(".pill", has_text="다시 풀기")).to_be_visible()

    page.click("#retryBtn")                                   # 남은 1개
    expect(page.locator("#setBar")).to_contain_text("다시 풀기 1 / 1")
    _play_set(page, ["B"], "다시 풀기 완료")
    page.click("#setMy")
    expect(page.locator("#retryInfo")).to_contain_text("다시 풀 틀린 문제가 없어요")
    expect(page.locator("#retryBtn")).to_be_disabled()


def test_retry_again_with_none_left_shows_toast(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/app.html")
    _drain_wrong(page, base_url)
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    _play_set(page, ["A", "B", "B", "B", "B"], "세트 완료")
    page.click("#setMy")
    expect(page.locator("#retryInfo")).to_contain_text("틀린 문제 1개가 남았어요")
    page.click("#retryBtn")
    _play_set(page, ["B"], "다시 풀기 완료")
    page.click("#setAgain")                                   # 남은 게 없음
    expect(page.locator("body")).to_contain_text("다시 풀 틀린 문제가 없어요.")


def _serve_question(page, base_url, question):
    """/api/question 응답만 시험용 문제로 바꿔서 글 표시 규칙(formatQ)을 확인한다."""
    import json
    body = {"id": "t-fmt", "question": question, "choices": ["A. one", "B. two", "C. three", "D. four"],
            "sub": "1.1", "sub_name": "x", "domain": "d", "domain_id": "1", "qtype": "mcq",
            "difficulty": "보통", "model": "", "source": "bank"}
    page.route("**/api/question", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(body)))
    page.goto(base_url + "/ccna/app.html")
    page.click('#qtypeSeg [data-v="mcq"]')
    page.click("#newQ")
    expect(page.locator("#qCard .choice")).to_have_count(4)


def test_question_table_lines_become_one_cli_block(logged_in, errors, base_url):
    q = ("Refer to the output.\nInterface  Grp  Pri  P  State    Active\n"
         "Vl10       10   90   P  Standby  10.1.10.2\nWhich router is active?")
    _serve_question(logged_in, base_url, q)
    cli = logged_in.locator("#qCard .q-text .cli")
    expect(cli).to_have_count(1)
    expect(cli).to_contain_text("Interface")
    expect(cli).to_contain_text("Vl10")
    expect(cli).not_to_contain_text("Refer to the output")
    expect(cli).not_to_contain_text("Which router")
    expect(logged_in.locator("#qCard .q-text")).to_contain_text("Refer to the output.")
    expect(logged_in.locator("#qCard .q-text")).to_contain_text("Which router is active?")


def test_question_single_line_with_show_command_has_no_cli(logged_in, errors, base_url):
    _serve_question(logged_in, base_url, "show crypto isakmp sa shows QM_IDLE. What does that indicate?")
    expect(logged_in.locator("#qCard .q-text")).to_contain_text("QM_IDLE")
    expect(logged_in.locator("#qCard .q-text .cli")).to_have_count(0)


# ---------- 관리자: 모의 화면(?demo=1)·명령창 ----------
_JS_STATS = """() => {
  const d = window.TracerAdminDemo.db, now = Date.now(), DAY = 864e5;
  const idle = d.users.filter(u => now - new Date(u.last_seen || u.created_at) > 365 * DAY);
  const me = d.users.find(u => u.role === 'owner' && u.email.startsWith('admin@'));
  const ed = u => u.role !== 'owner' && u.id !== me.id && u.role === 'user';
  return {idle: idle.length, openRep: d.app_reports.filter(r => !r.resolved).length,
          pending: d.users.filter(u => u.status === 'pending').length,
          delTargets: idle.filter(u => ed(u) && !u.delete_at).length,
          idleDeleted: idle.filter(u => u.delete_at).length};
}"""


def _stats(page):
    return page.evaluate(_JS_STATS)


def _demo(page, base_url, mode=None):
    if mode:  # 해석 방식 저장값(ai|rules). 규칙 동작을 보는 시험은 rules
        page.add_init_script(f"localStorage.setItem('tracer-admin-demo-mode', '{mode}')")
    page.goto(base_url + "/ccna/admin.html?demo=1")
    expect(page.locator("#demoBar")).to_be_visible()
    expect(page.locator("#cmd")).to_be_visible()


def _cmd(page, text):
    page.locator("#cmdIn").fill(text)
    page.locator("#cmdGo").click()
    return page.locator("#cmdLog li").first


def test_admin_demo_mode_labels_and_size(page, errors, base_url):
    _demo(page, base_url)
    expect(page.locator("#modeTag")).to_contain_text("모의")
    expect(page.locator("#mDemo")).to_have_attribute("aria-current", "page")
    expect(page.locator("html")).to_have_class(re.compile("demo"))
    page.locator("#demoSize").select_option("100")
    page.wait_for_url(re.compile("n=100"))
    expect(page.locator("#demoBar")).to_be_visible()
    assert len(page.evaluate("() => window.TracerAdminDemo.db.users")) >= 100


def test_admin_demo_rule_filter_and_answer(page, errors, base_url):
    _demo(page, base_url, "rules")
    st = _stats(page)
    li = _cmd(page, "1년 동안 접속 안 한 유저 찾아줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#uIdle")).to_have_value("365")
    expect(page.locator("#uCount")).to_contain_text(f"{st['idle']}명")
    page.locator("#tabs [data-tab=appr]").click()
    li = _cmd(page, "미처리 신고 몇 건이야?")
    expect(li.locator(".st")).to_contain_text("답변")
    expect(li).to_contain_text(f"{st['openRep']}건")
    expect(page.locator("#tabs [data-tab=appr]")).to_have_attribute("aria-selected", "true")


def test_admin_demo_delete_confirm_yes_and_no(page, errors, base_url):
    _demo(page, base_url)
    st = _stats(page)
    assert st["delTargets"] > 0
    _cmd(page, "1년 동안 접속 안 한 유저 지워줘")
    expect(page.locator("dialog#ask")).to_be_visible()
    expect(page.locator("#askL li")).to_have_count(min(st["delTargets"], 101))
    page.locator("#askNo").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("취소")
    assert _stats(page)["idleDeleted"] == st["idleDeleted"]
    _cmd(page, "1년 동안 접속 안 한 유저 지워줘")
    page.locator("#askYes").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("실행함")
    after = _stats(page)
    assert after["delTargets"] == 0
    assert after["idleDeleted"] == st["idleDeleted"] + st["delTargets"]


def test_admin_demo_approve_all_pending(page, errors, base_url):
    _demo(page, base_url)
    assert _stats(page)["pending"] > 0
    _cmd(page, "승인 대기 모두 승인해줘")
    page.locator("#askYes").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("실행함")
    assert _stats(page)["pending"] == 0
    page.locator("#tabs [data-tab=users]").click()
    page.locator("#uStatus").select_option("pending")
    expect(page.locator("#uRows tr[data-id]")).to_have_count(0)


def test_admin_demo_ai_fallback_low_confidence_and_refusal(page, errors, base_url):
    _demo(page, base_url)
    li = _cmd(page, "오래된 사람들")
    expect(li.locator(".st")).to_contain_text("확인 필요")
    expect(page.locator("#v-users")).to_be_hidden()
    li.get_by_role("button", name=re.compile("맞아요, 실행")).click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#v-users")).to_be_visible()
    li = _cmd(page, "오늘 날씨 어때")
    expect(li.locator(".st")).to_contain_text("못 함")


def test_admin_real_has_command_bar_and_new_filters(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("#mReal")).to_have_attribute("aria-current", "page")
    expect(page.locator("#demoBar")).to_be_hidden()
    expect(page.locator("#cmd")).to_be_hidden()          # 명령창 꺼짐(TRACER_ADMIN_AI 없음)
    page.locator("#dDays").select_option("7")
    expect(page.locator("#days .day")).to_have_count(7)
    page.locator("#dDays").select_option("30")
    expect(page.locator("#days .day")).to_have_count(30)
    page.locator("#tabs [data-tab=users]").click()
    expect(page.locator("#uIdle")).to_be_visible()
    expect(page.locator("#uStatus option[value=delete]")).to_have_count(1)
    expect(page.locator("#uRows [data-del]")).to_have_count(0)
    for i in ("#uBulkApprove", "#uBulkDelete", "#uBulkUndelete"):
        expect(page.locator(i)).to_be_hidden()
    page.locator("#tabs [data-tab=appr]").click()
    expect(page.locator("#arDays")).to_be_visible()
    expect(page.locator("#arBulkDone")).to_be_hidden()
    for path in ("/api/admin/ask", "/api/admin/users-bulk"):
        r = page.request.post(base_url + path, data={}, headers={"Authorization": "Bearer a"})
        assert r.status == 403


# ---------- 관리자 모의 화면 1단계: 정렬·페이지·일괄 선택·되돌리기·주소 저장 ----------
def test_admin_demo_users_sort_and_pager(page, errors, base_url):
    _demo(page, base_url)
    total = page.evaluate("() => window.TracerAdminDemo.db.users.length")
    page.locator("#tabs [data-tab=users]").click()
    expect(page.locator("#uPager")).to_contain_text(f"1–50 / {total}")
    expect(page.locator("#uRows tr[data-id]")).to_have_count(50)
    page.locator("#uPager").get_by_role("button", name="다음").click()
    expect(page.locator("#uPager")).to_contain_text(f"51–100 / {total}")
    page.locator("#uPager").get_by_role("button", name="처음").click()
    expect(page.locator("#uPager")).to_contain_text(f"1–50 / {total}")
    page.locator("#uSort").select_option("last_asc")
    expect(page.locator("#uPager")).to_contain_text(f"1–50 / {total}")


def test_admin_demo_users_bulk_block_and_undo(page, errors, base_url):
    _demo(page, base_url)
    page.locator("#tabs [data-tab=users]").click()
    expect(page.locator("#uRows [data-ck]").first).to_be_visible()
    page.locator("#uAll").check()
    n = page.locator("#uRows [data-ck]").count()
    assert n > 0
    expect(page.locator("#uSel")).to_contain_text(f"{n}명 선택")
    before = page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => u.status === 'blocked').length")
    page.locator("#uSel").get_by_role("button", name="차단", exact=True).click()
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askYes").click()
    expect(page.locator("#undo")).to_be_visible()
    mid = page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => u.status === 'blocked').length")
    assert mid > before
    page.locator("#undoBtn").click()
    page.wait_for_function("(b) => window.TracerAdminDemo.db.users.filter(u => u.status === 'blocked').length === b", arg=before)


def test_admin_demo_bank_and_reports_paging(page, errors, base_url):
    _demo(page, base_url)
    d = page.evaluate("() => ({q: window.TracerAdminDemo.db.questions.length, r: window.TracerAdminDemo.db.app_reports.length})")
    page.locator("#tabs [data-tab=bank]").click()
    page.locator("#qStatus").select_option("")
    expect(page.locator("#qCount")).to_contain_text(f"{d['q']}문제")
    expect(page.locator("#qList [data-ck]")).to_have_count(20)
    page.locator("#qSort").select_option("rate_asc")
    page.locator("#qAll").check()
    expect(page.locator("#qSel")).to_contain_text("20")
    page.locator("#qSel [data-clr]").click()
    expect(page.locator("#qSel")).to_be_hidden()
    page.locator("#tabs [data-tab=appr]").click()
    expect(page.locator("#arList [data-ck]")).to_have_count(20)
    expect(page.locator("#arBulkDone")).to_be_hidden()
    page.locator("#arSort").select_option("same_desc")
    page.locator("#arAll").check()
    expect(page.locator("#arSel")).to_contain_text("20")
    page.locator("#aPager").count()


def test_admin_demo_url_hash_saved_and_restored(page, errors, base_url):
    _demo(page, base_url)
    page.locator("#tabs [data-tab=users]").click()
    page.locator("#uSort").select_option("last_asc")
    page.locator("#uPager").get_by_role("button", name="다음").click()
    page.wait_for_function("() => /sort=last_asc/.test(location.hash) && /p=2/.test(location.hash)")
    h = page.evaluate("() => location.hash")
    assert h.startswith("#users")
    page.goto(base_url + "/ccna/admin.html?demo=1" + h)
    page.reload()
    expect(page.locator("#uSort")).to_have_value("last_asc")
    expect(page.locator("#uPager")).to_contain_text("51–")


def test_admin_real_has_no_demo_lab_elements(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("#dDays option")).to_have_count(4)
    page.locator("#tabs [data-tab=users]").click()
    expect(page.locator("#uRows [data-ck]")).to_have_count(0)
    for i in ("#uAll", "#uSel", "#uPager", "#uSort"):
        expect(page.locator(i)).to_be_hidden()


# ---------- 관리자 모의 화면 2단계: 오늘 할 일·사용자 상세·필터·명령창 확장 ----------
def test_admin_demo_todo_cards_open_filtered_users(page, errors, base_url):
    _demo(page, base_url)
    st = _stats(page)
    page.locator("[data-tab=todo]").click()
    cards = page.locator("#todo .card")
    expect(cards).to_have_count(9)
    expect(cards.nth(0).locator(".v")).to_have_text(str(st["pending"]))
    expect(cards.nth(5).locator(".v")).to_have_text(str(st["idle"]))
    for i in (0, 5):
        page.locator("[data-tab=todo]").click()
        n = page.locator("#todo .card").nth(i).locator(".v").inner_text().strip()
        page.locator("#todo .card").nth(i).click()
        expect(page.locator("#v-users")).to_be_visible()
        expect(page.locator("#uCount")).to_contain_text(f"{n}명")
    page.locator("[data-tab=todo]").click()
    page.locator("#todo .card").nth(1).click()
    expect(page.locator("#v-appr")).to_be_visible()
    page.locator("[data-tab=dash]").click()
    page.locator("#tiles [data-go]").first.click()
    expect(page.locator("#v-dash")).to_be_hidden()


def test_admin_demo_user_detail_note_save(page, errors, base_url):
    _demo(page, base_url)
    page.locator("#tabs [data-tab=users]").click()
    btn = page.locator("#uRows button.nm[data-detail]").first
    uid = btn.get_attribute("data-detail")
    btn.click()
    expect(page.locator("dialog#uDetail")).to_be_visible()
    expect(page.locator("#udBody")).to_contain_text("마지막 접속")
    if page.locator("#udSave").count():
        page.locator("#udNote").fill("시험 메모")
        page.locator("#udSave").click()
        page.wait_for_function(
            "(id) => window.TracerAdminDemo.db.users.find(u => u.id === id).note === '시험 메모'", arg=uid)
    page.locator("#udAll").click()
    expect(page.locator("dialog#uDetail")).to_be_hidden()
    expect(page.locator("#v-activity")).to_be_visible()
    page.locator("#tabs [data-tab=users]").click()
    page.locator("#uRows button.nm[data-detail]").first.click()
    page.locator("#udClose").click()
    expect(page.locator("dialog#uDetail")).to_be_hidden()


def test_admin_demo_new_filters(page, errors, base_url):
    _demo(page, base_url)
    page.locator("#tabs [data-tab=users]").click()
    n7 = page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => Date.now() - new Date(u.created_at) < 7 * 864e5).length")
    page.locator("#uJoined").select_option("7")
    expect(page.locator("#uCount")).to_contain_text(f"{n7}명")
    page.wait_for_function("() => /join=7/.test(location.hash)")
    page.locator("#tabs [data-tab=bank]").click()
    page.locator("#qStatus").select_option("")
    page.locator("#qDiff").select_option("hard")
    nh = page.evaluate("() => window.TracerAdminDemo.db.questions.filter(q => q.difficulty === 'hard').length")
    expect(page.locator("#qCount")).to_contain_text(f"{nh}문제")
    page.locator("#qSearch").fill("OSPF")
    page.wait_for_function("() => /q=OSPF/i.test(location.hash) && /diff=hard/.test(location.hash)")
    page.locator("#tabs [data-tab=appr]").click()
    page.locator("#arOpen").select_option("0")
    page.locator("#arReason").select_option("typo")
    page.wait_for_function("() => /reason=typo/.test(location.hash)")
    nt = page.evaluate("() => window.TracerAdminDemo.db.app_reports.filter(r => r.reason === 'typo').length")
    expect(page.locator("#arCount")).to_contain_text(str(nt))


def test_admin_demo_command_rules_show_screens(page, errors, base_url):
    _demo(page, base_url, "rules")
    li = _cmd(page, "오늘 할 일 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#v-todo")).to_be_visible()
    li = _cmd(page, "AI 제일 많이 쓴 사람 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#uSort")).to_have_value("ai_desc")
    li = _cmd(page, "최근 7일 가입자 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#uJoined")).to_have_value("7")
    expect(page.locator("#uSort")).to_have_value("created_desc")
    li = _cmd(page, "어려운 OSPF 문제 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#qSearch")).to_have_value("OSPF")
    expect(page.locator("#qDiff")).to_have_value("hard")
    li = _cmd(page, "오타 신고 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#arReason")).to_have_value("typo")


_JS_FLAGGED = "() => window.TracerAdminDemo.db.questions.filter(q => q.status === 'flagged').length"
_JS_HIDDEN = "() => window.TracerAdminDemo.db.questions.filter(q => q.status === 'hidden').length"
_JS_BLOCKED = "() => window.TracerAdminDemo.db.users.filter(u => u.status === 'blocked').length"


def test_admin_demo_command_hide_undo_and_cancel(page, errors, base_url):
    _demo(page, base_url)
    li = _cmd(page, "방금 거 되돌려줘")
    expect(li.locator(".st")).to_contain_text("못 함")
    fl, hd = page.evaluate(_JS_FLAGGED), page.evaluate(_JS_HIDDEN)
    assert fl > 0
    _cmd(page, "출제 중지 문제 모두 숨겨줘")
    expect(page.locator("dialog#ask")).to_be_visible()
    expect(page.locator("dialog#ask")).to_contain_text(str(fl))
    page.locator("#askYes").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("실행함")
    assert page.evaluate(_JS_FLAGGED) == 0 and page.evaluate(_JS_HIDDEN) == hd + fl
    li = _cmd(page, "방금 거 되돌려줘")
    expect(li.locator(".st")).to_contain_text("실행함")
    page.wait_for_function("(n) => window.TracerAdminDemo.db.questions.filter(q => q.status === 'flagged').length === n", arg=fl)
    assert page.evaluate(_JS_HIDDEN) == hd
    bl = page.evaluate(_JS_BLOCKED)
    assert bl > 0
    _cmd(page, "차단된 사람 모두 해제해줘")
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askNo").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("취소")
    assert page.evaluate(_JS_BLOCKED) == bl


def test_admin_real_has_no_todo_tab_or_user_detail(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("[data-tab=todo]")).to_be_hidden()
    page.locator("#tabs [data-tab=users]").click()
    expect(page.locator("#uRows tr[data-id]").first).to_be_visible()
    expect(page.locator("#uRows [data-detail]")).to_have_count(0)
    page.locator("#uRows tr[data-id] b").first.click()
    expect(page.locator("dialog#uDetail")).not_to_be_visible()


# ---------- 관리자 모의 3단계: 비교·범위별 정답률·CSV·묶음 접기 ----------
def _csv_lines(download):
    text = open(download.path(), encoding="utf-8", newline="").read()
    assert text.startswith("﻿")
    return text[1:].split("\r\n")


def test_admin_demo_dashboard_compare_and_subjects(page, errors, base_url):
    _demo(page, base_url)
    expect(page.locator("#cmpPanel")).to_be_visible()
    expect(page.locator("#cmpT")).to_contain_text("vs 그 전")
    expect(page.locator("#cmp > div")).to_have_count(5)
    expect(page.locator("#cmp")).to_contain_text(re.compile("[▲▼]"))
    expect(page.locator("#days .day .nums").first).to_contain_text("가입")
    expect(page.locator("#subPanel")).to_be_visible()
    expect(page.locator("#subs [data-sub]").first).to_be_visible()
    n = page.locator("#subs [data-sub]").count()
    assert 0 < n <= 10
    page.locator("#subMore").click()
    assert page.locator("#subs [data-sub]").count() >= n
    btn = page.locator("#subs [data-sub]").first
    sub = btn.get_attribute("data-sub")
    btn.click()
    expect(page.locator("#v-bank")).to_be_visible()
    expect(page.locator("#qSub")).to_have_value(sub)
    expect(page.locator("#qSort")).to_have_value("rate_asc")


def test_admin_demo_csv_downloads(page, errors, base_url):
    _demo(page, base_url)
    for tab, target, count_sel in [("users", "users", "#uPager"), ("bank", "bank", "#qCount"), ("appr", "appr", None)]:
        page.locator(f"#tabs [data-tab={tab}]").click()
        if tab == "bank":
            page.locator("#qStatus").select_option("")
        if tab == "appr":
            page.locator("#arOpen").select_option("0")
        list_sel = {"users": "#uRows tr[data-id]", "bank": "#qList [data-ck]", "appr": "#arList [data-ck]"}[tab]
        expect(page.locator(list_sel).first).to_be_visible()
        btn = page.locator(f"[data-csv={target}]")
        expect(btn).to_be_visible()
        expect(btn).to_contain_text("CSV")
        with page.expect_download() as dl:
            btn.click()
        d = dl.value
        assert re.fullmatch(rf"tracer-demo-{target}-\d{{8}}\.csv", d.suggested_filename)
        lines = _csv_lines(d)
        assert len(lines) > 2
        if tab == "users":
            total = page.evaluate("() => window.TracerAdminDemo.db.users.length")
            expect(page.locator("#uPager")).to_contain_text(f"/ {total}")
            assert len(lines) == total + 1
        if tab == "bank":
            total = page.evaluate("() => window.TracerAdminDemo.db.questions.length")
            assert len(lines) == total + 1
        if tab == "appr":
            total = page.evaluate("() => window.TracerAdminDemo.db.app_reports.length")
            assert len(lines) == total + 1
    page.locator("#tabs [data-tab=activity]").click()
    expect(page.locator("[data-csv=activity]")).to_be_visible()


def test_admin_demo_command_compare_weak_csv_and_buckets(page, errors, base_url):
    _demo(page, base_url)
    li = _cmd(page, "지난주랑 비교해줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(li).to_contain_text("최근 7일 vs 그 전")
    expect(page.locator("#dDays")).to_have_value("7")
    li = _cmd(page, "약한 범위 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    page.locator("#cmdIn").fill("사용자 목록 CSV로 받아줘")
    with page.expect_download() as dl:
        page.locator("#cmdGo").click()
    assert dl.value.suggested_filename.startswith("tracer-demo-users-")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("실행함")
    page.locator("#tabs [data-tab=bank]").click()
    expect(page.locator("#buckets")).to_be_hidden()
    page.locator("#bkToggle").click()
    expect(page.locator("#buckets")).to_be_visible()


def test_admin_real_has_no_stage3_elements(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("#cmpPanel")).to_be_hidden()
    expect(page.locator("#subPanel")).to_be_hidden()
    for tab in ("users", "bank", "appr"):
        page.locator(f"#tabs [data-tab={tab}]").click()
        expect(page.locator(f"[data-csv={tab}]")).to_be_hidden()


@pytest.mark.parametrize("login", [False, True])
def test_app_mypage_demo_admin_card(page, errors, base_url, login):
    if login:
        page.add_init_script("localStorage.setItem('fake-tok', 'a')")
    page.goto(base_url + "/ccna/app.html")
    page.locator("#tab-mypage").click()
    card = page.locator("a#demoAdmin")
    expect(card).to_be_visible()
    expect(card).to_have_attribute("href", "admin.html?demo=1")
    expect(card).to_contain_text("관리자 화면 체험")
    card.click()
    expect(page).to_have_url(re.compile(r"admin\.html\?demo=1"))
    expect(page.locator("#modeTag")).to_contain_text("모의")


# ---------- 관리자 모의: 명령 기록 탭 ----------
def _demo_fresh(page, base_url, mode=None):
    page.add_init_script("if (!sessionStorage.getItem('t-cleared')) { localStorage.removeItem('tracer-admin-demo-trace'); sessionStorage.setItem('t-cleared', '1'); }")
    _demo(page, base_url, mode)


def test_admin_demo_trace_records_steps_and_persists(page, errors, base_url):
    _demo_fresh(page, base_url, "rules")
    _cmd(page, "미처리 신고 몇 건이야?")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("답변")
    _cmd(page, "승인 대기 모두 승인해줘")
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askNo").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("취소")
    _cmd(page, "오늘 날씨 어때")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("못 함")
    li = _cmd(page, "명령 기록 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#v-trace")).to_be_visible()
    rows = page.locator("#tRows tr")
    expect(rows.filter(has_text="오늘 날씨 어때")).to_have_count(1)
    n = rows.count()
    assert n >= 3
    expect(page.locator("#tCount")).to_contain_text(str(n))
    expect(rows.filter(has_text="오늘 날씨 어때")).to_contain_text("규칙에 없음 → AI에 해석 요청")
    expect(rows.filter(has_text="오늘 날씨 어때")).to_contain_text("해당 명령 없음")
    expect(rows.filter(has_text="미처리 신고 몇 건이야")).to_contain_text("규칙으로 해석")
    expect(rows.filter(has_text="미처리 신고 몇 건이야")).to_contain_text("숫자 계산(화면 안)")
    expect(rows.filter(has_text="승인 대기 모두 승인")).to_contain_text("관리자: 취소")
    page.locator("#tSt").select_option("fail")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("오늘 날씨 어때")
    page.locator("#tSt").select_option("")
    page.locator("#tPath").select_option("ai")
    expect(rows).to_have_count(1)
    page.locator("#tPath").select_option("")
    page.reload()
    page.locator("#tabs [data-tab=trace]").click()
    expect(page.locator("#tRows tr").filter(has_text="오늘 날씨 어때")).to_have_count(1)
    expect(page.locator("#tRows tr").filter(has_text="미처리 신고 몇 건이야")).to_have_count(1)


def test_admin_demo_trace_csv_and_clear(page, errors, base_url):
    _demo_fresh(page, base_url, "rules")
    _cmd(page, "미처리 신고 몇 건이야?")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("답변")
    page.locator("#tabs [data-tab=trace]").click()
    expect(page.locator("#tRows tr")).to_have_count(1)
    with page.expect_download() as dl:
        page.locator("[data-csv=trace]").click()
    assert dl.value.suggested_filename.startswith("tracer-demo-trace-")
    assert len(_csv_lines(dl.value)) == 2
    page.locator("#tClear").click()
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askYes").click()
    expect(page.locator("#tRows tr[data-id], #tRows tr td[colspan]").or_(page.locator("#tRows tr")).first).to_be_visible()
    assert page.evaluate("() => (JSON.parse(localStorage.getItem('tracer-admin-demo-trace') || '[]')).length") == 0


def test_admin_real_has_no_trace_tab(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("[data-tab=trace]")).to_be_hidden()


# ---------- 관리자 모의: 해석 방식·아무 숫자 기간·SQL 조회 ----------
def test_admin_demo_mode_default_ai_falls_back_to_rules(page, errors, base_url):
    _demo_fresh(page, base_url)
    expect(page.locator("#cmdMode")).to_have_value("ai")
    li = _cmd(page, "AI 제일 많이 쓴 사람 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#uSort")).to_have_value("ai_desc")
    page.locator("#tabs [data-tab=trace]").click()
    row = page.locator("#tRows tr").filter(has_text="AI 제일 많이 쓴 사람")
    expect(row).to_contain_text("제미나이 우선 → AI에 해석 요청")
    expect(row).to_contain_text("AI는 해당 명령 없음 → 규칙으로 대신")
    page.locator("#cmdMode").select_option("rules")
    assert page.evaluate("() => localStorage.getItem('tracer-admin-demo-mode')") == "rules"


def test_admin_demo_any_number_of_days(page, errors, base_url):
    _demo(page, base_url, "rules")
    _cmd(page, "최근 10일 신고 내역 보여줘")
    expect(page.locator("#arDays")).to_have_value("10")
    expect(page.locator("#arDays option[value='10']")).to_have_text("최근 10일")
    only_open = page.locator("#arOpen").input_value() == "1"
    n = page.evaluate("(o) => window.TracerAdminDemo.db.app_reports.filter(r => (!o || !r.resolved) && Date.now() - new Date(r.at) <= 10 * 864e5).length", only_open)
    expect(page.locator("#arCount")).to_contain_text(f"{n}건 표시")
    li = _cmd(page, "45일 동안 접속 안 한 사람 찾아줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈")
    expect(page.locator("#uIdle")).to_have_value("45")
    m = page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => Date.now() - new Date(u.last_seen || u.created_at) > 45 * 864e5).length")
    expect(page.locator("#uCount")).to_contain_text(f"{m}명")


def test_admin_demo_custom_days_option(page, errors, base_url):
    _demo(page, base_url, "rules")
    page.evaluate("() => { window.prompt = () => '12'; }")
    page.locator("#tabs [data-tab=appr]").click()
    expect(page.locator("#arDays option[value='custom']")).to_have_count(1)
    page.locator("#arDays").select_option("custom")
    expect(page.locator("#arDays")).to_have_value("12")


def _qr_users(page):
    return page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => u.name.startsWith('최')).length")


def test_admin_demo_sql_query_ai_direct_and_blocked(page, errors, base_url):
    _demo_fresh(page, base_url, "rules")
    n = _qr_users(page)
    assert n > 0
    users_before = page.evaluate("() => window.TracerAdminDemo.db.users.length")
    li = _cmd(page, "최로 시작하는 사용자 보여줘")
    expect(li.locator(".st")).to_contain_text("화면 바꿈", timeout=30000)
    expect(page.locator("#v-query")).to_be_visible()
    expect(page.locator("#qrSql")).to_contain_text("LIKE '최%'")
    expect(page.locator("#qrInfo")).to_contain_text(f"{n}행")
    expect(page.locator("#qrRows tr")).to_have_count(n)
    li = _cmd(page, "SELECT id, name FROM users WHERE name LIKE '최%'")
    expect(li.locator(".st")).to_contain_text("화면 바꿈", timeout=30000)
    expect(page.locator("#qrInfo")).to_contain_text(f"{n}행")
    page.locator("#tabs [data-tab=trace]").click()
    expect(page.locator("#tRows tr").filter(has_text="SQL 직접").first).to_be_visible()
    li = _cmd(page, "SQL로 전부 지워줘")
    expect(li.locator(".st")).to_contain_text("못 함", timeout=30000)
    assert page.evaluate("() => window.TracerAdminDemo.db.users.length") == users_before


def test_admin_demo_sql_result_rows_block_and_undo(page, errors, base_url):
    _demo(page, base_url, "rules")
    ids = page.evaluate("() => window.TracerAdminDemo.db.users.filter(u => u.name.startsWith('최')).map(u => u.id)")
    _cmd(page, "최로 시작하는 사용자 보여줘")
    expect(page.locator("#qrAll")).to_be_visible(timeout=30000)
    page.locator("#qrAll").check()
    page.locator("#qrSel").get_by_role("button", name="차단", exact=True).click()
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askYes").click()
    expect(page.locator("#undo")).to_be_visible()
    page.wait_for_function("(ids) => ids.length > 0 && ids.every(i => window.TracerAdminDemo.db.users.find(u => u.id === i).status === 'blocked')", arg=ids)
    li = _cmd(page, "방금 거 되돌려줘")
    expect(li.locator(".st")).to_contain_text("실행")
    page.wait_for_function("(ids) => ids.every(i => window.TracerAdminDemo.db.users.find(u => u.id === i).status !== 'blocked')", arg=ids)


def test_admin_demo_trace_rerun_button_and_command(page, errors, base_url):
    _demo_fresh(page, base_url, "rules")
    _cmd(page, "미처리 신고 몇 건이야?")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("답변")
    _cmd(page, "승인 대기 모두 승인해줘")
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askNo").click()
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("취소")
    page.locator("#tabs [data-tab=trace]").click()
    page.locator('[data-rerun="2"]').click()
    expect(page.locator("dialog#ask")).to_be_visible()
    page.locator("#askYes").click()
    page.wait_for_function("() => window.TracerAdminDemo.db.users.filter(u => u.status === 'pending').length === 0")
    _cmd(page, "1번 다시 실행해줘")
    expect(page.locator("#cmdLog li").filter(has=page.locator(".st", has_text="실행함")).first).to_be_visible()
    expect(page.locator("#cmdLog li").filter(has=page.locator(".st", has_text="답변"))).to_have_count(2)


# ---------- 공통 대기 카드(tracer-wait.js) ----------
def test_tracer_wait_card_shows_and_hides(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.wait_for_function("() => window.TracerWait")
    page.evaluate("() => { window.__w = window.TracerWait.start('explain'); }")
    expect(page.locator(".tw")).to_be_visible()
    expect(page.locator(".tw .t")).to_contain_text("해설")
    expect(page.locator(".tw .tip")).not_to_be_empty()
    page.evaluate("() => window.__w.done()")
    expect(page.locator(".tw")).to_have_count(0)


def test_tracer_wait_card_skipped_when_fast(page, errors, base_url):
    page.goto(base_url + "/ccna/app.html")
    page.wait_for_function("() => window.TracerWait")
    shown = page.evaluate("""() => new Promise(res => {
      let seen = false;
      const mo = new MutationObserver(() => { if (document.querySelector('.tw')) seen = true; });
      mo.observe(document.body, {childList: true, subtree: true});
      const w = window.TracerWait.start('grade');
      setTimeout(() => { w.done(); setTimeout(() => { mo.disconnect(); res(seen || !!document.querySelector('.tw')); }, 1200); }, 100);
    })""")
    assert shown is False


def test_admin_demo_wait_card_step_shows_ms(page, errors, base_url):
    _demo(page, base_url)
    page.evaluate("() => { window.__w = window.TracerWait.start('admin'); }")
    expect(page.locator(".tw")).to_be_visible()
    page.evaluate("() => window.__w.step(3)")
    expect(page.locator(".tw .term")).to_contain_text("ms")
    page.evaluate("() => window.__w.done()")
    expect(page.locator(".tw")).to_have_count(0)


# ---------- 관리자 모의 화면: 보고서 탭 ----------
def _block_ask(page):
    """규칙에 안 맞는 말은 /api/demo/ask(제미나이)로 간다. 항상 실패시켜 '못 함'이 되게 한다."""
    page.route("**/api/demo/ask*", lambda r: r.abort())


def _open_report(page):
    page.locator("#tabs [data-tab=report]").click()
    expect(page.locator("#v-report")).to_be_visible()


def test_admin_demo_report_tab_opens(page, errors, base_url):
    _demo(page, base_url)
    _open_report(page)
    expect(page.locator("#rDays")).to_have_value("30")
    expect(page.locator("#rInfo")).to_contain_text("활동")
    expect(page.locator("#rBody .tile")).to_have_count(5)
    expect(page.locator("#rBody")).to_contain_text("한 줄 요약")
    expect(page.locator("#rBody")).to_contain_text("사용자 활동")


def test_admin_demo_report_days_change_updates_info_and_hash(page, errors, base_url):
    _demo(page, base_url)
    _open_report(page)
    expect(page.locator("#rInfo")).to_contain_text("활동")
    n = lambda: int(re.search(r"활동 ([\d,]+)건", page.locator("#rInfo").inner_text()).group(1).replace(",", ""))
    t30 = page.locator("#rInfo").inner_text()
    n30 = n()
    page.locator("#rDays").select_option("7")
    page.wait_for_function("() => /days=7/.test(location.hash)")
    page.wait_for_function("t => document.querySelector('#rInfo').textContent !== t", arg=t30)
    assert n() < n30


def test_admin_demo_report_hash_opens_directly(page, errors, base_url):
    page.goto(base_url + "/ccna/admin.html?demo=1#report?days=7")
    expect(page.locator("#v-report")).to_be_visible()
    expect(page.locator("#rDays")).to_have_value("7")
    expect(page.locator("#rInfo")).to_contain_text("활동")


def test_admin_demo_report_no_commands_shows_empty_notice(page, errors, base_url):
    _demo(page, base_url)
    page.evaluate("() => localStorage.removeItem('tracer-admin-demo-trace')")
    page.reload()
    expect(page.locator("#demoBar")).to_be_visible()
    _open_report(page)
    expect(page.locator("#rBody .rp-empty")).to_contain_text("명령 기록이 없어요")
    expect(page.locator("#rInfo")).to_contain_text("명령 0건")


def test_admin_demo_report_counts_commands_and_unrecognized(page, errors, base_url):
    _block_ask(page)
    _demo(page, base_url, "rules")
    page.evaluate("() => localStorage.removeItem('tracer-admin-demo-trace')")
    page.reload()
    expect(page.locator("#cmd")).to_be_visible()
    _cmd(page, "1년 동안 접속 안 한 유저 찾아줘")
    expect(page.locator("#cmdLog li").first.locator(".st")).to_contain_text("화면 바꿈")
    li = _cmd(page, "오늘 날씨 어때")
    expect(li.locator(".st")).to_contain_text("못 함")
    _cmd(page, "최근 30일 보고서 보여줘")
    expect(page.locator("#v-report")).to_be_visible()
    expect(page.locator("#rDays")).to_have_value("30")
    # 보고서 명령 자체도 기록에 남는다(명령이 끝난 뒤 저장되므로 기간을 바꿔 다시 만들면 3건)
    page.locator("#rDays").select_option("90")
    expect(page.locator("#rInfo")).to_contain_text("명령 3건")
    expect(page.locator("#rBody")).to_contain_text("못 알아들은 문장")
    expect(page.locator("#rBody .rlist li")).to_contain_text("오늘 날씨 어때")
    expect(page.locator("#rBody .rp-empty", has_text="명령 기록이 없어요")).to_have_count(0)


def test_admin_demo_report_download_command_saves_file_and_is_recorded(page, errors, base_url):
    _demo(page, base_url, "rules")
    page.evaluate("() => localStorage.removeItem('tracer-admin-demo-trace')")
    page.reload()
    expect(page.locator("#cmd")).to_be_visible()
    with page.expect_download() as dl:
        _cmd(page, "최근 7일 보고서 파일로 받아줘")
    assert re.fullmatch(r"tracer-demo-report-7d-\d{8}\.html", dl.value.suggested_filename)
    expect(page.locator("#rDays")).to_have_value("7")
    page.locator("#rDays").select_option("14")  # 다시 만들면 방금 명령이 기록에 보인다
    expect(page.locator("#rInfo")).to_contain_text("명령 1건")


def test_admin_real_hides_report_tab(logged_in, errors, base_url):
    page = logged_in
    page.goto(base_url + "/ccna/admin.html")
    expect(page.locator("#modeTag")).to_contain_text("실제")
    expect(page.locator("#tabs [data-tab=report]")).to_be_hidden()
