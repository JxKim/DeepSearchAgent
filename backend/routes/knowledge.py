from fastapi import APIRouter, Depends, UploadFile, File
from typing import List

#内部依赖
from routes.utils import get_current_user_from_token
from services.knowledge_service import knowledge_service
from routes.schema import (
    KnowledgeFileListResponse,
    KnowledgeFile,
    BaseResponse,
    ParseTaskResponse,
    ParseProgressResponse,
    RecallTestRequest,
    RecallTestResponse
)
from db.database import get_db

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])

@router.get("/info", response_model=KnowledgeFileListResponse)
async def get_user_knowledges(user_id=Depends(get_current_user_from_token)):
    """
    获取当前用户知识库列表
    """
    files = await knowledge_service.get_user_files(user_id)
    return KnowledgeFileListResponse(data=files)

@router.post("/upload", response_model=BaseResponse)
async def upload_file(file: UploadFile = File(...), user_id = Depends(get_current_user_from_token)):
    """
    上传文件到知识库,通过opendal存储文件
    支持类型为pdf,word, txt, csv
    """
    content = await file.read()
    await knowledge_service.upload_file(user_id, file.filename, content)
    return BaseResponse(message="上传成功")


@router.delete("/{file_id}", response_model=BaseResponse)
async def delete_knowledge(file_id: str, user_id=Depends(get_current_user_from_token)):
    """
    删除指定知识库
    """
    await knowledge_service.delete_file(user_id, file_id)
    return BaseResponse(message="删除成功")

@router.post("/parse/submit", response_model=ParseTaskResponse)
async def parse_file(file_id: str, user_id=Depends(get_current_user_from_token)):
    """
    长耗时任务，需要前端实时解析，当前解析到了哪一步。解析上传的文件
    """
    task_id = await knowledge_service.submit_parse_task(user_id, file_id)
    return ParseTaskResponse(data={"task_id": task_id})

@router.get("/parse/progress/{task_id}", response_model=ParseProgressResponse)
async def get_parse_progress(task_id: str, user_id=Depends(get_current_user_from_token)):
    """
    获取文件解析进度
    """
    progress = await knowledge_service.get_parse_status(task_id)
    return ParseProgressResponse(data=progress)

@router.post("/recall/test", response_model=RecallTestResponse)
async def test_recall(request: RecallTestRequest, user_id=Depends(get_current_user_from_token)):
    """
    测试知识库召回效果
    """
    # 1. 搜索
    results = await knowledge_service.search_content(request.query, request.limit)
    
    # 2. 丰富文件名信息
    # 我们需要 DB session，但 knowledge_service.search_content 没有用到 DB
    # 但 enrich_results_with_filenames 需要 DB
    # 我们可以在这里获取 DB session
    from db.database import get_db
    async for db in get_db():
        results = await knowledge_service.enrich_results_with_filenames(results, db)
        break # get_db is a generator, we just need one session
        
    return RecallTestResponse(data=results)

