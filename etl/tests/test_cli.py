import unittest
from datetime import date
from pathlib import Path

from playerhub_etl.cli import build_parser, selected_club_ids
from playerhub_etl.config import Settings


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            database_url="postgresql://example",
            dataset_root=Path("/data/raw"),
            data_as_of=date(2025, 9, 13),
            target_club_id=1234,
        )

    def test_uses_environment_club_when_no_override_is_provided(self) -> None:
        args = build_parser().parse_args(["load-club-snapshot"])
        self.assertEqual(selected_club_ids(args, self.settings), [1234])

    def test_accepts_and_deduplicates_multiple_clubs(self) -> None:
        args = build_parser().parse_args(
            ["load-club-data", "--club-id", "209", "--club-id", "189", "--club-id", "209"]
        )
        self.assertEqual(selected_club_ids(args, self.settings), [209, 189])

    def test_rejects_invalid_club_id(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["load-club-data", "--club-id", "0"])

    def test_catalog_filters_are_available(self) -> None:
        args = build_parser().parse_args(
            ["list-source-clubs", "--search", "River", "--country", "Argentina", "--limit", "5"]
        )
        self.assertEqual(args.search, "River")
        self.assertEqual(args.country, "Argentina")
        self.assertEqual(args.limit, 5)


if __name__ == "__main__":
    unittest.main()
