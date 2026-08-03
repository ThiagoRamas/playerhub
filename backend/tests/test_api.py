import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_independiente_vertical_slice(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "ok"}

    clubs = client.get("/api/v1/clubs", params={"search": "Independiente"})
    assert clubs.status_code == 200
    independiente = next(club for club in clubs.json() if club["name"] == "CA Independiente")

    detail = client.get(f"/api/v1/clubs/{independiente['id']}")
    assert detail.status_code == 200
    assert detail.json()["linked_players"] == 23

    squad = client.get(f"/api/v1/clubs/{independiente['id']}/squad")
    assert squad.status_code == 200
    members = squad.json()
    assert len(members) == 23
    assert sum(member["squad_status"] == "SQUAD" for member in members) == 12
    assert sum(member["squad_status"] == "ON_LOAN" for member in members) == 2
    assert sum(member["squad_status"] == "LOANED_OUT" for member in members) == 9

    player_id = members[0]["id"]
    assert client.get(f"/api/v1/players/{player_id}").status_code == 200
    assert client.get(f"/api/v1/players/{player_id}/performances").status_code == 200
    assert client.get(f"/api/v1/players/{player_id}/market-values").status_code == 200
    assert client.get(f"/api/v1/players/{player_id}/transfers").status_code == 200
    assert client.get(f"/api/v1/players/{player_id}/injuries").status_code == 200


def test_missing_entities_return_404(client: TestClient) -> None:
    missing_club = client.get("/api/v1/clubs/999999999")
    missing_player = client.get("/api/v1/players/999999999")

    assert missing_club.status_code == 404
    assert missing_club.json() == {"detail": "Club no encontrado"}
    assert missing_player.status_code == 404
    assert missing_player.json() == {"detail": "Jugador no encontrado"}


def test_lists_argentine_clubs_without_requiring_a_search(client: TestClient) -> None:
    response = client.get(
        "/api/v1/clubs",
        params={"country": "Argentina", "limit": 100},
    )

    assert response.status_code == 200
    clubs = response.json()
    assert len(clubs) > 1
    assert all(club["country"] == "Argentina" for club in clubs)
    assert clubs == sorted(clubs, key=lambda club: club["name"])


def test_searches_players_by_name(client: TestClient) -> None:
    clubs = client.get("/api/v1/clubs", params={"search": "Independiente"}).json()
    independiente = next(club for club in clubs if club["name"] == "CA Independiente")
    member = client.get(f"/api/v1/clubs/{independiente['id']}/squad").json()[0]

    response = client.get(
        "/api/v1/players",
        params={"search": member["display_name"], "limit": 20},
    )

    assert response.status_code == 200
    result = next(player for player in response.json() if player["id"] == member["id"])
    assert result["display_name"] == member["display_name"]
    assert "CA Independiente" in result["current_clubs"]
    assert "citizenships" in result


def test_reports_current_data_coverage(client: TestClient) -> None:
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["clubs"] >= 81
    assert stats["players"] >= 1091
    assert stats["performances"] > stats["players"]
    assert stats["market_values"] > 0
    assert stats["transfers"] > 0
    assert stats["injuries"] > 0
    assert stats["data_as_of"] is not None


def test_openapi_uses_spanish_product_language(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "API de PlayerHub"
    assert schema["paths"]["/api/v1/clubs"]["get"]["summary"] == "Listar o buscar clubes"
    assert schema["paths"]["/api/v1/players"]["get"]["summary"] == "Buscar jugadores"
    assert schema["paths"]["/api/v1/stats"]["get"]["summary"] == "Ver cobertura de datos"
    assert schema["paths"]["/api/v1/players/{player_id}/injuries"]["get"]["summary"] == "Ver lesiones"
