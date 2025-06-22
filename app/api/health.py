from fastapi import APIRouter, Depends
from ..schemas.common import ResponseBase
from ..core.config import settings
from ..db.mongodb import database

router = APIRouter()


@router.get("/", response_model=ResponseBase)
async def health_check():
    """
    健康检查端点
    
    Returns:
        ResponseBase: 健康状态
    """
    # 检查MongoDB连接
    try:
        await database.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "success": True,
        "message": f"Service is healthy. MongoDB: {db_status}"
    } 