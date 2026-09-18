# Cambridge Registration Automation

## Project Overview

This project automates candidate registration for Cambridge Linguaskill exams.

The X-Net/Victoria side is already largely implemented in Python. It retrieves
pending orders, extracts candidate and exam data, generates or recovers
passwords, builds session names, and updates the Victoria workflow status.

The main remaining task is to rebuild the Cambridge/Metrica part in Python with
Playwright.

The intended production flow is:

```text
Victoria/X-Net Python code
    -> normalized order data
    -> Cambridge Python + Playwright automation
    -> verified registration result
    -> Victoria status update
```

The final production workflow must be deterministic. It must not depend on
Claude, another AI agent, or UiPath at runtime.

## Existing Repository

Before changing code, inspect the existing Python files, especially:

- `runner.py`: current order retrieval pipeline
- `auth.py`: Victoria authentication and browser state
- `orders.py` and `get_data.py`: Victoria order extraction
- `get_passwords.py`: existing-candidate/password lookup
- `export_csv.py` and `session_name.py`: normalization and session metadata
- `update_status.py`: writing success or manual-review status back to Victoria
- `app.py`: current FastAPI entry points

Preserve working Victoria behavior. Do not rewrite or reorganize that part
unless a change is necessary for the Cambridge integration or explicitly
requested.

If you identify a significant flaw, security issue, reliability risk, or clear
architectural improvement in the existing Python code, explain it and propose
a concrete change. The same applies when the legacy UiPath workflow appears
incorrect, unsafe, unnecessarily fragile, or inconsistent with the intended
business process. Do not silently reproduce a known weakness simply because it
already exists.

Use judgment: mention improvements that would materially affect correctness,
security, maintainability, or operational reliability. Avoid distracting from
the Cambridge implementation with cosmetic refactors or speculative
over-engineering. Unless the improvement is necessary to complete the current
task safely, propose it first and wait for approval before making a broad or
unrelated change.

The current dataframe is expected to contain fields such as:

```text
order_number, surname, name, date_of_birth, gender, nationality,
id_number, email, exam_type, linguaskill_type, exam_date, exam_hour,
password, password_cms, password_generated, is_entry_code,
session_name, skills_code
```

Verify actual columns in the current code instead of relying only on this list.

## Legacy UiPath Reference

The old UiPath implementation is under:

`Solution/RPA Workflow/Main.xaml`

Its screenshots are under:

`Solution/RPA Workflow/.screenshots/`

The legacy project is read-only reference material. Do not repair, extend, run,
or make the Python application depend on UiPath.

Use `Main.xaml` and its screenshots to understand the intended business flow,
field mappings, branches, and historical interface. Do not mechanically copy
its selectors, coordinates, delays, credentials, or assumptions.

The legacy workflow indicates approximately this Cambridge process:

1. Log in to Cambridge/Metrica for institution `FR731`.
2. Open the Sessions area.
3. Search for the session using `session_name`.
4. If it does not exist, create it:
   - select Linguaskill General or Business;
   - select Remote delivery;
   - set the exam date and time;
   - keep only the components present in `skills_code` (`R`, `L`, `S`, `W`);
   - assign `session_name` and create the session.
5. Open the relevant session and select Add Entries.
6. If an existing Cambridge candidate should be reused, search by email and
   add that candidate to the session.
7. Otherwise use Single Candidate Entry and populate the candidate fields,
   including username/email, password, first name, last name, email, date of
   birth, gender, nationality, and identification document number.
8. Save the entry and verify that the candidate was actually added.
9. Return a structured success or failure result for `update_status.py`.

Treat this as a guide, not as guaranteed current behavior. Inspect the full
XAML for details and verify every important step on the current website.

Pay particular attention to:

- General versus Business product selection;
- session naming and session reuse;
- component selection/removal;
- the meaning of `password_cms`, `password_generated`, and `is_entry_code`;
- reuse of existing candidates versus creation of new candidates;
- date, gender, nationality, and identification mappings;
- the observable confirmation that proves registration succeeded.

If legacy behavior conflicts with the current website, use the current website
for technical behavior and selectors. Preserve the intended business outcome.
Document any ambiguity that requires a business decision instead of guessing.

## Cambridge Python Implementation

Implement the Cambridge/Metrica workflow in Python using Playwright. Keep it
separate from the Victoria scraping code.

A small module structure is sufficient, for example:

```text
cambridge/
    auth.py
    sessions.py
    candidates.py
    registration.py
```

Do not create unnecessary abstractions. Functions may include:

```python
ensure_logged_in(...)
find_session(...)
ensure_session_exists(...)
find_existing_candidate(...)
register_candidate(...)
verify_registration(...)
```

Use browser access during development to inspect the live Cambridge site and
discover the real page sequence and selectors. Implement one verified step at
a time, then test the resulting Python code through the same browser flow.

Prefer selectors in this order:

1. `get_by_role()`
2. `get_by_label()`
3. `get_by_placeholder()`
4. stable data attributes
5. stable CSS selectors
6. XPath only when no robust alternative exists

Avoid screen coordinates, absolute DOM paths, generated IDs, fragile class
chains, and arbitrary `sleep()` calls. Wait for observable states such as a
visible field, enabled button, expected URL, success message, or result row.

Do not consider an action successful merely because a button was clicked.
Confirm the resulting page state and return useful structured information, for
example:

```python
{
    "success": True,
    "order_number": "...",
    "email": "...",
    "session_name": "...",
    "confirmation": "...",
}
```

Unexpected pages, missing fields, unavailable sessions, duplicate ambiguity,
or Cambridge validation errors must fail safely and be sent for manual review.

## Safety

- Never submit a real registration during exploration without explicit human
  approval. Stop immediately before the final irreversible action.
- Prefer a sandbox or explicitly authorized test candidate when available.
- Never delete, cancel, or modify an existing registration unless explicitly
  requested.
- Do not guess when candidate identity, session, product, or components are
  ambiguous.
- Do not log unnecessary candidate personal data.
- Do not save candidate data in screenshots unless required for debugging;
  treat such screenshots as sensitive.
- Never hard-code or commit usernames, passwords, cookies, access tokens, or
  Playwright storage state. Use environment variables and ignored local files.
- Existing hard-coded credentials or committed session-state files are legacy
  security issues, not patterns to follow. Remove them from active code when
  working in the relevant area and report that their rotation may be needed.

## Testing and Completion

Use synthetic data for unit tests. Test mappings and validation without opening
a browser where possible.

Test the Cambridge browser workflow progressively:

1. authentication;
2. session search;
3. session creation up to the final confirmation;
4. existing-candidate lookup;
5. candidate form filling;
6. registration confirmation detection;
7. failure and manual-review behavior;
8. integration with the existing Victoria result update.

Retries must not create duplicate sessions or registrations. Before retrying a
submission, check whether Cambridge already completed the operation.

The work is complete when the Cambridge workflow is implemented in Python,
verified against the current website with authorized test data, safely handles
common failures and duplicate risk, and integrates with the existing Python
pipeline without requiring UiPath or an AI agent in production.

## Development Workflow

For this task:

1. Read the existing Python code and this file.
2. Inspect `Main.xaml` and relevant screenshots.
3. Summarize the inferred Cambridge workflow and unresolved questions.
4. Explore the current Cambridge site using browser tooling.
5. Implement the Cambridge flow incrementally in Python/Playwright.
6. Test each step and compare it with the intended legacy behavior.
7. Stop before irreversible real submissions unless approval is explicit.
8. Integrate the verified result with the existing pipeline.
9. Run relevant tests and report remaining assumptions or manual steps.

Do not spend time building agents, skills, hooks, or self-healing production
automation unless explicitly requested. The goal is reliable Python code.
