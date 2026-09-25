import pandas as pd
from playwright.sync_api import sync_playwright

from cambridge.auth import ensure_logged_in
from cambridge.sessions import ensure_session_exists, open_session, product_of
from cambridge.candidates import (
    find_existing_candidate,
    save_existing_candidate,
    fill_single_candidate_entry,
)


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


def _is_france_only(order: dict) -> bool:
    """Only nationality == France AND country of residence == France are
    handled automatically — everything else goes to manual review without
    ever touching Cambridge (per explicit business rule)."""
    nationality = str(order.get("nationality") or "").strip().lower()
    residence = str(order.get("country_of_residence") or "").strip().lower()
    return nationality == "france" and residence == "france"


def _exam_info(order: dict, est_validity) -> dict:
    """What update_status.py writes about the exam in the X-Net comment:
    the exam date/hour for Linguaskill, the validity window for EST."""
    if est_validity:
        return {"est_valid_from": est_validity[0], "est_valid_until": est_validity[1]}
    return {"exam_date": order.get("exam_date"), "exam_hour": order.get("exam_hour")}


def _memory_usage() -> str:
    """Container memory in use (Linux cgroup; empty elsewhere), logged per
    order so a creeping OOM is visible in Render's logs before it hits."""
    for path in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        try:
            with open(path) as f:
                return f" (mem {int(f.read()) // (1024 * 1024)} MB)"
        except (OSError, ValueError):
            continue
    return ""


def _log(order_number, message):
    print(f"[CAMBRIDGE] {order_number}: {message}", flush=True)


def _register(page, order: dict) -> dict:
    order_number = order.get("order_number")
    email = order.get("email")
    password = order.get("password")

    _log(order_number, f"starting ({email})")

    if order.get("is_entry_code"):
        _log(order_number, "skipped — entry-code candidate (manual review)")
        return {
            "success": False,
            "order_number": order_number,
            "email": email,
            "password": password,
            "manual_review_reason": "entry_code_candidate",
        }

    if not _is_france_only(order):
        _log(order_number, "skipped — nationality/residence is not France (manual review)")
        return {
            "success": False,
            "order_number": order_number,
            "email": email,
            "password": password,
            "manual_review_reason": "non_france_nationality_or_residence",
        }

    # A missing session_name/skills_code means X-Net's exam_type or
    # product label wasn't recognised by session_name.py — never guess.
    session_name = order.get("session_name")
    skills_code = order.get("skills_code")
    if not isinstance(session_name, str) or not isinstance(skills_code, str):
        _log(order_number, "skipped — unrecognised exam type/product (manual review)")
        return {
            "success": False,
            "order_number": order_number,
            "email": email,
            "password": password,
            "manual_review_reason": "unrecognised_exam_type_or_product",
        }
    product_of(order.get("linguaskill_type"))  # raises -> manual review

    _log(order_number, f"ensuring session exists: {session_name!r}")
    session_name, est_validity = ensure_session_exists(page, order)
    if session_name != order["session_name"]:
        _log(order_number, f"reusing EST session from an earlier run: {session_name!r}")
    _log(order_number, "opening session")
    open_session(page, session_name)

    if _already_registered(page, email):
        _log(order_number, "already registered in this session — skipping duplicate")
        return {
            "success": True,
            "order_number": order_number,
            "email": email,
            "password": password,
            "session_name": session_name,
            "confirmation": "already registered in this session — skipped duplicate registration",
            **_exam_info(order, est_validity),
        }

    _log(order_number, "clicking Add Entries")
    page.get_by_role("button", name="Add Entries").click()
    page.wait_for_load_state("networkidle")

    # Seen live: clicking "Add Entries" can itself be refused up front with
    # "This action cannot be performed as one or many test components has
    # no test credits left." — before any candidate tab is even reachable.
    if page.get_by_text("test credits left", exact=False).count() > 0:
        _log(order_number, "no test credits remaining for this component")
        raise RuntimeError("no_test_credits_remaining")

    # Always check Cambridge itself first — X-Net's password_cms is not
    # trusted alone (its history can be incomplete/stale). Decision matrix:
    #   found on Cambridge + password known on X-Net  -> reuse (normal case)
    #   found on Cambridge + NO password on X-Net     -> can't safely act:
    #     an account exists but we don't know its password to give back to
    #     the candidate/X-Net — manual review, never guess or reset it.
    #   not found on Cambridge + password on X-Net    -> X-Net's record is
    #     stale/wrong; create fresh, using that X-Net password (order
    #     already carries it as order["password"]).
    #   not found on Cambridge + no password on X-Net -> normal new
    #     candidate, using the freshly generated password.
    _log(order_number, "checking Search Existing on Cambridge")
    existing_checkbox = find_existing_candidate(page, email)
    if existing_checkbox is not None and not _has_password_on_file(order):
        _log(order_number, "found existing Cambridge account but no password on file (manual review)")
        raise RuntimeError(
            "existing_cambridge_candidate_found_but_no_password_on_file"
        )
    if existing_checkbox is not None:
        _log(order_number, "reusing existing Cambridge candidate")
        save_existing_candidate(page, existing_checkbox)
    else:
        _log(order_number, "creating new candidate entry")
        fill_single_candidate_entry(page, order)

    if page.get_by_text("test credits left", exact=False).count() > 0:
        _log(order_number, "no test credits remaining for this component")
        raise RuntimeError("no_test_credits_remaining")

    _log(order_number, "verifying registration")
    verify_registration(page, email)
    _log(order_number, "success")

    return {
        "success": True,
        "order_number": order_number,
        "email": email,
        "password": password,
        "session_name": session_name,
        "confirmation": "candidate present in session entries",
        **_exam_info(order, est_validity),
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
        print("[CAMBRIDGE] logging in...", flush=True)
        try:
            browser, context, page = ensure_logged_in(p, headless=headless)
        except Exception as exc:
            print(f"[CAMBRIDGE] login failed: {exc}", flush=True)
            return _failure_result(order, exc)
        print("[CAMBRIDGE] logged in", flush=True)
        try:
            result = _register(page, order)
        except Exception as exc:
            order_number = order.get("order_number")
            _log(order_number, f"failed — {exc}")
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
    total = len(orders)
    print(f"[CAMBRIDGE] logging in... ({total} order(s) to process)", flush=True)
    with sync_playwright() as p:
        try:
            browser, context, page = ensure_logged_in(p, headless=headless)
        except Exception as exc:
            print(f"[CAMBRIDGE] login failed: {exc}", flush=True)
            for order in orders:
                results[order.get("order_number")] = _failure_result(order, exc)
            return results
        print("[CAMBRIDGE] logged in", flush=True)

        try:
            for i, order in enumerate(orders, start=1):
                order_number = order.get("order_number")
                print(f"[CAMBRIDGE] --- order {i}/{total}: {order_number} ---{_memory_usage()}", flush=True)
                # A fresh tab per order: one long-lived tab across a whole
                # batch kept growing (heavy ASP.NET pages/postbacks) until
                # Render OOM-killed the container. The context — and so the
                # login cookies — is kept, so no re-login is needed. Safe
                # because every order starts with its own page.goto().
                if i > 1:
                    page.close()
                    page = context.new_page()
                try:
                    results[order_number] = _register(page, order)
                except Exception as exc:
                    _log(order_number, f"failed — {exc}")
                    results[order_number] = _failure_result(order, exc)
        finally:
            browser.close()
    return results
