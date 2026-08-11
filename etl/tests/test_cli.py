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

    def test_country_load_accepts_batch_and_test_limits(self) -> None:
        args = build_parser().parse_args(
            ["load-country", "--country", "Argentina", "--batch-size", "10", "--max-clubs", "3"]
        )
        self.assertEqual(args.country, "Argentina")
        self.assertEqual(args.batch_size, 10)
        self.assertEqual(args.max_clubs, 3)

    def test_live_squad_defaults_to_preview(self) -> None:
        args = build_parser().parse_args(
            ["sync-live-squad", "--club-id", "1234", "--provider-team-id", "99"]
        )
        self.assertFalse(args.apply)
        self.assertEqual(args.provider_team_id, 99)

    def test_live_squad_apply_is_explicit(self) -> None:
        args = build_parser().parse_args(["sync-live-squad", "--club-id", "1234", "--apply"])
        self.assertTrue(args.apply)

    def test_live_country_uses_safe_defaults(self) -> None:
        args = build_parser().parse_args(
            ["sync-live-country", "--country", "Argentina"]
        )
        self.assertFalse(args.apply)
        self.assertEqual(args.max_requests, 50)
        self.assertEqual(args.fresh_days, 7)

    def test_live_country_accepts_gradual_limits(self) -> None:
        args = build_parser().parse_args(
            [
                "sync-live-country",
                "--country",
                "Argentina",
                "--max-clubs",
                "2",
                "--max-requests",
                "40",
                "--fresh-days",
                "14",
                "--apply",
            ]
        )
        self.assertEqual(args.max_clubs, 2)
        self.assertEqual(args.max_requests, 40)
        self.assertEqual(args.fresh_days, 14)
        self.assertTrue(args.apply)


if __name__ == "__main__":
    unittest.main()
