import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from playerhub_etl.api_football import ApiFootballError
from playerhub_etl.config import Settings
from playerhub_etl.live_batch import sync_live_country


class LiveBatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            database_url="postgresql://example",
            dataset_root=Path("/data/raw"),
            data_as_of=date(2025, 9, 13),
            target_club_id=1234,
            api_football_key="secret",
        )
        self.client = MagicMock(requests_made=12)

    @patch("playerhub_etl.live_batch.sync_live_squad")
    def test_selects_stale_clubs_and_reuses_one_client(
        self, syncer: MagicMock
    ) -> None:
        repository = MagicMock()
        repository.__enter__.return_value = repository
        repository.live_sync_candidates.return_value = [
            {"legacy_club_id": 1, "name": "Club Uno"},
            {"legacy_club_id": 2, "name": "Club Dos"},
        ]
        syncer.side_effect = [
            {"club": {"legacy_club_id": 1}, "safe_to_apply": True},
            {"club": {"legacy_club_id": 2}, "safe_to_apply": True},
        ]

        result = sync_live_country(
            self.settings,
            "Argentina",
            max_clubs=2,
            max_requests=40,
            fresh_days=7,
            client=self.client,
            today=date(2026, 8, 11),
            repository_factory=MagicMock(return_value=repository),
        )

        repository.live_sync_candidates.assert_called_once_with(
            "Argentina", date(2026, 8, 4), 2, None
        )
        self.assertEqual(syncer.call_count, 2)
        self.assertIs(syncer.call_args_list[0].kwargs["client"], self.client)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["requests_used"], 12)

    @patch("playerhub_etl.live_batch.sync_live_squad")
    def test_stops_after_a_provider_error(
        self, syncer: MagicMock
    ) -> None:
        repository = MagicMock()
        repository.__enter__.return_value = repository
        repository.live_sync_candidates.return_value = [
            {"legacy_club_id": 1, "name": "Club Uno"},
            {"legacy_club_id": 2, "name": "Club Dos"},
        ]
        syncer.side_effect = ApiFootballError("quota unavailable")

        result = sync_live_country(
            self.settings,
            "Argentina",
            max_clubs=2,
            client=self.client,
            today=date(2026, 8, 11),
            repository_factory=MagicMock(return_value=repository),
        )

        self.assertEqual(syncer.call_count, 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["stopped_reason"], "provider_error")


if __name__ == "__main__":
    unittest.main()
