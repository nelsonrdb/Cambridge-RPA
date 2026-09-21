import numpy as np

letter_dic = {
    "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)": "RL",
    "3 SKILLS - READING & LISTENING + SPEAKING (Air France, etc.)": "RLS",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, etc.)": "RLSW",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, certaines compagnies aériennes, etc.)": 'RLSW',
    "Listening Seul": "L",
    "Reading Seul": "R",
    "Writing Seul": "W",
    "Speaking Seul": "S",
    "Reading & Speaking": "RS",
    "Speaking & Writing": "SW",
    "Reading & Listening + Writing": "RLW",
}

# The session-name code, WITHOUT the General/Business prefix (that's
# prepended in add_sessionname from linguaskill_type). e.g. exam_type
# "Speaking & Writing" + linguaskill_type "LINGUASKILL Business" ->
# code_dic value "SW" -> session code "BSW".
code_dic = {
    "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)": "2S",
    "3 SKILLS - READING & LISTENING + SPEAKING (Air France, etc.)": "3S",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, etc.)": "4S",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, certaines compagnies aériennes, etc.)": "4S",
    "Listening Seul": "L",
    "Reading Seul": "R",
    "Writing Seul": "W",
    "Speaking Seul": "S",
    "Reading & Speaking": "RS",
    "Speaking & Writing": "SW",
    "Reading & Listening + Writing": "RLW",
}

def add_sessionname(df):
    session_letter = df["linguaskill_type"].str.split().str[1].str[0]  # "General"/"Business" -> "G"/"B"
    code = df["exam_type"].map(code_dic)
    skill_code = np.where(
        code.notna() & session_letter.notna(),
        session_letter + code,
        np.nan
    )
    df["session_name"] = df["exam_date"] + ' ' + skill_code + " " + df["email"]
    df["skills_code"] = df["exam_type"].map(letter_dic)
    return df
