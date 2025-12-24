from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from routes.schema import MessageCreate, Session, SessionStatus
from db.db_models import Session
from services.agent import get_agent
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, AIMessage

from config.loguru_config import get_logger

logger = get_logger(__name__)

class SessionService:
    """

    """
    def __init__(self):
        # agent通过协程后面进行懒加载，现在仅需要给一个None即可
        self.agent = None
        # 对agent生成进行暂停flag
        self.session_keep_generate_flag = defaultdict(lambda : True)
        

    async def init_agent(self):
        """初始化agent"""
        if not self.agent:
            self.agent = await get_agent()

    
    async def create_session(self, user_id,title,db: AsyncSession) -> Session:
        """
        创建新会话
        
        :param self: Description
        :param user_id: Description
        :param title: Description
        :param db: Description
        :type db: AsyncSession
        :return: Description
        :rtype: Session
        """
        import uuid
        session_id = str(uuid.uuid4())
        db_session = Session(
            id=session_id,
            user_id=user_id,
            title=title,
            conversation_status=SessionStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message_count=0
        )
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session
    
    async def get_session(self, session_id: str,db: AsyncSession) -> Optional[Session]:
        """
        使用session_id从数据库中读取单条session会话
        """
        result = await db.execute(select(Session).where(Session.id == session_id))
        db_session = result.scalar_one_or_none()
        if not db_session:
            return None
        return Session(
            id=db_session.id,
            user_id=db_session.user_id,
            title=db_session.title,
            conversation_status=db_session.conversation_status,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            message_count=db_session.message_count
        )

    async def get_sessions(self,user_id: str,db: AsyncSession) -> list[Session]:
        """
        获取当前用户下面的所有session会话列表
        
        :param self: Description
        :param user_id: Description
        :type user_id: str
        :param db: Description
        :type db: AsyncSession
        :return: Description
        :rtype: list[Session]
        """
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
        )
        db_sessions = result.scalars().all()

        return [
            Session(
                id=session.id,
                user_id=session.user_id,
                title=session.title,
                conversation_status=session.conversation_status,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=session.message_count
            ) for session in db_sessions
        ]

    async def get_messages(self, session_id: str, db: AsyncSession) -> List[BaseMessage]:
        """
        从数据库获取会话历史消息
        """
        from db.db_models import ConversationHistory
        
        # 从数据库查询历史记录
        result = await db.execute(
            select(ConversationHistory)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at.asc())
        )
        history_records = result.scalars().all()
        
        messages = []
        for record in history_records:
            # 重构 HumanMessage
            if record.user_input:
                messages.append(HumanMessage(
                    content=record.user_input, 
                    id=f"{record.id}_user", # 构造唯一的ID
                    additional_kwargs={"created_at": record.created_at.isoformat()}
                ))
            
            # 重构 AIMessage
            if record.agent_output:
                messages.append(AIMessage(
                    content=record.agent_output,
                    id=f"{record.id}_agent", # 构造唯一的ID
                    additional_kwargs={"created_at": record.created_at.isoformat()}
                ))
                
        return messages

    async def add_message_to_session(self,session_id: str, user_id: str, message_data: MessageCreate,db: AsyncSession):
        """
        向会话添加消息
        """
        import json
        session = await session_service.get_session(session_id,db)
        if not session or session.user_id != user_id:
            return None
        logger.info("add_message_to_session invoking...")
        config = {
            "configurable":
                {"thread_id":session_id}
        }
        await self.init_agent()
        invoke_message = {"messages":("user",message_data.text)}
        return self._agent_generate_response(messages=invoke_message,config=config)

    async def tool_invoke(self,session_id,is_approved):
        """
        根据用户输入内容，判断是否需要执行真正工作调用。通过Interrupt / Consume 等 langgraph原语实现
        """
        import json
        config = {
            "configurable":
                {"thread_id": session_id}
        }
        await self.init_agent()
        if is_approved:
            # agent继续执行
            return self._agent_generate_response(command=Command(resume=True),config=config)
        else:
            return self._agent_generate_response(command=Command(resume=False),config=config)
    
    async def _agent_generate_response(self,*,command:Command=None,config:Dict=None,messages:Dict=None):
        """
        模型生成
        
        :param command: Description
        :type command: Command
        """
        import json
        logger.info("调用_agent_generate_response中")
        self.session_keep_generate_flag[config["configurable"]["thread_id"]] = True # 重新置为True,避免影响后面生成
        logger.info(f"当前flag值为:{self.session_keep_generate_flag[config["configurable"]["thread_id"]]}")
        async for chunk in self.agent.astream(
                    input=command or messages,
                    config=config,
                    stream_mode=["updates", "messages"]
            ):

            if not self.session_keep_generate_flag[config["configurable"]["thread_id"]]:
                logger.info(f"当前session_id为:{config["configurable"]["thread_id"]}置为True")
                self.session_keep_generate_flag[config["configurable"]["thread_id"]] = True # 重新置为True,避免影响后面生成

                break
        
        
            # 对于messages类型数据，需要判断是ai_message or tool_message，前端使用不同的方式渲染
            if chunk[0] == "messages":
                if isinstance(chunk[1][0], ToolMessage):
                    message_json = {
                            "tool_message": chunk[1][0].content
                    }
                elif chunk[1][0].content:
                    message_json = {
                        "ai_message": chunk[1][0].content
                    }
                else:
                    continue
                data = json.dumps(message_json)
                logger.debug(f'当前生成的AI消息为:{data}')
                yield f"data : {data}\n\n"

            # 对于状态更新类型的数据，且状态当中有interrupt，向前端发送特定类型数据
            elif chunk[0] == "updates" and "__interrupt__" in chunk[1]:
                interrupt_value = chunk[1]["__interrupt__"][0].value
                interrupt_json = {
                    "func_call":interrupt_value
                }
                data = json.dumps(interrupt_json)
                logger.debug(f"当前生成的状态更新消息为:{data}")
                yield f"data: {data}\n\n"
        
        
        yield "data : [DONE]\n\n"
        # 总是需要将状态重新置为True
        
            
    async def stop_generation(self,session_id:str)->bool:
        """
        暂停Agent继续生成
        
        :param session_id: Description
        :type session_id: str
        """
        logger.info(f"当前session_id为:{session_id}置为False")
        self.session_keep_generate_flag[session_id] = False # 将flag置为False,停止模型的生成
        return True
    
    async def delete_session(self,session_id:str,db: AsyncSession):
        """
        删除会话，包括会话中的所有消息
        
        :param session_id: Description
        :type session_id: str
        """
        from db.db_models import ConversationHistory, SessionSummary
        
        # 先删除关联表数据，解决外键约束问题
        await db.execute(delete(ConversationHistory).where(ConversationHistory.session_id == session_id))
        await db.execute(delete(SessionSummary).where(SessionSummary.session_id == session_id))
        
        # 最后删除会话
        await db.execute(delete(Session).where(Session.id == session_id))
        await db.commit()

    async def update_session_title(self, session_id: str, title: str):
        """
        更新会话标题 (独立事务)
        """
        from db.database import SessionLocal
        from sqlalchemy import update
        
        async with SessionLocal() as db:
            try:
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(title=title, updated_at=datetime.now())
                )
                await db.commit()
                logger.info(f"会话 {session_id} 标题已更新为: {title}")
            except Exception as e:
                logger.error(f"更新会话标题失败: {e}")
                await db.rollback()

        
        

# 创建单例实例
session_service = SessionService()
