from fastapi import HTTPException, Header
from typing import List, Optional

from routes.schema import  User
from services.auth_service import auth_service
from config.loguru_config import get_logger


logger = get_logger(__name__)


# 依赖函数：从请求头中获取并验证令牌
async def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> User:
    """从请求头中获取并验证令牌，返回当前用户"""
    from db.database import SessionLocal
    if not authorization:
        logger.error('未提供授权令牌')
        raise HTTPException(status_code=401, detail="未提供授权令牌")
    
    # 提取令牌（移除Bearer前缀）
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
        logger.info(f'提取到的令牌（无Bearer前缀）: {token}')
    
    # 验证令牌
    logger.debug('开始验证令牌')
    session = SessionLocal()
    try:
        user = await auth_service.verify_token(token,session)
        if not user:
            logger.info('无效的令牌')
            raise HTTPException(status_code=401, detail="无效的令牌")

        logger.debug(f'令牌验证成功，返回用户: {user.id}')
    finally:
        await session.close()
    return user