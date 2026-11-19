from playwright.sync_api import Page


class HomePage:
    """The list page: http://127.0.0.1:8000/"""

    def __init__(self, page: Page):
        self.page = page
        self.add_button = page.get_by_test_id("add-update")
        self.success_banner = page.get_by_test_id("success-banner")
        self.rows = page.get_by_test_id("update-row")
        self.filter = page.get_by_test_id("filter-jurisdiction")

    def open(self):
        self.page.goto("/")

    def row_with_title(self, title: str):
        return self.rows.filter(has_text=title)