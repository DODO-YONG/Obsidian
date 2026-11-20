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
    expect(page.locator("#gradeBtn")).to_have_text("다음 문제")


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
