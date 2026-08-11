import unittest
from datetime import date

from playerhub_etl.api_football import LivePlayer
from playerhub_etl.live_squad import (
    LocalPlayer,
    compare_squads,
    normalized_club_name,
    relocated_player_ids,
)


def live(external_id: int, name: str, age: int | None = None) -> LivePlayer:
    return LivePlayer(external_id, name, age, None, None, None)


class LiveSquadComparisonTest(unittest.TestCase):
    def test_normalizes_common_club_prefixes(self) -> None:
        self.assertEqual(normalized_club_name("CA Independiente"), "independiente")
        self.assertEqual(normalized_club_name("Club Atlético Independiente"), "independiente")

    def test_compares_additions_returns_departures_and_preserved_loans(self) -> None:
        local = [
            LocalPlayer(1, "Rodrigo Rey", date_of_birth=date(1991, 3, 8), membership_type="PERMANENT"),
            LocalPlayer(2, "Jugador Cedido", membership_type="PERMANENT", loaned_out=True),
            LocalPlayer(3, "Jugador Saliente", membership_type="PERMANENT"),
            LocalPlayer(5, "Otro Cedido", membership_type="PERMANENT", loaned_out=True),
        ]
        all_players = [*local, LocalPlayer(4, "Refuerzo Existente")]
        incoming = (
            live(10, "R. Rey", 35),
            live(20, "Jugador Cedido"),
            live(30, "Jugador Nuevo"),
            live(40, "Refuerzo Existente"),
        )

        result = compare_squads(
            incoming,
            local,
            all_players,
            {20: 2},
            today=date(2026, 8, 3),
        )

        self.assertEqual([item.playerhub_player_id for item in result.unchanged], [1])
        self.assertEqual([item.playerhub_player_id for item in result.returning], [2])
        self.assertEqual(
            [item.playerhub_player_id for item in result.additions], [None, 4]
        )
        self.assertEqual(relocated_player_ids(result), {4})
        self.assertEqual([item.player_id for item in result.departures], [3])
        self.assertEqual([item.player_id for item in result.preserved_loaned_out], [5])

    def test_does_not_guess_between_ambiguous_names(self) -> None:
        candidates = [
            LocalPlayer(1, "Juan Pérez"),
            LocalPlayer(2, "Juan Perez"),
        ]
        result = compare_squads(
            (live(10, "Juan Perez"),),
            candidates,
            candidates,
            {},
            today=date(2026, 8, 3),
        )
        self.assertIsNone(result.incoming[0].playerhub_player_id)
        self.assertEqual(result.incoming[0].match_method, "ambiguous")

    def test_matches_unique_abbreviated_name_outside_current_club_by_age(self) -> None:
        existing_elsewhere = LocalPlayer(
            8,
            "Maximiliano Meza",
            date_of_birth=date(1992, 12, 15),
        )
        result = compare_squads(
            (live(35550, "M. Meza", 33),),
            [],
            [existing_elsewhere],
            {},
            today=date(2026, 8, 3),
        )
        self.assertEqual(result.incoming[0].playerhub_player_id, 8)
        self.assertEqual(result.incoming[0].match_method, "compatible_name")

    def test_rejects_abbreviated_global_match_with_incompatible_age(self) -> None:
        existing_elsewhere = LocalPlayer(
            8,
            "Maximiliano Meza",
            date_of_birth=date(1992, 12, 15),
        )
        result = compare_squads(
            (live(35550, "M. Meza", 21),),
            [],
            [existing_elsewhere],
            {},
            today=date(2026, 8, 3),
        )
        self.assertIsNone(result.incoming[0].playerhub_player_id)

    def test_uses_enriched_full_name_and_exact_birth_date(self) -> None:
        existing_elsewhere = LocalPlayer(
            8,
            "Gabriel Ávalos",
            date_of_birth=date(1990, 10, 12),
        )
        enriched = LivePlayer(
            6483,
            "G. Ávalos",
            35,
            None,
            "Attacker",
            None,
            full_name="Gabriel Ávalos",
            date_of_birth=date(1990, 10, 12),
            nationality="Paraguay",
        )
        result = compare_squads(
            (enriched,),
            [],
            [existing_elsewhere],
            {},
            today=date(2026, 8, 3),
        )
        self.assertEqual(result.incoming[0].playerhub_player_id, 8)
        self.assertEqual(result.incoming[0].match_method, "exact_name")


if __name__ == "__main__":
    unittest.main()
