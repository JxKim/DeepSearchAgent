from work_flow.state import OverAllState
from langchain_core.runnables import RunnableConfig


async def long_term_memory_import(state: OverAllState) -> dict:
    """
   长期记忆导入节点
   
   Args:
      state: 当前状态
      
   Returns:
      dict: 更新后的状态
   """
    print("执行节点: long_term_memory_import")
    from db.database import SessionLocal
    from db.db_models import ConversationHistory, SessionSummary
    from sqlalchemy import select
    
    # 假设 session_id 已经存在于 state 中，或者从上下文获取
    # 这里为了演示暂时使用硬编码或从 state 获取
    session_id = state.get("session_id", "session_001") 

    # --- 优化策略：内存状态优先 ---
    # 检查 state 中是否已经存在 conversation_history
    # 存在 -> 说明是从 MemorySaver (RAM) 恢复的热数据，直接跳过 DB 读取
    if state.get("conversation_history"):
        print(f"✅ [内存命中] 检测到活跃会话状态 (历史条数: {len(state['conversation_history'])})，跳过数据库导入。")
        # 即使命中内存，也需要返回当前状态中的数据，以便前端展示
        return {
            "memory_summary": state.get("memory_summary", ""),
            # conversation_history 已经在 state 中，不返回也没关系，但为了保持一致性可以返回
        }
    
    # 不存在 -> 说明是冷启动（新会话或服务刚重启），需要从数据库加载
    print(f"⚠️ [内存未命中] 正在从数据库加载会话 {session_id} 的历史记录...")

    async with SessionLocal() as db:
        # 0. 检查 Session 是否存在，不存在则创建
        from db.db_models import Session
        session_result = await db.execute(select(Session).where(Session.id == session_id))
        if not session_result.scalars().first():
            print(f"会话 {session_id} 不存在，正在自动创建...")
            new_session = Session(
                id=session_id,
                user_id=state.get("user_id", "user_001"), # 优先从 state 获取 user_id
                title="New Session",
                conversation_status="active"
            )
            db.add(new_session)
            await db.commit()
            print(f"会话 {session_id} 创建成功")

        # 1. 获取长期记忆总结 (Summary)
        summary_result = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
        summary_obj = summary_result.scalars().first()
        memory_summary = summary_obj.summary if summary_obj else ""

        # 2. 获取最近 3 条完整对话历史 (Recent History)
        # 按时间倒序查询最近的 3 条，然后再反转回正序
        history_result = await db.execute(
            select(ConversationHistory)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at.desc())
            .limit(3)
        )
        recent_records = history_result.scalars().all()
        
        # 将记录转换为 Tuple[str, str] 的列表，并按时间正序排列
        conversation_history = [
            (record.user_input, record.agent_output) 
            for record in reversed(recent_records)
        ]

        print(f"导入记忆: 总结长度={len(memory_summary)}, 历史条数={len(conversation_history)}")

    # 更新状态
    return {
        "memory_summary": memory_summary,
        "conversation_history": conversation_history
    }


async def title_generate(state: OverAllState) -> dict:
    """
      标题创建

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
      """
    print("执行节点: title_generate")

    # 如果已经存在标题，则跳过
    if state.get("conversation_title"):
        return {}

    from work_flow.agent import get_agent
    from work_flow.agent.prompt import AgentPrompts
    from langchain_core.messages import HumanMessage

    original_query = state.get("original_query", "")
    
    # 构造 Prompt：因为是第一轮对话，对话历史就是用户的第一次输入
    prompt = AgentPrompts.SESSION_TITLE_SUMMARY.format(user_input=f"用户: {original_query}")
    
    # 获取不带工具的 Agent
    # 标题生成使用 lite 模型 (速度快)
    agent = await get_agent(system_prompt=prompt, llm_type="lite")
    
    # 调用 Agent
    response = await agent.ainvoke({"messages": [HumanMessage(content=original_query)]})
    
    # 提取生成的标题
    title = response["messages"][-1].content.strip()
    print(f"生成的标题: {title}")

    # 更新数据库中的会话标题
    session_id = state.get("session_id")
    if session_id:
        try:
            from services.session_service import session_service
            await session_service.update_session_title(session_id, title)
        except Exception as e:
            print(f"更新会话标题失败: {e}")

    return {"conversation_title": title}

async def intention_recognition(state: OverAllState) -> dict:
    """
      意图识别

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
      """
    print("执行节点: intention_recognition")
    from work_flow.agent import get_agent
    from work_flow.agent.prompt import AgentPrompts
    from langchain_core.messages import HumanMessage

    original_query = state.get("original_query", "")
    
    # 构造 Prompt
    prompt = AgentPrompts.INTENT_RECOGNITION.format(user_input=original_query)
    
    # 调用不带工具的 Agent 进行分析
    agent = await get_agent(system_prompt=prompt)
    response = await agent.ainvoke({"messages": [HumanMessage(content=original_query)]})
    
    # 获取意图分类结果
    intent = response["messages"][-1].content.strip().lower()
    print(f"识别到的意图: {intent}")

    rag_use = False
    tavily_use = False

    if "rag" in intent:
        rag_use = True
    elif "tavily" in intent:
        tavily_use = True
    elif "research" in intent:
        rag_use = True
        tavily_use = True
    else:
        # 默认兜底策略：如果无法识别，默认走网络搜索
        tavily_use = True

    return {"rag_use": rag_use, "tavily_use": tavily_use}

def convergence_node(state: OverAllState) -> dict:
    """
      汇合节点

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
      """
    print("执行节点: convergence_node")
    # 等待前序任务完成，继续传递工作流
    return {}

async def llm_response(state: OverAllState, config: RunnableConfig) -> dict:
    """
      生成回复节点

      Args:
         state: 当前状态
         config: 运行时配置

      Returns:
         dict: 更新后的状态
    """
    print("执行节点: llm_response")
    from work_flow.agent import get_agent
    from work_flow.agent.prompt import AgentPrompts
    from langchain_core.messages import HumanMessage

    # 1. 提取所有上下文信息
    user_input = state.get("original_query", "")
    memory_summary = state.get("memory_summary", "无")
    
    # 格式化最近三轮对话
    conversation_history = state.get("conversation_history", [])
    recent_history_str = ""
    for i, (q, a) in enumerate(conversation_history):
        recent_history_str += f"轮次 {i+1}:\n用户: {q}\n助手: {a}\n\n"
    if not recent_history_str:
        recent_history_str = "无"

    # 获取检索上下文 (可能是 rag, tavily 或 mix 的结果)
    # 根据 rag_use 和 tavily_use 状态判断是否加入 context
    rag_use = state.get("rag_use", False)
    tavily_use = state.get("tavily_use", False)
    
    context_parts = []
    
    if rag_use:
        rag_out = state.get("rag_output", "未找到相关本地知识。")
        context_parts.append(f"【本地知识库检索结果】\n{rag_out}")
        
    if tavily_use:
        tavily_out = state.get("tavily_output", "未找到相关网络信息。")
        context_parts.append(f"【互联网搜索结果】\n{tavily_out}")
        
    if not context_parts:
        context = "未执行检索，请基于现有知识回答。"
    else:
        context = "\n\n".join(context_parts)

    # 2. 构造 Prompt
    prompt = AgentPrompts.FINAL_GENERATION_PROMPT.format(
        user_input=user_input,
        memory_summary=memory_summary,
        recent_history=recent_history_str,
        context=context
    )

    # 3. 调用 Agent 生成回复
    # 添加 tag 以便在流式输出中识别
    child_config = config.copy()
    if "tags" not in child_config:
        child_config["tags"] = []
    child_config["tags"].append("node:llm_response")
    
    agent = await get_agent(system_prompt=prompt)
    response = await agent.ainvoke({"messages": [HumanMessage(content="请生成回答")]}, config=child_config)
    
    final_answer = response["messages"][-1].content.strip()
    print(f"LLM回复生成完成，长度: {len(final_answer)}")

    return {"final_answer": final_answer}

async def memory_summary(state: OverAllState) -> dict:
    """
      记忆总结节点

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
    """
    print("执行节点: memory_summary")
    from db.database import SessionLocal
    from db.db_models import ConversationHistory, SessionSummary
    from work_flow.agent import get_agent
    from work_flow.agent.prompt import AgentPrompts
    from langchain_core.messages import HumanMessage
    from sqlalchemy import select
    import uuid

    user_id = state.get("user_id")
    session_id = state.get("session_id")
    original_query = state.get("original_query")
    final_answer = state.get("final_answer")

    async with SessionLocal() as db:
        # 1. 存储本轮短时记忆
        new_history = ConversationHistory(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            user_input=original_query,
            agent_output=final_answer
        )
        db.add(new_history)
        await db.commit()
        print("短时记忆存储完成")

        # 2. 生成并更新长时记忆摘要
        # 获取现有的摘要
        summary_result = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
        existing_summary_obj = summary_result.scalars().first()
        existing_summary = existing_summary_obj.summary if existing_summary_obj else "无"

        # 获取短期会话记忆 (List[Tuple[str, str]])
        conversation_history = state.get("conversation_history", [])
        
        # 将本轮对话临时加入到历史中，用于生成摘要
        # 注意：这里只是为了生成 prompt，真正的状态更新在最后
        current_history_for_summary = conversation_history + [(original_query, final_answer)]
        
        # 将 conversation_history 格式化为字符串
        history_str = ""
        for i, (q, a) in enumerate(current_history_for_summary):
            history_str += f"轮次 {i+1}:\n用户: {q}\n助手: {a}\n\n"
        
        # 构造 Prompt
        prompt = AgentPrompts.SESSION_SUMMARY_PROMPT.format(
            existing_summary=existing_summary,
            recent_history=history_str
        )

        # 调用 Agent 生成新摘要
        # 摘要生成使用 lite 模型 (速度快且足够胜任)
        agent = await get_agent(system_prompt=prompt, llm_type="lite")
        response = await agent.ainvoke({"messages": [HumanMessage(content="请更新摘要")]})
        new_summary = response["messages"][-1].content.strip()

        # 更新或插入摘要
        if existing_summary_obj:
            existing_summary_obj.summary = new_summary
        else:
            new_summary_obj = SessionSummary(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=user_id,
                summary=new_summary
            )
            db.add(new_summary_obj)
        
        await db.commit()
        print("长时记忆摘要更新完成")

    # --- 关键步骤：更新状态以同步到 Checkpointer ---
    # 我们必须把本轮对话追加到 conversation_history 中并返回
    # 这样 MemorySaver 才会保存最新的历史，供下一次"内存命中"使用
    updated_history = conversation_history + [(original_query, final_answer)]
    
    # 简单的内存管理：限制只保留最近 10 轮，防止内存无限膨胀
    if len(updated_history) > 10:
        updated_history = updated_history[-10:]

    return {
        "memory_summary": new_summary,
        "conversation_history": updated_history
    }

async def rag_process(state: OverAllState) -> dict:
    """
      rag检索节点

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
    """
    print("执行节点: rag_process")
    from services.knowledge_service import knowledge_service
    
    # 获取用户查询
    original_query = state.get("original_query", "")
    
    # 调用知识库搜索
    # 默认返回 limit=5 条结果
    # search_content 返回格式: [[{'file_id':..., 'text':..., 'score':...}, ...]]
    search_results = await knowledge_service.search_content(query=original_query, limit=5)
    
    # 格式化检索结果
    rag_output = ""
    if search_results and len(search_results) > 0:
        for i, item in enumerate(search_results[0]):
            rag_output += f"来源 {i+1}:\n{item.get('text', '')}\n\n"
    else:
        rag_output = "知识库中未找到相关内容。"
        
    print(f"RAG检索完成，结果长度: {len(rag_output)}")

    return {"rag_output": rag_output}

async def tavily_process(state: OverAllState) -> dict:
    """
      tavily检索节点

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
    """
    print("执行节点: tavily_temp")
    from langchain_tavily import TavilySearch
    from config.loader import get_config
    
    config = get_config()
    tavily_search_tool = TavilySearch(tavily_api_key=config.tavily_api_key)
    
    # 获取用户查询
    original_query = state.get("original_query", "")
    
    # 调用 Tavily 搜索
    # tavily_search_tool.ainvoke(query) 返回的是搜索结果的字符串摘要
    search_result = await tavily_search_tool.ainvoke(original_query)
    
    print(f"Tavily检索完成，结果长度: {len(search_result)}")

    return {"tavily_output": search_result}

async def mix_process(state: OverAllState) -> dict:
    """
      混合检索节点：同时执行 RAG 和 Tavily 检索

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
    """
    print("执行节点: mix_temp (同时执行 RAG 和 Tavily)")
    from services.knowledge_service import knowledge_service
    from langchain_tavily import TavilySearch
    from config.loader import get_config
    import asyncio

    config = get_config()
    tavily_search_tool = TavilySearch(tavily_api_key=config.tavily_api_key)
    
    original_query = state.get("original_query", "")

    # 定义异步任务
    async def run_rag():
        results = await knowledge_service.search_content(query=original_query, limit=5)
        output = ""
        if results and len(results) > 0:
            for i, item in enumerate(results[0]):
                output += f"来源 {i+1}:\n{item.get('text', '')}\n\n"
        else:
            output = "知识库中未找到相关内容。"
        return output

    async def run_tavily():
        return await tavily_search_tool.ainvoke(original_query)

    # 并发执行两个任务
    rag_result, tavily_result = await asyncio.gather(run_rag(), run_tavily())

    # 整合结果
    mix_output = f"""
=== 本地知识库检索结果 ===
{rag_result}

=== 互联网搜索结果 ===
{tavily_result}
"""
    print(f"混合检索完成，总长度: {len(mix_output)}")
    return {"rag_output": rag_result, "tavily_output": tavily_result}

def finish(state :OverAllState) -> dict:
    """
      汇总结束节点

      Args:
         state: 当前状态

      Returns:
         dict: 更新后的状态
    """
    return
