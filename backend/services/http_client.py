"""
异步HTTP客户端管理器
提供基于httpx的异步HTTP客户端，支持连接池、重试、超时等特性
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager


from config.loader import get_config
from config.loguru_config import get_logger
logger = get_logger(__name__)



class HTTPClientManager:
    """HTTP客户端管理器"""
    
    # 保证单例模式
    _instance: Optional["HTTPClientManager"] = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config = get_config()
            self._client = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取异步HTTP客户端实例"""
        if self._client is None:
            await self._create_client()
        return self._client
    
    async def _create_client(self):
        """创建HTTP客户端"""
        http_config = self.config.http_client_config
        
        # 构建客户端配置
        client_kwargs: Dict[str, Any] = {
            "timeout": httpx.Timeout(http_config.timeout), # 配置超时
            # 配置连接池和保持连接
            "limits": httpx.Limits(
                max_connections=http_config.max_connections,
                max_keepalive_connections=http_config.max_keepalive_connections,
                keepalive_expiry=http_config.keepalive_expiry
            ),
            "headers": http_config.default_headers.copy(),
        }
        
        
        
        self._client = httpx.AsyncClient(**client_kwargs)
        logger.info("HTTP客户端已创建", 
                   timeout=http_config.timeout,
                   max_connections=http_config.max_connections)
    
    async def close(self):
        """关闭客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP客户端已关闭")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return await self.get_client()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        pass  # 不自动关闭，由管理器统一管理


# 全局管理器实例
_http_client_manager = HTTPClientManager()


async def get_http_client() -> httpx.AsyncClient:
    """获取全局HTTP客户端"""
    return await _http_client_manager.get_client()


@asynccontextmanager
async def http_client_context():
    """HTTP客户端上下文管理器"""
    client = await get_http_client()
    try:
        yield client
    except Exception as e:
        logger.error(f"HTTP请求失败: {e}")
        raise


class AsyncHTTPClient:
    """异步HTTP客户端包装器，提供便捷的请求方法"""
    
    def __init__(self, base_url: str = ""):
        # 初始化时，将base_url转换为标准格式（移除末尾的斜杠）
        self.base_url = base_url.rstrip("/")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """异步GET请求"""
        async with http_client_context() as client:
            full_url = self._build_url(url)
            return await client.get(full_url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """异步POST请求"""
        async with http_client_context() as client:
            full_url = self._build_url(url)
            return await client.post(full_url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """异步PUT请求"""
        async with http_client_context() as client:
            full_url = self._build_url(url)
            return await client.put(full_url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """异步DELETE请求"""
        async with http_client_context() as client:
            full_url = self._build_url(url)
            return await client.delete(full_url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """异步PATCH请求"""
        async with http_client_context() as client:
            full_url = self._build_url(url)
            return await client.patch(full_url, **kwargs)
    
    def _build_url(self, url: str) -> str:
        """使用base_url + endpoint构建完整URL，去除掉endpoint中的前导斜杠"""
        if self.base_url and not url.startswith(("http://", "https://")):
            return f"{self.base_url}/{url.lstrip('/')}"
        return url


async def shutdown_http_client():
    """关闭HTTP客户端（应用退出时调用）"""
    await _http_client_manager.close()