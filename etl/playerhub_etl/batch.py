from dataclasses import dataclass
from typing import Callable, Iterator, TYPE_CHECKING, TypeVar

from .config import Settings
from .source import DatasetSource


if TYPE_CHECKING:
    from .history import HistorySummary
    from .pipeline import LoadSummary


T = TypeVar("T")


def batches(values: list[T], size: int) -> Iterator[list[T]]:
    if size <= 0:
        raise ValueError("Batch size must be greater than zero")
    for index in range(0, len(values), size):
        yield values[index : index + size]


@dataclass(frozen=True)
class ClubBatchResult:
    club_id: int
    club_name: str
    snapshot: "LoadSummary"


@dataclass(frozen=True)
class CountryBatchResult:
    number: int
    clubs: list[ClubBatchResult]
    history: "HistorySummary"


@dataclass(frozen=True)
class CountryLoadSummary:
    country: str
    clubs: int
    players: int
    batches: list[CountryBatchResult]


def load_country(
    settings: Settings,
    country: str,
    *,
    search: str | None = None,
    batch_size: int = 20,
    max_clubs: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> CountryLoadSummary:
    from .history import load_player_history_for_players
    from .pipeline import load_club_snapshot

    source = DatasetSource(settings.dataset_root)
    catalog = source.available_clubs(search, country, max_clubs)
    if not catalog:
        raise ValueError(f"No loadable clubs found for country {country}")

    all_player_ids: set[int] = set()
    batch_results: list[CountryBatchResult] = []
    total_batches = (len(catalog) + batch_size - 1) // batch_size
    for batch_number, catalog_batch in enumerate(batches(catalog, batch_size), start=1):
        if progress:
            progress(
                f"Procesando lote {batch_number} de {total_batches} "
                f"({len(catalog_batch)} clubes)"
            )
        club_ids = {int(club["club_id"]) for club in catalog_batch}
        profiles_by_club = source.club_snapshot_profiles_by_club(club_ids)
        details_by_club = source.club_details(club_ids)
        batch_player_ids: set[int] = set()
        club_results: list[ClubBatchResult] = []

        for club in catalog_batch:
            club_id = int(club["club_id"])
            profiles = profiles_by_club[club_id]
            detail = details_by_club.get(club_id)
            if detail is None:
                raise ValueError(f"No team detail found for club {club_id}")
            if progress:
                progress(f"Cargando {club['club_name']} [{club_id}]")
            snapshot = load_club_snapshot(
                settings.for_club(club_id),
                source=source,
                profiles=profiles,
                detail=detail,
            )
            batch_player_ids.update(int(profile["player_id"]) for profile in profiles)
            club_results.append(
                ClubBatchResult(
                    club_id=club_id,
                    club_name=str(club["club_name"]),
                    snapshot=snapshot,
                )
            )

        if progress:
            progress(f"Importando historiales de {len(batch_player_ids)} jugadores")
        history = load_player_history_for_players(
            settings,
            batch_player_ids,
            source=source,
        )
        all_player_ids.update(batch_player_ids)
        batch_results.append(
            CountryBatchResult(
                number=batch_number,
                clubs=club_results,
                history=history,
            )
        )
        if progress:
            progress(f"Lote {batch_number} completado")

    return CountryLoadSummary(
        country=country,
        clubs=len(catalog),
        players=len(all_player_ids),
        batches=batch_results,
    )


def country_summary_payload(summary: CountryLoadSummary) -> dict[str, object]:
    return {
        "country": summary.country,
        "clubs": summary.clubs,
        "players": summary.players,
        "batches": [
            {
                "number": batch.number,
                "clubs": [
                    {
                        "club_id": club.club_id,
                        "club_name": club.club_name,
                        "snapshot": vars(club.snapshot),
                    }
                    for club in batch.clubs
                ],
                "history": vars(batch.history),
            }
            for batch in summary.batches
        ],
    }
