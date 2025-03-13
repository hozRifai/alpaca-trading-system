import os

from fastapi import FastAPI
from .utils import DatabaseManager
from .strategies import EmaCrossoverStrategy
from sqlalchemy.ext.declarative import declarative_base

app = FastAPI()
db_manager = DatabaseManager()
Base = declarative_base()


@app.on_event("startup")
async def startup_event():
    strategy_config = {
        "capital": 100000,
        "risk_per_trade": 0.02
    }
    
    app.state.ema_strategy = EmaCrossoverStrategy(strategy_config)
    Base.metadata.create_all(bind=db_manager.transactions_engine)

@app.get("/health")
def health_check():
    return {"status": "healthy"}