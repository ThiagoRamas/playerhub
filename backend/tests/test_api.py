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
    assert client.get("/api/v1/clubs/999999999").status_code == 404
    assert client.get("/api/v1/players/999999999").status_code == 404
