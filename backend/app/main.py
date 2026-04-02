import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import init_db
from app.routers import portfolios, holdings, performance, orders, market_data, export

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Portfolio Management System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolios.router)
app.include_router(holdings.router)
app.include_router(performance.router)
app.include_router(orders.router)
app.include_router(market_data.router)
app.include_router(export.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
