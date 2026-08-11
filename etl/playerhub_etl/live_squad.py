from dataclasses import asdict, dataclass
from datetime import date
import re
import unicodedata
from typing import Any

from . import __version__
from .api_football import (
    ApiFootballClient,
    ApiFootballError,
    ApiFootballRequestBudgetExceeded,
    LivePlayer,
    LiveTeam,
)
from .config import Settings
from .normalize import fingerprint
from .official_player_overrides import (
    OFFICIAL_PLAYER_OVERRIDES,
    apply_official_player_overrides,
    official_source_urls,
)


SOURCE_CODE = "API_FOOTBALL"
POSITION_CODES = {
    "goalkeeper": "GOALKEEPER",
    "defender": "DEFENDER",
    "midfielder": "MIDFIELDER",
    "attacker": "ATTACKER",
}
CLUB_STOP_WORDS = {"ac", "ca", "club", "de", "fc", "football", "atletico", "athletic"}


@dataclass(frozen=True)
class LocalPlayer:
    player_id: int
    display_name: str
    full_name: str | None = None
    date_of_birth: date | None = None
    membership_type: str | None = None
    loaned_out: bool = False


@dataclass(frozen=True)
class PlayerComparison:
    provider_player_id: int
    provider_name: str
    provider_full_name: str | None
    provider_date_of_birth: date | None
    provider_nationality: str | None
    playerhub_player_id: int | None
    playerhub_name: str | None
    match_method: str
    membership_type: str
    was_loaned_out: bool


@dataclass(frozen=True)
class SquadComparison:
    incoming: tuple[PlayerComparison, ...]
    additions: tuple[PlayerComparison, ...]
    returning: tuple[PlayerComparison, ...]
    unchanged: tuple[PlayerComparison, ...]
    departures: tuple[LocalPlayer, ...]
    preserved_loaned_out: tuple[LocalPlayer, ...]


def normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def normalized_club_name(value: str) -> str:
    tokens = [token for token in normalized_text(value).split() if token not in CLUB_STOP_WORDS]
    return " ".join(tokens)


def _age_on(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _age_matches(candidate: LocalPlayer, live: LivePlayer, today: date) -> bool:
    if candidate.date_of_birth is not None and live.date_of_birth is not None:
        return candidate.date_of_birth == live.date_of_birth
    if candidate.date_of_birth is None or live.age is None:
        return True
    return abs(_age_on(candidate.date_of_birth, today) - live.age) <= 1


def _name_score(candidate: LocalPlayer, live: LivePlayer) -> int:
    live_variants = [live.name]
    if live.full_name:
        live_variants.append(live.full_name)
    local_variants = [candidate.display_name]
    if candidate.full_name:
        local_variants.append(candidate.full_name)
    best = 0
    for live_variant in live_variants:
        live_tokens = normalized_text(live_variant).split()
        for local_variant in local_variants:
            local_tokens = normalized_text(local_variant).split()
            if not live_tokens or not local_tokens:
                continue
            if live_tokens == local_tokens:
                best = max(best, 100)
            elif live_tokens[0] == local_tokens[0] and live_tokens[-1] == local_tokens[-1]:
                best = max(best, 95)
            elif (
                live_tokens[-1] == local_tokens[-1]
                and live_tokens[0][0] == local_tokens[0][0]
            ):
                best = max(best, 80)
    return best


def _unique_match(
    live: LivePlayer, candidates: list[LocalPlayer], today: date, minimum_score: int
) -> tuple[LocalPlayer | None, str]:
    scored = [
        (score, candidate)
        for candidate in candidates
        if _age_matches(candidate, live, today)
        if (score := _name_score(candidate, live)) >= minimum_score
    ]
    if not scored:
        return None, "none"
    highest = max(score for score, _ in scored)
    winners = [candidate for score, candidate in scored if score == highest]
    if len(winners) != 1:
        return None, "ambiguous"
    return winners[0], "exact_name" if highest == 100 else "compatible_name"


def compare_squads(
    live_players: tuple[LivePlayer, ...],
    local_members: list[LocalPlayer],
    all_players: list[LocalPlayer],
    provider_mappings: dict[int, int],
    *,
    today: date,
) -> SquadComparison:
    local_by_id = {player.player_id: player for player in local_members}
    all_by_id = {player.player_id: player for player in all_players}
    incoming: list[PlayerComparison] = []
    matched_local_ids: set[int] = set()

    for live in live_players:
        match: LocalPlayer | None = None
        method = "new_player"
        mapped_id = provider_mappings.get(live.external_id)
        if mapped_id is not None:
            match = all_by_id.get(mapped_id)
            method = "provider_id"
        if match is None:
            match, method = _unique_match(live, local_members, today, 80)
        if match is None and method != "ambiguous":
            # A player joining this club may already exist in PlayerHub under
            # another club. API-Football often abbreviates names ("M. Meza"),
            # so a unique initial/surname match with a compatible age can
            # reuse that entity. Ties always remain unmatched.
            match, method = _unique_match(live, all_players, today, 80)

        local_membership = local_by_id.get(match.player_id) if match else None
        if match:
            matched_local_ids.add(match.player_id)
        incoming.append(
            PlayerComparison(
                provider_player_id=live.external_id,
                provider_name=live.name,
                provider_full_name=live.full_name,
                provider_date_of_birth=live.date_of_birth,
                provider_nationality=live.nationality,
                playerhub_player_id=match.player_id if match else None,
                playerhub_name=match.display_name if match else None,
                match_method=method,
                membership_type=(
                    local_membership.membership_type
                    if local_membership and local_membership.membership_type
                    else "UNKNOWN"
                ),
                was_loaned_out=bool(local_membership and local_membership.loaned_out),
            )
        )

    additions = tuple(
        item for item in incoming if item.playerhub_player_id not in local_by_id
    )
    returning = tuple(item for item in incoming if item.was_loaned_out)
    unchanged = tuple(
        item
        for item in incoming
        if item.playerhub_player_id in local_by_id and not item.was_loaned_out
    )
    departures = tuple(
        player
        for player in local_members
        if not player.loaned_out and player.player_id not in matched_local_ids
    )
    preserved_loaned_out = tuple(
        player
        for player in local_members
        if player.loaned_out and player.player_id not in matched_local_ids
    )
    return SquadComparison(
        incoming=tuple(incoming),
        additions=additions,
        returning=returning,
        unchanged=unchanged,
        departures=departures,
        preserved_loaned_out=preserved_loaned_out,
    )


def relocated_player_ids(comparison: SquadComparison) -> set[int]:
    return {
        item.playerhub_player_id
        for item in comparison.additions
        if item.playerhub_player_id is not None
    }


def _local_player(row: dict[str, Any]) -> LocalPlayer:
    return LocalPlayer(
        player_id=int(row["id"]),
        display_name=str(row["display_name"]),
        full_name=row.get("full_name"),
        date_of_birth=row.get("date_of_birth"),
        membership_type=row.get("membership_type"),
        loaned_out=bool(row.get("loaned_out", False)),
    )


def _team_payload(team: LiveTeam) -> dict[str, Any]:
    return {
        "provider_team_id": team.external_id,
        "name": team.name,
        "country": team.country,
        "logo_url": team.logo_url,
    }


def _comparison_payload(comparison: SquadComparison) -> dict[str, Any]:
    return {
        "counts": {
            "incoming": len(comparison.incoming),
            "additions": len(comparison.additions),
            "returning": len(comparison.returning),
            "unchanged": len(comparison.unchanged),
            "departures": len(comparison.departures),
            "relocated_from_other_clubs": len(relocated_player_ids(comparison)),
            "loaned_out_preserved": len(comparison.preserved_loaned_out),
        },
        "additions": [asdict(item) for item in comparison.additions],
        "returning": [asdict(item) for item in comparison.returning],
        "departures": [asdict(item) for item in comparison.departures],
        "loaned_out_preserved": [
            asdict(item) for item in comparison.preserved_loaned_out
        ],
    }


def _resolve_team(
    client: ApiFootballClient,
    club: dict[str, Any],
    mapped_team_id: str | None,
    requested_team_id: int | None,
) -> LiveTeam:
    if requested_team_id is not None:
        return client.get_team(requested_team_id)
    if mapped_team_id is not None:
        return client.get_team(int(mapped_team_id))
    expected = normalized_club_name(str(club["name"]))
    teams = client.search_teams(expected, club.get("country"))
    exact = [team for team in teams if normalized_club_name(team.name) == expected]
    if len(exact) == 1:
        return exact[0]
    candidates = ", ".join(f"{team.name} ({team.external_id})" for team in teams) or "none"
    raise ValueError(
        "Could not safely identify the club in API-Football. "
        f"Candidates: {candidates}. Run find-live-clubs and pass --provider-team-id."
    )


def find_live_clubs(
    settings: Settings, search: str, country: str | None = None
) -> list[dict[str, Any]]:
    client = ApiFootballClient(
        settings.require_api_football_key(),
        base_url=settings.api_football_base_url,
        timeout_seconds=settings.api_football_timeout_seconds,
        min_request_interval_seconds=settings.api_football_min_interval_seconds,
    )
    return [_team_payload(team) for team in client.search_teams(search, country)]


def sync_live_squad(
    settings: Settings,
    *,
    provider_team_id: int | None = None,
    apply: bool = False,
    client: ApiFootballClient | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    from .repository import Repository

    today = today or date.today()
    client = client or ApiFootballClient(
        settings.require_api_football_key(),
        base_url=settings.api_football_base_url,
        timeout_seconds=settings.api_football_timeout_seconds,
        min_request_interval_seconds=settings.api_football_min_interval_seconds,
    )

    with Repository(settings.database_url) as repository:
        club = repository.club_by_legacy_external_id(settings.target_club_id)
        if club is None:
            raise ValueError(
                f"Club {settings.target_club_id} is not loaded in PlayerHub"
            )
        mapped_team_id = repository.source_external_id(
            "club", int(club["id"]), SOURCE_CODE
        )
        team = _resolve_team(client, club, mapped_team_id, provider_team_id)
        squad = client.get_squad(team.external_id)

        local_rows = repository.current_club_players(int(club["id"]))
        local_members = [_local_player(row) for row in local_rows]
        all_players = [
            _local_player(row) for row in repository.player_name_candidates()
        ]
        provider_mappings = repository.provider_player_mappings(
            SOURCE_CODE, [player.external_id for player in squad.players]
        )
        comparison = compare_squads(
            squad.players,
            local_members,
            all_players,
            provider_mappings,
            today=today,
        )
        profile_ids = {
            item.provider_player_id
            for item in (*comparison.additions, *comparison.returning)
        }
        enrichment_warning: str | None = None
        try:
            squad = client.enrich_squad(squad, profile_ids)
        except ApiFootballRequestBudgetExceeded:
            raise
        except ApiFootballError as error:
            # The current squad is still useful when the provider limits its
            # optional profile endpoint. Preview remains available and apply
            # is blocked below if a new entity would only have an abbreviation.
            enrichment_warning = str(error)
        api_enriched_profiles = sum(
            1
            for player in squad.players
            if player.external_id in profile_ids and player.full_name
        )
        squad, official_override_ids = apply_official_player_overrides(squad)
        official_sources = official_source_urls(official_override_ids)
        comparison = compare_squads(
            squad.players,
            local_members,
            all_players,
            provider_mappings,
            today=today,
        )
        enriched_profiles = sum(
            1
            for player in squad.players
            if player.external_id in profile_ids and player.full_name
        )
        unsafe_new_players = [
            item
            for item in comparison.additions
            if item.playerhub_player_id is None
            and (not item.provider_full_name or item.match_method == "ambiguous")
        ]
        payload: dict[str, Any] = {
            "mode": "apply" if apply else "preview",
            "club": {
                "playerhub_club_id": int(club["id"]),
                "legacy_club_id": settings.target_club_id,
                "name": club["name"],
            },
            "provider_team": _team_payload(team),
            "data_as_of": today.isoformat(),
            "profile_enrichment": {
                "requested": len(profile_ids),
                "completed": enriched_profiles,
                "api_completed": api_enriched_profiles,
                "official_completed": len(official_override_ids),
                "official_override_ids": list(official_override_ids),
                "official_sources": list(official_sources),
                "warning": enrichment_warning,
            },
            "safe_to_apply": not unsafe_new_players,
            "unsafe_new_player_ids": [
                item.provider_player_id for item in unsafe_new_players
            ],
            **_comparison_payload(comparison),
        }
        if not apply:
            return payload
        if unsafe_new_players:
            raise ValueError(
                "Apply blocked: some new players still only have abbreviated "
                "or ambiguous names. Run preview again when profile enrichment "
                "is available."
            )

        source_payload = {
            "team": _team_payload(team),
            "official_profile_sources": list(official_sources),
            "players": [
                {
                    **asdict(player),
                    "date_of_birth": (
                        player.date_of_birth.isoformat() if player.date_of_birth else None
                    ),
                }
                for player in squad.players
            ],
        }
        source_fingerprint = fingerprint(source_payload)
        run_id = repository.start_run(
            f"{__version__}+api-football", source_fingerprint, today
        )
        try:
            repository.bind_source_identifier(
                "club", int(club["id"]), SOURCE_CODE, str(team.external_id), run_id
            )
            repository.touch_live_club(
                int(club["id"]), team.logo_url, today, run_id
            )

            local_members_by_id = {player.player_id: player for player in local_members}
            assigned_ids: dict[int, int] = {}
            inserted_players = 0
            country_cache: dict[str, int] = {}

            def country_id(name: str | None) -> int | None:
                if not name:
                    return None
                cleaned = name.strip()
                if not cleaned:
                    return None
                if cleaned not in country_cache:
                    country_cache[cleaned] = repository.upsert_country(cleaned)
                return country_cache[cleaned]

            for item, live_player in zip(comparison.incoming, squad.players, strict=True):
                player_id = item.playerhub_player_id
                birth_country_id = country_id(live_player.country_of_birth)
                if player_id is None:
                    player_id = repository.insert_live_player(
                        live_player.full_name or live_player.name,
                        live_player.full_name,
                        live_player.date_of_birth,
                        live_player.place_of_birth,
                        birth_country_id,
                        live_player.height_cm,
                        live_player.photo_url,
                        today,
                        run_id,
                    )
                    inserted_players += 1
                else:
                    repository.touch_live_player(
                        player_id,
                        live_player.full_name,
                        live_player.date_of_birth,
                        live_player.place_of_birth,
                        birth_country_id,
                        live_player.height_cm,
                        live_player.photo_url,
                        today,
                        run_id,
                    )
                nationality_id = country_id(live_player.nationality)
                if nationality_id is not None:
                    repository.add_citizenship(player_id, nationality_id, run_id)
                repository.bind_source_identifier(
                    "player",
                    player_id,
                    SOURCE_CODE,
                    str(live_player.external_id),
                    run_id,
                )
                repository.set_primary_position_if_missing(
                    player_id,
                    POSITION_CODES.get((live_player.position or "").lower()),
                    run_id,
                )
                assigned_ids[live_player.external_id] = player_id

            active_local_ids = {
                player.player_id for player in local_members if not player.loaned_out
            }
            returning_ids = {
                item.playerhub_player_id
                for item in comparison.returning
                if item.playerhub_player_id is not None
            }
            relocated_ids = relocated_player_ids(comparison)
            repository.deactivate_target_memberships(
                int(club["id"]), active_local_ids | returning_ids, today, run_id
            )
            repository.deactivate_other_current_loans(
                int(club["id"]), returning_ids, today, run_id
            )
            repository.deactivate_other_current_memberships(
                int(club["id"]), relocated_ids, today, run_id
            )

            for item, live_player in zip(comparison.incoming, squad.players, strict=True):
                player_id = assigned_ids[live_player.external_id]
                previous = local_members_by_id.get(player_id)
                membership_type = (
                    previous.membership_type
                    if previous and previous.membership_type in {"PERMANENT", "LOAN"}
                    else "UNKNOWN"
                )
                squad_number = live_player.number
                if squad_number is not None and not 1 <= squad_number <= 99:
                    squad_number = None
                repository.upsert_live_membership(
                    player_id,
                    int(club["id"]),
                    membership_type,
                    squad_number,
                    today,
                    run_id,
                )

            repository.record_file_result(
                run_id,
                f"api-football/players/squads/{team.external_id}",
                source_fingerprint,
                len(squad.players),
                inserted_players,
                len(squad.players) - inserted_players,
            )
            for source_url in official_sources:
                source_player_ids = sorted(
                    player_id
                    for player_id in official_override_ids
                    if OFFICIAL_PLAYER_OVERRIDES[player_id].source_url == source_url
                )
                repository.record_file_result(
                    run_id,
                    source_url,
                    fingerprint({"url": source_url, "player_ids": source_player_ids}),
                    len(source_player_ids),
                    0,
                    len(source_player_ids),
                )
            repository.finish_run(
                run_id,
                len(squad.players),
                len(squad.players) + len(comparison.departures),
            )
            repository.commit()
        except Exception as error:
            repository.fail_run(run_id, error)
            raise

        payload["run_id"] = run_id
        return payload
