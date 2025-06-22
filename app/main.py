from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
from contextlib import asynccontextmanager
import logging
import os

from .api import api_router
from .core.config import settings
from .core.logging import logger
from .db.mongodb import init_mongodb
from .middleware.auth import AuthMiddleware, PermissionMiddleware
from .core.permissions import setup_permissions
from .utils.helpers import FileUtils

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义lifespan上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"API_V1_STR: {settings.API_V1_STR}")
    logger.info(f"服务监听地址: http://service.scitiger.cn/video-service/")
    logger.info(f"API测试路由: http://service.scitiger.cn/video-service/api/test/")
    logger.info(f"健康检查路由: http://service.scitiger.cn/video-service{settings.API_V1_STR}/health/")
    logger.info(f"任务创建路由: http://service.scitiger.cn/video-service{settings.API_V1_STR}/tasks/")
    logger.info(f"静态媒体文件路径: http://127.0.0.1:8084/media/")
    
    # 初始化MongoDB
    await init_mongodb()
    logger.info("MongoDB连接初始化完成")
    
    # 初始化文件工具类
    await FileUtils.setup()
    logger.info("文件工具类初始化完成")
    
    # 初始化权限映射表
    setup_permissions(app)
    logger.info("权限映射表初始化完成")
    
    yield  # 应用运行
    
    # 关闭事件
    logger.info(f"Shutting down {settings.APP_NAME}")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="视频模型调用服务",
    version="0.1.0",
    lifespan=lifespan,  # 使用lifespan上下文管理器
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加权限检查中间件
app.add_middleware(PermissionMiddleware)

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 检查静态文件目录是否存在，不存在则创建
if not os.path.exists(settings.DATA_DIR):
    logger.warning(f"静态媒体文件目录不存在: {settings.DATA_DIR}，尝试创建...")
    try:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        logger.info(f"静态媒体文件目录创建成功: {settings.DATA_DIR}")
    except Exception as e:
        logger.error(f"创建静态媒体文件目录失败: {str(e)}")
        raise RuntimeError(f"无法创建静态媒体文件目录 '{settings.DATA_DIR}': {str(e)}")

# 挂载静态文件目录
app.mount("/media", StaticFiles(directory=settings.DATA_DIR), name="media")
logger.info(f"静态媒体文件目录挂载成功: {settings.DATA_DIR} -> /media")

# 添加详细的路由注册日志
logger.info(f"开始注册API路由，前缀: {settings.API_V1_STR}")
# 打印API路由器中的所有路由
for route in api_router.routes:
    logger.info(f"发现路由: {route.path}, 方法: {route.methods if hasattr(route, 'methods') else '未知'}")

# 添加API路由
app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info(f"API路由注册完成")

# 打印应用中的所有路由
logger.info("应用中的所有路由:")
for route in app.routes:
    if hasattr(route, "path"):
        logger.info(f"- 路由: {route.path}, 方法: {route.methods if hasattr(route, 'methods') else '未知'}")

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"请求处理时间: {process_time:.4f}秒")
    return response

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )

# 404错误处理
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """404错误处理器"""
    logger.warning(f"404错误 - 路径: {request.url.path}, 方法: {request.method}")
    logger.warning(f"请求头: {dict(request.headers)}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "message": "Resource not found",
            "path": request.url.path
        }
    )

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的中间件"""
    logger.info(f"收到请求: {request.method} {request.url.path}")
    
    # 记录请求头（排除敏感信息）
    headers = dict(request.headers)
    if "authorization" in headers:
        headers["authorization"] = "***" # 隐藏敏感信息
    logger.info(f"请求头: {headers}")
    
    # 继续处理请求
    response = await call_next(request)
    
    # 记录响应信息
    logger.info(f"响应状态: {response.status_code}")
    return response

# 健康检查路由
@app.get("/health", tags=["health"])
async def health():
    """健康检查"""
    return {"success": True, "message": "健康检查成功"}

# 添加测试路由，用于验证API可用性
@app.get("/api/test", tags=["test"])
async def api_test():
    """API测试路由"""
    logger.info("API测试路由被调用")
    return {"success": True, "message": "API路由工作正常"}

# 在API v1下添加测试路由
@app.get(f"{settings.API_V1_STR}/test", tags=["test"])
async def api_v1_test():
    """API测试路由"""
    logger.info("API测试路由被调用")
    return {"success": True, "message": "API路由工作正常"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
