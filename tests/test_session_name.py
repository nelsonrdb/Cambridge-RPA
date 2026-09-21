import unittest

import pandas as pd

from session_name import add_sessionname


def _session_name(linguaskill_type, exam_type):
    df = pd.DataFrame([{
        "linguaskill_type": linguaskill_type,
        "exam_type": exam_type,
        "exam_date": "01/01/2027",
        "email": "candidate@example.com",
    }])
    df = add_sessionname(df)
    return df["session_name"].iloc[0], df["skills_code"].iloc[0]


class TestSessionNamingScheme(unittest.TestCase):
    def test_official_packages(self):
        cases = [
            ("LINGUASKILL General", "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)", "G2S", "RL"),
            ("LINGUASKILL Business", "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)", "B2S", "RL"),
            ("LINGUASKILL General", "3 SKILLS - READING & LISTENING + SPEAKING (Air France, etc.)", "G3S", "RLS"),
            ("LINGUASKILL Business", "3 SKILLS - READING & LISTENING + SPEAKING (Air France, etc.)", "B3S", "RLS"),
            ("LINGUASKILL General", "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, etc.)", "G4S", "RLSW"),
            ("LINGUASKILL Business", "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, etc.)", "B4S", "RLSW"),
        ]
        for linguaskill_type, exam_type, expected_code, expected_skills in cases:
            name, skills = _session_name(linguaskill_type, exam_type)
            self.assertEqual(name, f"01/01/2027 {expected_code} candidate@example.com")
            self.assertEqual(skills, expected_skills)

    def test_single_skills(self):
        cases = [
            ("Listening Seul", "L"),
            ("Reading Seul", "R"),
            ("Speaking Seul", "S"),
            ("Writing Seul", "W"),
        ]
        for exam_type, letter in cases:
            name, skills = _session_name("LINGUASKILL General", exam_type)
            self.assertEqual(name, f"01/01/2027 G{letter} candidate@example.com")
            self.assertEqual(skills, letter)

            name, skills = _session_name("LINGUASKILL Business", exam_type)
            self.assertEqual(name, f"01/01/2027 B{letter} candidate@example.com")
            self.assertEqual(skills, letter)

    def test_atypical_combinations_no_plus_sign(self):
        cases = [
            ("Reading & Speaking", "RS"),
            ("Speaking & Writing", "SW"),
            ("Reading & Listening + Writing", "RLW"),
        ]
        for exam_type, code in cases:
            name, skills = _session_name("LINGUASKILL General", exam_type)
            self.assertEqual(name, f"01/01/2027 G{code} candidate@example.com")
            self.assertNotIn("+", name)
            self.assertEqual(skills, code)


if __name__ == "__main__":
    unittest.main()
