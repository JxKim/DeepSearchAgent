"""
配置数据模型 - 类型安全的配置管理
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, List, Any
from enum import Enum

class Environment(str, Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    LOCAL = "local"

# 日志配置模型
class ConsoleHandlerConfig(BaseModel):
    enabled: bool = True
    level: LogLevel = LogLevel.INFO
    colorize: bool = True

class FileHandlerConfig(BaseModel):
    enabled: bool = True
    level: LogLevel = LogLevel.INFO
    path: str = "logs/app.log"
    rotation: str = "10 MB"
    retention: str = "30 days"
    compression: str = "zip"

class HandlerConfig(BaseModel):
    console: ConsoleHandlerConfig = Field(default_factory=ConsoleHandlerConfig)
    file: FileHandlerConfig = Field(default_factory=FileHandlerConfig)

class LoggingConfig(BaseModel):
    level: LogLevel = LogLevel.INFO
    format: Dict[str, str] = Field(default_factory=dict)
    handlers: HandlerConfig = Field(default_factory=HandlerConfig)
    loggers: Dict[str, str] = Field(default_factory=dict)

# 飞书配置模型
class URLBuilder:
    """URL构建器 - 安全构建完整URL"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')  # 移除末尾斜杠
    
    def build_url(self, endpoint: str) -> str:
        """安全构建完整URL"""
        from urllib.parse import urljoin
        
        # 确保endpoint以斜杠开头
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        # 使用urljoin确保路径正确拼接
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    def build_url_with_params(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """构建带查询参数的URL"""
        from urllib.parse import urlencode
        
        url = self.build_url(endpoint)
        
        if params:
            # 过滤掉None值
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url += '?' + urlencode(filtered_params)
                
        return url
    
    def build_template_url(self, endpoint: str, **kwargs) -> str:
        """构建模板URL（支持路径参数）"""
        url = self.build_url(endpoint)
        
        # 替换路径参数
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))
                
        return url


class FeishuConfig(BaseModel):
    app_id: str = Field(..., description="飞书应用ID")
    app_secret: str = Field(..., description="飞书应用密钥")
    base_url: str = "https://open.feishu.cn"
    timeout: int = 30
    
    # API端点配置
    endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "get_tenant_token": "/open-apis/auth/v3/tenant_access_token/internal",
        "send_message": "/open-apis/im/v1/messages",
        "upload_file": "/open-apis/drive/v1/files/upload_all",
        "get_user_info": "/open-apis/contact/v3/users/{user_id}",
    })
    
    @property
    def url_builder(self) -> URLBuilder:
        """获取URL构建器实例"""
        return URLBuilder(self.base_url)

# LLM配置模型
class LLMConfig(BaseModel):
    provider: LLMProvider 
    api_key: str = Field(..., description="API密钥")
    base_url: str
    model: str 
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60
    
    @field_validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('温度值必须在0到2之间')
        return v

# LiteLLM配置模型 (与 LLMConfig 结构类似，但字段名可能不同，这里为了映射 config.yaml 中的 lite-llm 字段)
class LiteLLMConfig(BaseModel):
    provider: str = Field(default="openai", description="LiteLLM提供商")
    api_key: str = Field(..., description="API密钥")
    base_url: str = Field(..., description="Base URL")
    model: str = Field(..., description="模型名称")
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60

# 数据库配置模型
class PostgresDatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user:str="postgres"
    password: str = "postgres"
    dbname: str = "postgres"

# 服务配置模型
class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"

# HTTP客户端配置模型
class HTTPClientConfig(BaseModel):
    """HTTP客户端配置"""
    timeout: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    retries: int = 3
    backoff_factor: float = 0.5
    
    # 代理配置
    proxy: Optional[str] = None
    
    # SSL配置
    verify_ssl: bool = True
    cert: Optional[str] = None
    
    # 请求头默认值
    default_headers: Dict[str, str] = Field(default_factory=dict)


# 安全配置模型
class SecurityConfig(BaseModel):
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间（分钟）")
    secret_key: str = Field(..., description="用于JWT签名的密钥")
    algorithm: str = Field(default="HS256", description="JWT算法")

class StorageConfig(BaseModel):
    storage_type: str = Field(..., description="存储类型，例如'opendal'")
    scheme: str = Field(..., description="存储方案，例如's3', 'oss', 'local'等")
    file_path :str = Field(...,description="对于本地存储类型而言,存储文件的位置")

class EmbeddingConfig(BaseModel):
    """嵌入模型配置"""
    model_path: str = Field(..., description="嵌入模型路径")
    provider: str = Field(..., description="嵌入模型提供方")
    api_key: str = Field(..., description="嵌入模型API密钥")
    base_url: str = Field(..., description="嵌入模型API基础URL")
    dim: int = Field(..., description="嵌入向量维度")

class MilvusConfig(BaseModel):
    """Milvus配置"""
    uri: str = Field(default="http://localhost:19530", description="Milvus连接URI")
    token: str = Field(default="root:Milvus", description="Milvus认证令牌")
    db_name :str = Field(default="smartagent_db", description="Milvus数据库名称")
    collection_name :str = Field(default="smartagent_collection", description="Milvus集合名称")

    
class MineruConfig(BaseModel):
    """Mineru配置"""
    base_url: str = Field(default="http://localhost:8000", description="Mineru API基础URL")
    parse_endpoint: str = Field(default="/file_parse", description="Mineru解析文件端点")
    use_vllm: bool = Field(default=False, description="是否使用vLLM")
    
class RedisConfig(BaseModel):
    """Redis 配置"""
    host: str = "192.168.10.130"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    url: Optional[str] = None  # 支持直接通过 URL 连接

# 主配置模型
class AppConfig(BaseModel):
    """应用主配置"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # 各模块配置
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    # 使用 alias 来映射 yaml 中的 "lite-llm" 到 python 属性 "lite_llm"
    lite_llm: Optional[LiteLLMConfig] = Field(default=None, alias="lite-llm")
    postgres_database: PostgresDatabaseConfig = Field(default_factory=PostgresDatabaseConfig)
    tavily_api_key: str = Field(..., description="Tavily API密钥")
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig
    http_client: HTTPClientConfig = Field(default_factory=HTTPClientConfig)
    logging: LoggingConfig

    # 添加存储config
    storage : Optional[StorageConfig]=None
    # 添加嵌入模型配置
    embedding : Optional[EmbeddingConfig]=Field(default_factory=EmbeddingConfig)
    # 添加Milvus配置
    milvus : Optional[MilvusConfig]=Field(default_factory=MilvusConfig)
    # 添加Mineru配置
    mineru : Optional[MineruConfig]=Field(default_factory=MineruConfig)
    # 添加Redis配置
    redis: Optional[RedisConfig] = None

    # 前端服务地址：用以配置跨域请求
    front_end_base_url: str = Field(..., description="前端服务基础URL")



from dataclasses import dataclass

class MyDataClass(BaseModel):
    value_1:str

if __name__ == '__main__':
    t1 = MyDataClass(value_1=23)
    print(t1)
