from fastapi import HTTPException, Header
from typing import List, Optional
import jwt
from jwt.exceptions import InvalidTokenError
from routes.schema import  User
from services.auth_service import auth_service
from config.loguru_config import get_logger
from config.loader import get_config

logger = get_logger(__name__)
config = get_config()

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
        payload = jwt.decode(token,config.security.secret_key,algorithms=[config.security.algorithm])
        user_id = payload.get("user_id")
        user = await auth_service.get_user_by_id(user_id=user_id,db=session)
        logger.debug(f'令牌验证成功，返回用户: {user.id}')
    except InvalidTokenError:
        logger.error('无效的令牌')
        raise HTTPException(status_code=401, detail="无效的令牌")
    finally:
        await session.close()
    return user