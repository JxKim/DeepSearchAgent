from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
from pathlib import Path
from config.loader import get_config
config = get_config()

async def get_agent(system_prompt: str, llm_type: str = "standard"):
    """
    获取Agent实例
    :param system_prompt: 系统提示词，作为参数传入，而非固定
    :param llm_type: LLM类型，'standard' (高质量) 或 'lite' (高响应速度)
    :return: agent
    """
    from langchain_deepseek import ChatDeepSeek
    from langchain_openai import ChatOpenAI
    
    # 根据 llm_type 选择配置
    if llm_type == "lite" and config.lite_llm:
        target_config = config.lite_llm
    else:
        target_config = config.llm

    # 根据 provider 选择不同的 Chat 模型类
    # 注意：这里假设 config 中有 provider 字段，或者根据实际情况调整
    # 之前代码写死用 ChatDeepSeek，但 lite-llm 可能是 OpenAI 格式
    
    if target_config.provider == "deepseek":
        llm = ChatDeepSeek(
            model=target_config.model,
            api_key=target_config.api_key,
            base_url=target_config.base_url,
            temperature=target_config.temperature
        )
    else:
        # 默认使用 OpenAI 兼容客户端 (适用于 dashscope/openai/其他)
        openai_kwargs = {}
        # 针对阿里云 DashScope 的特殊处理：非流式调用需要显式关闭 thinking
        if "dashscope" in target_config.base_url:
            print("Detected DashScope, setting enable_thinking=False in extra_body")
            openai_kwargs["extra_body"] = {"enable_thinking": False}

        llm = ChatOpenAI(
            model=target_config.model,
            api_key=target_config.api_key,
            base_url=target_config.base_url,
            temperature=target_config.temperature,
            **openai_kwargs
        )
    
    # 确保存储路径存在
    db_path = Path(__file__).parent / "data" / "langgraph_checkpoint"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = await aiosqlite.connect(str(db_path))
    sqlite_saver = AsyncSqliteSaver(
        conn=conn
    )

    agent = create_agent(
        model=llm,
        tools=[],
        checkpointer=sqlite_saver,
        system_prompt=system_prompt # 使用传入的 prompt
    )

    return agent

if __name__ == '__main__':
    pass
