from __future__ import annotations
from pathlib import Path
import pandas as pd
from session_name import add_sessionname

country_map = {
    "Bolivia, Plurinational State of": "Bolivia",
    "Cape Verde": "Cabo Verde",
    "Congo, the Democratic Republic of the": "Congo (the Democratic Republic)",
    "Falkland Islands (Malvinas)": "Falkland Islands",
    "French Southern Territories": "French Southern Territories (the)",
    "Holy See (Vatican City State)": "Vatican City",
    "Hong Kong": "Hong Kong SAR, China",
    "Iran, Islamic Republic of": "Iran (Islamic Republic)",
    "Ireland": "Ireland (Republic of)",
    "Korea, Democratic People's Republic of": "Korea (Democratic People's Republic)",
    "Korea, Republic of": "Korea (Republic)",
    "Lao People's Democratic Republic": "Laos (People's Democratic Republic)",
    "Macao": "Macao SAR, China",
    "Macedonia, the Former Yugoslav Republic of": "Macedonia (the former Yugoslav Republic)",
    "Micronesia, Federated States of": "Micronesia",
    "Moldova, Republic of": "Moldova (Republic)",
    "Palestine, State of": "Palestine (State)",
    "Pitcairn": "Pitcairn Islands",
    "Saint Barthélemy": "Saint Barthelemy",
    "Saint Helena, Ascension and Tristan da Cunha": "Saint Helena Ascension and Tristan da Cunha",
    "Saint Kitts and Nevis": "Saint Kitts-Nevis",
    "Saint Martin (French part)": "Saint Martin",
    "Svalbard and Jan Mayen": "Svalbard",
    "Taiwan, Province of China": "Taiwan",
    "Tanzania, United Republic of": "Tanzania",
    "United States": "United States of America",
    "United States Minor Outlying Islands": "United States Minor Outlying Islands (the)",
    "Venezuela, Bolivarian Republic of": "Venezuela (Bolivarian Republic of)",
    "Viet Nam": "Vietnam",
    "Virgin Islands, British": "Virgin Islands (British)",
    "Virgin Islands, U.S.": "Virgin Islands (US)",
}

def create_dataframe(data, passwords):
    df = pd.DataFrame(data)
    df["nationality"] = df["nationality"].replace(country_map)
    pw = pd.DataFrame.from_dict(passwords, orient="index")
    pw.columns= ["password_cms", "password_generated", "password", "is_entry_code"]
    df = df.dropna(subset=["email"])
    df = df.merge(pw, left_on="email", right_index=True, how="left")
    df = add_sessionname(df)
    return df

def write_csv_same_columns(data, passwords, csv_path):
    df = pd.DataFrame(data)  
    pw = pd.DataFrame.from_dict(passwords, orient="index")
    pw.columns= ["password_cms", "password_generated", "password", "is_entry_code"]
    df = df.merge(pw, left_on="email", left_index=False, right_index=True, how="left")
    df = df.dropna(subset=["email"])
    df.to_csv(csv_path, index=False, encoding="utf-8", mode = "w")

def write_done_flag(output_dir: str | Path, filename: str = "DONE.flag") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    flag = out / filename
    flag.write_text("OK\n", encoding="utf-8")
    return flag

def remove_done_flag(output_dir: str | Path, filename: str = "DONE.flag") -> None:
    flag = Path(output_dir) / filename
    if flag.exists():
        flag.unlink()