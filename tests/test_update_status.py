import unittest

from update_status import manual_review_comment


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


if __name__ == "__main__":
    unittest.main()
