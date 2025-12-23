from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import uvicorn
import os

# 导入loguru配置
from config.loguru_config import get_logger, setup_logging
from config.loader import get_config
from services.http_client import shutdown_http_client
# 直接导入路由模块
from routes import auth, sessions, system
from db.database import db_startup,db_shutdown
# 初始化配置和日志
config = get_config()
setup_logging()
logger = get_logger("main")

async def startup(app):
    """应用启动时执行"""
    logger.info("SmartAgent API 服务启动成功")
    await db_startup()

async def cleanup(app):
    """
    应用关闭时，执行操作
    """
    await db_shutdown()
    await shutdown_http_client()
    logger.info("SmartAgent API 服务已关闭")

@asynccontextmanager
async def app_lifespan(app:FastAPI):
    await startup(app)
    # 设置连接池等对象，或者通过构造一个方法，来初始化所有操作
    yield
    await cleanup(app)
# 创建FastAPI应用
app = FastAPI(
    title="SmartAgent API",
    description="智能代理系统后端API接口",
    version="1.0.0",
    lifespan=app_lifespan
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # 生产环境中应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(system.router, prefix="/api")

@app.get("/")
async def root():
    """根路径，返回API基本信息"""
    return {
        "message": "SmartAgent API 服务运行中",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }



if __name__ == "__main__":
    # 从配置文件中读取端口设置
    port = config.server.port
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=port,
        log_level="error",
        reload=True,
    )