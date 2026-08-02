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

    def for_club(self, club_id: int) -> "Settings":
        if club_id <= 0:
            raise ValueError("Club ID must be a positive integer")
        return replace(self, target_club_id=club_id)

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

        return cls(
            database_url=database_url,
            dataset_root=dataset_root,
            data_as_of=data_as_of,
            target_club_id=target_club_id,
        )
