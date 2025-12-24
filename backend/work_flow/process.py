from langgraph.checkpoint.memory import MemorySaver
from config.loader import get_config
from db.redis import SimpleRedisSaver
from work_flow.graph import create_graph
from config.loguru_config import get_logger
logger = get_logger(__name__)

# 尝试导入 Redis 相关库
try:
    from redis.asyncio import Redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

async def get_redis_checkpointer():
    """
    获取 Redis 持久化器 (Checkpointer)
    如果 Redis 不可用或连接失败，自动降级为 MemorySaver
    """
    if not HAS_REDIS:
        logger.info("ℹ️ 未安装 Redis 库，使用 MemorySaver")
        return MemorySaver()
  
    try:
        # 读取配置
        config = get_config()
        redis_config = config.redis
        
        if redis_config and redis_config.url:
            redis_url = redis_config.url
        elif redis_config:
            auth_part = f":{redis_config.password}@" if redis_config.password else ""
            redis_url = f"redis://{auth_part}{redis_config.host}:{redis_config.port}/{redis_config.db}"
        else:
            redis_url = "redis://localhost:6379/0"

        logger.info(f"🔄 正在连接 Redis: {redis_url} ...")
        
        # 建立连接
        redis_client = Redis.from_url(redis_url)
        # 测试连接是否通畅
        await redis_client.ping()
        
        checkpointer = SimpleRedisSaver(redis_client)
        logger.info("✅ Redis Checkpointer (Custom) 就绪")
        return checkpointer
        
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}，降级使用 MemorySaver")
        return MemorySaver()

async def run_workflow(session_id: str, user_id: str, original_query: str, thread_id: str = None, checkpointer=None):
    """
    运行工作流
    
    Args:
        session_id (str): 会话ID
        user_id (str): 用户ID
        original_query (str): 用户查询
        thread_id (str, optional): 线程ID，用于持久化状态隔离。如果不传，默认使用 session_id
        checkpointer (optional): 传入已初始化的 checkpointer，避免重复创建
    
    Returns:
        dict: 工作流执行结果
    """
    
    # 如果没有传入 checkpointer，则尝试获取
    if checkpointer is None:
        checkpointer = await get_redis_checkpointer()

    # 创建图
    graph = create_graph(checkpointer=checkpointer)
    
    # 构造初始状态
    initial_state = {
        "user_id": user_id, 
        "session_id": session_id,
        "original_query": original_query
    }
    
    # 如果没传 thread_id，默认使用 session_id
    if not thread_id:
        thread_id = session_id
        
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"▶️ 开始执行工作流 [Thread: {thread_id}]")
    print(f"👤 用户: {user_id} | 💬 查询: {original_query}")
    
    try:
        # 异步调用图
        result = await graph.ainvoke(initial_state, config=config)
        return result
    except Exception as e:
        print(f"❌ 工作流执行出错: {e}")
        import traceback
        traceback.print_exc()
        raise e

async def stream_workflow(session_id: str, user_id: str, original_query: str, thread_id: str = None, checkpointer=None):
    """
    流式运行工作流 (Generator)
    """
    if checkpointer is None:
        checkpointer = await get_redis_checkpointer()

    graph = create_graph(checkpointer=checkpointer)
    
    initial_state = {
        "user_id": user_id, 
        "session_id": session_id,
        "original_query": original_query
    }
    
    if not thread_id:
        thread_id = session_id
        
    config = {"configurable": {"thread_id": thread_id}}
    
    # 使用 astream_events 获取更细粒度的流式更新 (包括 LLM 的 token 流)
    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            
            # 1. 处理 LLM 流式输出 (Token 级别)
            if kind == "on_chat_model_stream":
                # 获取当前生成的 token
                content = event["data"]["chunk"].content
                
                # 获取事件 tags
                tags = event.get("tags", [])
                
                # 只流式传输带有 node:llm_response 标签的输出
                if content and "node:llm_response" in tags:
                    yield {
                        "event": "llm_stream",
                        "node": "llm_response", 
                        "data": content
                    }
            
            # 2. 处理节点状态更新 (Node 级别)
            elif kind == "on_chain_end":
                # 筛选出图节点的结束事件
                if event["name"] and event["name"] in graph.nodes:
                    node_name = event["name"]
                    # 注意：on_chain_end 的 output 可能是 State update，也可能是其他
                    # 这里我们主要关注节点执行完成的信号，具体数据可能需要根据节点返回值结构调整
                    # 为了保持兼容性，我们可以简化处理，或者只发送特定节点的结束信号
                    
                    # 只有当 output 是字典且包含更新时才发送
                    output = event["data"].get("output")
                    if isinstance(output, dict):
                         yield {
                            "event": "node_update",
                            "node": node_name,
                            "data": output
                        }
                        
    except Exception as e:
        print(f"❌ 流式执行出错: {e}")
        yield {"event": "error", "error": str(e)}
        raise e

async def main():
    # 初始化数据库连接
    from db.database import db_startup, db_shutdown
    await db_startup()
    
    checkpointer = await get_redis_checkpointer()
    
    try:
        # 测试数据
        session_id = "session_memory_demo_final"
        user_id = "bf1aea34-4dea-4a08-aed4-42734bc78a46"
        thread_id = session_id # 使用 session_id 作为 thread_id
        
        print(f"\n=== [Run 1] 第一次调用 (冷启动) ===")
        query_1 = "DeepSeek R1模型的主要特点是什么？"
        result_1 = await run_workflow(
            session_id=session_id,
            user_id=user_id,
            original_query=query_1,
            thread_id=thread_id,
            checkpointer=checkpointer
        )
        print(f"✅ [Run 1] 完成. 最终回答: {result_1.get('final_answer')[:30]}...")

        print(f"\n\n=== [Run 2] 第二次调用 (热运行) ===")
        query_2 = "那它的推理成本相比o1如何？"
        result_2 = await run_workflow(
            session_id=session_id,
            user_id=user_id,
            original_query=query_2,
            thread_id=thread_id,
            checkpointer=checkpointer
        )
        print(f"✅ [Run 2] 完成. 最终回答: {result_2.get('final_answer')[:30]}...")
        
        # 验证历史记录
        history = result_2.get("conversation_history", [])
        print(f"\n🏆 最终验证：当前历史对话条数: {len(history)} (应为 2 条)")

    finally:
        await db_shutdown()
        # 关闭 Redis 连接
        if hasattr(checkpointer, "client"):
            await checkpointer.client.aclose()

if __name__ == "__main__":
    import sys
    import asyncio
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
