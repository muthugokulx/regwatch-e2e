"""RegWatch - a small "regulatory updates" app to practise end-to-end testing.

Layers you will test:
  UI  : http://127.0.0.1:8000/          (list page)  and  /new  (create form)
  API : http://127.0.0.1:8000/api/updates  (REST, JSON)   docs at /docs
  DB  : SQLite file regwatch.db, table regulatory_updates
"""
import html
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import FastAPI, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, ValidationError

DB_PATH = os.getenv("DB_PATH", "regwatch.db")
API_KEY = os.getenv("API_KEY", "dev-key")

JURISDICTIONS = ["UK", "US", "EU", "IN", "SG", "AU"]
CATEGORIES = ["Rule change", "Consultation", "Guidance", "Enforcement"]


# ---------------------------------------------------------------- database
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS regulatory_updates (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT NOT NULL,
                jurisdiction   TEXT NOT NULL,
                category       TEXT NOT NULL,
                published_date TEXT NOT NULL,
                summary        TEXT,
                created_at     TEXT NOT NULL
            )
            """
        )


init_db()


# ---------------------------------------------------------------- models
class UpdateIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    jurisdiction: Literal["UK", "US", "EU", "IN", "SG", "AU"]
    category: Literal["Rule change", "Consultation", "Guidance", "Enforcement"]
    published_date: date
    summary: str = Field(min_length=5, max_length=2000)


def insert_update(u: UpdateIn) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO regulatory_updates "
            "(title, jurisdiction, category, published_date, summary, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                u.title.strip(),
                u.jurisdiction,
                u.category,
                u.published_date.isoformat(),
                u.summary,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def fetch_all(jurisdiction: Optional[str] = None):
    sql = "SELECT * FROM regulatory_updates"
    params = ()
    if jurisdiction:
        sql += " WHERE jurisdiction = ?"
        params = (jurisdiction,)
    sql += " ORDER BY id DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def fetch_one(update_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM regulatory_updates WHERE id = ?", (update_id,)
        ).fetchone()
    return dict(row) if row else None


def check_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(title="RegWatch", version="1.0")


# ---------------------------------------------------------------- API
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/updates")
def list_updates(jurisdiction: Optional[str] = None):
    if jurisdiction and jurisdiction not in JURISDICTIONS:
        raise HTTPException(status_code=400, detail="Unknown jurisdiction")
    return fetch_all(jurisdiction)


@app.get("/api/updates/{update_id}")
def get_update(update_id: int):
    row = fetch_one(update_id)
    if not row:
        raise HTTPException(status_code=404, detail="Update not found")
    return row


@app.post("/api/updates", status_code=201)
def create_update(payload: UpdateIn, x_api_key: Optional[str] = Header(default=None)):
    check_key(x_api_key)
    new_id = insert_update(payload)
    return fetch_one(new_id)


@app.delete("/api/updates/{update_id}", status_code=204)
def delete_update(update_id: int, x_api_key: Optional[str] = Header(default=None)):
    check_key(x_api_key)
    if not fetch_one(update_id):
        raise HTTPException(status_code=404, detail="Update not found")
    with get_conn() as conn:
        conn.execute("DELETE FROM regulatory_updates WHERE id = ?", (update_id,))


# ---------------------------------------------------------------- UI
STYLE = """
<style>
 body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:30px auto;padding:0 16px;color:#222}
 h1{color:#1f3a5f} table{width:100%;border-collapse:collapse;margin-top:16px}
 th,td{border-bottom:1px solid #ddd;padding:8px;text-align:left} th{background:#f2f5f9}
 a.btn,button{background:#1f3a5f;color:#fff;padding:8px 14px;border:0;border-radius:4px;text-decoration:none;cursor:pointer}
 label{display:block;margin-top:12px;font-weight:600} input,select,textarea{width:100%;padding:6px;margin-top:4px}
 .ok{background:#e5f4e4;padding:10px;border-radius:4px} .err{background:#fbebeb;padding:10px;border-radius:4px}
</style>
"""


def page(title: str, body: str) -> str:
    return f"<!doctype html><html><head><title>{title}</title>{STYLE}</head><body>{body}</body></html>"


@app.get("/", response_class=HTMLResponse)
def home(created: Optional[int] = None, jurisdiction: Optional[str] = None):
    rows = fetch_all(jurisdiction if jurisdiction in JURISDICTIONS else None)
    banner = (
        f'<p class="ok" data-testid="success-banner">Update #{created} created successfully.</p>'
        if created
        else ""
    )
    options = "".join(
        f'<option value="{j}" {"selected" if j == jurisdiction else ""}>{j}</option>'
        for j in JURISDICTIONS
    )
    trs = "".join(
        f'<tr data-testid="update-row" data-id="{r["id"]}">'
        f'<td>{r["id"]}</td><td data-testid="row-title">{html.escape(r["title"])}</td>'
        f'<td>{r["jurisdiction"]}</td><td>{r["category"]}</td><td>{r["published_date"]}</td></tr>'
        for r in rows
    )
    empty = '<p data-testid="empty-state">No regulatory updates yet.</p>' if not rows else ""
    body = f"""
    <h1>RegWatch - Regulatory Updates</h1>
    {banner}
    <a class="btn" href="/new" data-testid="add-update">+ Add update</a>
    <form method="get" action="/" style="margin-top:16px">
      <label for="filter">Filter by jurisdiction</label>
      <select id="filter" name="jurisdiction" data-testid="filter-jurisdiction" onchange="this.form.submit()">
        <option value="">All</option>{options}
      </select>
    </form>
    <table data-testid="updates-table">
      <thead><tr><th>ID</th><th>Title</th><th>Jurisdiction</th><th>Category</th><th>Published</th></tr></thead>
      <tbody>{trs}</tbody>
    </table>
    {empty}
    """
    return page("RegWatch", body)


def form_html(error: str = "", values: Optional[dict] = None) -> str:
    v = values or {}
    err = f'<p class="err" data-testid="form-error">{html.escape(error)}</p>' if error else ""
    j_opts = "".join(
        f'<option value="{j}" {"selected" if v.get("jurisdiction") == j else ""}>{j}</option>'
        for j in JURISDICTIONS
    )
    c_opts = "".join(
        f'<option value="{c}" {"selected" if v.get("category") == c else ""}>{c}</option>'
        for c in CATEGORIES
    )
    return page(
        "New update - RegWatch",
        f"""
    <h1>Add regulatory update</h1>
    {err}
    <form method="post" action="/updates" data-testid="update-form">
      <label for="title">Title</label>
      <input id="title" name="title" data-testid="input-title" value="{html.escape(v.get('title', ''))}">
      <label for="jurisdiction">Jurisdiction</label>
      <select id="jurisdiction" name="jurisdiction" data-testid="select-jurisdiction">
        <option value="">-- select --</option>{j_opts}
      </select>
      <label for="category">Category</label>
      <select id="category" name="category" data-testid="select-category">
        <option value="">-- select --</option>{c_opts}
      </select>
      <label for="published_date">Published date</label>
      <input id="published_date" type="date" name="published_date" data-testid="input-date" value="{html.escape(v.get('published_date', ''))}">
      <label for="summary">Summary</label>
      <textarea id="summary" name="summary" rows="4" data-testid="input-summary">{html.escape(v.get('summary', ''))}</textarea>
      <p><button type="submit" data-testid="submit">Save update</button>
         <a href="/" data-testid="cancel">Cancel</a></p>
    </form>
    """,
    )


@app.get("/new", response_class=HTMLResponse)
def new_form():
    return form_html()


@app.post("/updates")
def submit_form(
    title: str = Form(""),
    jurisdiction: str = Form(""),
    category: str = Form(""),
    published_date: str = Form(""),
    summary: str = Form(""),
):
    values = dict(
        title=title,
        jurisdiction=jurisdiction,
        category=category,
        published_date=published_date,
        summary=summary,
    )
    try:
        payload = UpdateIn(
            title=title,
            jurisdiction=jurisdiction,
            category=category,
            published_date=published_date,
            summary=summary.strip(),
        )
    except ValidationError as e:
        first = e.errors()[0]
        field = first["loc"][0] if first["loc"] else "form"
        return HTMLResponse(
            form_html(f"Please fix '{field}': {first['msg']}", values), status_code=400
        )
    new_id = insert_update(payload)
    return RedirectResponse(url=f"/?created={new_id}", status_code=303)
