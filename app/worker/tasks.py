import asyncio
from typing import Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from ..core.celery_app import celery_app
from ..core.logging import logger
from ..core.config import settings
from ..models.task import TaskStatus
from ..services.edit_processors import get_processor
from ..db.mongodb import MONGODB_POOL_SETTINGS


@celery_app.task(bind=True)
def process_video_edit_task(self, task_id: str, operation: str, processor_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理视频编辑任务
    
    Args:
        task_id: 任务ID
        operation: 操作类型
        processor_name: 处理器名称
        parameters: 操作参数
        
    Returns:
        Dict[str, Any]: 任务结果
    """
    logger.info(f"Processing video edit task {task_id} with operation {operation} and processor {processor_name}")
    
    # 创建异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 在任务中创建MongoDB连接，确保使用当前事件循环并配置连接池
    client = None
    db = None
    task_collection = None
    
    try:
        # 创建新的MongoDB客户端连接，指定当前事件循环和连接池配置
        client = AsyncIOMotorClient(
            settings.MONGODB_CONNECTION_STRING,
            io_loop=loop,
            **MONGODB_POOL_SETTINGS
        )
        db = client[settings.MONGODB_DB_NAME]
        task_collection = db.get_collection("tasks")
        
        # 更新任务状态为运行中
        try:
            loop.run_until_complete(update_task_status(task_collection, task_id, TaskStatus.RUNNING))
        except Exception as e:
            logger.error(f"Error updating task status to running: {str(e)}")
            # 不抛出异常，继续执行
        
        # 获取视频处理器
        processor = get_processor(processor_name)
        
        # 处理视频
        result = loop.run_until_complete(processor.process_video(operation, parameters))
        
        # 更新任务结果
        try:
            loop.run_until_complete(update_task_result(task_collection, task_id, result))
        except Exception as e:
            logger.error(f"Error updating task result: {str(e)}")
            # 不抛出异常，继续返回结果
        
        logger.info(f"Task {task_id} completed successfully")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value
        }
    
    except Exception as e:
        # 记录错误
        error_message = f"Error processing task {task_id}: {str(e)}"
        logger.error(error_message)
        
        # 更新任务状态为失败
        if not loop.is_closed() and task_collection is not None:
            try:
                loop.run_until_complete(update_task_error(task_collection, task_id, str(e)))
            except Exception as update_error:
                logger.error(f"Error updating task error: {str(update_error)}")
        
        return {
            "success": False,
            "task_id": task_id,
            "status": TaskStatus.FAILED.value,
            "error": str(e)
        }
    
    finally:
        # 关闭MongoDB连接
        if client is not None:
            # 注意：我们不再显式关闭连接，而是将连接返回到连接池
            # 但为了释放客户端对象相关资源，我们仍然应该将client设为None
            client = None
        
        # 确保关闭事件循环
        if not loop.is_closed():
            loop.close()


async def update_task_status(collection, task_id: str, status: TaskStatus) -> bool:
    """更新任务状态"""
    from bson import ObjectId
    
    result = await collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "status": status.value,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }}
    )
    
    return result.modified_count > 0


async def update_task_result(collection, task_id: str, result: Dict[str, Any]) -> bool:
    """更新任务结果"""
    from bson import ObjectId
    
    update_data = {
        "status": TaskStatus.COMPLETED.value,
        "result": result,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    result = await collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def update_task_error(collection, task_id: str, error: str) -> bool:
    """更新任务错误"""
    from bson import ObjectId
    
    update_data = {
        "status": TaskStatus.FAILED.value,
        "error": error,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    result = await collection.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    return result.modified_count > 0 