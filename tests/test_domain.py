import unittest
from datetime import date

from wise_library.app.domain import PortalError, parse_loans, summarize, validate_session


class DomainTests(unittest.TestCase):
    def test_dutch_loan_dates_are_not_renewal_offer_dates(self):
        rows = [
            {
                "title": "A library book",
                "text": "Writer Name\nA library book\nGeleend op: 12-10-2026 | Inleverdatum: 05-12-2026 | Van vestiging: Bibliotheek Stadspolders | Exemplaar: 12345 Verlengen tot en met 24-12-2026 9 dagen",
            }
        ]
        result = parse_loans(rows, "Totaal geleend: 1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["due_date"], "2026-12-05")
        self.assertEqual(result[0]["branch"], "Bibliotheek Stadspolders")

    def test_missing_cards_is_not_an_empty_account(self):
        with self.assertRaises(PortalError):
            parse_loans([], "Totaal geleend: 4")

    def test_login_page_is_not_an_empty_account(self):
        with self.assertRaises(PortalError):
            parse_loans([], "Log in Gebruikersnaam Wachtwoord")

    def test_explicit_empty_account(self):
        self.assertEqual(parse_loans([], "Totaal geleend: 0"), [])

    def test_summary_due_today_and_overdue(self):
        result = summarize(
            [{"due_date": "2026-11-25"}, {"due_date": "2026-11-26"}, {"due_date": "2026-11-29"}], date(2026, 11, 26)
        )
        self.assertEqual(
            result, {"loan_count": 3, "overdue_count": 1, "due_soon_count": 2, "next_due_date": "2026-11-25"}
        )

    def test_session_rejects_unrelated_account_cookies(self):
        with self.assertRaises(ValueError):
            validate_session({"cookies": [{"domain": ".google.com", "name": "secret", "value": "x"}], "origins": []})

    def test_session_accepts_only_the_library_hosts(self):
        state = {"cookies": [{"domain": "bibliotheek.wise.oclc.org", "name": "session", "value": "x"}], "origins": []}
        self.assertEqual(validate_session(state), state)

    def test_session_storage_must_contain_only_strings(self):
        with self.assertRaises(ValueError):
            validate_session(
                {
                    "cookies": [],
                    "origins": [{"origin": "https://bibliotheek.wise.oclc.org", "localStorage": []}],
                    "sessionStorage": {"token": {"nested": "invalid"}},
                }
            )


if __name__ == "__main__":
    unittest.main()
