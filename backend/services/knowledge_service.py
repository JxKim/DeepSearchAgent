"""
Docstring for backend.services.knowledge_service
构建知识库相关接口

todo: 
1、解析过程是否使用线程池
2、如果使用，那是否还需要使用协程
3、如果不使用，怎么实现异步提交任务的过程
"""
import opendal
from opendal import Operator, AsyncOperator
from pymilvus import MilvusClient, DataType, FunctionType, Function, AsyncMilvusClient
from langchain.embeddings import init_embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from config.loader import get_config
from config.loguru_config import get_logger
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_models import KnowledgeFile, KnowledgeChunk, KnowledgeCategory
import uuid
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_core.documents import Document
from mineru_vl_utils import MinerUClient
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
        
        # storage_type = config.storage.storage_type
        scheme = "fs"
        # retry_layer = opendal.layers.RetryLayer(max_times=3, factor=2.0, jitter=True)
        self.op = AsyncOperator(scheme=scheme,root=config.storage.file_path)

        # 异步的milvus client，在query时会使用到
        # 初始化时先设为None，在需要使用时再初始化，
        # 避免在单元测试时，__init__中创建异步连接导致的event loop问题 
        self._milvus_client = None
        
        # 同步的milvus client，在解析任务当中使用
        self.sync_milvus_client = MilvusClient(
            uri=config.milvus.uri,
            token=config.milvus.token
        )
        
        
        
        if config.embedding.provider == "self-hosted":
            self.embedding_model = HuggingFaceEmbeddings(model_name=config.embedding.model_path)
        else:
            self.embedding_model = init_embeddings(
                model=config.embedding.model, 
                provider=config.embedding.provider, 
                api_key=config.embedding.api_key, 
                base_url=config.embedding.base_url)
        # 此处采用多线程方式进行解析，实际生产环境下，可以单独配置celery worker进行异步解析
        self.parse_executor = ThreadPoolExecutor(max_workers=10)

        self.milvus_collection_name = config.milvus.collection_name

    @property
    def milvus_client(self):
        if self._milvus_client is None:
            self._milvus_client = AsyncMilvusClient(
                uri=config.milvus.uri,
                token=config.milvus.token
            )
        return self._milvus_client

    async def _ensure_collection_exists(self):
        if not await self.milvus_client.has_collection(collection_name=self.milvus_collection_name):
            await self._init_collection()

    async def _init_collection(self,):
        """
        初始化collection信息
        通过milvus来实现混合检索，
        稀疏向量，用以做全文检索，
        稠密向量，用以做向量检索
        """
        logger.info("开始初始化Milvus Collection")
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
        if await self.milvus_client.has_collection(collection_name=self.milvus_collection_name):
            logger.info("Milvus Collection 初始化完成")
        else:
            logger.error("Milvus Collection 初始化失败")

    async def get_user_files(self, user_id: str,db: AsyncSession):
        """
        获取用户的所有知识库文件信息
        :param user_id: 用户ID
        :return: List[KnowledgeFile]
        """
        
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.user_id == user_id))
        files = result.scalars().all()
        return files

    async def upload_file(self, user_id: str, file_name: str, file_content: bytes,db: AsyncSession,category_id: str = None):
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
        file_path = f"{user_id}_{file_id}_{file_name}"
        
        # 写入到具体的存储后端
        await self.op.write(file_path, file_content)
        logger.info(f"文件 {file_path} 上传成功")
        # 将数据保存至数据库当中
        new_file = KnowledgeFile(
            id=file_id,
            user_id=user_id,
            file_name=file_name,
            file_size=len(file_content),
            file_type=file_name.split('.')[-1],
            storage_path=file_path,
            is_parsed=False,
            parse_status="pending",
            category_id=category_id
        )
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        return new_file
    
    async def delete_file(self, user_id: str, file_id: str,db: AsyncSession)->bool:
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
            
        # 删除存储后端的文件
        await self.op.delete(file_record.storage_path)

        # Delete chunks from Milvus 
        
        await self._ensure_collection_exists()
        # 对于大批量的数据，milvus删除的性能怎么样？是否需要分批次删除？
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
        使用同步方式处理
        """
        from db.database import SyncSessionLocal
        
        # 确保数据库已初始化 (在某些极端的测试或脚本场景下可能未初始化)
        if not SyncSessionLocal:
             logger.error("SyncSessionLocal is not initialized!")
             return

        try:
            self._process_file_parsing_sync(user_id, file_id, SyncSessionLocal)
        except Exception as e:
            # 记录错误日志
            logger.error(f"Error in parse task: {e}")

    def _process_file_parsing_sync(self, user_id: str, file_id: str, SessionLocal):
        """
        实际的解析逻辑 (同步版本)
        """
        import magic
        from services.parsers.pdf_parser import MineruPDFLoader
        from services.parsers.markdown_parser import MarkdownParser
        from services.parsers.csv_parser import CSVParser
        import os
        
        with SessionLocal() as db:
            try:
                # 获取文件记录
                file_record = db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id)).scalars().first()
                
                if not file_record:
                    return

                # 1. 从存储中读取文件内容 (同步读取)
                # opendal 的 read 方法默认是 async 的，但是我们可以在这里使用 blocking operator 或者其它方式
                # 由于 self.op 是 AsyncOperator，我们需要一个 BlockingOperator
                
                from opendal import Operator
                blocking_op = Operator(scheme="fs", root=config.storage.file_path)
                file_content = blocking_op.read(file_record.storage_path)
                
                # 2. 判断文件类型
                mime_type = magic.from_buffer(file_content, mime=True)
                
                # 3. 根据文件类型选择解析器
                parser = None
                if mime_type == 'application/pdf':
                    parser = MineruPDFLoader()
                elif mime_type == 'text/csv' or mime_type == 'text/plain': # csv sometimes detected as text/plain
                     if file_record.file_name.endswith('.csv'):
                         parser = CSVParser()
                documents = []
                if parser:
                    # 临时保存文件以便解析器使用
                    import tempfile
                    try:
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_record.file_type}") as tmp_file:
                            tmp_file.write(file_content)
                            tmp_path = tmp_file.name
                            
                        # 同步解析
                        documents = parser.parse(tmp_path)
                            
                        logger.info("准备将数据写入Milvus")
                        self._ensure_collection_exists_sync()
                        
                        # 同步生成 embedding
                        texts = [doc.page_content for doc in documents]
                        milvus_data = []
                        logger.info(f"documents len: {len(documents)},开始将数据写入至Milvus")
                        start_time = time.time()
                        for i, doc in enumerate(documents):
                            milvus_data.append({
                                "file_id": file_id,
                                "file_name": file_record.file_name,
                                "text": doc.page_content,
                                "text_dense": self.embedding_model.embed_documents([doc.page_content])[0] # 注意这里可能需要优化，批量处理
                            })
                        end_time = time.time()
                        logger.info(f"成功将 {len(milvus_data)} 条数据生成embedding, 耗时: {end_time - start_time} 秒")

                        start_time = time.time()    
                        self.sync_milvus_client.insert(collection_name=self.milvus_collection_name, data=milvus_data)
                        end_time = time.time()
                        logger.info(f"成功将 {len(milvus_data)} 条数据写入Milvus, 耗时: {end_time - start_time} 秒")
                        logger.info(f"Parsed {len(documents)} documents from {file_record.file_name}")
                    except Exception as e:
                        logger.error(f"Error parsing {file_record.file_name}: {e}")
                        file_record.parse_status = "failed"
                        db.commit()
                        return
                    finally:
                        if 'tmp_path' in locals() and os.path.exists(tmp_path):
                            os.remove(tmp_path)

                # 模拟解析完成
                file_record.parse_status = "completed"
                file_record.is_parsed = True
                file_record.chunk_count = len(documents)
                db.commit()
                
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                if file_record:
                    file_record.parse_status = "failed"
                    db.commit()

    def _ensure_collection_exists_sync(self):
        
        if not self.sync_milvus_client.has_collection(collection_name=self.milvus_collection_name):
            logger.info(f"Collection {self.milvus_collection_name} not found, initializing...")
            self._init_collection_sync()

    def _init_collection_sync(self):
        """
        初始化collection信息 (同步版本)
        """
        logger.info("开始初始化Milvus Collection (Sync)")
        schema = self.sync_milvus_client.create_schema()

        schema.add_field(
            field_name="id",
            datatype=DataType.INT64,
            is_primary=True,
            auto_id=True
        )
        schema.add_field(
            field_name="file_name",
            datatype=DataType.VARCHAR,
            max_length=1024,
        )

        analyzer_params = {
            "type":"chinese"
        }
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            analyzer_params=analyzer_params, 
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

        index_params = self.sync_milvus_client.prepare_index_params()

        index_params.add_index(
            field_name="text_sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
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

        self.sync_milvus_client.create_collection(
            collection_name=config.milvus.collection_name,
            schema=schema,
            index_params=index_params
        )
        if self.sync_milvus_client.has_collection(collection_name=self.milvus_collection_name):
            logger.info("Milvus Collection 初始化完成 (Sync)")
        else:
            logger.error("Milvus Collection 初始化失败 (Sync)")
    
    async def get_parse_status(self, file_id: str,db: AsyncSession):
        """
        获取解析状态
        :param file_id: 文件ID
        :return: ParseProgressResponse data dict
        """
        result = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id))
        file_record = result.scalars().first()
        if not file_record:
            return None
        return {"status": file_record.parse_status,"file_name":file_record.file_name,"chunk_count":file_record.chunk_count,"file_id":file_record.id}

    async def search_content(self, query: str | list[str], limit: int = 5,search_strategy:str = SearchStrategy.FULL_TEXT)->list[list[dict]]:
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
        if isinstance(query, str):
            query = [query]
        
        logger.info(f"search_content query: {query}")
        query_dense_vector = await self.embedding_model.aembed_documents(query)
        

        search_param_1 = {
            "data": query_dense_vector,
            "anns_field": "text_dense",
            "param": {"nprobe": 10},
            "limit": limit
        }
        request_1 = AnnSearchRequest(**search_param_1)

        search_param_2 = {
            "data": query,
            "anns_field": "text_sparse",
            "param": {"drop_ratio_search": 0.2},
            "limit": limit
        }
        request_2 = AnnSearchRequest(**search_param_2)

        
        if search_strategy == SearchStrategy.FULL_TEXT:
            reqs = [request_1]
        elif search_strategy == SearchStrategy.VECTOR:
            reqs = [request_2]
        else:
            reqs = [request_1, request_2]

        # 召回策略
        ranker = Function(
            name="rrf",
            input_field_names=[], # 
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
            output_fields=["file_id", "file_name","text"],
        )
        return_result = []
        for query_result_list in result:
            return_query_result_list = []    
            for single_result in query_result_list:
                return_query_result_list.append({
                    "file_id": single_result["file_id"],
                    "file_name": single_result["file_name"],
                    "text": single_result["text"],
                })
            return_result.append(return_query_result_list)

        logger.info(f"search_content return_result: {return_result}")
        return return_result

    async def _prepare_milvus_data(self, documents:list[Document],file_id:str,file_name:str)->list[dict]:
        """
        将langchain文档转换为milvus格式
        """
        data = []
        for doc in documents:
            data.append({
                "id": doc.id,
                "file_id": file_id,
                "file_name": file_name,
                "text": doc.page_content,
                "text_sparse": await self.embedding_model.aembed_documents([doc.page_content]),
            })
        return data
    
    async def create_category(self, name: str, description: str, db: AsyncSession):
        """
        创建知识库类别
        :param name: 类别名称
        :param description: 类别描述
        :return: KnowledgeCategory
        """
        # 检查类别名称是否已存在
        result = await db.execute(select(KnowledgeCategory).where(KnowledgeCategory.name == name))
        if result.scalars().first():
            raise ValueError(f"Category with name '{name}' already exists")

        new_category = KnowledgeCategory(
            id=str(uuid.uuid4()),
            name=name,
            description=description
        )
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        return new_category

    async def get_all_categories(self, db: AsyncSession):
        """
        获取所有知识库类别
        :return: List[KnowledgeCategory]
        """
        result = await db.execute(select(KnowledgeCategory))
        categories = result.scalars().all()
        return categories

    async def get_files_by_category(self, user_id: str, category_id: str, db: AsyncSession):
        """
        获取指定类别的所有文件
        :param user_id: 用户ID
        :param category_id: 类别ID
        :return: List[KnowledgeFile]
        """
        result = await db.execute(
            select(KnowledgeFile)
            .where(KnowledgeFile.user_id == user_id, KnowledgeFile.category_id == category_id)
        )
        files = result.scalars().all()
        return files
    
    async def get_knowledge_summary(self, user_id: str, db: AsyncSession)->str:
        """
        以人类可读的形式，展示当前知识库当中，包含的类别，描述信息
        :param user_id: 用户ID
        :return: str
        """
        # 获取所有类别
        categories = await self.get_all_categories(db)
        
        summary = "当前知识库包含以下类别：\n"
        for category in categories:
            summary += f"- {category.name}: {category.description}\n"
            # 获取该类别下的文件数量
            result = await db.execute(
                select(func.count(KnowledgeFile.id))
                .where(KnowledgeFile.user_id == user_id, KnowledgeFile.category_id == category.id)
            )
            file_count = result.scalar()
            summary += f"  包含文件数量: {file_count}\n"
            
        return summary
        
    


knowledge_service = KnowledgeService()