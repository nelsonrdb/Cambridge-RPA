import pandas as pd 
import numpy as np

name_dic = {
    "2 SKILLS - READING & LISTENING (Grandes Ecoles, Universités, etc.)": "2S",
    "3 SKILLS - READING & LISTENING + SPEAKING (Compagnies Aériennes, etc.)": "3S",
    "4 SKILLS - READING & LISTENING + SPEAKING + WRITING (Candidats Internationaux, ParcoursSup, Masters, Etranger, etc.)": "4S",
    "Listening Seul": "1S L",
    "Reading Seul": "1S R",
    "Writing Seul": "1S W",
    "Speaking Seul": "1S S",
    "Reading & Speaking": "2S RS",
    "Speaking & Writing": "2S SW",
    "Reading & Listening + Writing": "3S RLW",
}

def add_sessionname(csv_path):
    df = pd.read_csv(csv_path)
    session_letter = df["linguaskill_type"].str.split().str[1].str[0]
    pattern = df["exam_type"].map(name_dic)  # ATTENTION: ton dict correspond à exam_type, pas linguaskill_type

    #df["skill_code"] = np.where(    
    skill_code = np.where(
        pattern.notna() & session_letter.notna(),
        pattern.str.split("S", n=1).str[0] + "S" + session_letter + pattern.str.split("S", n=1).str[1],
        np.nan
    )
    df["session_name"] = df["exam_date"] + ' ' + skill_code + " " + df["email"]
    df.to_csv(csv_path, index = False)