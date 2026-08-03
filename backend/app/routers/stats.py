from typing import Annotated

from fastapi import APIRouter, Depends
from psycopg import Connection

from ..database import get_connection
from ..schemas import PlatformStats


router = APIRouter(prefix="/stats", tags=["Estadísticas"])
DatabaseConnection = Annotated[Connection, Depends(get_connection)]


@router.get(
    "",
    response_model=PlatformStats,
    summary="Ver cobertura de datos",
    description="Devuelve las cantidades actuales de clubes, jugadores y registros históricos.",
)
def get_stats(connection: DatabaseConnection) -> dict:
    return connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM clubs WHERE is_complete) AS clubs,
            (SELECT COUNT(*) FROM players WHERE is_complete) AS players,
            (SELECT COUNT(*) FROM performances) AS performances,
            (SELECT COUNT(*) FROM market_values) AS market_values,
            (SELECT COUNT(*) FROM transfers) AS transfers,
            (SELECT COUNT(*) FROM injuries) AS injuries,
            (SELECT MAX(data_as_of) FROM players WHERE is_complete) AS data_as_of
        """
    ).fetchone()
