from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection

from ..database import get_connection
from ..schemas import (
    InjuryItem,
    MarketValueItem,
    PerformanceItem,
    PlayerDetail,
    PlayerSummary,
    TransferItem,
)


router = APIRouter(prefix="/players", tags=["Jugadores"])
DatabaseConnection = Annotated[Connection, Depends(get_connection)]


@router.get(
    "",
    response_model=list[PlayerSummary],
    summary="Buscar jugadores",
    description="Busca futbolistas por nombre o apellido y devuelve primero las coincidencias más cercanas.",
)
def search_players(
    connection: DatabaseConnection,
    search: Annotated[
        str,
        Query(min_length=2, max_length=100, description="Nombre o apellido del jugador."),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Cantidad máxima de resultados."),
    ] = 20,
) -> list[dict]:
    pattern = f"%{search}%"
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
               ARRAY(
                   SELECT c.name
                   FROM player_club_memberships m
                   JOIN clubs c ON c.id = m.club_id
                   WHERE m.player_id = p.id AND m.is_current
                   ORDER BY CASE WHEN m.membership_type = 'LOAN' THEN 0 ELSE 1 END, c.name
               ) AS current_clubs,
               (
                   SELECT mv.amount
                   FROM market_values mv
                   WHERE mv.player_id = p.id
                   ORDER BY mv.valued_on DESC
                   LIMIT 1
               ) AS latest_market_value
        FROM players p
        LEFT JOIN player_positions pp ON pp.player_id = p.id AND pp.is_primary
        LEFT JOIN positions pos ON pos.id = pp.position_id
        WHERE p.display_name ILIKE %s OR COALESCE(p.full_name, '') ILIKE %s
        ORDER BY similarity(p.display_name, %s) DESC, p.display_name
        LIMIT %s
        """,
        (pattern, pattern, search, limit),
    ).fetchall()


def require_player(connection: Connection, player_id: int) -> None:
    if connection.execute("SELECT 1 FROM players WHERE id = %s", (player_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")


@router.get(
    "/{player_id}",
    response_model=PlayerDetail,
    summary="Ver un jugador",
    description="Devuelve el perfil del jugador, su posición, nacionalidades, clubes y valor actual.",
)
def get_player(player_id: int, connection: DatabaseConnection) -> dict:
    player = connection.execute(
        """
        SELECT p.id, p.display_name, p.full_name, p.slug, p.image_url,
               p.date_of_birth, p.date_of_death, p.place_of_birth,
               birth_country.name AS country_of_birth, p.height_cm,
               p.preferred_foot, p.career_status, pos.name AS position,
               ARRAY(
                   SELECT co.name
                   FROM player_citizenships pc
                   JOIN countries co ON co.id = pc.country_id
                   WHERE pc.player_id = p.id ORDER BY co.name
               ) AS citizenships,
               (
                   SELECT mv.amount FROM market_values mv
                   WHERE mv.player_id = p.id
                   ORDER BY mv.valued_on DESC LIMIT 1
               ) AS latest_market_value,
               p.data_as_of
        FROM players p
        LEFT JOIN countries birth_country ON birth_country.id = p.country_of_birth_id
        LEFT JOIN player_positions pp ON pp.player_id = p.id AND pp.is_primary
        LEFT JOIN positions pos ON pos.id = pp.position_id
        WHERE p.id = %s
        """,
        (player_id,),
    ).fetchone()
    if player is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    player["current_clubs"] = connection.execute(
        """
        SELECT c.id, c.name, m.membership_type, m.is_current
        FROM player_club_memberships m
        JOIN clubs c ON c.id = m.club_id
        WHERE m.player_id = %s AND m.is_current
        ORDER BY m.membership_type, c.name
        """,
        (player_id,),
    ).fetchall()
    return player


@router.get(
    "/{player_id}/performances",
    response_model=list[PerformanceItem],
    summary="Ver rendimientos",
    description="Lista los rendimientos del jugador por temporada, club y competencia.",
)
def get_performances(player_id: int, connection: DatabaseConnection) -> list[dict]:
    require_player(connection, player_id)
    return connection.execute(
        """
        SELECT s.label AS season, c.name AS club, co.name AS competition,
               p.appearances, p.goals, p.assists, p.minutes_played,
               p.yellow_cards, p.red_cards
        FROM performances p
        JOIN seasons s ON s.id = p.season_id
        JOIN clubs c ON c.id = p.club_id
        JOIN competitions co ON co.id = p.competition_id
        WHERE p.player_id = %s
        ORDER BY s.start_year DESC, co.name, c.name
        """,
        (player_id,),
    ).fetchall()


@router.get(
    "/{player_id}/market-values",
    response_model=list[MarketValueItem],
    summary="Ver valores de mercado",
    description="Devuelve la evolución histórica del valor de mercado del jugador.",
)
def get_market_values(player_id: int, connection: DatabaseConnection) -> list[dict]:
    require_player(connection, player_id)
    return connection.execute(
        """
        SELECT valued_on, amount, currency_code
        FROM market_values WHERE player_id = %s ORDER BY valued_on
        """,
        (player_id,),
    ).fetchall()


@router.get(
    "/{player_id}/transfers",
    response_model=list[TransferItem],
    summary="Ver transferencias",
    description="Lista los movimientos del jugador entre clubes a lo largo de su carrera.",
)
def get_transfers(player_id: int, connection: DatabaseConnection) -> list[dict]:
    require_player(connection, player_id)
    return connection.execute(
        """
        SELECT t.transfer_date, s.label AS season,
               COALESCE(origin.name, t.from_career_state) AS from_team,
               COALESCE(destination.name, t.to_career_state) AS to_team,
               t.transfer_type, t.market_value_amount, t.fee_amount, t.currency_code
        FROM transfers t
        LEFT JOIN seasons s ON s.id = t.season_id
        LEFT JOIN clubs origin ON origin.id = t.from_club_id
        LEFT JOIN clubs destination ON destination.id = t.to_club_id
        WHERE t.player_id = %s
        ORDER BY t.transfer_date DESC NULLS LAST, t.id DESC
        """,
        (player_id,),
    ).fetchall()


@router.get(
    "/{player_id}/injuries",
    response_model=list[InjuryItem],
    summary="Ver lesiones",
    description="Lista las lesiones registradas y el tiempo de ausencia del jugador.",
)
def get_injuries(player_id: int, connection: DatabaseConnection) -> list[dict]:
    require_player(connection, player_id)
    return connection.execute(
        """
        SELECT s.label AS season, i.reason, i.started_on, i.ended_on,
               i.days_missed, i.games_missed
        FROM injuries i
        LEFT JOIN seasons s ON s.id = i.season_id
        WHERE i.player_id = %s
        ORDER BY i.started_on DESC NULLS LAST, i.id DESC
        """,
        (player_id,),
    ).fetchall()
