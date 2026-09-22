import unittest

import pandas as pd

from cambridge.sessions import (
    linguaskill_kind, GROUP_BY_KIND, normalize_exam_hour, product_of, group_for,
    EST, LINGUASKILL, _parse_ddmmyyyy,
)
from cambridge.candidates import map_gender
from cambridge.registration import _has_password_on_file, _is_france_only


class TestNormalizeExamHour(unittest.TestCase):
    def test_french_shorthand(self):
        self.assertEqual(normalize_exam_hour("10h"), "10:00")
        self.assertEqual(normalize_exam_hour("9h"), "09:00")
        self.assertEqual(normalize_exam_hour(" 9h"), "09:00")

    def test_already_hh_mm_passthrough(self):
        self.assertEqual(normalize_exam_hour("10:00"), "10:00")
        self.assertEqual(normalize_exam_hour("09:30"), "09:30")


class TestLinguaskillKind(unittest.TestCase):
    def test_general(self):
        self.assertEqual(linguaskill_kind("LINGUASKILL General"), "General")
        self.assertEqual(GROUP_BY_KIND["General"], "New Linguaskill General Remote")

    def test_business(self):
        self.assertEqual(linguaskill_kind("LINGUASKILL Business"), "Business")
        self.assertEqual(GROUP_BY_KIND["Business"], "New Linguaskill Business Remote")

    def test_unrecognised(self):
        with self.assertRaises(ValueError):
            linguaskill_kind("something else")

    def test_empty(self):
        with self.assertRaises(ValueError):
            linguaskill_kind("")


class TestProductGroup(unittest.TestCase):
    def test_linguaskill_groups(self):
        self.assertEqual(product_of("LINGUASKILL General"), LINGUASKILL)
        self.assertEqual(group_for("LINGUASKILL General"), "New Linguaskill General Remote")
        self.assertEqual(group_for("LINGUASKILL Business"), "New Linguaskill Business Remote")

    def test_est_groups(self):
        self.assertEqual(product_of("ENGLISH SKILLS TEST General"), EST)
        self.assertEqual(group_for("ENGLISH SKILLS TEST General"), "EST General")
        self.assertEqual(group_for("ENGLISH SKILLS TEST Business"), "EST for Business")

    def test_unknown_product(self):
        for raw in [None, "", "TOEIC General"]:
            with self.assertRaises(ValueError):
                product_of(raw)

    def test_parse_creation_date(self):
        from datetime import date
        self.assertEqual(_parse_ddmmyyyy("22/09/2026 16:32"), date(2026, 9, 22))
        self.assertIsNone(_parse_ddmmyyyy(None))
        self.assertIsNone(_parse_ddmmyyyy("garbage"))


class TestGenderMapping(unittest.TestCase):
    def test_recognised_values(self):
        for raw, expected in [
            ("Male", "m"), ("male", "m"), ("M", "m"), ("Homme", "m"),
            ("Female", "f"), ("female", "f"), ("F", "f"), ("Femme", "f"),
        ]:
            self.assertEqual(map_gender(raw), expected, msg=raw)

    def test_ambiguous_or_missing_is_none(self):
        for raw in [None, "", "Non-binary", "unknown", "X"]:
            self.assertIsNone(map_gender(raw))


class TestPasswordReuseDecision(unittest.TestCase):
    def test_reuse_when_password_on_file(self):
        self.assertTrue(_has_password_on_file({"password_cms": "Abcd1234"}))

    def test_new_candidate_when_na(self):
        self.assertFalse(_has_password_on_file({"password_cms": "NA"}))
        self.assertFalse(_has_password_on_file({"password_cms": "na"}))
        self.assertFalse(_has_password_on_file({"password_cms": ""}))
        self.assertFalse(_has_password_on_file({"password_cms": None}))
        self.assertFalse(_has_password_on_file({}))

    def test_new_candidate_when_pandas_na(self):
        # get_passwords.py actually stores a real pd.NA, not the string
        # "NA", when no existing password was found.
        self.assertFalse(_has_password_on_file({"password_cms": pd.NA}))
        self.assertFalse(_has_password_on_file({"password_cms": float("nan")}))


class TestFranceOnlyFilter(unittest.TestCase):
    def test_both_france_passes(self):
        self.assertTrue(_is_france_only({"nationality": "France", "country_of_residence": "France"}))
        self.assertTrue(_is_france_only({"nationality": "france", "country_of_residence": "FRANCE"}))

    def test_nationality_not_france_fails(self):
        self.assertFalse(_is_france_only({"nationality": "Burkina Faso", "country_of_residence": "France"}))

    def test_residence_not_france_fails(self):
        self.assertFalse(_is_france_only({"nationality": "France", "country_of_residence": "Belgium"}))

    def test_missing_fields_fail(self):
        self.assertFalse(_is_france_only({}))
        self.assertFalse(_is_france_only({"nationality": "France"}))
        self.assertFalse(_is_france_only({"nationality": None, "country_of_residence": None}))


if __name__ == "__main__":
    unittest.main()
