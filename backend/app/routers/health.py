from typing import Annotated

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..database import get_connection
from ..schemas import HealthResponse


router = APIRouter(tags=["Estado"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Comprobar el estado del servicio",
    description="Verifica que la API pueda comunicarse con PostgreSQL.",
)
def health(connection: Annotated[Connection, Depends(get_connection)]) -> HealthResponse:
    connection.execute("SELECT 1").fetchone()
    return HealthResponse(status="ok", database="ok")
