import re
from datetime import date
from urllib.parse import urlsplit

PORTAL_HOST = "bibliotheek.wise.oclc.org"
ALLOWED_HOSTS = {
    PORTAL_HOST,
    "wise.oclc.org",
    "iam-emea.wise.oclc.org",
    "emea-iam.wise.oclc.org",
    "login.bibliotheek.nl",
    "inloggen.kb.nl",
}


class PortalError(Exception):
    pass


class AuthenticationError(PortalError):
    """Stop automatic retries until the user changes settings or requests a retry."""


ISBN = re.compile(r"isbn=([0-9]{13}|[0-9]{9}[0-9Xx])(?![0-9])")
RENEWAL = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
COPY = re.compile(r"Exemplaar:\s*(\d+)")


def isbn_of(cover_url):
    found = ISBN.search(cover_url or "")
    return found[1].upper() if found else ""


def with_ids(items, parts, prefix=""):
    """The portal gives reservations no identifier, so identical entries are told apart by position."""
    seen = {}
    result = []
    for item in items:
        base = "|".join(str(item.get(part) or "") for part in parts)
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append({**item, "id": f"{prefix}{base}|{count}"})
    return result


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
        offer = RENEWAL.search(row.get("renewUntil") or "")
        renew_until = date(int(offer[3]), int(offer[2]), int(offer[1])).isoformat() if offer else None
        copy = COPY.search(row["text"])
        result.append(
            {
                "id": copy[1] if copy else "",
                "renew_id": row.get("id") or None,
                "title": row["title"],
                "author": row.get("author") or "",
                "isbn": isbn_of(row.get("cover")),
                "due_date": due_date,
                "branch": branch[1].strip() if branch else "",
                "renew_until": renew_until,
            }
        )
    return [loan if loan["id"] else {**loan, "id": f"unknown|{n}"} for n, loan in enumerate(result)]


def summarize(loans, today):
    dates = [date.fromisoformat(item["due_date"]) for item in loans]
    return {
        "loan_count": len(loans),
        "overdue_count": sum(d < today for d in dates),
        "due_soon_count": sum(0 <= (d - today).days <= 3 for d in dates),
        "next_due_date": min(dates).isoformat() if dates else None,
    }


def library_only(state):
    return {
        **state,
        "cookies": [c for c in state["cookies"] if c.get("domain", "").lstrip(".") in ALLOWED_HOSTS],
        "origins": [o for o in state["origins"] if urlsplit(o.get("origin", "")).hostname in ALLOWED_HOSTS],
    }


def validate_session(state):
    if (
        not isinstance(state, dict)
        or not isinstance(state.get("cookies"), list)
        or not isinstance(state.get("origins"), list)
    ):
        raise ValueError("Expected a Playwright storage-state file.")  # noqa: TRY004 -- callers catch ValueError
    if not state["cookies"] and not state["origins"]:
        raise ValueError("The session file is empty.")
    storage = state.get("sessionStorage", {})
    if not isinstance(storage, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in storage.items()):
        raise ValueError("Invalid session storage.")
    for cookie in state["cookies"]:
        if not isinstance(cookie, dict) or cookie.get("domain", "").lstrip(".") not in ALLOWED_HOSTS:
            raise ValueError("Session contains cookies outside the supported library hosts.")
    for origin in state["origins"]:
        parsed = urlsplit(origin.get("origin", ""))
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Session contains storage outside the supported library hosts.")
    return state
