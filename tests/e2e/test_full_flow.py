"""The star test: ONE user action verified at EVERY layer - UI -> API -> DB."""
import re
import uuid

import pytest
import requests
from playwright.sync_api import Page, expect

from pages.home_page import HomePage
from pages.new_update_page import NewUpdatePage

TIMEOUT = 10  # seconds - never let a hung backend hang the whole CI job


@pytest.fixture
def cleanup(api_url, auth_headers, db):
    """Collects titles of records this test creates; deletes them afterwards, whatever happened."""
    titles = []
    yield titles
    for title in titles:
        for row in db.execute("SELECT id FROM regulatory_updates WHERE title = ?", (title,)):
            r = requests.delete(f"{api_url}/updates/{row['id']}", headers=auth_headers, timeout=TIMEOUT)
            assert r.status_code in (204, 404), f"Cleanup failed for id {row['id']}: {r.status_code}"


def test_update_created_in_ui_is_correct_in_api_and_db(page: Page, api_url, db, cleanup):
    # One place for the expected data - used for the form AND every check
    expected = {
        "title": f"E2E MAS crypto rules {uuid.uuid4().hex[:6]}",
        "jurisdiction": "SG",
        "category": "Rule change",
        "published_date": "2026-11-21",
        "summary": "End-to-end check across UI, API and DB",
    }
    cleanup.append(expected["title"])  # registered BEFORE anything can fail

    # ---------- 1. UI: a user creates the update through the form
    form = NewUpdatePage(page)
    form.open()
    form.fill_form(**expected)
    form.submit()

    home = HomePage(page)
    expect(home.success_banner).to_be_visible()
    expect(home.row_with_title(expected["title"])).to_have_count(1)
    expect(page).to_have_url(re.compile(r"created=\d+"))
    new_id = int(re.search(r"created=(\d+)", page.url).group(1))

    # ---------- 2. API: the same record, every field compared at once
    response = requests.get(f"{api_url}/updates/{new_id}", timeout=TIMEOUT)
    assert response.status_code == 200
    api_record = response.json()
    assert {k: api_record[k] for k in expected} == expected

    # ---------- 3. DB: exactly one row, every field compared at once
    rows = db.execute("SELECT * FROM regulatory_updates WHERE title = ?", (expected["title"],)).fetchall()
    assert len(rows) == 1, f"Expected exactly 1 row, found {len(rows)}"
    row = dict(rows[0])
    assert {k: row[k] for k in expected} == expected
    assert row["created_at"]

    # ---------- 4. Layers agree with each other
    assert api_record["id"] == row["id"] == new_id
