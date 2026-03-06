from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

from runner import main

app = FastAPI()

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))  # mount path Render Disk
CSV_PATH = DATA_DIR / "orders.csv"

def generate_csv():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = main()
    df.to_csv(CSV_PATH, index=False)
    return df

@app.post("/run")
def run():
    df = generate_csv()
    return {"ok": True, "rows": len(df)}

@app.get("/")
def root():
    return {"ok": True, "message": "API is running"}

@app.get("/output")
def output():
    generate_csv()
    return FileResponse(str(CSV_PATH), media_type="text/csv", filename="orders.csv")