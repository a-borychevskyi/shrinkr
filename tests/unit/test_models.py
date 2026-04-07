from datetime import datetime, UTC

from src.models.url.entity import UrlModel
from src.models.url_stats.entity import UrlStatsModel
from src.models.base import ManyCustomResponse


class TestUrlModel:
    def test_to_orm(self):
        model = UrlModel(
            id=1,
            target_url="https://example.com",
            short_code="abc123",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            deleted_at=None,
        )
        orm_dict = model.to_orm()

        assert orm_dict["id"] == 1
        assert orm_dict["target_url"] == "https://example.com"
        assert orm_dict["short_code"] == "abc123"

    def test_from_attributes(self):
        model = UrlModel.model_validate(
            {
                "id": 1,
                "target_url": "https://example.com",
                "short_code": "abc",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                "deleted_at": None,
            }
        )
        assert model.short_code == "abc"


class TestUrlStatsModel:
    def test_to_orm(self):
        model = UrlStatsModel(
            id=1,
            url_id=1,
            user_agent="Mozilla/5.0",
            ip_address="127.0.0.1",
            access_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        orm_dict = model.to_orm()

        assert orm_dict["url_id"] == 1
        assert orm_dict["user_agent"] == "Mozilla/5.0"

    def test_excludes_unset_fields(self):
        model = UrlStatsModel(
            id=None,
            url_id=1,
            user_agent="curl",
            ip_address="10.0.0.1",
            access_time=None,
        )
        orm_dict = model.to_orm()
        assert "id" in orm_dict
        assert orm_dict["access_time"] is None


class TestManyCustomResponse:
    def test_with_alias(self):
        resp = ManyCustomResponse(total_count=5, data=[1, 2, 3])
        assert resp.count == 5
        assert len(resp.data) == 3

    def test_defaults(self):
        resp = ManyCustomResponse()
        assert resp.count == 0
        assert resp.data == []
