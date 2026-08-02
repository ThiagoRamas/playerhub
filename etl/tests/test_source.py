import csv
import tempfile
import unittest
from pathlib import Path

from playerhub_etl.source import DatasetSource, FILE_PATHS


class SourceCatalogTest(unittest.TestCase):
    def write_rows(self, root: Path, key: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path = root / FILE_PATHS[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_lists_only_clubs_with_snapshot_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_rows(
                root,
                "profiles",
                ["player_id", "current_club_id", "on_loan_from_club_id"],
                [
                    {"player_id": "1", "current_club_id": "209", "on_loan_from_club_id": ""},
                    {"player_id": "2", "current_club_id": "209", "on_loan_from_club_id": "189"},
                    {"player_id": "3", "current_club_id": "189", "on_loan_from_club_id": ""},
                ],
            )
            self.write_rows(
                root,
                "team_details",
                ["club_id", "club_name", "country_name"],
                [
                    {"club_id": "209", "club_name": "CA River Plate (209)", "country_name": "Argentina"},
                    {"club_id": "189", "club_name": "CA Boca Juniors (189)", "country_name": "Argentina"},
                    {"club_id": "999", "club_name": "Club sin perfiles (999)", "country_name": "Argentina"},
                ],
            )

            clubs = DatasetSource(root).available_clubs(country="argentina")

            self.assertEqual([club["club_id"] for club in clubs], [189, 209])
            self.assertEqual([club["players"] for club in clubs], [2, 2])
            self.assertNotIn(999, [club["club_id"] for club in clubs])

    def test_filters_catalog_by_name_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_rows(
                root,
                "profiles",
                ["player_id", "current_club_id", "on_loan_from_club_id"],
                [{"player_id": "1", "current_club_id": "209", "on_loan_from_club_id": ""}],
            )
            self.write_rows(
                root,
                "team_details",
                ["club_id", "club_name", "country_name"],
                [{"club_id": "209", "club_name": "CA River Plate (209)", "country_name": "Argentina"}],
            )

            clubs = DatasetSource(root).available_clubs(search="river", limit=1)

            self.assertEqual(len(clubs), 1)
            self.assertEqual(clubs[0]["club_id"], 209)


if __name__ == "__main__":
    unittest.main()
