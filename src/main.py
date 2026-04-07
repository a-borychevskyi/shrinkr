from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    from src.config.app import AppConfig

    config = AppConfig()
    uvicorn.run(
        app=app,
        host=config.APP_HOST,
        port=config.APP_PORT,
    )
