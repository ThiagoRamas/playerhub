from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import pool
from .routers import clubs, health, players


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open()
    pool.wait()
    yield
    pool.close()


app = FastAPI(
    title="API de PlayerHub",
    version="0.1.0",
    description=(
        "API REST de PlayerHub para consultar clubes, planteles, futbolistas "
        "y sus antecedentes deportivos."
    ),
    openapi_tags=[
        {
            "name": "Estado",
            "description": "Comprobaciones de disponibilidad de la aplicación y la base de datos.",
        },
        {
            "name": "Clubes",
            "description": "Búsqueda de clubes, información general y planteles.",
        },
        {
            "name": "Jugadores",
            "description": (
                "Perfiles de jugadores, rendimientos, valores de mercado, "
                "transferencias y lesiones."
            ),
        },
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(clubs.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
