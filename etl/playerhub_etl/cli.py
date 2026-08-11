import argparse
import json

from .config import Settings
from .normalize import clean_entity_name
from .source import DatasetSource


COMMANDS = (
    "list-source-clubs",
    "load-club-snapshot",
    "load-player-history",
    "load-club-data",
    "load-country",
    "find-live-clubs",
    "sync-live-squad",
    "sync-live-country",
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("el identificador debe ser mayor que cero")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("el valor no puede ser negativo")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importador de datos de PlayerHub")
    parser.add_argument(
        "command",
        choices=COMMANDS,
        nargs="?",
        default="load-club-snapshot",
        help="Operación que se desea ejecutar.",
    )
    parser.add_argument(
        "--club-id",
        dest="club_ids",
        action="append",
        type=positive_int,
        help="ID externo del club. Puede repetirse para cargar varios clubes.",
    )
    parser.add_argument(
        "--search",
        help="Texto contenido en el nombre para buscar clubes disponibles.",
    )
    parser.add_argument(
        "--country",
        help="País exacto para filtrar clubes disponibles.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=20,
        help="Cantidad máxima de clubes a mostrar (por defecto: 20).",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=20,
        help="Clubes procesados juntos en cada lote (por defecto: 20).",
    )
    parser.add_argument(
        "--max-clubs",
        type=positive_int,
        help="Límite opcional de clubes para una carga de prueba.",
    )
    parser.add_argument(
        "--provider-team-id",
        type=positive_int,
        help="ID del club en API-Football cuando no puede identificarse automáticamente.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica la sincronización. Sin esta opción solo muestra diferencias.",
    )
    parser.add_argument(
        "--max-requests",
        type=positive_int,
        default=50,
        help="Límite local de consultas a API-Football (por defecto: 50).",
    )
    parser.add_argument(
        "--fresh-days",
        type=non_negative_int,
        default=7,
        help="Días durante los que un plantel se considera actualizado (por defecto: 7).",
    )
    return parser


def selected_club_ids(args: argparse.Namespace, settings: Settings) -> list[int]:
    return list(dict.fromkeys(args.club_ids or [settings.target_club_id]))


def summary_payload(club_id: int, summary: object) -> dict[str, object]:
    return {"club_id": club_id, **vars(summary)}


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_environment()
    if args.command == "find-live-clubs":
        if not args.search:
            parser = build_parser()
            parser.error("find-live-clubs requiere --search")
        from .live_squad import find_live_clubs

        print(
            json.dumps(
                find_live_clubs(settings, args.search, args.country),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "sync-live-squad":
        from .live_squad import sync_live_squad

        club_ids = selected_club_ids(args, settings)
        if args.provider_team_id and len(club_ids) != 1:
            parser = build_parser()
            parser.error("--provider-team-id solo puede usarse con un club")
        results = [
            sync_live_squad(
                settings.for_club(club_id),
                provider_team_id=args.provider_team_id,
                apply=args.apply,
            )
            for club_id in club_ids
        ]
        print(
            json.dumps(
                results[0] if len(results) == 1 else {"clubs": results},
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )
        return

    if args.command == "sync-live-country":
        if not args.country:
            parser = build_parser()
            parser.error("sync-live-country requiere --country")
        from .live_batch import sync_live_country

        result = sync_live_country(
            settings,
            args.country,
            search=args.search,
            max_clubs=args.max_clubs or 1,
            max_requests=args.max_requests,
            fresh_days=args.fresh_days,
            apply=args.apply,
            progress=lambda message: print(message, flush=True),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    if args.command == "list-source-clubs":
        source = DatasetSource(settings.dataset_root)
        clubs = source.available_clubs(args.search, args.country, args.limit)
        payload = [
            {
                **club,
                "club_name": clean_entity_name(str(club["club_name"]), int(club["club_id"])),
            }
            for club in clubs
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if args.command == "load-country":
        if not args.country:
            parser = build_parser()
            parser.error("load-country requiere --country")
        from .batch import country_summary_payload, load_country

        summary = load_country(
            settings,
            args.country,
            search=args.search,
            batch_size=args.batch_size,
            max_clubs=args.max_clubs,
            progress=lambda message: print(message, flush=True),
        )
        print(json.dumps(country_summary_payload(summary), indent=2, ensure_ascii=False))
        return

    club_ids = selected_club_ids(args, settings)
    from .history import load_player_history
    from .pipeline import load_club_snapshot

    results: list[dict[str, object]] = []
    for club_id in club_ids:
        club_settings = settings.for_club(club_id)
        if args.command == "load-club-snapshot":
            results.append(summary_payload(club_id, load_club_snapshot(club_settings)))
        elif args.command == "load-player-history":
            results.append(summary_payload(club_id, load_player_history(club_settings)))
        elif args.command == "load-club-data":
            snapshot = load_club_snapshot(club_settings)
            history = load_player_history(club_settings)
            results.append(
                {
                    "club_id": club_id,
                    "snapshot": vars(snapshot),
                    "history": vars(history),
                }
            )

    if len(results) == 1 and args.command != "load-club-data":
        legacy_payload = {key: value for key, value in results[0].items() if key != "club_id"}
        print(json.dumps(legacy_payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"clubs": results}, indent=2, ensure_ascii=False))
