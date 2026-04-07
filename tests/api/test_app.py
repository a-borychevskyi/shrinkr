from fastapi import FastAPI
from httpx import AsyncClient

from src.api.app import create_app


class TestAppFactory:
    def test_create_app_returns_fastapi_instance(self):
        app = create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "URL Shortener API"
        assert app.version == "0.1.0"

    def test_app_has_docs_urls(self):
        app = create_app()

        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_app_includes_routes(self):
        app = create_app()
        paths = [route.path for route in app.routes]

        assert "/v0/system/health" in paths
        assert "/v0/shortner/" in paths


class TestExceptionHandlers:
    async def test_http_404_returns_json(self, client: AsyncClient):
        response = await client.get("/nonexistent-path")

        assert response.status_code == 404
        body = response.json()
        assert body["errors"][0]["type"] == "NOT_FOUND"

    async def test_http_404_includes_error_class(self, client: AsyncClient):
        response = await client.get("/nonexistent-path")

        body = response.json()
        assert "errorClass" in body["errors"][0]

    async def test_validation_error_has_field_name(self, client: AsyncClient):
        response = await client.post(
            "/v0/shortner/", json={"target_url": 12345}
        )

        assert response.status_code == 422
        body = response.json()
        assert any(e.get("field") == "target_url" for e in body["errors"])

    async def test_validation_error_multiple_fields(self, client: AsyncClient):
        response = await client.post("/v0/shortner/", json={})

        assert response.status_code == 422
        body = response.json()
        assert len(body["errors"]) >= 1
