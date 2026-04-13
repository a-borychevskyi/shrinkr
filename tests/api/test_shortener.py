from datetime import datetime, UTC
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import AsyncClient

from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.di.services.url_stats import get_url_stats_service
from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.models.url_stats.entity import UrlStatsModel
from src.kafka.schema import ClickEvent
from src.utils.exceptions.base import NotFound


SAMPLE_URL = UrlModel(
    id=1,
    target_url="https://example.com",
    short_code="abc123",
    created_at=datetime(2026, 1, 1, tzinfo=UTC),
    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    deleted_at=None,
)

SAMPLE_STATS = [
    UrlStatsModel(
        id=1,
        url_id=1,
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        access_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    ),
    UrlStatsModel(
        id=2,
        url_id=1,
        user_agent="curl/8.0",
        ip_address="192.168.1.1",
        access_time=datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC),
    ),
]


def _mock_service(**methods):
    svc = AsyncMock()
    for name, value in methods.items():
        if isinstance(value, Exception):
            getattr(svc, name).side_effect = value
        else:
            getattr(svc, name).return_value = value
    return svc


def _mock_cache_repo(get_by_short_code=None, set_short_code=None, delete_short_code=0):
    repo = AsyncMock()
    repo.get_by_short_code.return_value = get_by_short_code
    repo.set_short_code.return_value = set_short_code
    repo.delete_short_code.return_value = delete_short_code
    return repo


# --- Redirect endpoint ---


class TestRedirectToUrl:
    async def test_redirect_returns_none(self, app: FastAPI, client: AsyncClient):
        mock_url = _mock_service(get_one=None)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_url
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.get("/abc123", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        app.state.click_producer.send.assert_not_called()

    async def test_redirect_cache_miss_falls_back_to_db(
        self, app: FastAPI, client: AsyncClient
    ):
        mock_url = _mock_service(get_one=SAMPLE_URL)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_url
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.get("/abc123", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com"
        mock_cache.get_by_short_code.assert_awaited_once_with("abc123")
        mock_url.get_one.assert_awaited_once()
        mock_cache.set_short_code.assert_awaited_once()
        app.state.click_producer.send.assert_called_once()

    async def test_redirect_cache_hit_skips_db(self, app: FastAPI, client: AsyncClient):
        mock_url = _mock_service()
        mock_cache = _mock_cache_repo(get_by_short_code=SAMPLE_URL)

        app.dependency_overrides[get_url_service] = lambda: mock_url
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.get("/abc123", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com"
        mock_cache.get_by_short_code.assert_awaited_once_with("abc123")
        mock_url.get_one.assert_not_awaited()
        mock_cache.set_short_code.assert_not_awaited()
        app.state.click_producer.send.assert_called_once()

    async def test_redirect_not_found(self, app: FastAPI, client: AsyncClient):
        mock_url = _mock_service(get_one=NotFound(message="Url not found"))
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_url
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.get("/nonexistent")

        assert response.status_code == 404
        body = response.json()
        assert body["errors"][0]["type"] == "NOT_FOUND"
        app.state.click_producer.send.assert_not_called()

    async def test_redirect_tracks_ip_and_user_agent(
        self, app: FastAPI, client: AsyncClient
    ):
        mock_url = _mock_service(get_one=SAMPLE_URL)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_url
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        await client.get(
            "/abc123",
            headers={"user-agent": "TestBot/1.0"},
            follow_redirects=False,
        )

        app.state.click_producer.send.assert_called_once()
        event = app.state.click_producer.send.call_args.args[0]
        assert isinstance(event, ClickEvent)
        assert event.user_agent == "TestBot/1.0"
        assert event.url_id == 1

    async def test_redirect_does_not_shadow_api_routes(self, client: AsyncClient):
        # The catch-all redirect must not intercept /docs, /openapi.json,
        # or /v0/* routes.
        docs_response = await client.get("/docs", follow_redirects=False)
        assert docs_response.status_code == 200


# --- Stats endpoint ---


class TestGetShortUrlStats:
    async def test_stats_success(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(
            get_list=ManyCustomResponse(count=2, data=SAMPLE_STATS)
        )

        app.dependency_overrides[get_url_stats_service] = lambda: mock_svc

        response = await client.get(
            "/v0/shortner/stats", params={"short_code": "abc123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["payload"]) == 2
        assert body["payload"][0]["url_id"] == 1
        assert body["payload"][0]["user_agent"] == "Mozilla/5.0"
        assert body["payload"][1]["ip_address"] == "192.168.1.1"

    async def test_stats_not_found(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(get_list=NotFound(message="Url not found"))

        app.dependency_overrides[get_url_stats_service] = lambda: mock_svc

        response = await client.get(
            "/v0/shortner/stats", params={"short_code": "nonexistent"}
        )

        assert response.status_code == 404

    async def test_stats_empty(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(get_list=ManyCustomResponse(count=0, data=[]))

        app.dependency_overrides[get_url_stats_service] = lambda: mock_svc

        response = await client.get(
            "/v0/shortner/stats", params={"short_code": "abc123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["payload"] == []

    async def test_stats_missing_short_code(self, client: AsyncClient):
        response = await client.get("/v0/shortner/stats")

        assert response.status_code == 422


# --- Create short URL ---


class TestCreateShortUrl:
    async def test_create_success(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(create=SAMPLE_URL)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.post(
            "/v0/shortner/", json={"target_url": "https://example.com"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["payload"]["short_code"] == "abc123"
        mock_cache.set_short_code.assert_awaited_once_with("abc123", SAMPLE_URL)

    async def test_create_invalid_url(self, client: AsyncClient):
        response = await client.post("/v0/shortner/", json={"target_url": "not-a-url"})

        assert response.status_code == 422
        body = response.json()
        assert body["errors"][0]["type"] == "VALIDATION_ERROR"

    async def test_create_missing_body(self, client: AsyncClient):
        response = await client.post("/v0/shortner/")

        assert response.status_code == 422


# --- Deactivate short URL ---


class TestDeactivateShortUrl:
    async def test_deactivate_success(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(mark_as_deleted=SAMPLE_URL)
        mock_cache = _mock_cache_repo(delete_short_code=1)

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.post(
            "/v0/shortner/deactivate", json={"short_code": "abc123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["payload"]["message"] == "Short URL deactivated"
        mock_cache.delete_short_code.assert_awaited_once_with("abc123")

    async def test_deactivate_not_found(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(mark_as_deleted=None)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.post(
            "/v0/shortner/deactivate", json={"short_code": "nonexistent"}
        )

        assert response.status_code == 404
        body = response.json()
        assert "not found or already deactivated" in body["payload"]["message"]
        mock_cache.delete_short_code.assert_not_awaited()

    async def test_deactivate_missing_body(self, client: AsyncClient):
        response = await client.post("/v0/shortner/deactivate")

        assert response.status_code == 422


# --- Activate short URL ---


class TestActivateShortUrl:
    async def test_activate_success(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(mark_as_active=SAMPLE_URL)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.post(
            "/v0/shortner/activate", json={"short_code": "abc123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["payload"]["message"] == "Short URL activated"
        mock_cache.set_short_code.assert_awaited_once_with("abc123", SAMPLE_URL)

    async def test_activate_not_found(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(mark_as_active=None)
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.post(
            "/v0/shortner/activate", json={"short_code": "nonexistent"}
        )

        assert response.status_code == 404
        body = response.json()
        assert "not found or already activated" in body["payload"]["message"]
        mock_cache.set_short_code.assert_not_awaited()

    async def test_activate_missing_body(self, client: AsyncClient):
        response = await client.post("/v0/shortner/activate")

        assert response.status_code == 422


# --- Delete short URL ---


class TestDeleteShortUrl:
    async def test_delete_success(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(delete=1)
        mock_cache = _mock_cache_repo(delete_short_code=1)

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.delete(
            "/v0/shortner/abc123", params={"short_code": "abc123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["payload"]["message"] == "Short URL deleted"
        mock_cache.delete_short_code.assert_awaited_once_with("abc123")

    async def test_delete_not_found(self, app: FastAPI, client: AsyncClient):
        mock_svc = _mock_service(delete=NotFound(message="Url not found"))
        mock_cache = _mock_cache_repo()

        app.dependency_overrides[get_url_service] = lambda: mock_svc
        app.dependency_overrides[get_url_cache_repository] = lambda: mock_cache

        response = await client.delete(
            "/v0/shortner/abc123", params={"short_code": "abc123"}
        )

        assert response.status_code == 404
        body = response.json()
        assert body["errors"][0]["type"] == "NOT_FOUND"
        mock_cache.delete_short_code.assert_not_awaited()
