from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from solarpros.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SolarPros API",
        description="Multi-Agent Solar Prospect Targeting System",
        version="0.1.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from solarpros.api.v1 import agents, campaigns, dashboard, owners, properties, scores, solar

    app.include_router(properties.router, prefix="/api/v1")
    app.include_router(solar.router, prefix="/api/v1")
    app.include_router(owners.router, prefix="/api/v1")
    app.include_router(scores.router, prefix="/api/v1")
    app.include_router(campaigns.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "solarpros"}

    return app


app = create_app()
