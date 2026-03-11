import uvicorn

from src.api.rest.app import create_app
from src.config.settings import settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )