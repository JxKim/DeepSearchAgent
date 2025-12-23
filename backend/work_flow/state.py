from typing import TypedDict, List, Tuple


class OverAllState(TypedDict):
   user_id: str   #用户ID
   session_id: str   #会话ID
   conversation_history: List[Tuple[str, str]]  #短期会话记忆
   original_query: str  #原始查询

   # 会话标题节点生成
   conversation_title:str  #会话标题

   # 长期记忆导入节点生成
   memory_summary:List[str]   #长期记忆摘要

   # 意图识别节点
   rag_use:bool   #是否使用RAG
   tavily_use:bool   #是否使用Tavily

   # 生成最终回答节点
   final_answer:str  #最终回答

   rag_output:str  #RAG检索输出

   tavily_output:str #tavily检索输出