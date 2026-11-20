"""Data-quality checks: the same SQL a data QA runs by hand, now automated."""


def test_no_duplicate_updates(db):
    rows = db.execute(
        """
        SELECT title, jurisdiction, published_date, COUNT(*) AS copies
        FROM regulatory_updates
        GROUP BY title, jurisdiction, published_date
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    assert rows == [], f"Duplicate updates found: {[dict(r) for r in rows]}"


def test_all_jurisdictions_are_valid(db):
    rows = db.execute(
        """
        SELECT u.id, u.title, u.jurisdiction
        FROM regulatory_updates u
        LEFT JOIN jurisdictions j ON j.code = u.jurisdiction
        WHERE j.code IS NULL
        """
    ).fetchall()
    assert rows == [], f"Unknown jurisdiction codes: {[dict(r) for r in rows]}"


def test_no_orphan_reviews(db):
    rows = db.execute(
        """
        SELECT r.id, r.update_id
        FROM reviews r
        LEFT JOIN regulatory_updates u ON u.id = r.update_id
        WHERE u.id IS NULL
        """
    ).fetchall()
    assert rows == [], f"Reviews pointing to missing updates: {[dict(r) for r in rows]}"


def test_every_update_has_a_summary(db):
    rows = db.execute(
        """
        SELECT id, title
        FROM regulatory_updates
        WHERE summary IS NULL OR TRIM(summary) = ''
        """
    ).fetchall()
    assert rows == [], f"Updates missing a summary: {[dict(r) for r in rows]}"