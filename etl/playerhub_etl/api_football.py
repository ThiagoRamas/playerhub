from dataclasses import dataclass, replace
from datetime import date
import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import __version__


class ApiFootballError(RuntimeError):
    pass


class ApiFootballRequestBudgetExceeded(ApiFootballError):
    pass


@dataclass(frozen=True)
class LiveTeam:
    external_id: int
    name: str
    country: str | None
    logo_url: str | None


@dataclass(frozen=True)
class LivePlayer:
    external_id: int
    name: str
    age: int | None
    number: int | None
    position: str | None
    photo_url: str | None
    full_name: str | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = None
    country_of_birth: str | None = None
    nationality: str | None = None
    height_cm: int | None = None


@dataclass(frozen=True)
class LiveSquad:
    team: LiveTeam
    players: tuple[LivePlayer, ...]


OpenUrl = Callable[..., Any]


class ApiFootballClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://v3.football.api-sports.io",
        timeout_seconds: float = 20.0,
        min_request_interval_seconds: float = 0.0,
        max_request_count: int | None = None,
        opener: OpenUrl = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not api_key.strip():
            raise ValueError("API-Football key cannot be empty")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.min_request_interval_seconds = max(0.0, min_request_interval_seconds)
        if max_request_count is not None and max_request_count <= 0:
            raise ValueError("max_request_count must be greater than zero")
        self.max_request_count = max_request_count
        self.requests_made = 0
        self.opener = opener
        self.sleeper = sleeper
        self.clock = clock
        self._last_request_at: float | None = None

    def _wait_for_rate_slot(self) -> None:
        now = self.clock()
        if self._last_request_at is not None:
            wait_seconds = (
                self.min_request_interval_seconds - (now - self._last_request_at)
            )
            if wait_seconds > 0:
                self.sleeper(wait_seconds)
        self._last_request_at = self.clock()

    def _get(self, path: str, parameters: dict[str, str | int]) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}?{urlencode(parameters)}"
        request = Request(
            url,
            headers={
                "x-apisports-key": self.api_key,
                "Accept": "application/json",
                "User-Agent": f"PlayerHub-ETL/{__version__}",
            },
        )
        last_error: Exception | None = None
        for attempt in range(3):
            if (
                self.max_request_count is not None
                and self.requests_made >= self.max_request_count
            ):
                raise ApiFootballRequestBudgetExceeded(
                    "API-Football request budget exhausted before starting another request"
                )
            self._wait_for_rate_slot()
            self.requests_made += 1
            try:
                with self.opener(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                errors = payload.get("errors")
                if errors:
                    raise ApiFootballError(f"API-Football rejected the request: {errors}")
                if not isinstance(payload.get("response"), list):
                    raise ApiFootballError("API-Football returned an unexpected response")
                return payload
            except HTTPError as error:
                last_error = error
                if error.code != 429 and error.code < 500:
                    break
                if error.code == 429 and attempt < 2:
                    self.sleeper(float(15 * (2**attempt)))
                    self._last_request_at = None
                    continue
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
            if attempt < 2:
                self.sleeper(float(2**attempt))
        raise ApiFootballError(f"Could not query API-Football: {last_error}") from last_error

    @staticmethod
    def _team(item: dict[str, Any]) -> LiveTeam:
        team = item.get("team") or {}
        venue = item.get("venue") or {}
        return LiveTeam(
            external_id=int(team["id"]),
            name=str(team["name"]),
            country=team.get("country") or venue.get("country"),
            logo_url=team.get("logo"),
        )

    def search_teams(self, search: str, country: str | None = None) -> list[LiveTeam]:
        # API-Football rejects `search` and `country` when they are sent
        # together, so country filtering is intentionally performed locally.
        payload = self._get("teams", {"search": search})
        teams = [self._team(item) for item in payload["response"]]
        if not country:
            return teams
        expected_country = country.strip().casefold()
        return [
            team
            for team in teams
            if team.country and team.country.strip().casefold() == expected_country
        ]

    def get_team(self, team_id: int) -> LiveTeam:
        payload = self._get("teams", {"id": team_id})
        if len(payload["response"]) != 1:
            raise ApiFootballError(f"No unique API-Football team found for id {team_id}")
        return self._team(payload["response"][0])

    def get_squad(self, team_id: int) -> LiveSquad:
        payload = self._get("players/squads", {"team": team_id})
        if len(payload["response"]) != 1:
            raise ApiFootballError(f"No current squad found for API-Football team {team_id}")
        item = payload["response"][0]
        team = self._team({"team": item.get("team") or {}})
        players = tuple(
            LivePlayer(
                external_id=int(player["id"]),
                name=str(player["name"]),
                age=int(player["age"]) if player.get("age") is not None else None,
                number=int(player["number"]) if player.get("number") is not None else None,
                position=player.get("position"),
                photo_url=player.get("photo"),
            )
            for player in item.get("players") or []
        )
        if not players:
            raise ApiFootballError(f"API-Football returned an empty squad for team {team_id}")
        return LiveSquad(team=team, players=players)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _height_cm(value: Any) -> int | None:
        text = ApiFootballClient._optional_text(value)
        if not text:
            return None
        digits = "".join(character for character in text if character.isdigit())
        if not digits:
            return None
        height = int(digits)
        return height if 100 <= height <= 250 else None

    @staticmethod
    def _profile_player(item: dict[str, Any]) -> LivePlayer:
        player = item.get("player") or {}
        birth = player.get("birth") or {}
        first_name = ApiFootballClient._optional_text(player.get("firstname"))
        last_name = ApiFootballClient._optional_text(player.get("lastname"))
        full_name = " ".join(
            part for part in (first_name, last_name) if part
        ) or None
        birth_date = ApiFootballClient._optional_text(birth.get("date"))
        statistics = item.get("statistics") or []
        games = (statistics[0].get("games") or {}) if statistics else {}
        return LivePlayer(
            external_id=int(player["id"]),
            name=str(player.get("name") or full_name or player["id"]),
            age=int(player["age"]) if player.get("age") is not None else None,
            number=(
                int(player["number"])
                if player.get("number") is not None
                else None
            ),
            position=player.get("position") or games.get("position"),
            photo_url=player.get("photo"),
            full_name=full_name,
            date_of_birth=date.fromisoformat(birth_date) if birth_date else None,
            place_of_birth=ApiFootballClient._optional_text(birth.get("place")),
            country_of_birth=ApiFootballClient._optional_text(birth.get("country")),
            nationality=ApiFootballClient._optional_text(player.get("nationality")),
            height_cm=ApiFootballClient._height_cm(player.get("height")),
        )

    def get_player_profile(self, player_id: int) -> LivePlayer | None:
        payload = self._get("players/profiles", {"player": player_id})
        if not payload["response"]:
            return None
        if len(payload["response"]) != 1:
            raise ApiFootballError(
                f"No unique API-Football player profile found for id {player_id}"
            )
        return self._profile_player(payload["response"][0])

    def enrich_squad(
        self, squad: LiveSquad, player_ids: set[int] | None = None
    ) -> LiveSquad:
        selected_ids = player_ids or {player.external_id for player in squad.players}
        profiles = {
            player_id: profile
            for player_id in selected_ids
            if (profile := self.get_player_profile(player_id)) is not None
        }
        enriched: list[LivePlayer] = []
        for player in squad.players:
            profile = profiles.get(player.external_id)
            if profile is None:
                enriched.append(player)
                continue
            enriched.append(
                replace(
                    player,
                    age=profile.age or player.age,
                    position=profile.position or player.position,
                    photo_url=profile.photo_url or player.photo_url,
                    full_name=profile.full_name,
                    date_of_birth=profile.date_of_birth,
                    place_of_birth=profile.place_of_birth,
                    country_of_birth=profile.country_of_birth,
                    nationality=profile.nationality,
                    height_cm=profile.height_cm,
                )
            )
        return LiveSquad(team=squad.team, players=tuple(enriched))
