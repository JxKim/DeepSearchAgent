from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import List, Optional

#内部依赖
from routes.utils import get_current_user_from_token
from services.knowledge_service import knowledge_service
from routes.schema import (
    KnowledgeFileListResponse,
    KnowledgeCategoryListResponse,
    KnowledgeCategoryCreate,
    KnowledgeCategory,
    KnowledgeFile,
    BaseResponse,
    ParseTaskResponse,
    ParseProgressResponse,
    RecallTestRequest,
    RecallTestResponse,
    RecallResult
)
from db.database import get_db

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])

@router.get("/info", response_model=KnowledgeFileListResponse)
async def get_user_knowledges(user_id=Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    获取当前用户知识库列表
    """
    files = await knowledge_service.get_user_files(user_id,db=db)
    return KnowledgeFileListResponse(data=files)

@router.post("/upload", response_model=BaseResponse)
async def upload_file(file: UploadFile = File(...), user_id = Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    上传文件到知识库,通过opendal存储文件
    支持类型为pdf,word, txt, csv
    """
    content = await file.read()
    await knowledge_service.upload_file(user_id, file.filename, content,db=db)
    return BaseResponse(message="上传成功")


@router.delete("/{file_id}", response_model=BaseResponse)
async def delete_knowledge(file_id: str, user_id=Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    删除指定知识库
    """
    await knowledge_service.delete_file(user_id, file_id,db=db)
    return BaseResponse(message="删除成功")

@router.post("/parse/submit", response_model=ParseTaskResponse)
async def parse_file(file_id: str, user_id=Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    长耗时任务，需要前端实时解析，当前解析到了哪一步。解析上传的文件
    """
    file_id = await knowledge_service.submit_parse_task(user_id, file_id,db=db)
    return ParseTaskResponse(data={"file_id": file_id,"status":"processing"})

@router.get("/parse/progress/{file_id}", response_model=ParseProgressResponse)
async def get_parse_progress(file_id: str, user_id=Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    获取文件解析进度
    """
    progress = await knowledge_service.get_parse_status(file_id,db=db)
    return ParseProgressResponse(data={**progress})

@router.post("/recall/test", response_model=RecallTestResponse)
async def test_recall(request: RecallTestRequest, user_id=Depends(get_current_user_from_token)):
    """
    测试知识库召回效果
    """
    # 1. 搜索
    results = await knowledge_service.search_content(request.query, request.limit)

    data_list = []
    if results:
        single_query_result = results[0]
        for single_result in single_query_result:
            data_list.append(RecallResult(
                file_name=single_result["file_name"],
                content=single_result["text"],
            ))
        
    return RecallTestResponse(data=data_list)

@router.post("/category", response_model=KnowledgeCategory)
async def create_category(
    category: KnowledgeCategoryCreate,
    user_id=Depends(get_current_user_from_token), 
    db=Depends(get_db)
):
    """
    创建知识库类别
    """
    try:
        new_category = await knowledge_service.create_category(category.name, category.description, db=db)
        return new_category
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories", response_model=KnowledgeCategoryListResponse)
async def get_all_categories(user_id=Depends(get_current_user_from_token),db=Depends(get_db)):
    """
    获取所有知识库类别
    """
    categories = await knowledge_service.get_all_categories(db=db)
    return KnowledgeCategoryListResponse(data=categories)

@router.get("/category/{category_id}/files", response_model=KnowledgeFileListResponse)
async def get_files_by_category(category_id: str, user_id=Depends(get_current_user_from_token), db=Depends(get_db)):
    """
    获取指定类别的所有文件
    """
    files = await knowledge_service.get_files_by_category(user_id, category_id, db=db)
    return KnowledgeFileListResponse(data=files)