from fastapi import FastAPI

from app.api import router as api_router


def create_app() -> FastAPI:
    """
    Build and return a FastAPI application instance.
    """
    app = FastAPI(
        title="Ace AI",
        version="0.1.0",
        # 权限控制已在 api router 中按路由分别配置
    )
    
    # 注册 API Router（各路由自行管理权限）
    app.include_router(api_router)
    
    return app


app = create_app()
