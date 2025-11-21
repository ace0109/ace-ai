from fastapi import FastAPI, Depends

from app.api import router as api_router
from app.core.auth import require_api_key


def create_app() -> FastAPI:
    """
    Build and return a FastAPI application instance.
    """
    app = FastAPI(
        title="Ace AI",
        version="0.1.0",
        dependencies=[Depends(require_api_key)],
    )
    
    # 注册受保护的 API Router
    app.include_router(api_router)
    
    return app


app = create_app()
