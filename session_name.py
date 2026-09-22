import numpy as np
import pandas as pd

# Keys are the exam_type label WITHOUT any trailing "(...)" audience note:
# X-Net labels the same package differently per product, e.g. Linguaskill
# "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)" vs
# EST "2 SKILLS - READING & LISTENING" — see normalize_exam_type().
letter_dic = {
    "2 SKILLS - READING & LISTENING": "RL",
    "3 SKILLS - READING & LISTENING + SPEAKING": "RLS",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING": "RLSW",
    "Listening Seul": "L",
    "Reading Seul": "R",
    "Writing Seul": "W",
    "Speaking Seul": "S",
    "Reading & Speaking": "RS",
    "Speaking & Writing": "SW",
    "Reading & Listening + Writing": "RLW",
}

# The session-name code, WITHOUT the product/General/Business prefix (that's
# prepended in add_sessionname from linguaskill_type). e.g. exam_type
# "Speaking & Writing" + linguaskill_type "LINGUASKILL Business" -> "BSW",
# or + "ENGLISH SKILLS TEST Business" -> "ESTBSW".
code_dic = {
    "2 SKILLS - READING & LISTENING": "2S",
    "3 SKILLS - READING & LISTENING + SPEAKING": "3S",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING": "4S",
    "Listening Seul": "L",
    "Reading Seul": "R",
    "Writing Seul": "W",
    "Speaking Seul": "S",
    "Reading & Speaking": "RS",
    "Speaking & Writing": "SW",
    "Reading & Listening + Writing": "RLW",
}

EST_MARKER = "ENGLISH SKILLS TEST"


def normalize_exam_type(exam_type):
    return exam_type.str.replace(r"\s*\(.*\)\s*$", "", regex=True).str.strip()


def add_sessionname(df):
    ltype = df["linguaskill_type"].fillna("")
    # "General"/"Business" -> "G"/"B". Searched anywhere in the label rather
    # than by word position: "LINGUASKILL General" vs "ENGLISH SKILLS TEST
    # General" put it at different positions.
    session_letter = pd.Series(
        np.select(
            [ltype.str.contains("General"), ltype.str.contains("Business")],
            ["G", "B"],
            default="",
        ),
        index=df.index,
    )
    prefix = pd.Series(
        np.where(ltype.str.upper().str.contains(EST_MARKER), "EST", ""),
        index=df.index,
    )
    exam_type = normalize_exam_type(df["exam_type"].fillna(""))
    code = exam_type.map(code_dic)
    skill_code = np.where(
        code.notna() & (session_letter != ""),
        prefix + session_letter + code.fillna(""),
        np.nan,
    )
    df["session_name"] = df["exam_date"] + ' ' + skill_code + " " + df["email"]
    df["skills_code"] = exam_type.map(letter_dic)
    return df
