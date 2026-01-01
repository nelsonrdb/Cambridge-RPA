from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def write_csv_same_columns(
    data: Iterable[Any],
    csv_path: str | Path,
    encoding: str = "utf-8",
) -> Path:
    """
    Écrit un CSV en supposant que si data contient des dict, ils ont tous les mêmes colonnes.
    Sinon -> une colonne 'row_json' avec une version JSON de chaque ligne.
    """
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    data_list = list(data)

    if data_list and isinstance(data_list[0], dict):
        fieldnames = list(data_list[0].keys())  # colonnes du 1er dict (ordre conservé)
        with csv_path.open("w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_list)
    else:
        with csv_path.open("w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=["row_json"])
            writer.writeheader()
            for x in data_list:
                writer.writerow({"row_json": json.dumps(x, ensure_ascii=False)})

    return csv_path

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




