from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from typing import Optional, Any, Sequence, Tuple
import json
from config.loader import get_config

# 手动实现 Redis Saver，规避库版本兼容问题
class SimpleRedisSaver(BaseCheckpointSaver):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.serde = JsonPlusSerializer()

    async def aget_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        data = await self.client.get(key)
        if not data:
            return None
        
        if isinstance(data, bytes):
            data = data.decode('utf-8')
            
        saved_data = json.loads(data)
        
        # 恢复 CheckpointTuple
        checkpoint_blob = saved_data["checkpoint"]
        
        if isinstance(checkpoint_blob, list):
            checkpoint_blob = tuple(checkpoint_blob)
            encoding = saved_data.get("encoding", "utf-8")
            
            type_str = checkpoint_blob[0]
            data_content = checkpoint_blob[1]
            
            if encoding == "hex":
                try:
                    data_content = bytes.fromhex(data_content)
                except ValueError:
                    pass 
            
            checkpoint_blob = (type_str, data_content)

        try:
             checkpoint = self.serde.loads_typed(checkpoint_blob)
        except Exception as e:
             print(f"Error loading checkpoint: {e}")
             return None

        metadata = saved_data["metadata"]
        parent_config = saved_data.get("parent_config")
        
        return CheckpointTuple(config, checkpoint, metadata, parent_config, [])

    def _sanitize_for_json(self, obj):
        """递归清洗对象，使其可被 JSON 序列化"""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, bytes):
            return obj.hex() 
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items() if isinstance(k, str)}
        return None 

    async def aput(self, config: dict, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> dict:
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        
        serialized_tuple = self.serde.dumps_typed(checkpoint)
        type_str = serialized_tuple[0]
        data_raw = serialized_tuple[1]
        encoding = "utf-8"
        
        if isinstance(data_raw, bytes):
            data_to_store = data_raw.hex()
            encoding = "hex"
        else:
            data_to_store = data_raw
        
        clean_config = {
            "configurable": config.get("configurable", {})
        }
        
        clean_metadata = self._sanitize_for_json(metadata)

        save_data = {
            "checkpoint": [type_str, data_to_store], 
            "metadata": clean_metadata,
            "parent_config": clean_config,
            "encoding": encoding
        }
        
        def json_default(obj):
            try:
                return str(obj)
            except:
                return "<not_serializable>"
        
        await self.client.set(key, json.dumps(save_data, default=json_default))
        return config

    # 实现 aput_writes 以支持 LangGraph 3.x
    async def aput_writes(self, config: dict, writes: Sequence[Tuple[str, Any]], task_id: str) -> None:
        """存储中间写入结果"""
        # 为了简化，我们暂时只做空实现，或者简单打印
        # 完整的 RedisSaver 会将其存储到 Hash 或 List 中
        # 如果不需要"从断点恢复"的高级功能，空实现通常是可以的
        # print(f"DEBUG: aput_writes called for task {task_id}")
        pass