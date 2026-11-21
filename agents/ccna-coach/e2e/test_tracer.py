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


# ---------- 휴대폰 화면 ----------
@pytest.mark.parametrize("path", ["/ccna/", "/ccna/about.html", "/ccna/app.html"])
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
