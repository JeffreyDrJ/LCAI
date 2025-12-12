from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager  # 新增：用于定义lifespan
from app.config.settings import settings
from app.api.v1.lcai import router as lcai_router
from app.utils.logger import logger
import asyncio
import uvicorn #

# ------------------------------
# 1. 定义生命周期处理器（替代原on_event）
# ------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行的逻辑（可选，如初始化客户端）
    logger.info("LCAI服务启动中，初始化依赖客户端...")
    yield  # 服务运行期间
    # 关闭时执行的逻辑（原shutdown事件逻辑）
    logger.info("LCAI服务开始关闭，释放资源...")
    from app.services.ds_platform import ds_client
    from app.services.form_storage import form_storage_client
    await ds_client.close()
    await form_storage_client.close()
    logger.info("LCAI服务已关闭，资源释放完成")

# ------------------------------
# 2. 创建FastAPI应用（指定lifespan）
# ------------------------------
app = FastAPI(
    title="LCAI (LowCodeAI) API",
    description="低代码AI智能体平台API",
    version="0.114.514",
    lifespan=lifespan  # 核心修改：绑定生命周期处理器
)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(lcai_router, prefix="/api/v1")

# 健康检查接口
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {
        "status": "healthy",
        "service": "lcai",
        "version": "0.114.514"
    }

# ------------------------------
# 3. 启动服务
# ------------------------------
if __name__ == "__main__":
    import uvicorn  # 此处导入需确保uvicorn已安装
    logger.info(f"启动LCAI服务：http://{settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,  # 开发环境开启热重载，生产环境关闭
        workers=1,    # 生产环境可改为CPU核心数（如4）
        log_level="info"
    )