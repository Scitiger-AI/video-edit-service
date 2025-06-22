from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings
from ..core.logging import logger

# MongoDB连接池配置
MONGODB_POOL_SETTINGS = {
    "maxPoolSize": 100,      # 最大连接池大小
    "minPoolSize": 10,       # 最小连接池大小(预创建)
    "maxIdleTimeMS": 30000,  # 连接最大空闲时间(30秒)
    "waitQueueTimeoutMS": 10000,  # 等待队列超时(10秒)
    "connectTimeoutMS": 5000 # 连接超时(5秒)
}

# MongoDB客户端连接
try:
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL} (DB: {settings.MONGODB_DB_NAME})")
    # 隐藏敏感信息的连接字符串（用于日志）
    log_connection_string = settings.MONGODB_CONNECTION_STRING
    if settings.MONGODB_USER and settings.MONGODB_PASSWORD:
        log_connection_string = log_connection_string.replace(settings.MONGODB_PASSWORD, "********")
    logger.debug(f"MongoDB connection string: {log_connection_string}")
    
    # 使用连接池配置创建客户端
    client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_STRING, **MONGODB_POOL_SETTINGS)
    database = client[settings.MONGODB_DB_NAME]
    
    # 任务集合
    task_collection = database.get_collection("tasks")
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {str(e)}")
    raise

# 索引初始化函数
async def init_mongodb():
    """初始化MongoDB索引"""
    try:
        # 创建任务集合的索引
        await task_collection.create_index("user_id")
        await task_collection.create_index("tenant_id")
        await task_collection.create_index("status")
        await task_collection.create_index("created_at")
        await task_collection.create_index([("model", 1), ("provider", 1)])
        
        logger.info("MongoDB indexes initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing MongoDB indexes: {str(e)}")
        raise 