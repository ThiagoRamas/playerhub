from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection

from ..database import get_connection
from ..schemas import ClubDetail, ClubSummary, SquadMember


router = APIRouter(prefix="/clubs", tags=["Clubes"])
DatabaseConnection = Annotated[Connection, Depends(get_connection)]


@router.get(
    "",
    response_model=list[ClubSummary],
    summary="Buscar clubes",
    description="Busca clubes por nombre y devuelve primero las coincidencias más cercanas.",
)
def search_clubs(
    connection: DatabaseConnection,
    search: Annotated[
        str,
        Query(min_length=2, max_length=100, description="Nombre o parte del nombre del club."),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Cantidad máxima de resultados."),
    ] = 20,
) -> list[dict]:
    return connection.execute(
        """
        SELECT c.id, c.name, c.slug, co.name AS country, c.logo_url, c.is_complete
        FROM clubs c
        LEFT JOIN countries co ON co.id = c.country_id
        WHERE c.name ILIKE %s
        ORDER BY similarity(c.name, %s) DESC, c.name
        LIMIT %s
        """,
        (f"%{search}%", search, limit),
    ).fetchall()


@router.get(
    "/{club_id}",
    response_model=ClubDetail,
    summary="Ver un club",
    description="Devuelve la información general de un club y su cantidad de jugadores vinculados.",
)
def get_club(club_id: int, connection: DatabaseConnection) -> dict:
    club = connection.execute(
        """
        SELECT c.id, c.name, c.slug, co.name AS country, c.logo_url, c.is_complete,
               c.team_type, c.data_as_of,
               COUNT(DISTINCT m.player_id) FILTER (WHERE m.is_current) AS linked_players
        FROM clubs c
        LEFT JOIN countries co ON co.id = c.country_id
        LEFT JOIN player_club_memberships m ON m.club_id = c.id
        WHERE c.id = %s
        GROUP BY c.id, co.name
        """,
        (club_id,),
    ).fetchone()
    if club is None:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    return club


@router.get(
    "/{club_id}/squad",
    response_model=list[SquadMember],
    summary="Ver el plantel de un club",
    description=(
        "Devuelve los jugadores del plantel y diferencia a quienes están en el club, "
        "a préstamo o cedidos a otra institución."
    ),
)
def get_squad(club_id: int, connection: DatabaseConnection) -> list[dict]:
    exists = connection.execute("SELECT 1 FROM clubs WHERE id = %s", (club_id,)).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail="Club no encontrado")

    return connection.execute(
        """
        SELECT p.id, p.display_name, p.image_url, p.date_of_birth,
               pos.name AS position,
               ARRAY(
                   SELECT co.name
                   FROM player_citizenships pc
                   JOIN countries co ON co.id = pc.country_id
                   WHERE pc.player_id = p.id
                   ORDER BY co.name
               ) AS citizenships,
               (
                   SELECT mv.amount FROM market_values mv
                   WHERE mv.player_id = p.id
                   ORDER BY mv.valued_on DESC LIMIT 1
               ) AS latest_market_value,
               m.membership_type,
               CASE
                   WHEN m.membership_type = 'PERMANENT' AND EXISTS (
                       SELECT 1 FROM player_club_memberships loan
                       WHERE loan.player_id = p.id AND loan.is_current
                         AND loan.club_id <> m.club_id AND loan.membership_type = 'LOAN'
                   ) THEN 'LOANED_OUT'
                   WHEN m.membership_type = 'LOAN' THEN 'ON_LOAN'
                   ELSE 'SQUAD'
               END AS squad_status
        FROM player_club_memberships m
        JOIN players p ON p.id = m.player_id
        LEFT JOIN player_positions pp ON pp.player_id = p.id AND pp.is_primary
        LEFT JOIN positions pos ON pos.id = pp.position_id
        WHERE m.club_id = %s AND m.is_current
        ORDER BY squad_status, pos.name NULLS LAST, p.display_name
        """,
        (club_id,),
    ).fetchall()
