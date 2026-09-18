import json
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = os.getenv(
    "CAMBRIDGE_SHEET_ID", "1YygZmt2X717DTLprSoXPKOHzT8JpCiNRHp3wSLnktOg"
)
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_service_account.json")
REGISTRATIONS_SHEET_NAME = "Registrations"


def _credentials_info() -> dict:
    # On Render (no persistent disk / no local file), the full JSON key is
    # set directly as an env var. Locally, a gitignored file is simpler.
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        return json.loads(raw)
    path = Path(CREDENTIALS_FILE)
    if path.exists():
        return json.loads(path.read_text())
    raise RuntimeError(
        "No Google service account credentials found. Set the "
        "GOOGLE_SERVICE_ACCOUNT_JSON env var (full JSON key content) or "
        f"provide a file at {CREDENTIALS_FILE}."
    )


def _client() -> gspread.Client:
    creds = Credentials.from_service_account_info(_credentials_info(), scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_worksheet(sheet_name: str, header: list[str]) -> gspread.Worksheet:
    sh = _client().open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=max(len(header), 10))
        ws.append_row(header)
        return ws


def upsert_registrations(rows: list[dict], fields: list[str]):
    """Write validated registrations to the shared "Registrations" sheet.

    One row per order_number: a rerun of the same order (e.g. a retry that
    now succeeds) replaces its previous row instead of duplicating it —
    same semantics as the local xlsx database this replaces.
    """
    if not rows:
        return

    ws = _get_or_create_worksheet(REGISTRATIONS_SHEET_NAME, fields)
    existing = ws.get_all_values()
    header = existing[0] if existing else fields
    order_number_col = header.index("order_number")

    # Map order_number -> 1-indexed sheet row number, for existing rows.
    existing_rows = {
        row[order_number_col]: idx
        for idx, row in enumerate(existing[1:], start=2)
        if len(row) > order_number_col
    }

    updates = []
    appends = []
    for row_dict in rows:
        row_values = [str(row_dict.get(field, "")) for field in header]
        order_number = str(row_dict.get("order_number", ""))
        if order_number in existing_rows:
            updates.append((existing_rows[order_number], row_values))
        else:
            appends.append(row_values)

    for row_number, row_values in updates:
        ws.update(f"A{row_number}", [row_values])
    if appends:
        ws.append_rows(appends)
