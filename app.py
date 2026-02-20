from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import subprocess
from pathlib import Path

app = FastAPI(title="Scraper Launcher API")

BASE_DIR = Path(__file__).parent
SCRIPT_PATH = BASE_DIR / "runner.py"
OUTPUT_PATH = BASE_DIR / "shared" / "orders_test.csv" 


@app.get("/")
def root():
    return {"ok": True, "hint": "GET /run pour lancer le programme"}

@app.get("/run")
def run_program():
    if not SCRIPT_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Script introuvable: {SCRIPT_PATH}")

    try:
        result = subprocess.run(
            ["python", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "launched": True,
            "returncode": result.returncode,
            "stdout": result.stdout[-5000:],  
            "stderr": result.stderr[-5000:],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/output")
def get_output_file():
    if not OUTPUT_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fichier output introuvable: {OUTPUT_PATH}"
        )

    if OUTPUT_PATH.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="Fichier output vide")

    return FileResponse(
        path=str(OUTPUT_PATH),
        filename=OUTPUT_PATH.name,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )