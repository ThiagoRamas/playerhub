from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("PLAYERHUB_DATABASE_URL")
        if not database_url:
            raise ValueError("PLAYERHUB_DATABASE_URL is required")
        origins = tuple(
            value.strip()
            for value in os.environ.get(
                "PLAYERHUB_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
            ).split(",")
            if value.strip()
        )
        return cls(database_url=database_url, cors_origins=origins)


settings = Settings.from_environment()

