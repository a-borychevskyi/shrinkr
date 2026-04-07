from src.api.app import create_app
from src.config.app import AppConfig

app = create_app()
config = AppConfig()


def production_handler():
    raise NotImplementedError


def development_handler():
    return {
        "app": app,
        "host": config.APP_HOST,
        "port": config.APP_PORT,
    }


handlers_map = {"production": production_handler, "development": development_handler}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(**handlers_map[config.APP_ENVIRONMENT.lower()]())
