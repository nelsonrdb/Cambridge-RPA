from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io

from runner import main  # tu crées cette fonction

app = FastAPI()

@app.get("/output")
def output():
    df = main()  # retourne un DataFrame
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'}
    )
