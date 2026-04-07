from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/v0/system/health")

    assert response.status_code == 200
    body = response.json()
    assert body["payload"]["status"] == "ok"
