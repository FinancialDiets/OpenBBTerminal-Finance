import webbrowser
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openbb_terminal import api

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def runme():
    webbrowser.open("http://localhost:3000")
    # webbrowser.open(f"https://pro.openbb.co/?host=http://localhost:{6969}")


@app.get("/", status_code=200)
def home(ticker: str, instrument_type: str = "stocks"):
    df = pd.DataFrame()
    if instrument_type == "stocks":
        df = api.stocks.load(ticker)
    elif instrument_type == "crypto":
        df = api.crypto.load(ticker)
    df.reset_index(inplace=True)
    df.columns = df.columns.str.lower()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    # rename date to time
    df.rename(columns={"date": "time"}, inplace=True)
    return df.to_dict(orient="records")
