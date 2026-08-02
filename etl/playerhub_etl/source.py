import csv
from collections import defaultdict
import hashlib
from pathlib import Path
from typing import Iterator


FILE_PATHS = {
    "profiles": "player_profiles/player_profiles.csv",
    "team_details": "team_details/team_details.csv",
    "performances": "player_performances/player_performances.csv",
    "market_values": "player_market_value/player_market_value.csv",
    "transfers": "transfer_history/transfer_history.csv",
    "injuries": "player_injuries/player_injuries.csv",
}


class DatasetSource:
    def __init__(self, root: Path):
        self.root = root

    def path_for(self, key: str) -> Path:
        path = self.root / FILE_PATHS[key]
        if not path.is_file():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        return path

    def rows(self, key: str) -> Iterator[dict[str, str]]:
        with self.path_for(key).open("r", encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)

    def fingerprint(self, keys: tuple[str, ...]) -> str:
        digest = hashlib.sha256()
        for key in keys:
            path = self.path_for(key)
            stat = path.stat()
            digest.update(f"{key}:{stat.st_size}:{stat.st_mtime_ns}\n".encode())
        return digest.hexdigest()

    def file_fingerprint(self, key: str) -> str:
        path = self.path_for(key)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def club_detail(self, external_id: int) -> dict[str, str] | None:
        target = str(external_id)
        return next((row for row in self.rows("team_details") if row["club_id"] == target), None)

    def club_details(self, external_ids: set[int]) -> dict[int, dict[str, str]]:
        return {
            club_id: row
            for row in self.rows("team_details")
            if (club_id := int(row["club_id"])) in external_ids
        }

    def club_snapshot_profiles(self, external_id: int) -> list[dict[str, str]]:
        target = str(external_id)
        return [
            row
            for row in self.rows("profiles")
            if row["current_club_id"] == target or row["on_loan_from_club_id"] == target
        ]

    def club_snapshot_profiles_by_club(
        self, external_ids: set[int]
    ) -> dict[int, list[dict[str, str]]]:
        profiles_by_club = {club_id: [] for club_id in external_ids}
        for row in self.rows("profiles"):
            referenced_clubs = {
                int(raw_id)
                for field in ("current_club_id", "on_loan_from_club_id")
                if (raw_id := row[field].strip()).isdigit()
            }
            for club_id in referenced_clubs & external_ids:
                profiles_by_club[club_id].append(row)
        return profiles_by_club

    def available_clubs(
        self,
        search: str | None = None,
        country: str | None = None,
        limit: int | None = 20,
    ) -> list[dict[str, str | int]]:
        players_by_club: dict[int, set[int]] = defaultdict(set)
        for row in self.rows("profiles"):
            player_id = int(row["player_id"])
            for field in ("current_club_id", "on_loan_from_club_id"):
                raw_club_id = row[field].strip()
                if raw_club_id.isdigit():
                    players_by_club[int(raw_club_id)].add(player_id)

        search_value = search.casefold().strip() if search else None
        country_value = country.casefold().strip() if country else None
        clubs: list[dict[str, str | int]] = []
        for row in self.rows("team_details"):
            club_id = int(row["club_id"])
            player_count = len(players_by_club.get(club_id, set()))
            if player_count == 0:
                continue
            if search_value and search_value not in row["club_name"].casefold():
                continue
            if country_value and country_value != row["country_name"].casefold():
                continue
            clubs.append(
                {
                    "club_id": club_id,
                    "club_name": row["club_name"],
                    "country_name": row["country_name"],
                    "players": player_count,
                }
            )

        clubs.sort(key=lambda club: (-int(club["players"]), str(club["club_name"])))
        return clubs if limit is None else clubs[:limit]

    def rows_for_players(self, key: str, player_ids: set[int]) -> Iterator[dict[str, str]]:
        for row in self.rows(key):
            if int(row["player_id"]) in player_ids:
                yield row
