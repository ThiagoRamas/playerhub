from dataclasses import dataclass, replace
from datetime import date
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    dataset_root: Path
    data_as_of: date
    target_club_id: int
    api_football_key: str | None = None
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_timeout_seconds: float = 20.0
    api_football_min_interval_seconds: float = 6.5

    def for_club(self, club_id: int) -> "Settings":
        if club_id <= 0:
            raise ValueError("Club ID must be a positive integer")
        return replace(self, target_club_id=club_id)

    def require_api_football_key(self) -> str:
        if not self.api_football_key:
            raise ValueError(
                "API_FOOTBALL_KEY is required. Add it to the local .env file; "
                "do not paste it into commands or commit it to Git."
            )
        return self.api_football_key

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("PLAYERHUB_DATABASE_URL")
        if not database_url:
            raise ValueError("PLAYERHUB_DATABASE_URL is required")

        dataset_root = Path(os.environ.get("PLAYERHUB_DATASET_ROOT", "/data/raw"))
        data_as_of = date.fromisoformat(
            os.environ.get("PLAYERHUB_DATA_AS_OF", "2025-09-13")
        )
        target_club_id = int(os.environ.get("PLAYERHUB_TARGET_CLUB_ID", "1234"))
        api_football_key = os.environ.get("API_FOOTBALL_KEY") or None
        api_football_base_url = os.environ.get(
            "API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io"
        ).rstrip("/")
        api_football_timeout_seconds = float(
            os.environ.get("API_FOOTBALL_TIMEOUT_SECONDS", "20")
        )
        api_football_min_interval_seconds = float(
            os.environ.get("API_FOOTBALL_MIN_INTERVAL_SECONDS", "6.5")
        )

        return cls(
            database_url=database_url,
            dataset_root=dataset_root,
            data_as_of=data_as_of,
            target_club_id=target_club_id,
            api_football_key=api_football_key,
            api_football_base_url=api_football_base_url,
            api_football_timeout_seconds=api_football_timeout_seconds,
            api_football_min_interval_seconds=api_football_min_interval_seconds,
        )
