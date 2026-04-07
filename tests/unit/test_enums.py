from src.utils.enums.app_environment import AppEnvironment


class TestAppEnvironment:
    def test_values(self):
        assert AppEnvironment.PRODUCTION == "PRODUCTION"
        assert AppEnvironment.DEVELOPMENT == "DEVELOPMENT"

    def test_is_str(self):
        assert isinstance(AppEnvironment.PRODUCTION, str)
