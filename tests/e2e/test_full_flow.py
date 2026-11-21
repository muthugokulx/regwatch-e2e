"""The star test: ONE user action verified at EVERY layer - UI -> API -> DB."""
import re
import uuid

import requests
from playwright.sync_api import Page, expect

from pages.home_page import HomePage
from pages.new_update_page import NewUpdatePage


def test_update_created_in_ui_is_correct_in_api_and_db(page: Page, api_url, auth_headers, db):
    title = f"E2E MAS crypto rules {uuid.uuid4().hex[:6]}"
    summary = "End-to-end check across UI, API and DB"

    # ---------- 1. UI: a user creates the update through the form
    form = NewUpdatePage(page)
    form.open()
    form.fill_form(title, "SG", "Rule change", "2026-11-21", summary)
    form.submit()

    home = HomePage(page)
    expect(home.success_banner).to_be_visible()
    expect(home.row_with_title(title)).to_have_count(1)

    # The app redirects to /?created=<id> - read the new record's id from the URL
    expect(page).to_have_url(re.compile(r"created=\d+"))
    new_id = int(re.search(r"created=(\d+)", page.url).group(1))

    try:
        # ---------- 2. API: the same record is returned correctly by the backend
        response = requests.get(f"{api_url}/updates/{new_id}")
        assert response.status_code == 200
        api_record = response.json()
        assert api_record["title"] == title
        assert api_record["jurisdiction"] == "SG"
        assert api_record["category"] == "Rule change"
        assert api_record["published_date"] == "2026-11-21"
        assert api_record["summary"] == summary

        # ---------- 3. DB: the row is stored exactly once, with the right values
        rows = db.execute(
            "SELECT * FROM regulatory_updates WHERE title = ?", (title,)
        ).fetchall()
        assert len(rows) == 1, f"Expected exactly 1 row, found {len(rows)}"
        row = rows[0]
        assert row["id"] == new_id
        assert row["jurisdiction"] == "SG"
        assert row["category"] == "Rule change"
        assert row["published_date"] == "2026-11-21"
        assert row["summary"] == summary
        assert row["created_at"] is not None

        # ---------- 4. Layers agree with each other
        assert api_record["id"] == row["id"]
        assert api_record["created_at"] == row["created_at"]
    finally:
        # ---------- cleanup: remove test data even if an assertion failed
        requests.delete(f"{api_url}/updates/{new_id}", headers=auth_headers)
