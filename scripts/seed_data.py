"""Fill regwatch.db with practice data for SQL learning.

Run from the project root:
    python scripts/seed_data.py           # practice data WITH planted bugs (for learning)
    python scripts/seed_data.py --clean   # clean data, no bugs (used by CI)

Creates / refills 3 tables:
  regulatory_updates  - the app's main table (30 rows, some with planted data problems)
  jurisdictions       - lookup table: code -> country name + regulator
  reviews             - compliance team reviews of each update (for JOIN practice)

Planted data-quality problems (find them with SQL!):
  - a duplicate update (same title + jurisdiction + date)
  - an update with an unknown jurisdiction code
  - updates with a missing (NULL) summary
  - a review that points to an update that does not exist (orphan record)
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import DB_PATH, init_db  # noqa: E402

CLEAN = "--clean" in sys.argv

init_db()
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript(
    """
    DROP TABLE IF EXISTS reviews;
    DROP TABLE IF EXISTS jurisdictions;
    DELETE FROM regulatory_updates;
    DELETE FROM sqlite_sequence WHERE name = 'regulatory_updates';

    CREATE TABLE jurisdictions (
        code      TEXT PRIMARY KEY,
        country   TEXT NOT NULL,
        regulator TEXT NOT NULL
    );

    CREATE TABLE reviews (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        update_id   INTEGER NOT NULL,
        reviewer    TEXT NOT NULL,
        status      TEXT NOT NULL,      -- Pending / Approved / Rejected
        risk_level  TEXT NOT NULL,      -- Low / Medium / High
        reviewed_at TEXT
    );
    """
)

cur.executemany(
    "INSERT INTO jurisdictions VALUES (?, ?, ?)",
    [
        ("UK", "United Kingdom", "FCA"),
        ("US", "United States", "SEC"),
        ("EU", "European Union", "ESMA"),
        ("IN", "India", "RBI"),
        ("SG", "Singapore", "MAS"),
        ("AU", "Australia", "ASIC"),
    ],
)

updates = [
    # title, jurisdiction, category, published_date, summary
    ("Consumer Duty implementation review", "UK", "Guidance", "2026-01-15", "FCA expectations for fair value"),
    ("Climate disclosure rules", "US", "Rule change", "2026-02-03", "SEC climate reporting requirements"),
    ("MiCA crypto-asset licensing", "EU", "Rule change", "2026-02-20", "Licensing for crypto service providers"),
    ("KYC master direction amendment", "IN", "Rule change", "2026-03-01", "Updated customer due diligence"),
    ("Technology risk management", "SG", "Guidance", "2026-03-10", "MAS TRM guidelines refresh"),
    ("Design and distribution obligations", "AU", "Guidance", "2026-03-18", None),
    ("Operational resilience deadline", "UK", "Rule change", "2026-03-31", "Firms must remain within impact tolerances"),
    ("Insider trading enforcement action", "US", "Enforcement", "2026-04-05", "Penalty against broker-dealer"),
    ("DORA ICT incident reporting", "EU", "Rule change", "2026-04-12", "Incident classification thresholds"),
    ("Digital lending guidelines", "IN", "Guidance", "2026-04-20", "Rules for lending apps"),
    ("AML notice consultation", "SG", "Consultation", "2026-05-02", "Proposed AML/CFT changes"),
    ("Greenwashing enforcement", "AU", "Enforcement", "2026-05-15", "ASIC action on misleading ESG claims"),
    ("Smarter regulatory framework", "UK", "Consultation", "2026-05-28", None),
    ("Best execution amendments", "US", "Consultation", "2026-06-04", "Proposed Regulation Best Execution"),
    ("AI Act obligations for banks", "EU", "Guidance", "2026-06-15", "High-risk AI system requirements"),
    ("Cybersecurity framework for banks", "IN", "Rule change", "2026-06-22", "Mandatory cyber controls"),
    ("Payment services act update", "SG", "Rule change", "2026-07-01", "New stablecoin rules"),
    ("Scams prevention framework", "AU", "Rule change", "2026-07-09", "Bank obligations against scams"),
    ("Market abuse fine", "UK", "Enforcement", "2026-07-21", "Fine for failing to report suspicious trades"),
    ("Cyber incident disclosure", "US", "Guidance", "2026-08-02", "Form 8-K cyber disclosures"),
    ("ESG fund naming guidelines", "EU", "Guidance", "2026-08-14", None),
    ("Fraud risk management directions", "IN", "Guidance", "2026-08-25", "Early warning signals for fraud"),
    ("Outsourcing guidelines", "SG", "Consultation", "2026-09-05", "Third-party risk management"),
    ("Breach reporting update", "AU", "Guidance", "2026-09-16", "Clarified reportable situations"),
    ("Consumer Duty implementation review", "UK", "Guidance", "2026-01-15", "FCA expectations for fair value"),  # DUPLICATE
    ("Basel III endgame proposal", "US", "Consultation", "2026-10-01", "Capital requirements for large banks"),
    ("Sanctions screening expectations", "EU", "Enforcement", "2026-10-11", "Penalty for sanctions breaches"),
    ("Climate risk disclosure", "IN", "Consultation", "2026-10-20", "Draft climate disclosure framework"),
    ("Unknown regulator bulletin", "XX", "Guidance", "2026-10-28", "Bad jurisdiction code from import"),  # BAD CODE
    ("Crypto custody rules", "SG", "Rule change", "2026-11-05", "Safeguarding customer crypto assets"),
]
if CLEAN:
    updates = [u for u in updates if u[1] != "XX"]                      # drop bad code
    updates = list(dict.fromkeys(updates))                               # drop duplicate
    updates = [(t, j, c, d, s or "Summary pending from regulator") for t, j, c, d, s in updates]

cur.executemany(
    "INSERT INTO regulatory_updates "
    "(title, jurisdiction, category, published_date, summary, created_at) "
    "VALUES (?, ?, ?, ?, ?, datetime('now'))",
    updates,
)

reviewers = ["Priya", "Arjun", "Meera", "Karthik"]
statuses = ["Approved", "Approved", "Pending", "Rejected", "Approved"]
risks = ["Low", "Medium", "High"]
reviews = []
for update_id in range(1, 25):  # updates 25-30 have no review yet
    reviews.append(
        (
            update_id,
            reviewers[update_id % 4],
            statuses[update_id % 5],
            risks[update_id % 3],
            None if statuses[update_id % 5] == "Pending" else f"2026-11-{(update_id % 18) + 1:02d}",
        )
    )
if not CLEAN:
    reviews.append((999, "Arjun", "Approved", "High", "2026-11-10"))  # ORPHAN: update 999 does not exist
cur.executemany(
    "INSERT INTO reviews (update_id, reviewer, status, risk_level, reviewed_at) VALUES (?, ?, ?, ?, ?)",
    reviews,
)

conn.commit()
for table in ("regulatory_updates", "jurisdictions", "reviews"):
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table:20} {count} rows")
conn.close()
print("Done. Open regwatch.db in DB Browser for SQLite.")
