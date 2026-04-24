"""FastAPI application factory and startup."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Luxury Gold Trading Bot — REST API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files for admin panel
    app.mount("/static", StaticFiles(directory="app/admin/static"), name="static")

    # API routers
    from app.api.routers import orders, prices, users, webhooks, withdrawals

    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
    app.include_router(withdrawals.router, prefix="/api/v1/withdrawals", tags=["Withdrawals"])
    app.include_router(prices.router, prefix="/api/v1/prices", tags=["Prices"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

    # Admin panel
    from app.admin.router import router as admin_router

    app.include_router(admin_router, prefix="/admin", tags=["Admin"])

    # Bot webhook endpoint (if using webhook mode)
    from app.api.routers.bot_webhook import router as bot_router

    app.include_router(bot_router, prefix="/bot", tags=["Bot"])

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
