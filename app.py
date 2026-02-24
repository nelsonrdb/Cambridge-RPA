from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

from runner import main

app = FastAPI()

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))  # mount path Render Disk
CSV_PATH = DATA_DIR / "orders.csv"

@app.post("/run")
def run():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = main()
    df.to_csv(CSV_PATH, index=False)
    return {"ok": True, "rows": len(df)}

@app.get("/output")
def output():
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="No CSV yet. Call POST /run first.")
    return FileResponse(str(CSV_PATH), media_type="text/csv", filename="orders.csv")