from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum as SQLEnum, JSON, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class KnowledgeFile(Base):
    """知识库文件模型"""
    __tablename__ = "knowledge_files"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    is_parsed = Column(Boolean, default=False)
    parse_status = Column(String, default='pending')
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Session(Base):
    """会话模型"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    conversation_status = Column(String,default="")
    current_action = Column(String, nullable=True)
    waiting_for = Column(String, nullable=True)
    context = Column(JSON, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class KnowledgeChunk(Base):
    """知识库切片模型"""
    __tablename__ = "knowledge_chunks"
    
    id = Column(String, primary_key=True, index=True)
    file_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    meta_info = Column(JSON, nullable=True)
    vector_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Token(Base):
    """令牌模型"""
    __tablename__ = "tokens"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConversationHistory(Base):
    """短时记忆模型"""
    __tablename__ = "conversation_history"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    user_id = Column(String, nullable=False)
    user_input = Column(String, nullable=False)
    agent_output = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionSummary(Base):
    """长时记忆模型"""
    __tablename__ = "session_summaries"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, nullable=False)
    summary = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
