import json
import unittest

from playerhub_etl.api_football import ApiFootballClient


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class ApiFootballClientTest(unittest.TestCase):
    def test_parses_team_search_without_exposing_key_in_url(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["key"] = request.headers["X-apisports-key"]
            captured["timeout"] = timeout
            return FakeResponse(
                {
                    "errors": [],
                    "response": [
                        {
                            "team": {
                                "id": 123,
                                "name": "Independiente",
                                "country": "Argentina",
                                "logo": "https://example.test/logo.png",
                            },
                            "venue": {},
                        },
                        {
                            "team": {
                                "id": 999,
                                "name": "Independiente FC",
                                "country": "Colombia",
                                "logo": None,
                            },
                            "venue": {},
                        },
                    ],
                }
            )

        client = ApiFootballClient("secret", opener=opener)
        teams = client.search_teams("Independiente", "Argentina")

        self.assertEqual(teams[0].external_id, 123)
        self.assertEqual(teams[0].name, "Independiente")
        self.assertEqual(len(teams), 1)
        self.assertNotIn("country=", captured["url"])
        self.assertNotIn("secret", captured["url"])
        self.assertEqual(captured["key"], "secret")
        self.assertEqual(captured["timeout"], 20.0)

    def test_parses_current_squad(self) -> None:
        def opener(request, timeout):
            return FakeResponse(
                {
                    "errors": [],
                    "response": [
                        {
                            "team": {"id": 123, "name": "Independiente", "logo": None},
                            "players": [
                                {
                                    "id": 45,
                                    "name": "R. Rey",
                                    "age": 34,
                                    "number": 33,
                                    "position": "Goalkeeper",
                                    "photo": "https://example.test/player.png",
                                }
                            ],
                        }
                    ],
                }
            )

        squad = ApiFootballClient("secret", opener=opener).get_squad(123)

        self.assertEqual(squad.team.external_id, 123)
        self.assertEqual(squad.players[0].external_id, 45)
        self.assertEqual(squad.players[0].position, "Goalkeeper")

    def test_loads_profile_without_requiring_a_season(self) -> None:
        requested_urls = []

        def opener(request, timeout):
            requested_urls.append(request.full_url)
            return FakeResponse(
                {
                    "errors": [],
                    "response": [
                        {
                            "player": {
                                "id": 45,
                                "name": "M. Meza",
                                "firstname": "Maximiliano",
                                "lastname": "Meza",
                                "age": 33,
                                "birth": {
                                    "date": "1992-12-15",
                                    "place": "General Paz",
                                    "country": "Argentina",
                                },
                                "nationality": "Argentina",
                                "height": "180 cm",
                                "number": 8,
                                "position": "Midfielder",
                                "photo": "https://example.test/player.png",
                            }
                        }
                    ],
                }
            )

        profile = ApiFootballClient("secret", opener=opener).get_player_profile(45)

        self.assertEqual(len(requested_urls), 1)
        self.assertIn("players/profiles?player=45", requested_urls[0])
        self.assertEqual(profile.full_name, "Maximiliano Meza")
        self.assertEqual(profile.date_of_birth.isoformat(), "1992-12-15")
        self.assertEqual(profile.nationality, "Argentina")
        self.assertEqual(profile.height_cm, 180)
        self.assertEqual(profile.position, "Midfielder")


if __name__ == "__main__":
    unittest.main()
