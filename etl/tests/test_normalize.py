import unittest

from playerhub_etl.normalize import (
    career_status,
    clean_entity_name,
    optional_int,
    position_code,
    preferred_foot,
    split_citizenships,
)


class NormalizeTest(unittest.TestCase):
    def test_removes_only_matching_external_id_suffix(self) -> None:
        self.assertEqual(clean_entity_name("Miroslav Klose (10)", 10), "Miroslav Klose")
        self.assertEqual(clean_entity_name("Player (11)", 10), "Player (11)")

    def test_preserves_unicode(self) -> None:
        self.assertEqual(clean_entity_name("Nicolás Vallejo (1040204)", 1040204), "Nicolás Vallejo")

    def test_splits_multiple_citizenships(self) -> None:
        self.assertEqual(split_citizenships("Argentina  Italy"), ["Argentina", "Italy"])
        self.assertEqual(split_citizenships("Brazil"), ["Brazil"])

    def test_normalizes_zero_height_and_foot(self) -> None:
        self.assertIsNone(optional_int("0.0", zero_is_null=True))
        self.assertEqual(optional_int("180.0", zero_is_null=True), 180)
        self.assertEqual(preferred_foot("N/A"), "UNKNOWN")

    def test_maps_position_and_career_status(self) -> None:
        self.assertEqual(position_code("Attack - Right Winger"), "RIGHT_WINGER")
        self.assertEqual(career_status("Retired"), "RETIRED")
        self.assertEqual(career_status("CA Independiente"), "ACTIVE")
        self.assertEqual(career_status("Unknown"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
