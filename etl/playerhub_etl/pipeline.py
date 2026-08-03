from dataclasses import dataclass
from typing import Any

from . import __version__
from .config import Settings
from .normalize import (
    NON_CLUB_NAMES,
    career_status,
    clean_entity_name,
    optional_date,
    optional_int,
    optional_text,
    position_code,
    preferred_foot,
    resolve_club_name,
    split_citizenships,
)
from .repository import Repository
from .source import DatasetSource


@dataclass(frozen=True)
class LoadSummary:
    run_id: int
    players: int
    clubs: int
    memberships: int


def _club_reference(external_id: str, name: str) -> tuple[int, str] | None:
    if not external_id or name in NON_CLUB_NAMES:
        return None
    return int(external_id), clean_entity_name(name, external_id)


def load_club_snapshot(
    settings: Settings,
    *,
    source: DatasetSource | None = None,
    profiles: list[dict[str, str]] | None = None,
    detail: dict[str, str] | None = None,
) -> LoadSummary:
    source = source or DatasetSource(settings.dataset_root)
    source_fingerprint = source.fingerprint(("profiles", "team_details"))
    profiles = profiles if profiles is not None else source.club_snapshot_profiles(settings.target_club_id)
    if not profiles:
        raise ValueError(f"No profiles found for club {settings.target_club_id}")

    detail = detail if detail is not None else source.club_detail(settings.target_club_id)
    if detail is None:
        raise ValueError(f"No team detail found for club {settings.target_club_id}")

    with Repository(settings.database_url) as repository:
        run_id = repository.start_run(__version__, source_fingerprint, settings.data_as_of)
        try:
            profile_external_ids = [int(profile["player_id"]) for profile in profiles]
            existing_player_ids = repository.existing_player_external_ids(profile_external_ids)
            country_cache: dict[str, int] = {}
            club_cache: dict[int, int] = {}
            agent_cache: dict[int, int] = {}

            def country_id(name: str | None) -> int | None:
                cleaned = optional_text(name)
                if not cleaned:
                    return None
                if cleaned not in country_cache:
                    country_cache[cleaned] = repository.upsert_country(cleaned)
                return country_cache[cleaned]

            target_country_id = country_id(detail["country_name"])
            target_external_id = str(settings.target_club_id)
            target_profile_names = [
                profile[name_field]
                for profile in profiles
                for external_field, name_field in (
                    ("current_club_id", "current_club_name"),
                    ("on_loan_from_club_id", "on_loan_from_club_name"),
                )
                if profile[external_field] == target_external_id
            ]
            target_internal_id = repository.upsert_club(
                settings.target_club_id,
                resolve_club_name(
                    settings.target_club_id,
                    detail["club_name"],
                    target_profile_names,
                ),
                run_id,
                slug=optional_text(detail["club_slug"]),
                country_id=target_country_id,
                logo_url=optional_text(detail["logo_url"]),
                is_complete=True,
                data_as_of=settings.data_as_of,
            )
            club_cache[settings.target_club_id] = target_internal_id

            memberships_written = 0
            for profile in profiles:
                for external_field, name_field in (
                    ("current_club_id", "current_club_name"),
                    ("on_loan_from_club_id", "on_loan_from_club_name"),
                ):
                    reference = _club_reference(profile[external_field], profile[name_field])
                    if reference and reference[0] not in club_cache:
                        external_id, name = reference
                        club_cache[external_id] = repository.upsert_club(
                            external_id,
                            name,
                            run_id,
                            data_as_of=settings.data_as_of,
                        )

                birth_country_id = country_id(profile["country_of_birth"])
                player_id = repository.upsert_player(
                    {
                        "source_external_id": int(profile["player_id"]),
                        "slug": optional_text(profile["player_slug"]),
                        "display_name": clean_entity_name(profile["player_name"], profile["player_id"]),
                        "full_name": optional_text(profile["name_in_home_country"]),
                        "date_of_birth": optional_date(profile["date_of_birth"]),
                        "date_of_death": optional_date(profile["date_of_death"]),
                        "place_of_birth": optional_text(profile["place_of_birth"]),
                        "country_of_birth_id": birth_country_id,
                        "height_cm": optional_int(profile["height"], zero_is_null=True),
                        "preferred_foot": preferred_foot(profile["foot"]),
                        "career_status": career_status(profile["current_club_name"]),
                        "image_url": optional_text(profile["player_image_url"]),
                        "data_as_of": settings.data_as_of,
                        "source_etl_run_id": run_id,
                    }
                )

                citizenship_ids = [
                    country_id(name) for name in split_citizenships(profile["citizenship"])
                ]
                repository.replace_citizenships(
                    player_id, [value for value in citizenship_ids if value is not None], run_id
                )
                repository.replace_primary_position(
                    player_id, position_code(profile["position"]), run_id
                )

                agent_external_id = optional_int(profile["player_agent_id"])
                agent_name = optional_text(profile["player_agent_name"])
                agent_id = None
                if agent_external_id and agent_name:
                    if agent_external_id not in agent_cache:
                        agent_cache[agent_external_id] = repository.upsert_agent(
                            agent_external_id, agent_name, run_id
                        )
                    agent_id = agent_cache[agent_external_id]
                repository.replace_current_agent(player_id, agent_id, settings.data_as_of, run_id)

                memberships: list[dict[str, Any]] = []
                current_reference = _club_reference(
                    profile["current_club_id"], profile["current_club_name"]
                )
                owner_reference = _club_reference(
                    profile["on_loan_from_club_id"], profile["on_loan_from_club_name"]
                )
                if current_reference:
                    memberships.append(
                        {
                            "club_id": club_cache[current_reference[0]],
                            "membership_type": "LOAN" if owner_reference else "PERMANENT",
                            "start_date": optional_date(profile["joined"]),
                            "end_date": optional_date(profile["contract_expires"]),
                            "data_as_of": settings.data_as_of,
                        }
                    )
                if owner_reference:
                    memberships.append(
                        {
                            "club_id": club_cache[owner_reference[0]],
                            "membership_type": "PERMANENT",
                            "start_date": None,
                            "end_date": optional_date(profile["contract_there_expires"]),
                            "data_as_of": settings.data_as_of,
                        }
                    )
                repository.replace_profile_memberships(player_id, memberships, run_id)
                memberships_written += len(memberships)

            repository.record_file_result(
                run_id,
                "player_profiles.csv",
                source.file_fingerprint("profiles"),
                len(profiles),
                len(profiles) - len(existing_player_ids),
                len(existing_player_ids),
            )
            repository.finish_run(
                run_id,
                len(profiles),
                len(profiles) + len(club_cache) + memberships_written,
            )
            repository.commit()
        except Exception as error:
            repository.fail_run(run_id, error)
            raise

    return LoadSummary(
        run_id=run_id,
        players=len(profiles),
        clubs=len(club_cache),
        memberships=memberships_written,
    )
