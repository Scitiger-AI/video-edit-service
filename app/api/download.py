from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from typing import Optional
import os
from pathlib import Path
from ..core.security import get_current_user
from ..core.permissions import requires_permission
from ..core.logging import logger
from ..core.config import settings

router = APIRouter()

@router.get("/{file_name}")
async def download_file(
    file_name: str,
    request: Request,
    # current_user: dict = Depends(get_current_user)
):
    """
    下载文件
    
    Args:
        file_name: 文件名
        request: 请求对象
        current_user: 当前用户
    
    Returns:
        FileResponse: 文件响应
    """
    try:
        # 在数据目录中查找文件
        data_dir = Path(settings.DATA_DIR)
        
        # 首先检查是否直接存在于videos目录下
        videos_dir = data_dir / "videos"
        file_path = videos_dir / file_name
        
        if not file_path.exists():
            # 如果不存在，在整个数据目录中递归查找
            matching_files = list(data_dir.glob(f"**/{file_name}"))
            
            if not matching_files:
                logger.error(f"文件未找到: {file_name}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_name}"
                )
            
            file_path = matching_files[0]
            
        logger.info(f"提供文件下载: {file_path}")
        
        # 返回文件
        return FileResponse(
            path=str(file_path),
            filename=file_name,
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件下载请求时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process download request: {str(e)}"
        ) 