"""
Docstring for backend.services.knowledge_service
构建知识库相关接口
"""
import opendal
from opendal import Operator, AsyncOperator
from pymilvus import MilvusClient, DataType, FunctionType, Function, AsyncMilvusClient
from langchain.embeddings import init_embeddings
from config.loader import get_config
from config.loguru_config import get_logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_models import KnowledgeFile, KnowledgeChunk
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

config = get_config()
logger = get_logger()

class SearchStrategy:
    """
    搜索策略枚举类
    """
    HYBRID = "hybrid"
    VECTOR = "vector"
    FULL_TEXT = "full_text"

class KnowledgeService:
    """
    知识库相关的service逻辑层
    """
    bm25_function = Function(
        name="text_bm25_emb",
        input_field_names=["text"],
        output_field_names=["text_sparse"],
        function_type=FunctionType.BM25,
    )

    def __init__(self):
        # storage_type实现可插拔的存储组件,可以使用file system 和OSS对象存储
        
        storage_type = config.storage.storage_type
        scheme = config.storage.scheme
        # retry_layer = opendal.layers.RetryLayer(max_times=3, factor=2.0, jitter=True)
        # self.op = AsyncOperator(scheme=scheme)

        self.milvus_client = AsyncMilvusClient(
            uri=config.milvus.uri,
            token=config.milvus.token
        )
        # 判断collection是否存在，如果不存在进行初始化

        # await self._ensure_collection_exists()
        
        # 初始化embedding模型
        self.embedding_model = init_embeddings(
            model=config.embedding.model, 
            provider=config.embedding.provider, 
            api_key=config.embedding.api_key, 
            base_url=config.embedding.base_url)
        
        # 此处采用多线程方式进行解析，实际生产环境下，可以单独配置celery worker进行异步解析
        self.parse_executor = ThreadPoolExecutor(max_workers=10)

    async def _ensure_collection_exists(self):
        if not await self.milvus_client.has_collection(collection_name=config.milvus.collection_name):
            await self._init_collection()

    async def _init_collection(self,):
        """
        初始化collection信息
        通过milvus来实现混合检索，
        稀疏向量，用以做全文检索，
        稠密向量，用以做向量检索
        """
        schema = self.milvus_client.create_schema()

        schema.add_field(
            field_name="id",
            datatype=DataType.INT64,
            is_primary=True,
            auto_id=True
        )
        analyzer_params = {
            "type":"chinese"
        }
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            analyzer_params=analyzer_params, # 使用自定义的中文分析器
        )
        schema.add_field(
            field_name="text_sparse",
            datatype=DataType.SPARSE_FLOAT_VECTOR
        )
        schema.add_field(
            field_name="text_dense",
            datatype=DataType.FLOAT_VECTOR,
            dim=config.embedding.dim
        )
        schema.add_field(
            field_name="file_id",
            datatype=DataType.VARCHAR,
            max_length=255
        )
        schema.add_function(self.bm25_function)

        index_params = self.milvus_client.prepare_index_params()

        index_params.add_index(
            field_name="text_sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                # "bm25_k1": 1.2,
                # "bm25_b": 0.75
            }
        )
        
        index_params.add_index(
            field_name="text_dense",
            index_name="text_dense_index",
            index_type="HNSW",
            metric_type="COSINE",
             params={
                "M": 16,
                "efConstruction": 200
            }
        )

        await self.milvus_client.create_collection(
            collection_name=config.milvus.collection_name,
            schema=schema,
            index_params=index_params
        )

    async def get_user_files(self, user_id: str,db: AsyncSession):
        """
        获取用户的所有知识库文件信息
        :param user_id: 用户ID
        :return: List[KnowledgeFile]
        """
        
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.user_id == user_id))
        files = result.scalars().all()
        return files

    async def upload_file(self, user_id: str, file_name: str, file_content: bytes,db: AsyncSession):
        """
        上传文件：
            1、生成唯一的文件ID
            2、构建文件存储路径
            3、将文件内容写入到存储后端
            4、将文件元数据保存至数据库
        
        todo:
            边界情况/异常情况处理
            1、上传到一半，网络等异常导致上传失败，需要回滚数据库

        :param user_id: 用户ID
        :param file_name: 文件名
        :param file_content: 文件内容
        :return: KnowledgeFile
        """
        file_id = str(uuid.uuid4())
        file_path = f"{user_id}/{file_id}/{file_name}"
        
        # 写入到具体的存储后端
        await self.op.write(file_path, file_content)
        
        # 将数据保存至数据库当中
        new_file = KnowledgeFile(
            id=file_id,
            user_id=user_id,
            file_name=file_name,
            file_size=len(file_content),
            file_type=file_name.split('.')[-1],
            storage_path=file_path,
            is_parsed=False,
            parse_status="pending"
        )
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        return new_file
    
    async def delete_file(self, user_id: str, file_id: str,db: AsyncSession):
        """
        删除文件
        :param user_id: 用户ID
        :param file_id: 文件ID
        :return: bool
        """
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id))
        file_record = result.scalars().first()
        if not file_record:
                return False
            

        await self.op.delete(file_record.storage_path)

        # Delete chunks from Milvus 
        
        await self._ensure_collection_exists()
        await self.milvus_client.delete(
            collection_name=config.milvus.collection_name,
            filter=f"file_id == '{file_id}'"
        )
        from sqlalchemy import delete
        await db.execute(delete(KnowledgeFile).where(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id))
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.file_id == file_id))
        
        await db.delete(file_record)
        await db.commit()
        return True
    
    async def submit_parse_task(self, user_id: str, file_id: str, db: AsyncSession):
        """
        提交解析任务
        :param user_id: 用户ID
        :param file_id: 文件ID
        :return: task_id (str)
        """
        # 查询文件记录
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id))
        file_record = result.scalars().first()
        
        if file_record:
            # 更新状态为处理中
            file_record.parse_status = "processing"
            await db.commit()
            
            # 提交到线程池执行
            # 注意：在异步上下文中，我们需要确保数据库操作是线程安全的
            # 这里我们传递必要的信息，在任务内部创建新的数据库会话
            self.parse_executor.submit(
                self._run_parse_task,
                user_id,
                file_id
            )
            
            return file_id 
        return None

    def _run_parse_task(self, user_id: str, file_id: str):
        """
        在线程池中运行的解析任务
        需要创建一个新的事件循环来运行异步代码，或者使用同步方式处理
        由于我们的数据库操作是异步的，这里我们需要运行异步代码
        """
        try:
            # 创建一个新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步解析任务
            loop.run_until_complete(self._process_file_parsing(user_id, file_id))
            
            loop.close()
        except Exception as e:
            # 记录错误日志
            logger.error(f"Error in parse task: {e}")
            # 这里应该有错误处理逻辑，比如更新数据库状态为 failed
            # 由于是在线程中，我们需要单独处理数据库连接

    async def _process_file_parsing(self, user_id: str, file_id: str):
        """
        实际的解析逻辑
        """
        from db.database import SessionLocal
        import magic
        from services.parsers.pdf_parser import PDFParser
        from services.parsers.csv_parser import CSVParser
        

        async with SessionLocal() as db:
            try:
                # 获取文件记录
                result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id))
                file_record = result.scalars().first()
                
                if not file_record:
                    return

                # 1. 从存储中读取文件内容
                file_content = await self.op.read(file_record.storage_path)
                
                # 2. 判断文件类型
                mime_type = magic.from_buffer(file_content, mime=True)
                
                # 3. 根据文件类型选择解析器
                parser = None
                if mime_type == 'application/pdf':
                    parser = PDFParser()
                elif mime_type == 'text/csv' or mime_type == 'text/plain': # csv sometimes detected as text/plain
                     if file_record.file_name.endswith('.csv'):
                         parser = CSVParser()
                
                if parser:
                    # 临时保存文件以便解析器使用（如果解析器需要文件路径）
                    # 这里假设解析器需要文件路径，我们先写入临时文件
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_record.file_type}") as tmp_file:
                        tmp_file.write(file_content)
                        tmp_path = tmp_file.name
                        
                    try:
                        documents = parser.parse(tmp_path)
                        # todo: 处理解析后的文档，切分，embedding，存入Milvus
                        # 这里暂时只做解析
                        logger.info(f"Parsed {len(documents)} documents from {file_record.file_name}")
                        
                    finally:
                        os.remove(tmp_path)

                # 模拟解析完成
                file_record.parse_status = "completed"
                file_record.is_parsed = True
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                if file_record:
                    file_record.parse_status = "failed"
                    await db.commit()
    
    async def get_parse_status(self, task_id: str,db: AsyncSession):
        """
        获取解析状态
        :param task_id: 任务ID (here we use file_id as task_id for simplicity)
        :return: ParseProgressResponse data dict
        """
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == task_id))
        file_record = result.scalars().first()
        if not file_record:
            return None
        return {"status": file_record.parse_status}

    async def search_content(self, query: str | list[str], limit: int = 5,search_strategy:str = SearchStrategy.HYBRID)->list[list[dict]]:
        """
        根据 query 召回文档，
        :param query: 查询语句
        :param limit: 返回数量
        :param search_strategy: 搜索策略
        :return: List[Dict]

        返回结果为： 第一层为搜索batch,第二层为每个query具体的搜索结果
        [[
        {
            'file_id':'456',
            'file_name':'2025财务年度中期报告（繁体中文）.pdf'
            'text':'具体chunk文档内容',
            'score':0.95,
        }
        ]]
        """
        from pymilvus import AnnSearchRequest
        await self._ensure_collection_exists()
        
        from pymilvus import AnnSearchRequest

        query_text = "white headphones, quiet and comfortable"
        query_dense_vector = await self.embedding_model.aembed_query(query)
        

        search_param_1 = {
            "data": [query_dense_vector],
            "anns_field": "text_dense",
            "param": {"nprobe": 10},
            "limit": 2
        }
        request_1 = AnnSearchRequest(**search_param_1)

        search_param_2 = {
            "data": [query_text],
            "anns_field": "text_sparse",
            "param": {"drop_ratio_search": 0.2},
            "limit": 2
        }
        request_2 = AnnSearchRequest(**search_param_2)

        

        reqs = [request_1, request_2]

        ranker = Function(
            name="rrf",
            input_field_names=[], # Must be an empty list
            function_type=FunctionType.RERANK,
            params={
                "reranker": "rrf", 
                "k": 100  # Optional
            }
        )

        result = await self.milvus_client.hybrid_search(
            collection_name=config.milvus.collection_name,
            reqs=reqs,
            ranker=ranker,
            limit=limit,
            output_fields=["id", "file_id", "text"],
        )

        return result

    
    
        
    


knowledge_service = KnowledgeService()