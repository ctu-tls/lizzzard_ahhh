from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from strategy_config import StrategyConfig
from strategy_runner import run_backtest

app = FastAPI(title="Trading Strategy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/backtest")
def backtest(config: StrategyConfig):
    try:
        return run_backtest(config)
    except Exception as e:
        return {
            "error": "Backend crashed while running backtest",
            "details": str(e),
        }