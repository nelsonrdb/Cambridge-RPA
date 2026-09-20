import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USERNAME)
MAIL_TO = [addr.strip() for addr in os.getenv("MAIL_TO", "").split(",") if addr.strip()]


def _build_summary_body(rows: list[dict], timestamp: str) -> str:
    ok_count = sum(1 for r in rows if r["success"])
    lines = [
        f"Cambridge registration run — {timestamp}",
        f"{ok_count}/{len(rows)} orders registered successfully.",
        "",
    ]
    for r in rows:
        confirmation = r.get("confirmation") or ""
        if not r["success"]:
            status = "MANUAL REVIEW"
        elif "skipped duplicate registration" in confirmation:
            status = "SUCCESS (deja inscrit, pas reinscrit)"
        else:
            status = "SUCCESS"
        lines.append(f"- {r['order_number']} ({r['email']}) — {status}")
        if not r["success"]:
            lines.append(f"    Reason: {r['manual_review_reason']}")
    return "\n".join(lines)


def send_run_summary_email(rows: list[dict], timestamp: str):
    """Email a plain-text summary of a registration run.

    No-ops silently if SMTP isn't configured (SMTP_HOST/USERNAME/PASSWORD
    or MAIL_TO missing) — email is a convenience notification, not a
    required part of the pipeline, and local/dev runs shouldn't need it
    set up to work.
    """
    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and MAIL_TO):
        return

    if not rows:
        return

    ok_count = sum(1 for r in rows if r["success"])
    msg = EmailMessage()
    msg["Subject"] = f"Cambridge registration run: {ok_count}/{len(rows)} succeeded"
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(MAIL_TO)
    msg.set_content(_build_summary_body(rows, timestamp))

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
