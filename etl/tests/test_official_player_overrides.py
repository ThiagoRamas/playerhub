import unittest

from playerhub_etl.api_football import LivePlayer, LiveSquad, LiveTeam
from playerhub_etl.official_player_overrides import (
    OFFICIAL_RESERVE_SQUAD_URL,
    apply_official_player_overrides,
    official_source_urls,
)


class OfficialPlayerOverridesTest(unittest.TestCase):
    def test_completes_missing_profile_from_official_club_source(self) -> None:
        squad = LiveSquad(
            LiveTeam(453, "Independiente", "Argentina", None),
            (LivePlayer(669570, "J. Arrayago", 17, None, "Defender", None),),
        )

        enriched, applied_ids = apply_official_player_overrides(squad)

        self.assertEqual(applied_ids, (669570,))
        self.assertEqual(enriched.players[0].full_name, "Juan Miguel Arrayago")
        self.assertEqual(
            enriched.players[0].date_of_birth.isoformat(), "2008-11-17"
        )
        self.assertEqual(
            official_source_urls(applied_ids), (OFFICIAL_RESERVE_SQUAD_URL,)
        )

    def test_preserves_unicode_in_official_override(self) -> None:
        squad = LiveSquad(
            LiveTeam(453, "Independiente", "Argentina", None),
            (LivePlayer(560351, "S. Bodnar", 18, None, "Midfielder", None),),
        )

        enriched, applied_ids = apply_official_player_overrides(squad)

        self.assertEqual(applied_ids, (560351,))
        self.assertEqual(enriched.players[0].full_name, "Sim\u00f3n Bodnar")
        self.assertEqual(
            enriched.players[0].date_of_birth.isoformat(), "2007-08-22"
        )


if __name__ == "__main__":
    unittest.main()
