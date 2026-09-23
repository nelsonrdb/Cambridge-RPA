import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cambridge.auth import SESSIONS_URL

# Two products, each in General/Business, mapped to their own Group:
#  - Linguaskill orders -> "New Linguaskill ... Remote". Never EST: a
#    Linguaskill candidate was once wrongly registered under "EST for
#    Business" — cross-checked live against a candidate's own prior correct
#    session (Invigilation Method "Remote - Record and Review").
#  - English Skills Test (EST) orders -> "EST General" / "EST for Business"
#    (Invigilation Method auto-fills to "EST/EST For School"). Confirmed
#    live 2026-09-22 — the site's option labels carry a trailing space,
#    which select_option(label=...) tolerates.
LINGUASKILL = "LINGUASKILL"
EST = "EST"
GROUP_BY_PRODUCT_KIND = {
    (LINGUASKILL, "General"): "New Linguaskill General Remote",
    (LINGUASKILL, "Business"): "New Linguaskill Business Remote",
    (EST, "General"): "EST General",
    (EST, "Business"): "EST for Business",
}
GROUP_BY_KIND = {
    kind: group
    for (product, kind), group in GROUP_BY_PRODUCT_KIND.items()
    if product == LINGUASKILL
}
PARIS = ZoneInfo("Europe/Paris")
VENUE = "REMOTE"

# Order of the four possible test components as they appear on the site.
COMPONENT_LABELS = {
    "R": "Reading",
    "L": "Listening",
    "S": "Speaking",
    "W": "Writing",
}


def normalize_exam_hour(exam_hour: str) -> str:
    """X-Net stores exam_hour in French shorthand, e.g. "10h" (always on
    the hour, per get_data.py's parse_exam_id_block) — the legacy UiPath
    workflow converted this the same way before typing it into Metrica.
    Passes "HH:MM" through unchanged in case the source format changes.
    """
    exam_hour = exam_hour.strip()
    if "h" in exam_hour.lower():
        hour = exam_hour.lower().replace("h", "").strip()
        return f"{int(hour):02d}:00"
    return exam_hour


def product_of(linguaskill_type: str) -> str:
    """'LINGUASKILL General' -> LINGUASKILL, 'ENGLISH SKILLS TEST Business' -> EST."""
    upper = (linguaskill_type or "").upper()
    if "ENGLISH SKILLS TEST" in upper:
        return EST
    if "LINGUASKILL" in upper:
        return LINGUASKILL
    raise ValueError(f"Unrecognised product in linguaskill_type: {linguaskill_type!r}")


def group_for(linguaskill_type: str) -> str:
    return GROUP_BY_PRODUCT_KIND[(product_of(linguaskill_type), linguaskill_kind(linguaskill_type))]


def linguaskill_kind(linguaskill_type: str) -> str:
    """'LINGUASKILL General' / 'ENGLISH SKILLS TEST Business' -> 'General' / 'Business'."""
    if not linguaskill_type:
        raise ValueError("linguaskill_type is empty")
    if "General" in linguaskill_type:
        return "General"
    if "Business" in linguaskill_type:
        return "Business"
    raise ValueError(f"Unrecognised linguaskill_type: {linguaskill_type!r}")


def _settle(page):
    """Wait out an ASP.NET partial-postback. networkidle alone is not
    enough: consecutive postbacks fired too quickly get dropped/raced, and
    under real (slower) conditions a second navigation can still be
    in-flight when networkidle first resolves — retry once if so."""
    for _ in range(3):
        try:
            page.wait_for_load_state("networkidle")
            break
        except Exception:
            page.wait_for_timeout(500)
    page.wait_for_timeout(800)


def _safe_title(page, retries: int = 5, delay_ms: int = 500) -> str:
    """page.title() can raise "Execution context was destroyed" if a
    navigation is still in flight right after _settle() returns — retry
    briefly instead of treating that as a real failure."""
    for attempt in range(retries):
        try:
            return page.title()
        except Exception:
            if attempt == retries - 1:
                raise
            page.wait_for_timeout(delay_ms)


def _open_search_panel(page):
    # id "showSearch2" confirmed live: the icon-only button (no accessible
    # name) that reveals the Session Name / Test / Venue / Client filters.
    toggle = page.locator("#showSearch2")
    field = page.get_by_label("Session Name")
    if not field.is_visible():
        try:
            toggle.click(timeout=15000)
        except Exception as exc:
            from cambridge.auth import is_login_page

            raise RuntimeError(
                "Could not find the Sessions page search toggle "
                f"(#showSearch2). URL: {page.url}. Title: {_safe_title(page)!r}. "
                f"Looks like the login page: {is_login_page(page)}. "
                f"Original error: {exc}"
            )
    field.wait_for(state="visible", timeout=10000)


def find_session(page, session_name: str):
    """Return the session row link if a session with this exact name exists, else None."""
    page.goto(SESSIONS_URL, wait_until="domcontentloaded")
    _open_search_panel(page)
    page.get_by_label("Session Name").fill(session_name)
    # Not get_by_role("button", name="Search"): the search-panel *toggle*
    # button also exposes an accessible name of "Search" (via its icon's
    # alt text), which makes that lookup ambiguous. This id is stable.
    page.locator("#ctl00_ContentPlaceHolder_btnSearch").click()
    _settle(page)

    link = page.get_by_role("link", name=session_name, exact=True)
    if link.count() == 0:
        return None
    return link.first


def open_session(page, session_name: str):
    """Find and open a session's entries page. Raises if it doesn't exist
    or if the navigation into it doesn't take (seen live: the postback can
    resolve "networkidle" before the actual page swap happens)."""
    link = find_session(page, session_name)
    if link is None:
        raise RuntimeError(f"Session not found: {session_name!r}")
    link.click()
    _settle(page)

    title = _safe_title(page)
    if "Session Entries" not in title:
        raise RuntimeError(
            f"Opening session {session_name!r} did not land on its entries page "
            f"(title was {title!r})"
        )


def create_session(page, order: dict):
    """Create a new session for `order` on the currently-loaded Sessions page.

    `order` must provide: linguaskill_type, exam_date (DD/MM/YYYY), exam_hour
    (HH:MM), skills_code (subset of "RLSW"), session_name.

    EST has no exam date: the session starts one hour from now (Paris time
    — same as Cambridge's own default, and never in the past on submit)
    and Cambridge itself sets the end ~3 months later. exam_date/exam_hour are ignored.

    Returns the EST validity window (start_date, end_date) as read from the
    form, or None for Linguaskill.
    """
    is_est = product_of(order["linguaskill_type"]) == EST
    group = group_for(order["linguaskill_type"])
    skills_code = order["skills_code"]
    if not skills_code:
        raise ValueError(f"order {order.get('order_number')} has no skills_code")

    page.goto(SESSIONS_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="Add Session").click()
    _settle(page)

    # Group/Venue are native <select> elements behind a bootstrap-select
    # overlay; select_option() drives the real <select> directly instead of
    # fighting with the fake dropdown UI. Ids confirmed live and stable.
    page.locator("#ctl00_ContentPlaceHolder_createSession1_ddlSessionGroup").select_option(
        label=group
    )
    _settle(page)

    # "Who is it for?" is not always pre-selected depending on the Group.
    # The native radio input itself renders off-screen (a styled label is
    # shown instead), so Playwright can never click the input directly —
    # click its visible label text instead.
    my_institution = page.get_by_role("radio", name="My Institution")
    if not my_institution.is_checked():
        page.locator(f"label[for='{my_institution.get_attribute('id')}']").click()
        _settle(page)

    page.locator("#ctl00_ContentPlaceHolder_createSession1_ddlVenue").select_option(
        label=VENUE
    )
    _settle(page)

    unlimited = page.get_by_role("radio", name="Unlimited capacity")
    if not unlimited.is_checked():
        page.locator(f"label[for='{unlimited.get_attribute('id')}']").click()
        _settle(page)

    # Telerik RadDateInput/RadTimePicker widgets: the visible text input is
    # the "_dateInput" child of the "_dpkDate"/"_dpkTime" picker (confirmed
    # live). A Tab after filling is required to commit the value into the
    # widget's internal client state, matching the legacy UiPath workflow's
    # own use of Tab here.
    base = "#ctl00_ContentPlaceHolder_createSession1_dtStartDateTime_"
    date_input = page.locator(base + "dpkDate_dateInput")
    time_input = page.locator(base + "dpkTime_dateInput")
    if is_est:
        start = datetime.now(PARIS) + timedelta(hours=1)
        start_date, start_time = start.strftime("%d/%m/%Y"), start.strftime("%H:%M")
    else:
        start_date, start_time = order["exam_date"], normalize_exam_hour(order["exam_hour"])
    date_input.fill(start_date)
    date_input.press("Tab")
    _settle(page)
    time_input.fill(start_time)
    time_input.press("Tab")
    _settle(page)
    if is_est:
        # The EST form derives its end date (start + ~90 days) from the
        # start — confirmed live. Never create an EST session without one.
        end_input = page.locator("#ctl00_ContentPlaceHolder_createSession1_dtEndDateTime_dpkDate_dateInput")
        end_date = end_input.input_value().strip()
        if not end_date:
            raise RuntimeError("EST session form has no end date after setting the start date")
        validity = (date_input.input_value().strip(), end_date)
    else:
        validity = None

    page.get_by_role("link", name="Add Test Component").click()
    _settle(page)
    # "Add Test Component" always adds all four rows at once, in this fixed
    # order: Listening, Reading, Speaking, Writing (confirmed live for both
    # the General and Business groups). Each row has its own "Remove -" link.
    # Remove from the last row backwards so earlier indices stay valid as
    # rows disappear; each removal is its own postback, so settle between.
    default_order = ["L", "R", "S", "W"]
    for idx in reversed(range(len(default_order))):
        if default_order[idx] not in skills_code:
            page.get_by_role("link", name="Remove -").nth(idx).click()
            _settle(page)

    page.get_by_label("Session Name").fill(order["session_name"])
    page.get_by_role("button", name="Create Session").click()
    _settle(page)

    # Creation redirects to the unfiltered Session List, where the new
    # session isn't necessarily visible without paging/sorting — search
    # for it properly rather than scanning the current page's text. Seen
    # live: the new session can briefly not show up in search right after
    # creation (server-side list indexing lag), so retry a few times
    # before concluding creation actually failed.
    for attempt in range(3):
        if find_session(page, order["session_name"]) is not None:
            return validity
        page.wait_for_timeout(1500)
    raise RuntimeError(
        f"Session creation for {order['session_name']!r} could not be confirmed"
    )


def _parse_ddmmyyyy(value):
    match = re.match(r"\s*(\d{2}/\d{2}/\d{4})", str(value or ""))
    return datetime.strptime(match.group(1), "%d/%m/%Y").date() if match else None


def find_existing_est_session(page, order: dict):
    """Return the name of an EST session already created for this order on
    an earlier run, or None.

    EST session names are dated with the day the order is processed, so a
    retry on a later day (e.g. Cambridge succeeded but the X-Net status
    update didn't) would otherwise compute a new name and register the
    candidate twice. Any same-code session for this email dated on/after
    the order's creation date can only belong to this order. More than one
    is ambiguous and must not be guessed.
    """
    date_part, code, email = order["session_name"].split(" ", 2)
    created = _parse_ddmmyyyy(order.get("dt_creation"))
    if created is None:
        return None

    page.goto(SESSIONS_URL, wait_until="domcontentloaded")
    _open_search_panel(page)
    page.get_by_label("Session Name").fill(f"{code} {email}")
    page.locator("#ctl00_ContentPlaceHolder_btnSearch").click()
    _settle(page)

    pattern = re.compile(rf"(\d{{2}}/\d{{2}}/\d{{4}}) {re.escape(code)} {re.escape(email)}", re.I)
    names = set()
    for text in page.get_by_role("link").all_inner_texts():
        match = pattern.fullmatch((text.strip().splitlines() or [''])[0].strip())
        if match and _parse_ddmmyyyy(match.group(1)) >= created:
            names.add(match.group(0))
    if len(names) > 1:
        raise RuntimeError(f"ambiguous_existing_est_sessions: {sorted(names)}")
    return names.pop() if names else None


# Cambridge sets an EST session's end date 90 days after its start
# (confirmed live: start 22/09/2026 -> end 21/12/2026).
EST_VALIDITY_DAYS = 90


def est_validity_from_name(session_name: str):
    """(start_date, end_date) of an EST session we didn't create in this
    run, derived from the date its name starts with."""
    start = _parse_ddmmyyyy(session_name)
    if start is None:
        return None
    end = start + timedelta(days=EST_VALIDITY_DAYS)
    return start.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")


def ensure_session_exists(page, order: dict):
    """Find the order's session, creating it if missing. Idempotent.

    Returns (session_name, validity): the session name actually used — for
    EST this can be an earlier run's session rather than
    order["session_name"] — and, for EST only, its (start_date, end_date).
    """
    is_est = product_of(order["linguaskill_type"]) == EST
    session_name = order["session_name"]
    if find_session(page, session_name) is not None:
        return session_name, est_validity_from_name(session_name) if is_est else None
    if is_est:
        existing = find_existing_est_session(page, order)
        if existing is not None:
            return existing, est_validity_from_name(existing)
    validity = create_session(page, order)
    return session_name, validity
