from passlib.context import CryptContext
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import uuid
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routes.schema import (
    User, UserCreate, UserUpdate, LoginRequest, Token,
    BaseResponse, UserListResponse
)
from db.db_models import User as DBUser, Token as DBToken
from db.database import SessionLocal
from config.loguru_config import get_logger
from config.loader import get_config
logger = get_logger(__name__)
config = get_config()
pwd_context = PasswordHash.recommended()
# 使用openssl rand -hex 32
SECRET_KEY = config.security.secret_key
ALGORITHM = config.security.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = config.security.access_token_expire_minutes
# pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# 密码哈希辅助函数
def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class AuthService:

    user_tokens: dict = {}
    user_passwords: dict = {}  # 存储用户密码

    def __init__(self):
        pass

    # 认证相关函数
    async def authenticate_user(self,username: str, password: str,db:AsyncSession) -> Optional[User]:
        """用户认证"""
        # db = self.get_db_session()
        # try:
        #     # 从数据库查询用户
        result = await db.execute(select(DBUser).where(DBUser.username == username))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None

        # 验证密码
        if not verify_password(password, db_user.password):
            return None

        # 转换为响应模型
        user = User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active
        )
        return user

    async def create_access_token(self,user_id: str,db:AsyncSession) -> str:
        """创建访问令牌"""
        token = str(uuid.uuid4())
        # 使用带时区的时间
        token = create_access_token({"sub": user_id},expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))    
        db_token = DBToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=token,
            expires=expires
        )
        db.add(db_token)
        await db.commit()
        await db.refresh(db_token)

        return token

    # async def verify_token(self,token: str,db:AsyncSession) -> Optional[User]:
    #     """验证令牌"""

    #     result = await db.execute(select(DBToken).where(DBToken.token == token))
    #     db_token = result.scalar_one_or_none()
    #     if not db_token:
    #         return None

    #     # 检查令牌是否过期，使用带时区的时间
    #     now_time = datetime.now(timezone.utc)
    #     logger.info('当前时间为：', now_time)
    #     logger.info('令牌过期时间为：', db_token.expires)
    #     if now_time > db_token.expires:
    #         # 删除过期令牌
    #         await db.delete(db_token)
    #         await db.commit()
    #         return None

    #     # 查询对应的用户
    #     result = await db.execute(select(DBUser).where(DBUser.id == db_token.user_id))
    #     db_user = result.scalar_one_or_none()
    #     if not db_user:
    #         return None

    #     # 转换为响应模型
    #     user = User(
    #         id=db_user.id,
    #         username=db_user.username,
    #         email=db_user.email,
    #         full_name=db_user.full_name,
    #         created_at=db_user.created_at,
    #         updated_at=db_user.updated_at,
    #         is_active=db_user.is_active
    #     )
    #     return user


    async def login_user(self,login_data: LoginRequest,db:AsyncSession) -> Token:
        """用户登录"""
        user = await self.authenticate_user(login_data.username, login_data.password,db=db)
        if not user:
            raise ValueError("用户名或密码错误")

        access_token = await self.create_access_token(user.id,db=db)

        return Token(
            access_token=access_token,
            expires_in=config.security.access_token_expire_minutes * 60
        )

    async def get_current_user(self,token: str,db:AsyncSession) -> User:
        """获取当前用户"""
        user = await get_current_user_from_token(token)
        if not user:
            raise ValueError("无效的令牌")
        return user

    async def logout_user(self,token: str,db:AsyncSession) -> BaseResponse:
        """用户登出"""

        result = await db.execute(select(DBToken).where(DBToken.token == token))
        db_token = result.scalar_one_or_none()
        if db_token:
            await db.delete(db_token)
            await db.commit()

        return BaseResponse(message="登出成功")


    async def get_user_profile(self,user_id: str,db:AsyncSession) -> User:
        """获取用户信息"""

        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            raise ValueError("用户不存在")

        # 转换为响应模型
        user = User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active
        )
        return user

    async def update_user_profile(self,user_id: str, update_data: UserUpdate,db:AsyncSession) -> User:
        """更新用户信息"""
        # 调用update_user函数实现相同的功能
        updated_user = await self.update_user(user_id, update_data,db)
        if not updated_user:
            raise ValueError("用户不存在")
        return updated_user

    # 缺失的函数实现
    async def register_user(self,user_data: UserCreate,db:AsyncSession) -> Token:
        """用户注册"""
        # 检查用户名是否已存在
        result = await db.execute(select(DBUser).where(DBUser.username == user_data.username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        result = await db.execute(select(DBUser).where(DBUser.email == user_data.email))
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise ValueError("邮箱已存在")

        # 创建新用户
        user_id = str(uuid.uuid4())
        # 确保密码不超过72字节
        password = user_data.password[:72] if len(user_data.password) > 72 else user_data.password
        hashed_password = get_password_hash(password)

        db_user = DBUser(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password=hashed_password,
            is_active=True
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # 创建访问令牌
        token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=config.security.access_token_expire_minutes)
        )

        return Token(
            access_token=token,
            expires_in=config.security.access_token_expire_minutes * 60
        )

    async def get_user_by_id(self,user_id: str,db:AsyncSession) -> Optional[User]:
        """根据ID获取用户"""
        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None

        # 转换为响应模型
        user = User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active
        )
        return user

    async def update_user(self,user_id: str, user_data: UserUpdate,db:AsyncSession) -> Optional[User]:
        """更新用户信息"""

        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None

        # 更新字段
        if user_data.email:
            # 检查邮箱是否已被其他用户使用
            result = await db.execute(select(DBUser).where(DBUser.email == user_data.email,DBUser.id != user_id))
            existing_email = result.scalar_one_or_none()
            if existing_email:
                raise ValueError("邮箱已被其他用户使用")
            db_user.email = user_data.email

        if user_data.full_name:
            db_user.full_name = user_data.full_name

        if user_data.password:
            # 确保密码不超过72字节
            password = user_data.password[:72] if len(user_data.password) > 72 else user_data.password
            # 更新密码，需要重新哈希
            db_user.password = get_password_hash(password)

        # 提交更新
        await db.commit()
        await db.refresh(db_user)

        # 转换为响应模型
        user = User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active
        )
        return user

    async def delete_user(self,user_id: str,db:AsyncSession) -> BaseResponse:
        """删除用户"""
        # db = self.get_db_session()
        try:
            # 查询用户
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if not db_user:
                return BaseResponse(message="用户不存在", success=False)

            # 删除该用户的所有令牌
            db.query(DBToken).filter(DBToken.user_id == user_id).delete()

            # 删除用户
            db.delete(db_user)
            db.commit()

            return BaseResponse(message="用户删除成功")
        finally:
            db.close()


auth_service = AuthService()