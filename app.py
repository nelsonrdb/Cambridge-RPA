from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import os
import queue
import sys
import threading
import time
import traceback
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
def register(limit: Optional[int] = None, order: Optional[str] = None, stream: bool = False):
    """Fetch pending orders and register them against Cambridge/Metrica.

    Optional query params for a cautious first test instead of processing
    every pending order at once:
      POST /register?order=AD226-0004   — only this one order_number
      POST /register?limit=1            — only the first N pending orders

    Progress is printed to stdout throughout (visible live in Render's
    Logs tab while the request is in flight). Without `stream`, the HTTP
    response itself only comes back once everything is done.

      POST /register?stream=true        — also stream those same log
                                          lines live in the response body
                                          (use `curl -N` to see them)
    """
    if not stream:
        return _register(limit, order)
    if not _stream_lock.acquire(blocking=False):
        return StreamingResponse(
            iter(["[REGISTER] another streamed registration is already running — not starting a second one\n"]),
            media_type="text/plain; charset=utf-8",
            status_code=409,
        )
    return StreamingResponse(
        _stream_output(lambda: _register(limit, order)),
        media_type="text/plain; charset=utf-8",
    )


def _register(limit: Optional[int], order: Optional[str]):
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


# sys.stdout is process-wide, so only one streamed run may capture it at
# a time. Held from request start until the worker thread finishes.
_stream_lock = threading.Lock()
_DONE = object()


class _Tee:
    """Keeps writing to the real stdout (Render's Logs tab) while also
    handing every chunk to the streamed HTTP response."""

    def __init__(self, original, q):
        self._original, self._q = original, q

    def write(self, text):
        self._original.write(text)
        if text:
            self._q.put(text)
        return len(text)

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def _stream_output(job):
    q = queue.Queue()

    def worker():
        original = sys.stdout
        sys.stdout = _Tee(original, q)
        try:
            result = job()
            _print_result_summary(result)
        except Exception:
            traceback.print_exc(file=sys.stdout)
            print("[REGISTER] failed — see error above", flush=True)
        finally:
            sys.stdout = original
            q.put(_DONE)
            _stream_lock.release()

    # The run goes on to completion even if the client disconnects: never
    # abort halfway through a registration or an X-Net status update.
    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is _DONE:
            return
        yield item


def _print_result_summary(result):
    """End-of-run recap for the streamed response. No passwords/emails:
    the terminal output may be copied around."""
    results = (result or {}).get("results") or {}
    for order_number, r in results.items():
        if r.get("success"):
            print(f"[RESULT] {order_number}: OK — {r.get('confirmation', '')}", flush=True)
        else:
            print(f"[RESULT] {order_number}: MANUEL — {r.get('manual_review_reason', '')}", flush=True)
    print(f"[RESULT] {sum(1 for r in results.values() if r.get('success'))}/{len(results)} succeeded", flush=True)
