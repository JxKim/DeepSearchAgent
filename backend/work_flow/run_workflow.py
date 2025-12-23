import sys
import os
import asyncio

# 1. 配置 Python 路径
# 获取当前脚本所在目录 (backend/work_flow)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取 backend 目录 (父目录)
backend_dir = os.path.dirname(current_dir)

# 将 backend 目录加入路径，以便能导入 services, config, db 等
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# 将 work_flow 目录本身也加入路径，以便能直接导入 state, node 等 (如果代码中有 from state import ... 这种写法)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 现在可以导入 graph 了
from work_flow.graph import graph
from db.database import db_startup, db_shutdown

async def main():
    # 初始化数据库连接
    await db_startup()
    
    # 2. 构造初始状态
    # 这里模拟一个用户提问
    initial_state = {
        # 使用数据库中真实存在的 user_001 的 UUID
        "user_id": "bf1aea34-4dea-4a08-aed4-42734bc78a46", 
        "session_id": "session_test_001",
        # 您可以修改这里的问题来测试不同的路由 (rag, tavily, 或 mix)
        "original_query": "DeepSeek R1模型的主要特点是什么？它和OpenAI o1有什么区别？" 
    }
    
    print(f"=== 开始执行工作流 ===\n用户问题: {initial_state['original_query']}\n")
    
    try:
        # 3. 异步调用图
        # 使用 ainvoke 因为我们的节点大都是 async 的
        result = await graph.ainvoke(initial_state)
        
        print("\n=== 执行完成 ===")
        print(f"最终回答:\n{result.get('final_answer')}")
        
        print("\n--- 调试信息 ---")
        print(f"RAG使用: {result.get('rag_use')}")
        print(f"Tavily使用: {result.get('tavily_use')}")
        if result.get('conversation_title'):
            print(f"生成的标题: {result.get('conversation_title')}")
        
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭数据库连接
        await db_shutdown()

if __name__ == "__main__":
    # Windows 下通常需要设置事件循环策略以避免某些 asyncio 错误
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
