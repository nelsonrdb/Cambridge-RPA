from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os
import time


from runner import main

app = FastAPI()

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))  # mount path Render Disk
CSV_PATH = DATA_DIR / "orders.csv"

def generate_csv():
    print("Generating csv file")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = main()
    print(df)
    df.to_csv(CSV_PATH, index=False)
    return df

def generate_timed_csv():
    t0 = time.perf_counter()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    t1 = time.perf_counter()

    df = main()
    t2 = time.perf_counter()

    df.to_csv(CSV_PATH, index=False)
    t3 = time.perf_counter()

    print({
        "mkdir": round(t1 - t0, 2),
        "main": round(t2 - t1, 2),
        "to_csv": round(t3 - t2, 2),
        "total": round(t3 - t0, 2),
    })
    return df

@app.post("/run")
def run():
    df = generate_timed_csv()
    return {"ok": True, "rows": len(df)}

@app.get("/")
def root():
    return {"ok": True, "message": "API is running"}

@app.get("/output")
def output():
    generate_timed_csv()
    return FileResponse(str(CSV_PATH), media_type="text/csv", filename="orders.csv")