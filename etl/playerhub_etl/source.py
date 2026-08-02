import csv
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

    def club_snapshot_profiles(self, external_id: int) -> list[dict[str, str]]:
        target = str(external_id)
        return [
            row
            for row in self.rows("profiles")
            if row["current_club_id"] == target or row["on_loan_from_club_id"] == target
        ]

    def rows_for_players(self, key: str, player_ids: set[int]) -> Iterator[dict[str, str]]:
        for row in self.rows(key):
            if int(row["player_id"]) in player_ids:
                yield row
