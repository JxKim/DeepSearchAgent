from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import List, Optional

from langchain_core.messages import HumanMessage, AIMessage
from starlette.responses import StreamingResponse

from routes.schema import (
    Session, SessionListItem, Message, MessageCreate,
    SessionListResponse, User, SenderType, ToolRequestResponse, ToolInvokeRequest, SessionCreate,BaseResponse
)
# from controllers.auth_controller import verify_token
from services.session_service import session_service
from services.auth_service import auth_service
from config.loguru_config import get_logger
from routes.utils import get_current_user_from_token
from db.database import get_db
from work_flow.process import run_workflow, stream_workflow
import json

logger = get_logger(__name__)


router = APIRouter(prefix="/sessions", tags=["会话管理"])

@router.post("/", response_model=Session)
async def create_new_session(session_create:SessionCreate,current_user: User = Depends(get_current_user_from_token),db=Depends(get_db)):
    """创建新会话"""
    return await session_service.create_session(current_user.id,session_create.title,db=db)

@router.get("/", response_model=SessionListResponse)
async def list_sessions(current_user: User = Depends(get_current_user_from_token),db=Depends(get_db)):
    """获取所有会话"""
    sessions = await session_service.get_sessions(current_user.id,db=db)
    session_list=[]
    for session in sessions:
        session_list.append(SessionListItem(
            id=session.id,
            title=session.title,
            last_message=None,
            last_message_time=None,
            message_count=0,
            conversation_status=session.conversation_status,
            created_at=session.created_at
        ))
    return SessionListResponse(data=session_list)

@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user: User = Depends(get_current_user_from_token),db=Depends(get_db)):
    """获取特定会话"""
    session = await session_service.get_session(session_id,db=db)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    return session

@router.post("/{session_id}/workflow_test")
async def test_workflow(
    session_id: str, 
    query: str, 
    request: Request,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    [测试接口] 运行 DeepResearch 工作流
    """
    # 1. 获取全局 checkpointer
    if not hasattr(request.app.state, "checkpointer"):
        raise HTTPException(status_code=500, detail="Redis Checkpointer not initialized")
    
    checkpointer = request.app.state.checkpointer
    
    # 2. 运行工作流
    try:
        result = await run_workflow(
            session_id=session_id,
            user_id=current_user.id,
            original_query=query,
            thread_id=session_id,
            checkpointer=checkpointer
        )
        return {
            "session_id": session_id,
            "query": query,
            "final_answer": result.get("final_answer"),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/workflow_stream")
async def stream_workflow_endpoint(
    session_id: str, 
    query: str, 
    request: Request,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    [测试接口] 流式运行 DeepResearch 工作流 (SSE)
    """
    logger.info(f"收到流式请求: session_id={session_id}, query={query}")
    
    # 1. 获取全局 checkpointer
    if not hasattr(request.app.state, "checkpointer"):
        logger.error("Redis Checkpointer not initialized")
        raise HTTPException(status_code=500, detail="Redis Checkpointer not initialized")
    
    checkpointer = request.app.state.checkpointer
    logger.info("Checkpointer 获取成功")
    
    # 2. 定义流式生成器
    async def event_generator():
        logger.info("开始执行 event_generator")
        try:
            # 调用流式工作流函数
            async for chunk in stream_workflow(
                session_id=session_id,
                user_id=current_user.id,
                original_query=query,
                thread_id=session_id,
                checkpointer=checkpointer
            ):
                # 转换为 SSE 格式: "data: {json}\n\n"
                # ensure_ascii=False 保证中文正常显示
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Stream workflow execution failed: {e}")
            error_msg = json.dumps({"event": "error", "error": str(e)}, ensure_ascii=False)
            yield f"data: {error_msg}\n\n"

    # 3. 返回 StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/{session_id}/messages/", response_model=Message)
async def add_message(session_id: str, message_data: MessageCreate, current_user: User = Depends(get_current_user_from_token),db=Depends(get_db)):
    """当用户输入消息时，添加消息到会话，agent回复用户消息"""
    message_generator = await session_service.add_message_to_session(session_id, current_user.id, message_data,db=db)
    if not message_generator:
        raise HTTPException(status_code=404, detail="会话未找到")
    return StreamingResponse(message_generator,media_type="text/event-stream",)

@router.get("/{session_id}/messages/", response_model=List[Message])
async def get_messages(session_id: str, current_user: User = Depends(get_current_user_from_token)):
    """获取会话中的所有消息"""
    messages = await session_service.get_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="会话未找到")
    message_list = []
    for message in messages:
        if type(message) not in (HumanMessage, AIMessage):
            continue
        message_list.append(
            Message(
                id=message.id,
                session_id=session_id,
                sender=SenderType.USER if type(message)==HumanMessage else SenderType.AGENT,
                timestamp=None,
                text=message.content if message.content else ' ',
                metadata=message.response_metadata
            )
        )
    return message_list

@router.post("/{session_id}/messages/tools/", response_model=List[ToolRequestResponse])
async def tool_invoke(session_id:str,tool_invoke_request: ToolInvokeRequest,current_user: User = Depends(get_current_user_from_token)):
    """
    agent调用工具时，发起请求，是否需要获取用户允许，当用户允许时，继续执行工具调用
    否则不进行具体调用
    """
    stream_generator = await session_service.tool_invoke(session_id=session_id,is_approved=tool_invoke_request.is_authorized)
    return StreamingResponse(stream_generator,media_type="text/event-stream",)


# todo 定义response_model
@router.post("/{session_id}/stop",response_model=BaseResponse)
async def stop_generation(session_id:str,current_user:User = Depends(get_current_user_from_token)):
    """
    停止此刻模型的生成。消息列表中仅保留已生成的token消息列表
    
    :param session_id: Description
    :type session_id: str
    """
    # resp = await session_service.stop_generation(session_id = session_id)
    return BaseResponse(success=True,message="Stop generating new tokens succeeded.")

@router.delete("/{session_id}",response_model=BaseResponse)
async def delete_session(session_id:str,current_user:User = Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    删除会话，包括会话中的所有消息
    
    :param session_id: Description
    :type session_id: str
    """
    await session_service.delete_session(session_id = session_id,db=db)
    return BaseResponse(success=True,message="Delete session succeeded.")
