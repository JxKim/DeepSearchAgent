from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from config.loguru_config import get_logger
from config.loader import get_config
logger = get_logger(__name__)
config = get_config()
# 新创建的数据库连接URL
pg_connection_url = (f"postgresql+psycopg://"
                     f"{config.postgres_database.user}:{config.postgres_database.password}"
                     f"@{config.postgres_database.host}:{config.postgres_database.port}/{config.postgres_database.dbname}")

# 创建数据库引擎，使用新创建的数据库
engine = None

# 创建会话工厂
# 实际生产环境下,不要使用同步模式
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = None

async def db_startup():
    logger.info("正在初始化数据库连接池")
    global engine, SessionLocal
    if not engine and not SessionLocal:
        engine = create_async_engine(
            url=pg_connection_url,
            pool_size=10,  # 连接池大小：保持 10 个活跃连接
            max_overflow=20,  # 最大溢出连接：连接池满时额外创建 20 个连接
            pool_pre_ping=True,  # 连接预检：使用连接前检查连接是否有效
            pool_recycle=3600,  # 连接回收时间：连接使用 1 小时后自动回收，防止连接过期
            echo=False,  # 关闭 SQL 日志输出，生产环境建议关闭以提高性能
        )
        SessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(f"数据库连接池初始化完成,session为:{SessionLocal}")

async def db_shutdown():
    """关闭数据库连接池"""
    logger.info("正在关闭数据库连接池")
    if engine:
        await engine.dispose()
        logger.info("数据库连接池已关闭")

# 依赖项：获取数据库会话
async def get_db() -> AsyncSession:
    # yield前的代码相当于 __enter__ / __aenter__
    logger.info("Creating session...")
    session = SessionLocal()

    try:
        # yield的值会注入到路径操作函数
        yield session

        # yield后的代码相当于 __exit__ / __aexit__ (正常情况)
        await session.commit()
    except Exception:
        # yield后的代码相当于 __exit__ / __aexit__ (异常情况)
        await session.rollback()
        raise
    finally:
        # finally中的代码一定会执行
        logger.info("Closing session...")
        await session.close()



# 检查数据库连接
async def check_db_connection():
    """检查数据库连接"""
    try:
        session = SessionLocal()
        await session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        print(f"数据库连接失败: {e}")
        return False

if __name__ == '__main__':
    pass