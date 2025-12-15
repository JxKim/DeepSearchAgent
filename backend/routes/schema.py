from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# # 枚举定义
# class MessageType(str, Enum):
#     TEXT = "text"
#     IMAGE = "image"
#     FILE = "file"
#     SYSTEM = "system"

class SenderType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_AUTHORIZATION = "waiting_authorization"
    COMPLETED = "completed"

class ToolRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

# 基础响应模型
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None

class ErrorResponse(BaseResponse):
    success: bool = False
    error_code: str
    error_details: Optional[Dict[str, Any]] = None

# 用户相关模型
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserListResponse(BaseResponse):
    data: List[User]

# 认证相关模型
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    username: str
    password: str

class VerifyRequest(BaseModel):
    token: str

# 会话相关模型
class SessionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    conversation_status: Optional[SessionStatus] = None
    current_action: Optional[str] = None
    waiting_for: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class Session(SessionBase):
    id: str
    user_id: str
    conversation_status: SessionStatus = SessionStatus.ACTIVE
    current_action: Optional[str] = None
    waiting_for: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

class SessionListItem(BaseModel):
    id: str
    title: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    message_count: int = 0
    conversation_status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime

class SessionListResponse(BaseResponse):
    data: List[SessionListItem]

# 消息相关模型
class MessageBase(BaseModel):
    text: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None

class MessageCreate(MessageBase):
    sender: SenderType

class Message(MessageBase):
    id: str
    session_id: str
    sender: SenderType
    timestamp: datetime |  None
    is_processed: bool = False

class MessageListResponse(BaseResponse):
    data: List[Message]

# 工具调用相关模型
class ToolInvokeRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    is_authorized: bool = False

class ToolRequestCreate(ToolInvokeRequest):
    pass

class ToolRequestUpdate(BaseModel):
    """更新工具请求的模型"""
    status: Optional[ToolRequestStatus] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class ToolRequest(ToolInvokeRequest):
    id: str
    session_id: str
    user_id: str
    status: ToolRequestStatus = ToolRequestStatus.PENDING
    authorized_by: Optional[str] = None
    authorization_time: Optional[datetime] = None
    execution_result: Optional[Dict[str, Any]] = None
    execution_time: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ToolRequestResponse(BaseResponse):
    data: ToolRequest

class ToolRequestListResponse(BaseResponse):
    data: List[ToolRequest]

class ToolAuthorizationRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None

class ToolAuthorization(BaseModel):
    """工具授权模型"""
    id: str
    tool_request_id: str
    authorized_by: str
    authorized_at: datetime
    expires_at: Optional[datetime] = None

class ToolExecutionResult(BaseModel):
    """工具执行结果模型"""
    id: str
    tool_request_id: str
    executed_at: datetime
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

# 系统状态模型
class SystemStatus(BaseModel):
    version: str
    status: str
    uptime: int
    active_sessions: int
    total_messages: int
    database_status: str

class HealthCheckResponse(BaseResponse):
    data: SystemStatus


# 知识库相关模型
class SearchType(str, Enum):
    HYBRID = "hybrid_search"
    VECTOR = "vector_search"
    KEYWORD = "keyword_search"

class ParseStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class KnowledgeFileBase(BaseModel):
    file_name: str
    file_id: str
    is_parsed: bool = False
    chunk_num: int = 0
    search_type: SearchType = SearchType.VECTOR
    parse_status: ParseStatus = ParseStatus.PENDING # 对应获取解析状态
    
class KnowledgeFile(KnowledgeFileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    size: int # 文件大小

class KnowledgeFileListResponse(BaseResponse):
    data: List[KnowledgeFile]

class ParseTaskResponse(BaseResponse):
    data: Dict[str, str] # task_id

class ParseProgressResponse(BaseResponse):
    data: Dict[str, Any] # status, progress, etc.

class RecallTestRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = 5

class RecallResult(BaseModel):
    file_name: str
    content: str
    score: float

class RecallTestResponse(BaseResponse):
    data: List[RecallResult]