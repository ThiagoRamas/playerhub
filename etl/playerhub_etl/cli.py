import argparse
import json

from .config import Settings
from .history import load_player_history
from .pipeline import load_club_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PlayerHub ETL")
    parser.add_argument(
        "command",
        choices=("load-club-snapshot", "load-player-history"),
        nargs="?",
        default="load-club-snapshot",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_environment()
    if args.command == "load-club-snapshot":
        summary = load_club_snapshot(settings)
        print(json.dumps(summary.__dict__, indent=2))
    elif args.command == "load-player-history":
        summary = load_player_history(settings)
        print(json.dumps(summary.__dict__, indent=2))
