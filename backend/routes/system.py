import datetime

from fastapi import APIRouter
from tests.models import SystemStatus, HealthCheckResponse
from db.database import check_db_connection
router = APIRouter(prefix="/system", tags=["系统管理"])

@router.get("/status", response_model=SystemStatus)
async def system_status():
    """获取系统状态"""
    return '200'

@router.get("/health", response_model=HealthCheckResponse)
async def health():
    """健康检查"""
    db_is_healthy = await check_db_connection()
    if db_is_healthy:
        status = "healthy"
    else:
        status = "unhealthy"
    health_status = {
        "status": {status},
        "service": "SmartAgent",
        "timestamp": str(datetime.datetime.now()),
    }

    return health_status