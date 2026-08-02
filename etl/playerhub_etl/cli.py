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
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("el identificador debe ser mayor que cero")
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
    return parser


def selected_club_ids(args: argparse.Namespace, settings: Settings) -> list[int]:
    return list(dict.fromkeys(args.club_ids or [settings.target_club_id]))


def summary_payload(club_id: int, summary: object) -> dict[str, object]:
    return {"club_id": club_id, **vars(summary)}


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_environment()
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
