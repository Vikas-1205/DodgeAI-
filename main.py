"""
FastAPI Application Entry Point.

Business Data Management System — handles customers, addresses,
products, orders, deliveries, invoices, and payments.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routes import customers, addresses, products, orders, deliveries, invoices, payments, order_items
from routes import graph as graph_routes
from routes import chat as chat_route


# ─── Application Lifespan ────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


# ─── FastAPI App ──────────────────────────────────────────────────────────────


app = FastAPI(
    title="Business Data Management API",
    description=(
        "Production-ready API for managing customers, addresses, products, "
        "orders, deliveries, invoices, and payments."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(customers.router, prefix=API_PREFIX)
app.include_router(addresses.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(deliveries.router, prefix=API_PREFIX)
app.include_router(invoices.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(order_items.router, prefix=API_PREFIX)
app.include_router(graph_routes.router, prefix=API_PREFIX)
app.include_router(chat_route.router, prefix=API_PREFIX)


# ─── Health Check ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"])
def health_check():
    """Returns application health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }
