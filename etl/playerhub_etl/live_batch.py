from datetime import date, timedelta
from typing import Any, Callable

from .api_football import (
    ApiFootballClient,
    ApiFootballError,
    ApiFootballRequestBudgetExceeded,
)
from .config import Settings
from .live_squad import sync_live_squad


Progress = Callable[[str], None]


def sync_live_country(
    settings: Settings,
    country: str,
    *,
    search: str | None = None,
    max_clubs: int = 1,
    max_requests: int = 50,
    fresh_days: int = 7,
    apply: bool = False,
    client: ApiFootballClient | None = None,
    today: date | None = None,
    progress: Progress | None = None,
    repository_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    if max_clubs <= 0:
        raise ValueError("max_clubs must be greater than zero")
    if max_requests <= 0:
        raise ValueError("max_requests must be greater than zero")
    if fresh_days < 0:
        raise ValueError("fresh_days cannot be negative")

    today = today or date.today()
    stale_before = today - timedelta(days=fresh_days)
    progress = progress or (lambda _message: None)
    if repository_factory is None:
        from .repository import Repository

        repository_factory = Repository

    with repository_factory(settings.database_url) as repository:
        candidates = repository.live_sync_candidates(
            country,
            stale_before,
            max_clubs,
            search,
        )

    client = client or ApiFootballClient(
        settings.require_api_football_key(),
        base_url=settings.api_football_base_url,
        timeout_seconds=settings.api_football_timeout_seconds,
        min_request_interval_seconds=settings.api_football_min_interval_seconds,
        max_request_count=max_requests,
    )

    completed: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    stopped_reason: str | None = None

    for candidate in candidates:
        legacy_club_id = int(candidate["legacy_club_id"])
        progress(
            f"Procesando {candidate['name']} ({legacy_club_id}) "
            f"en modo {'aplicación' if apply else 'vista previa'}"
        )
        try:
            result = sync_live_squad(
                settings.for_club(legacy_club_id),
                apply=apply,
                client=client,
                today=today,
            )
        except ApiFootballRequestBudgetExceeded as error:
            failed.append(
                {
                    "legacy_club_id": legacy_club_id,
                    "name": candidate["name"],
                    "error": str(error),
                }
            )
            stopped_reason = "request_budget_exhausted"
            progress("Se alcanzó el límite local de consultas; el lote se detuvo.")
            break
        except ApiFootballError as error:
            failed.append(
                {
                    "legacy_club_id": legacy_club_id,
                    "name": candidate["name"],
                    "error": str(error),
                }
            )
            stopped_reason = "provider_error"
            progress("El proveedor rechazó una consulta; el lote se detuvo.")
            break
        except ValueError as error:
            failed.append(
                {
                    "legacy_club_id": legacy_club_id,
                    "name": candidate["name"],
                    "error": str(error),
                }
            )
            progress(f"No se pudo sincronizar {candidate['name']}; se continúa.")
            continue

        completed.append(result)
        progress(f"{candidate['name']} completado de forma segura.")

    requests_used = getattr(client, "requests_made", 0)
    return {
        "mode": "apply" if apply else "preview",
        "country": country,
        "data_as_of": today.isoformat(),
        "fresh_days": fresh_days,
        "stale_before": stale_before.isoformat(),
        "max_clubs": max_clubs,
        "max_requests": max_requests,
        "requests_used": requests_used,
        "selected": len(candidates),
        "attempted": len(completed) + len(failed),
        "completed": len(completed),
        "failed": len(failed),
        "stopped_reason": stopped_reason,
        "clubs": completed,
        "errors": failed,
    }
