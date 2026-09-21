from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
import os
import time
from update_status import main as do_update_status
from register_orders import register_orders
from typing import Dict, Any, Optional



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
def register(limit: Optional[int] = None, order: Optional[str] = None):
    """Fetch pending orders and register them against Cambridge/Metrica.

    Optional query params for a cautious first test instead of processing
    every pending order at once:
      POST /register?order=AD226-0004   — only this one order_number
      POST /register?limit=1            — only the first N pending orders

    Progress is printed to stdout throughout (visible live in Render's
    Logs tab while the request is in flight — the HTTP response itself
    only comes back once everything is done).
    """
    print(f"[REGISTER] request received (order={order!r}, limit={limit!r})", flush=True)
    df = generate_csv()
    if order:
        df = df[df["order_number"] == order]
    elif limit:
        df = df.head(limit)

    if len(df) == 0:
        print("[REGISTER] nothing to register", flush=True)
        return {"ok": True, "rows": 0}
    results = register_orders(df)
    print(f"[REGISTER] done — {sum(1 for r in results.values() if r['success'])}/{len(results)} succeeded", flush=True)
    return {"ok": True, "rows": len(df), "results": results}
