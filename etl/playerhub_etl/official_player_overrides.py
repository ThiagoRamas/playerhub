from dataclasses import dataclass, replace
from datetime import date

from .api_football import LiveSquad


OFFICIAL_RESERVE_SQUAD_URL = (
    "https://clubaindependiente.com.ar/futbol/reserva/plantel"
)
OFFICIAL_MATEO_PEREZ_URL = (
    "https://clubaindependiente.com.ar/futbol/plantel/perfil/mateoperezcurci"
)


@dataclass(frozen=True)
class OfficialPlayerOverride:
    full_name: str
    date_of_birth: date
    source_url: str
    nationality: str | None = None


OFFICIAL_PLAYER_OVERRIDES = {
    669570: OfficialPlayerOverride(
        "Juan Miguel Arrayago", date(2008, 11, 17), OFFICIAL_RESERVE_SQUAD_URL
    ),
    560351: OfficialPlayerOverride(
        "Sim\u00f3n Bodnar", date(2007, 8, 22), OFFICIAL_RESERVE_SQUAD_URL
    ),
    669779: OfficialPlayerOverride(
        "Facundo Lionel Cruz", date(2006, 5, 22), OFFICIAL_RESERVE_SQUAD_URL
    ),
    599937: OfficialPlayerOverride(
        "Josias Emanuel Palais", date(2006, 4, 11), OFFICIAL_RESERVE_SQUAD_URL
    ),
    560306: OfficialPlayerOverride(
        "Mateo P\u00e9rez Curci",
        date(2006, 1, 24),
        OFFICIAL_MATEO_PEREZ_URL,
        nationality="Argentina",
    ),
    560463: OfficialPlayerOverride(
        "Joshua Guillermo Velardez", date(2006, 3, 6), OFFICIAL_RESERVE_SQUAD_URL
    ),
    642717: OfficialPlayerOverride(
        "Mathias De Las Carreras", date(2007, 8, 3), OFFICIAL_RESERVE_SQUAD_URL
    ),
    560363: OfficialPlayerOverride(
        "Felipe Tempone", date(2006, 2, 3), OFFICIAL_RESERVE_SQUAD_URL
    ),
    643831: OfficialPlayerOverride(
        "Facundo Samuel Vald\u00e9z", date(2006, 4, 10), OFFICIAL_RESERVE_SQUAD_URL
    ),
}


def apply_official_player_overrides(
    squad: LiveSquad,
) -> tuple[LiveSquad, tuple[int, ...]]:
    players = []
    applied_ids = []
    for player in squad.players:
        override = OFFICIAL_PLAYER_OVERRIDES.get(player.external_id)
        if override is None or (player.full_name and player.date_of_birth):
            players.append(player)
            continue
        players.append(
            replace(
                player,
                full_name=player.full_name or override.full_name,
                date_of_birth=player.date_of_birth or override.date_of_birth,
                nationality=player.nationality or override.nationality,
            )
        )
        applied_ids.append(player.external_id)
    return replace(squad, players=tuple(players)), tuple(applied_ids)


def official_source_urls(player_ids: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(
        sorted({OFFICIAL_PLAYER_OVERRIDES[player_id].source_url for player_id in player_ids})
    )
