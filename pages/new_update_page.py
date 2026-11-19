from playwright.sync_api import Page


class NewUpdatePage:
    """The create form: http://127.0.0.1:8000/new"""

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("input-title")
        self.jurisdiction = page.get_by_test_id("select-jurisdiction")
        self.category = page.get_by_test_id("select-category")
        self.date = page.get_by_test_id("input-date")
        self.summary = page.get_by_test_id("input-summary")
        self.submit_button = page.get_by_test_id("submit")
        self.error = page.get_by_test_id("form-error")

    def open(self):
        self.page.goto("/new")

    def fill_form(self, title, jurisdiction, category, published_date, summary=""):
        self.title.fill(title)
        self.jurisdiction.select_option(jurisdiction)
        self.category.select_option(category)
        self.date.fill(published_date)  # format: YYYY-MM-DD
        self.summary.fill(summary)

    def submit(self):
        self.submit_button.click()

    def create(self, title, jurisdiction, category, published_date, summary=""):
        self.open()
        self.fill_form(title, jurisdiction, category, published_date, summary)
        self.submit()