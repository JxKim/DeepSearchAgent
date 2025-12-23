from fastapi import APIRouter, HTTPException, Depends
from routes.schema import (
    User, UserCreate, LoginRequest, Token,
    BaseResponse, VerifyRequest
)
from services.auth_service import auth_service
from db.database import get_db
from config.loguru_config import get_logger
from routes.utils import get_current_user_from_token
logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["认证管理"])

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """用户注册"""
    try:
        return await auth_service.register_user(user_data,db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"注册用户出错: {e}")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db=Depends(get_db)):
    """用户登录"""
    try:
        return await auth_service.login_user(login_data,db=db)
    except ValueError as e:
        logger.error(f"登录用户出错: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"登录用户出错: {e}")
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")

@router.post("/logout", response_model=BaseResponse)
async def logout(token: str, db=Depends(get_db)):
    """用户登出"""
    return await auth_service.logout_user(token,db=db)


@router.get("/me", response_model=User)
async def get_my_info(token: str, db=Depends(get_db),user:User=Depends(get_current_user_from_token)):
    """获取当前用户信息"""
    if not user:
        raise HTTPException(status_code=401, detail="无效的令牌")
    return user