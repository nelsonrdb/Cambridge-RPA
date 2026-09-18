import pandas as pd
from playwright.sync_api import sync_playwright

from cambridge.auth import ensure_logged_in
from cambridge.sessions import ensure_session_exists, open_session
from cambridge.candidates import add_existing_candidate, fill_single_candidate_entry


def _has_password_on_file(order: dict) -> bool:
    # get_passwords.py stores a missing password_cms as pd.NA (not the
    # string "NA") — bool(pd.NA) raises, so isna() must run first.
    value = order.get("password_cms")
    if value is None or pd.isna(value):
        return False
    return str(value).strip().upper() not in ("", "NA")


def verify_registration(page, email: str):
    """Confirm the candidate now appears in the session's entry list."""
    row = page.get_by_role("link", name=email, exact=True)
    if row.count() == 0:
        raise RuntimeError(f"{email!r} not found in session entries after save")


def _already_registered(page, email: str) -> bool:
    """True if `email` already has a non-withdrawn entry in the currently
    open session. A session sharing a name with no candidates in it is
    fine (that's just session reuse) — this only guards against
    registering the *same person* into it a second time, e.g. on a retry.
    A withdrawn entry doesn't count: it's no longer an active registration.
    """
    link = page.get_by_role("link", name=email, exact=True)
    if link.count() == 0:
        return False
    row_text = link.first.locator("xpath=ancestor::tr[1]").inner_text().lower()
    return "withdrawn" not in row_text


def _register(page, order: dict) -> dict:
    order_number = order.get("order_number")
    email = order.get("email")
    password = order.get("password")

    if order.get("is_entry_code"):
        return {
            "success": False,
            "order_number": order_number,
            "email": email,
            "password": password,
            "manual_review_reason": "entry_code_candidate",
        }

    session_name = order["session_name"]
    ensure_session_exists(page, order)
    open_session(page, session_name)

    if _already_registered(page, email):
        return {
            "success": True,
            "order_number": order_number,
            "email": email,
            "password": password,
            "session_name": session_name,
            "confirmation": "already registered in this session — skipped duplicate registration",
        }

    page.get_by_role("button", name="Add Entries").click()
    page.wait_for_load_state("networkidle")

    # Seen live: clicking "Add Entries" can itself be refused up front with
    # "This action cannot be performed as one or many test components has
    # no test credits left." — before any candidate tab is even reachable.
    if page.get_by_text("test credits left", exact=False).count() > 0:
        raise RuntimeError("no_test_credits_remaining")

    if _has_password_on_file(order):
        add_existing_candidate(page, email)
    else:
        fill_single_candidate_entry(page, order)

    if page.get_by_text("test credits left", exact=False).count() > 0:
        raise RuntimeError("no_test_credits_remaining")

    verify_registration(page, email)

    return {
        "success": True,
        "order_number": order_number,
        "email": email,
        "password": password,
        "session_name": session_name,
        "confirmation": "candidate present in session entries",
    }


def _failure_result(order: dict, exc: Exception) -> dict:
    return {
        "success": False,
        "order_number": order.get("order_number"),
        "email": order.get("email"),
        "password": order.get("password"),
        "manual_review_reason": str(exc),
    }


def register_candidate(order: dict, headless: bool = True) -> dict:
    """Run the full Cambridge/Metrica registration flow for one order,
    opening and logging into its own dedicated browser session.

    Returns a structured result compatible with update_status.py's
    expected {order_number: {"email", "password", "success"}} contract
    (plus an optional "manual_review_reason" / "confirmation" for
    diagnostics). Never raises: any failure — including a login failure —
    is reported as success=False with a reason.

    For registering many orders in one run, prefer register_orders() below:
    it logs in once and reuses that session, which is both faster and
    avoids repeatedly cycling the Cambridge/Metrica login (this site
    appears to allow only one active session per account).
    """
    with sync_playwright() as p:
        try:
            browser, context, page = ensure_logged_in(p, headless=headless)
        except Exception as exc:
            return _failure_result(order, exc)
        try:
            result = _register(page, order)
        except Exception as exc:
            result = _failure_result(order, exc)
        finally:
            browser.close()
    return result


def register_orders(orders: list[dict], headless: bool = True) -> dict:
    """Register many orders in a single login session.

    Logs in once, then registers each order in turn. A failure on any one
    order (login problem excepted — see below) is recorded and the loop
    moves on to the next order; it never aborts the whole batch. Returns
    {order_number: {...}} for every order, in the same shape as
    register_candidate()'s result.

    If the initial login itself fails, every order is reported as a
    failure with that same reason (there is nothing else to try without a
    session).
    """
    results = {}
    with sync_playwright() as p:
        try:
            browser, context, page = ensure_logged_in(p, headless=headless)
        except Exception as exc:
            for order in orders:
                results[order.get("order_number")] = _failure_result(order, exc)
            return results

        try:
            for order in orders:
                order_number = order.get("order_number")
                try:
                    results[order_number] = _register(page, order)
                except Exception as exc:
                    results[order_number] = _failure_result(order, exc)
        finally:
            browser.close()
    return results
