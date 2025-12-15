from fastapi import APIRouter, HTTPException, Depends
from routes.schema import (
    User, UserCreate, LoginRequest, Token,
    BaseResponse, VerifyRequest
)
from services.auth_service import auth_service
from db.database import get_db
router = APIRouter(prefix="/auth", tags=["认证管理"])

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """用户注册"""
    try:
        return await auth_service.register_user(user_data,db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db=Depends(get_db)):
    """用户登录"""
    try:
        return await auth_service.login_user(login_data,db=db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")

@router.post("/logout", response_model=BaseResponse)
async def logout(token: str, db=Depends(get_db)):
    """用户登出"""
    return await auth_service.logout_user(token,db=db)

@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str, db=Depends(get_db)):
    """刷新令牌"""
    return await auth_service.refresh_token(refresh_token,db=db)

@router.post("/verify", response_model=BaseResponse)
async def verify(token: VerifyRequest, db=Depends(get_db)):
    """验证令牌"""
    user = await auth_service.verify_token(token.token,db=db)
    if user:
        return BaseResponse(message="令牌有效", data=user)
    else:
        return BaseResponse(success=False, message="令牌无效")

@router.get("/me", response_model=User)
async def get_my_info(token: str, db=Depends(get_db)):
    """获取当前用户信息"""
    user = await auth_service.get_current_user(token,db=db)
    if not user:
        raise HTTPException(status_code=401, detail="无效的令牌")
    return user


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str, db=Depends(get_db)):
    """获取特定用户信息"""
    user = await auth_service.get_user_by_id(user_id,db=db)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user