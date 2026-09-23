import unittest

from update_status import manual_review_comment, success_comment
from cambridge.sessions import est_validity_from_name


class TestManualReviewComment(unittest.TestCase):
    def test_known_reasons_are_explained(self):
        self.assertIn("Entry code", manual_review_comment("entry_code_candidate"))
        self.assertIn("crédits", manual_review_comment("no_test_credits_remaining"))
        self.assertIn("France", manual_review_comment("non_france_nationality_or_residence"))
        self.assertIn("sessions EST", manual_review_comment("ambiguous_existing_est_sessions: ['a', 'b']"))
        self.assertIn("connexion", manual_review_comment("Cambridge login failed. Still on login page: True."))

    def test_technical_error_keeps_first_line_only(self):
        comment = manual_review_comment("Locator.click: Timeout 30000ms exceeded.\nCall log:\n  - waiting for x")
        self.assertIn("erreur technique", comment)
        self.assertIn("Timeout 30000ms", comment)
        self.assertNotIn("Call log", comment)

    def test_missing_reason(self):
        self.assertIn("raison inconnue", manual_review_comment(None))


class TestSuccessComment(unittest.TestCase):
    BASE = {"email": "candidate@example.com", "password": "Abcd1234", "session_name": "x"}

    def test_linguaskill(self):
        info = dict(self.BASE, exam_date="28/09/2026", exam_hour="17h")
        self.assertEqual(
            success_comment(info),
            "Date / Heure d'Examen - Le 28/09/2026 à 17h\n"
            "Username : candidate@example.com\n"
            "Password : Abcd1234\n"
            "Institution : FR731",
        )

    def test_est_validity_window(self):
        info = dict(self.BASE, est_valid_from="23/09/2026", est_valid_until="22/12/2026")
        self.assertEqual(
            success_comment(info).splitlines()[0],
            "Test à passer entre le 23/09/2026 et le 22/12/2026",
        )

    def test_no_session_name_and_no_date_line_when_missing(self):
        comment = success_comment(dict(self.BASE, exam_date=float("nan"), exam_hour=None))
        self.assertNotIn("Session", comment)
        self.assertTrue(comment.startswith("Username : "))


class TestESTValidityFromName(unittest.TestCase):
    def test_ninety_days(self):
        self.assertEqual(
            est_validity_from_name("22/09/2026 ESTG2S candidate@example.com"),
            ("22/09/2026", "21/12/2026"),
        )


if __name__ == "__main__":
    unittest.main()
