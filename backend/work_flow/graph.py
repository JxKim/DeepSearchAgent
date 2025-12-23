from typing import Literal

from langgraph.constants import START
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from work_flow.state import OverAllState
from work_flow import node

# 条件边的路由函数
def route_condition(state: OverAllState) -> Literal["mix", "rag", "tavily"]:
   """根据value值决定路由到哪个节点"""
   if state["rag_use"]  == True and state["tavily_use"] == True:
      return "mix" # 偶数路由到节点B
   elif state["rag_use"] == True and state["tavily_use"] == False:
      return "rag" # 奇数路由到节点C
   else:
       return "tavily"

def main_graph(checkpointer=None):
   # 每次调用时创建新的 builder，避免重复添加节点报错
   builder = StateGraph(OverAllState)

   builder.add_node("long_term_memory_import", node.long_term_memory_import)
   builder.add_node("title_generate", node.title_generate)
   builder.add_node("intention_recognition", node.intention_recognition)
   builder.add_node("convergence_node", node.convergence_node, defer = True)
   builder.add_node("llm_response", node.llm_response)
   builder.add_node("memory_summary", node.memory_summary)
   builder.add_node("rag_process",node.rag_process)
   builder.add_node("tavily_process",node.tavily_process)
   builder.add_node("mix_process",node.mix_process)

   builder.add_edge(START,"long_term_memory_import")
   builder.add_edge(START,"title_generate")
   builder.add_edge("long_term_memory_import","intention_recognition")
   builder.add_edge("title_generate","convergence_node")
   builder.add_edge("intention_recognition","convergence_node")
   builder.add_conditional_edges(
      "convergence_node",
      route_condition,
      {
         "mix": "mix_process",
         "tavily": "tavily_process",
         "rag": "rag_process"
      }
   )
   builder.add_edge("mix_process","llm_response")
   builder.add_edge("tavily_process","llm_response")
   builder.add_edge("rag_process","llm_response")
   builder.add_edge("llm_response","memory_summary")
   builder.add_edge("memory_summary",END)
   
   # 如果没有传入 checkpointer，则不启用持久化
   if checkpointer:
       return builder.compile(checkpointer=checkpointer)
   return builder.compile()

# 提供工厂函数
def create_graph(checkpointer=None):
    return main_graph(checkpointer)

# 默认实例 (使用 MemorySaver，方便测试和单机运行)
default_saver = MemorySaver()
graph = create_graph(checkpointer=default_saver)
graph.invoke
