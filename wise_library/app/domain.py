import re
from datetime import date
from urllib.parse import urlsplit

PORTAL_HOST = "bibliotheek.wise.oclc.org"
ALLOWED_HOSTS = {PORTAL_HOST, "iam-emea.wise.oclc.org", "emea-iam.wise.oclc.org", "login.bibliotheek.nl"}

class PortalError(Exception):
    pass

def parse_loans(rows, text):
    total = re.search(r"Totaal geleend:\s*(\d+)", text)
    if not total or int(total[1]) != len(rows):
        raise PortalError("Loan page could not be verified. Reconnect or check for a changed portal layout.")
    result = []
    for row in rows:
        due = re.search(r"Inleverdatum:\s*(\d{2})-(\d{2})-(\d{4})", row["text"])
        branch = re.search(r"Van vestiging:\s*([^|]+)", row["text"])
        if not due or not row.get("title"):
            raise PortalError("A loan is missing its title or return date.")
        try:
            due_date = date(int(due[3]), int(due[2]), int(due[1])).isoformat()
        except ValueError:
            raise PortalError("A loan has an invalid return date.") from None
        result.append({"title": row["title"], "due_date": due_date,
                       "branch": branch[1].strip() if branch else ""})
    return result

def summarize(loans, today):
    dates = [date.fromisoformat(item["due_date"]) for item in loans]
    return {"loan_count": len(loans), "overdue_count": sum(d < today for d in dates),
            "due_soon_count": sum(0 <= (d - today).days <= 3 for d in dates),
            "next_due_date": min(dates).isoformat() if dates else None}

def validate_session(state):
    if not isinstance(state, dict) or not isinstance(state.get("cookies"), list) or not isinstance(state.get("origins"), list):
        raise ValueError("Expected a Playwright storage-state file.")
    if not state["cookies"] and not state["origins"]:
        raise ValueError("The session file is empty.")
    storage = state.get('sessionStorage', {})
    if not isinstance(storage, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in storage.items()):
        raise ValueError('Invalid session storage.')
    for cookie in state["cookies"]:
        if not isinstance(cookie, dict) or cookie.get("domain", "").lstrip(".") not in ALLOWED_HOSTS:
            raise ValueError("Session contains cookies outside the supported library hosts.")
    for origin in state["origins"]:
        parsed = urlsplit(origin.get("origin", ""))
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Session contains storage outside the supported library hosts.")
    return state
