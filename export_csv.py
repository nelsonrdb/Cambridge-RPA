from __future__ import annotations
from pathlib import Path
import pandas as pd
from session_name import add_sessionname

def create_dataframe(data, passwords):
    df = pd.DataFrame(data)  
    pw = pd.DataFrame.from_dict(passwords, orient="index")
    pw.columns= ["password_cms", "password_generated", "password", "is_entry_code"]
    df = df.dropna(subset=["email"])
    df = df.merge(pw, left_on="email", right_index=True, how="left")
    df = add_sessionname(df)
    df.to_csv("shared/orders.csv", index=False)
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