from dataclasses import dataclass
from typing import Any

from . import __version__
from .config import Settings
from .normalize import (
    career_state,
    clean_entity_name,
    fingerprint,
    optional_date,
    optional_int,
    optional_text,
    season_values,
    transfer_type,
)
from .repository import Repository
from .source import DatasetSource


HISTORY_FILES = ("performances", "market_values", "transfers", "injuries")


@dataclass(frozen=True)
class HistorySummary:
    run_id: int
    players: int
    performances: int
    market_values: int
    transfers: int
    injuries: int


def load_player_history(settings: Settings) -> HistorySummary:
    source = DatasetSource(settings.dataset_root)
    profiles = source.club_snapshot_profiles(settings.target_club_id)
    external_player_ids = {int(profile["player_id"]) for profile in profiles}
    if not external_player_ids:
        raise ValueError(f"No profiles found for club {settings.target_club_id}")

    rows_by_file = {
        key: list(source.rows_for_players(key, external_player_ids))
        for key in HISTORY_FILES
    }
    dataset_fingerprint = source.fingerprint(HISTORY_FILES)

    with Repository(settings.database_url) as repository:
        run_id = repository.start_run(__version__, dataset_fingerprint, settings.data_as_of)
        try:
            player_ids = repository.player_ids_by_external_id(external_player_ids)
            missing_players = external_player_ids - set(player_ids)
            if missing_players:
                raise ValueError(
                    "Run load-club-snapshot first; missing players: "
                    + ", ".join(str(value) for value in sorted(missing_players))
                )

            club_cache: dict[int, int] = {}
            competition_cache: dict[str, int] = {}
            season_cache: dict[tuple[str, int, int], int] = {}

            def get_club(external_id: str, name: str) -> int:
                parsed_id = int(external_id)
                if parsed_id not in club_cache:
                    club_cache[parsed_id] = repository.upsert_club(
                        parsed_id,
                        clean_entity_name(name, parsed_id),
                        run_id,
                        data_as_of=settings.data_as_of,
                    )
                return club_cache[parsed_id]

            def get_competition(external_id: str, name: str) -> int:
                if external_id not in competition_cache:
                    competition_cache[external_id] = repository.upsert_competition(
                        external_id,
                        optional_text(name) or f"Unknown competition {external_id}",
                        run_id,
                    )
                return competition_cache[external_id]

            def get_season(label: str | None) -> int | None:
                cleaned = optional_text(label)
                if not cleaned:
                    return None
                normalized = season_values(cleaned)
                key = normalized[:3]
                if key not in season_cache:
                    season_cache[key] = repository.upsert_season(*normalized)
                return season_cache[key]

            counters: dict[str, dict[str, int]] = {
                key: {"inserted": 0, "updated": 0} for key in HISTORY_FILES
            }

            for row in rows_by_file["performances"]:
                inserted = repository.upsert_performance(
                    {
                        "player_id": player_ids[int(row["player_id"])],
                        "club_id": get_club(row["team_id"], row["team_name"]),
                        "competition_id": get_competition(
                            row["competition_id"], row["competition_name"]
                        ),
                        "season_id": get_season(row["season_name"]),
                        "squad_appearances": optional_int(row["nb_in_group"]),
                        "appearances": optional_int(row["nb_on_pitch"]),
                        "goals": optional_int(row["goals"]),
                        "assists": optional_int(row["assists"]),
                        "own_goals": optional_int(row["own_goals"]),
                        "substituted_in": optional_int(row["subed_in"]),
                        "substituted_out": optional_int(row["subed_out"]),
                        "yellow_cards": optional_int(row["yellow_cards"]),
                        "second_yellow_cards": optional_int(row["second_yellow_cards"]),
                        "red_cards": optional_int(row["direct_red_cards"]),
                        "penalty_goals": optional_int(row["penalty_goals"]),
                        "minutes_played": optional_int(row["minutes_played"]),
                        "goals_conceded": optional_int(row["goals_conceded"]),
                        "clean_sheets": optional_int(row["clean_sheets"]),
                        "source_etl_run_id": run_id,
                    }
                )
                counters["performances"]["inserted" if inserted else "updated"] += 1

            for row in rows_by_file["market_values"]:
                inserted = repository.upsert_market_value(
                    {
                        "player_id": player_ids[int(row["player_id"])],
                        "valued_on": optional_date(row["date_unix"]),
                        "amount": optional_int(row["value"]),
                        "currency_code": None,
                        "source_etl_run_id": run_id,
                    }
                )
                counters["market_values"]["inserted" if inserted else "updated"] += 1

            for row in rows_by_file["transfers"]:
                from_state = career_state(row["from_team_name"])
                to_state = career_state(row["to_team_name"])
                payload = {
                    "player_id": player_ids[int(row["player_id"])],
                    "season_id": get_season(row["season_name"]),
                    "transfer_date": optional_date(row["transfer_date"]),
                    "from_club_id": None
                    if from_state
                    else get_club(row["from_team_id"], row["from_team_name"]),
                    "to_club_id": None
                    if to_state
                    else get_club(row["to_team_id"], row["to_team_name"]),
                    "transfer_type": transfer_type(row["transfer_type"]),
                    "from_career_state": from_state,
                    "to_career_state": to_state,
                    "market_value_amount": optional_int(row["value_at_transfer"]),
                    "fee_amount": optional_int(row["transfer_fee"]),
                    "currency_code": None,
                    "source_etl_run_id": run_id,
                }
                payload["source_fingerprint"] = fingerprint(
                    {
                        "player_external_id": int(row["player_id"]),
                        "season": row["season_name"],
                        "date": row["transfer_date"],
                        "from": row["from_team_id"],
                        "to": row["to_team_id"],
                        "type": row["transfer_type"],
                    }
                )
                inserted = repository.upsert_transfer(payload)
                counters["transfers"]["inserted" if inserted else "updated"] += 1

            for row in rows_by_file["injuries"]:
                payload = {
                    "player_id": player_ids[int(row["player_id"])],
                    "season_id": get_season(row["season_name"]),
                    "reason": optional_text(row["injury_reason"]) or "Unknown injury",
                    "started_on": optional_date(row["from_date"]),
                    "ended_on": optional_date(row["end_date"]),
                    "days_missed": optional_int(row["days_missed"]),
                    "games_missed": optional_int(row["games_missed"]),
                    "source_etl_run_id": run_id,
                }
                payload["source_fingerprint"] = fingerprint(
                    {
                        "player_external_id": int(row["player_id"]),
                        "season": row["season_name"],
                        "reason": row["injury_reason"],
                        "from": row["from_date"],
                        "to": row["end_date"],
                    }
                )
                inserted = repository.upsert_injury(payload)
                counters["injuries"]["inserted" if inserted else "updated"] += 1

            total_rows = 0
            for key in HISTORY_FILES:
                row_count = len(rows_by_file[key])
                total_rows += row_count
                repository.record_file_result(
                    run_id,
                    source.path_for(key).name,
                    source.file_fingerprint(key),
                    row_count,
                    counters[key]["inserted"],
                    counters[key]["updated"],
                )

            repository.finish_run(run_id, total_rows, total_rows)
            repository.commit()
        except Exception as error:
            repository.fail_run(run_id, error)
            raise

    return HistorySummary(
        run_id=run_id,
        players=len(player_ids),
        performances=len(rows_by_file["performances"]),
        market_values=len(rows_by_file["market_values"]),
        transfers=len(rows_by_file["transfers"]),
        injuries=len(rows_by_file["injuries"]),
    )

