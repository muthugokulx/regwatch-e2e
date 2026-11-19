import re
import uuid

from playwright.sync_api import Page, expect

from pages.home_page import HomePage
from pages.new_update_page import NewUpdatePage


def unique_title(prefix: str) -> str:
    # A random suffix so every run creates a NEW record we can find for sure
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def test_add_update_appears_in_list(page: Page):
    title = unique_title("RBI KYC update")

    form = NewUpdatePage(page)
    form.open()
    form.fill_form(title, "IN", "Rule change", "2026-11-20", "New KYC rules for banks")
    form.submit()

    home = HomePage(page)
    expect(home.success_banner).to_be_visible()
    expect(home.row_with_title(title)).to_have_count(1)
    expect(home.row_with_title(title)).to_contain_text("IN")
    expect(home.row_with_title(title)).to_contain_text("Rule change")


def test_short_title_shows_error(page: Page):
    form = NewUpdatePage(page)
    form.open()
    form.fill_form("ab", "UK", "Guidance", "2026-11-20")
    form.submit()

    expect(form.error).to_be_visible()
    expect(form.error).to_contain_text("title")


def test_filter_by_jurisdiction(page: Page):
    uk_title = unique_title("FCA guidance")
    sg_title = unique_title("MAS notice")

    form = NewUpdatePage(page)
    form.create(uk_title, "UK", "Guidance", "2026-11-20")
    expect(HomePage(page).success_banner).to_be_visible()

    form.create(sg_title, "SG", "Consultation", "2026-11-20")
    expect(HomePage(page).success_banner).to_be_visible()
    home = HomePage(page)
    home.open()
    home.filter.select_option("UK")

    expect(page).to_have_url(re.compile(r"jurisdiction=UK"))
    expect(home.row_with_title(uk_title)).to_have_count(1)
    expect(home.row_with_title(sg_title)).to_have_count(0)
