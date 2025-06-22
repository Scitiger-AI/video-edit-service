from fastapi import APIRouter
from . import health, tasks, models, download

api_router = APIRouter()

# 添加健康检查路由
api_router.include_router(health.router, prefix="/health", tags=["health"])

# 添加任务管理路由
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

# 添加模型查询路由
api_router.include_router(models.router, prefix="/models", tags=["models"])

# 添加文件下载路由
api_router.include_router(download.router, prefix="/download", tags=["download"])