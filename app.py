from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
import os
import time
from update_status import main as do_update_status
from register_orders import register_orders
from typing import Dict, Any



from runner import main

app = FastAPI()

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))  # mount path Render Disk
CSV_PATH = DATA_DIR / "orders.csv"

def generate_csv():
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
    df = generate_csv()
    return {"ok": True, "rows": len(df)}

@app.get("/")
def root():
    return {"ok": True, "message": "API is running"}

@app.get("/output")
def output():
    generate_csv()
    return FileResponse(str(CSV_PATH), media_type="text/csv", filename="orders.csv")

@app.post("/update_status")
def update_status(payload: Dict[str, Any]):
    do_update_status(payload)
    return {"ok": True}

@app.post("/register")
def register():
    df = generate_csv()
    if len(df) == 0:
        return {"ok": True, "rows": 0}
    results = register_orders(df)
    return {"ok": True, "rows": len(df), "results": results}
