import unittest

import pandas as pd

from cambridge.sessions import linguaskill_kind, GROUP_BY_KIND, normalize_exam_hour
from cambridge.candidates import map_gender
from cambridge.registration import _has_password_on_file


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
        self.assertEqual(GROUP_BY_KIND["General"], "EST General")

    def test_business(self):
        self.assertEqual(linguaskill_kind("LINGUASKILL Business"), "Business")
        self.assertEqual(GROUP_BY_KIND["Business"], "EST for Business")

    def test_unrecognised(self):
        with self.assertRaises(ValueError):
            linguaskill_kind("something else")

    def test_empty(self):
        with self.assertRaises(ValueError):
            linguaskill_kind("")


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


if __name__ == "__main__":
    unittest.main()
