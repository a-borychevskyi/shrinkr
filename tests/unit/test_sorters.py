from src.orm.sorters.base import sort_convertor
from src.orm.sorters.url import UrlSortModel
from src.utils.enums.sort import SortOption


class TestValidateSortOption:
    def test_valid_field_and_direction(self):
        model = UrlSortModel()
        assert model.validate_sort_option("id", SortOption.ASC) is True

    def test_invalid_field(self):
        model = UrlSortModel()
        assert model.validate_sort_option("nonexistent", SortOption.ASC) is False

    def test_invalid_direction(self):
        model = UrlSortModel()
        assert model.validate_sort_option("id", "INVALID") is False


class TestGenerateParams:
    def test_single_sort_field(self):
        model = UrlSortModel(id=SortOption.ASC)
        params = model.generate_params()
        assert len(params) == 1
        assert str(params[0]) == "id ASC"

    def test_multiple_sort_fields(self):
        model = UrlSortModel(id=SortOption.ASC, created_at=SortOption.DESC)
        params = model.generate_params()
        assert len(params) == 2
        texts = {str(p) for p in params}
        assert "id ASC" in texts
        assert "created_at DESC" in texts

    def test_no_fields_set(self):
        model = UrlSortModel()
        params = model.generate_params()
        assert params == []

    def test_invalid_direction_is_skipped(self):
        model = UrlSortModel()
        model.model_fields_set.add("id")
        object.__setattr__(model, "id", "INVALID")
        params = model.generate_params()
        assert params == []


class TestSortConvertor:
    def test_single_asc_field(self):
        result = sort_convertor(UrlSortModel, "id")
        assert result.id == SortOption.ASC

    def test_single_desc_field(self):
        result = sort_convertor(UrlSortModel, "-id")
        assert result.id == SortOption.DESC

    def test_multiple_fields(self):
        result = sort_convertor(UrlSortModel, "-id,created_at")
        assert result.id == SortOption.DESC
        assert result.created_at == SortOption.ASC

    def test_empty_string_returns_default(self):
        result = sort_convertor(UrlSortModel, "")
        assert result.id is None
        assert result.created_at is None

    def test_whitespace_in_fields(self):
        result = sort_convertor(UrlSortModel, " id , -created_at ")
        assert result.id == SortOption.ASC
        assert result.created_at == SortOption.DESC
