import logging
import sys
from .config import settings

# 配置根日志记录器
def setup_logging():
    """设置日志配置"""
    log_level = getattr(logging, settings.LOG_LEVEL)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("celery").setLevel(log_level)
    
    # 返回应用日志记录器
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(log_level)
    
    return logger

# 创建应用日志记录器
logger = setup_logging() 