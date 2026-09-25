from playwright.sync_api import TimeoutError as PWTimeoutError

from cambridge.sessions import _settle

GENDER_MAP = {
    "m": "m",
    "male": "m",
    "homme": "m",
    "h": "m",
    "f": "f",
    "female": "f",
    "femme": "f",
}


def map_gender(raw: str):
    """Map a raw X-Net gender value to Metrica's option value ('m'/'f').

    Returns None when the value is missing or not confidently recognised —
    callers must treat that as ambiguous and route the order to manual
    review rather than guessing (per project safety rules).
    """
    if not raw:
        return None
    return GENDER_MAP.get(raw.strip().lower())


# Stable ids confirmed live. get_by_label() is unreliable on this form: the
# "Search Existing" text box has no accessible label at all, its own
# "Search" button collides by name with an unrelated toggle elsewhere on
# the site, and generic labels like "DD"/"MM"/"YYYY" have been observed to
# resolve to the wrong field entirely (the form has hidden/duplicated
# fields depending on product). Explicit ids avoid all of that.
_PREFIX = "#ctl00_ContentPlaceHolder_registeredCandidates1_"
_SEARCH_BOX_ID = _PREFIX + "txtSearch"
_SEARCH_BTN_ID = _PREFIX + "btnSearch"
_ADD_EXISTING_SAVE_ID = _PREFIX + "btnAddExistingSave"
_USERNAME_ID = _PREFIX + "txtLogin"
_PASSWORD_ID = _PREFIX + "txtPassword"
_FIRST_NAME_ID = _PREFIX + "txtFirstName"
_LAST_NAME_ID = _PREFIX + "txtSurname"
# These ids carry an "EST" infix under the EST General/Business groups
# (e.g. "txtESTEmailAddress") but NOT under the New Linguaskill groups
# (just "txtEmailAddress") — confirmed live for both. Suffix-match instead
# of hardcoding either variant so this works for both session types. Tag
# name is required: plain "[id$=...]" also matches hidden ASP.NET
# validator spans with ids like "rfvtxtEmailAddress", causing ambiguity.
_EMAIL_ID = 'input[id$="EmailAddress"]'
_DOB_DAY_ID = 'select[id$="Day"]'
_DOB_MONTH_ID = 'select[id$="Month"]'
_DOB_YEAR_ID = 'select[id$="Year"]'
_GENDER_ID = 'select[id$="Gender"]'
_ID_NUMBER_ID = 'input[id$="identitydocumentnumber"]'
_NATIONALITY_ID = 'select[id$="Nationality"]'
_SINGLE_SAVE_ID = _PREFIX + "btnAddSingleSave"
_RESULTS_GRID_ID = _PREFIX + "grdSelectUsers"
_NO_MATCH_TEXT = "There are no matching students"


def click_and_wait_for_page(page, locator):
    """Click something that reloads the whole page and wait for the new one.

    Confirmed live: Add Entries, the "Search Existing"/"Single candidate
    Entry" tabs and the Search button are all full-page form posts. Wait
    for that navigation instead of "networkidle": the site's background
    telemetry can keep the network busy, and on Render networkidle then
    never came within 30s (26-2415 failed that way in Search Existing).
    """
    with page.expect_navigation(wait_until="domcontentloaded", timeout=60_000):
        locator.click()


def find_existing_candidate(page, email: str):
    """Search the "Search Existing" tab for an exact email match.

    Returns:
      - a Locator for the matching row's checkbox, if exactly one match
      - None if there is no match
      - raises RuntimeError if the search is ambiguous (more than one
        exact match) — this must not be guessed away.
    """
    click_and_wait_for_page(page, page.get_by_role("link", name="Search Existing"))
    page.locator(_SEARCH_BOX_ID).fill(email)
    click_and_wait_for_page(page, page.locator(_SEARCH_BTN_ID))

    # "No row matched" is only trustworthy once the results are really on
    # screen — reading an unfinished page as "no match" would create a
    # duplicate Cambridge account. Require the results grid or the site's
    # own no-match message.
    try:
        page.locator(_RESULTS_GRID_ID).or_(page.get_by_text(_NO_MATCH_TEXT)).first.wait_for(
            state="visible", timeout=15_000
        )
    except PWTimeoutError:
        raise RuntimeError("'Search Existing' results did not load — cannot tell whether the candidate exists")

    rows = page.locator("tr").filter(has_text=email)
    count = rows.count()
    if count == 0:
        return None
    if count > 1:
        raise RuntimeError(
            f"Ambiguous 'Search Existing' match for {email!r}: {count} rows"
        )
    return rows.first.locator('input[type="checkbox"]')


def save_existing_candidate(page, checkbox):
    """Check the given "Search Existing" row's checkbox and save it into
    the session. `checkbox` is the Locator returned by
    find_existing_candidate() — call that first to locate it."""
    # This checkbox (id ends in "chkSelect") renders outside the visible
    # viewport — confirmed live: Playwright's check()/click() hang forever
    # retrying "element is outside of the viewport". Dispatch a real DOM
    # click via JS instead, which fires the same onclick handler.
    checkbox.evaluate("el => el.click()")
    page.locator(_ADD_EXISTING_SAVE_ID).click()
    _settle(page)  # tolerant wait; verify_registration() checks the outcome


def fill_single_candidate_entry(page, order: dict):
    """Fill and save the Single Candidate Entry form for a new candidate.

    `order` must provide: email, password, name, surname, date_of_birth
    (DD/MM/YYYY), gender, nationality, id_number.
    """
    gender_code = map_gender(order.get("gender"))
    if gender_code is None:
        raise RuntimeError(
            f"Cannot map gender {order.get('gender')!r} for order "
            f"{order.get('order_number')} — needs manual review"
        )

    day, month, year = order["date_of_birth"].split("/")
    day, month = day.zfill(2), month.zfill(2)  # option values are "01".."31" / "01".."12"

    click_and_wait_for_page(page, page.get_by_role("link", name="Single candidate Entry"))
    page.locator(_USERNAME_ID).wait_for(state="visible", timeout=15_000)

    page.locator(_USERNAME_ID).fill(order["email"])
    page.locator(_PASSWORD_ID).fill(order["password"])
    page.locator(_FIRST_NAME_ID).fill(order["name"])
    page.locator(_LAST_NAME_ID).fill(order["surname"])
    page.locator(_EMAIL_ID).fill(order["email"])

    page.locator(_DOB_DAY_ID).select_option(value=day)
    page.locator(_DOB_MONTH_ID).select_option(value=month)
    page.locator(_DOB_YEAR_ID).select_option(value=year)

    page.locator(_GENDER_ID).select_option(value=gender_code)
    page.locator(_ID_NUMBER_ID).fill(order["id_number"])
    page.locator(_NATIONALITY_ID).select_option(label=order["nationality"])

    page.locator(_SINGLE_SAVE_ID).click()
    _settle(page)  # tolerant wait; verify_registration() checks the outcome
