from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status, Request, Form
from fastapi.responses import JSONResponse
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from ..core.security import get_current_user
from ..core.permissions import requires_permission
from ..core.logging import logger
from ..core.config import settings
from ..utils.response import success_response, error_response
from ..utils.helpers import FileUtils

router = APIRouter()

async def determine_category(file: UploadFile, user_category: Optional[str] = None) -> str:
    """
    根据文件类型自动判断分类目录
    
    Args:
        file: 上传的文件
        user_category: 用户指定的分类（如果有）
        
    Returns:
        str: 确定的分类目录名
    """
    if user_category:
        return user_category
        
    # 获取文件扩展名
    file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    
    # 获取文件的MIME类型
    content_type = file.content_type or ""
    logger.info(f"自动判断文件类别 - 文件名: {file.filename}, 扩展名: {file_extension}, MIME类型: {content_type}")
    
    # 根据MIME类型判断
    if content_type.startswith("image/"):
        return "images"
    elif content_type.startswith("video/"):
        return "videos"
    elif content_type.startswith("audio/"):
        return "audio"
    elif (content_type.startswith("text/") or 
          content_type in ["application/pdf", "application/msword", 
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]):
        return "documents"
    
    # 如果MIME类型无法判断，根据扩展名判断
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"]
    audio_extensions = [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"]
    document_extensions = [".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"]
    
    if file_extension in image_extensions:
        return "images"
    elif file_extension in video_extensions:
        return "videos"
    elif file_extension in audio_extensions:
        return "audio"
    elif file_extension in document_extensions:
        return "documents"
    
    # 默认分类
    logger.info(f"无法判断文件类别，使用默认类别: general")
    return "general"

@router.post("/")
@requires_permission(resource="upload", action="create")
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = None,
    request: Request = None
):
    """
    上传文件
    
    Args:
        file: 上传的文件
        category: 文件分类（例如：videos, images, audio等）
        request: 请求对象
    
    Returns:
        JSONResponse: 包含文件URL的响应
    """
    try:
        # 自动判断category
        determined_category = await determine_category(file, category)
        
        logger.info(f"文件上传 - 文件名: {file.filename}, 类别: {determined_category}")
        
        # 创建保存目录
        upload_dir = Path(settings.DATA_DIR) / determined_category
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        safe_filename = f"{timestamp}_{random_id}{file_extension}"
        
        # 保存文件
        file_path = upload_dir / safe_filename
        
        # 读取文件内容并写入
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"文件已保存: {file_path}")
        
        # 生成访问URL
        relative_path = file_path.relative_to(Path(settings.DATA_DIR))
        media_url = f"{settings.MEDIA_BASE_PATH}/{relative_path}".replace("\\", "/")
        full_url = f"{settings.SERVICE_BASE_URL}{media_url}"
        download_url = f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{safe_filename}"
        
        return success_response(
            data={
                "filename": safe_filename,
                "original_filename": file.filename,
                "size": len(content),
                "content_type": file.content_type,
                "category": determined_category,
                "media_url": media_url,
                "full_url": full_url,
                "download_url": download_url
            },
            message="文件上传成功"
        )
    
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return error_response(
            message=f"文件上传失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/batch")
@requires_permission(resource="upload", action="create")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    category: Optional[str] = None,
    request: Request = None
):
    """
    批量上传文件
    
    Args:
        files: 上传的文件列表
        category: 文件分类（例如：videos, images, audio等）
        request: 请求对象
    
    Returns:
        JSONResponse: 包含文件URL列表的响应
    """
    try:
        logger.info(f"批量文件上传 - 文件数量: {len(files)}, 用户指定类别: {category or '无'}")
        
        result = []
        
        for file in files:
            # 自动判断category
            determined_category = await determine_category(file, category)
            
            # 创建保存目录
            upload_dir = Path(settings.DATA_DIR) / determined_category
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            file_extension = os.path.splitext(file.filename)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_id = str(uuid.uuid4())[:8]
            safe_filename = f"{timestamp}_{random_id}{file_extension}"
            
            # 保存文件
            file_path = upload_dir / safe_filename
            
            # 读取文件内容并写入
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"文件已保存: {file_path}, 类别: {determined_category}")
            
            # 生成访问URL
            relative_path = file_path.relative_to(Path(settings.DATA_DIR))
            media_url = f"{settings.MEDIA_BASE_PATH}/{relative_path}".replace("\\", "/")
            full_url = f"{settings.SERVICE_BASE_URL}{media_url}"
            download_url = f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{safe_filename}"
            
            result.append({
                "filename": safe_filename,
                "original_filename": file.filename,
                "size": len(content),
                "content_type": file.content_type,
                "category": determined_category,
                "media_url": media_url,
                "full_url": full_url,
                "download_url": download_url
            })
        
        return success_response(
            data=result,
            message=f"成功上传 {len(result)} 个文件"
        )
    
    except Exception as e:
        logger.error(f"批量文件上传失败: {str(e)}")
        return error_response(
            message=f"批量文件上传失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 