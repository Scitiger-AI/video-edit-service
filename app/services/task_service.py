from typing import Dict, Any, Optional, List, Tuple
from ..db.repositories.task_repository import TaskRepository
from ..models.task import TaskStatus
from .edit_processors import get_processor
from ..core.logging import logger
from ..utils.helpers import FileUtils


class TaskService:
    """任务服务"""
    
    def __init__(self):
        self.task_repo = TaskRepository()
    
    async def create_task(
        self,
        tenant_id: str,
        user_id: str,
        operation: str,
        processor: str,
        parameters: Dict[str, Any],
        is_async: bool = True
    ) -> str:
        """
        创建任务
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            operation: 操作类型
            processor: 处理器名称
            parameters: 操作参数
            is_async: 是否异步执行
            
        Returns:
            str: 任务ID
        """
        try:
            # 验证参数
            processor_instance = get_processor(processor)
            validated_parameters = await processor_instance.validate_parameters(operation, parameters)
            
            # 创建任务
            task_id = await self.task_repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                operation=operation,
                processor=processor,
                parameters=validated_parameters,
                is_async=is_async
            )
            
            return task_id
        
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态，不存在时返回None
        """
        task = await self.task_repo.get_by_id(task_id)
        
        if not task:
            return None
        
        return {
            "task_id": task["_id"],
            "status": task["status"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"]
        }
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务结果，不存在时返回None
        """
        task = await self.task_repo.get_by_id(task_id)
        
        if not task:
            return None
        
        # 构建基本结果
        result = {
            "task_id": task["_id"],
            "status": task["status"],
            "result": task.get("result"),
            "error": task.get("error")
        }
        
        # 转换结果中的文件路径为URL
        if result.get("result"):
            result["result"] = FileUtils.convert_path_to_urls(result["result"])
        
        return result
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功
        """
        return await self.task_repo.cancel_task(task_id)
    
    async def get_user_tasks(
        self,
        user_id: str,
        tenant_id: str,
        status: Optional[str] = None,
        operation: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        ordering: str = "-created_at"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取用户的任务列表
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            status: 任务状态（可选）
            operation: 操作类型（可选）
            page: 页码
            page_size: 每页数量
            ordering: 排序字段，'-'前缀表示降序，例如：'-created_at'表示按创建时间降序
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: (任务列表, 总数)
        """
        skip = (page - 1) * page_size
        
        tasks, total = await self.task_repo.get_user_tasks(
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            operation=operation,
            skip=skip,
            limit=page_size,
            ordering=ordering
        )
        
        # 转换任务数据
        task_list = []
        for task in tasks:
            task_list.append({
                "task_id": task["_id"],
                "status": task["status"],
                "operation": task["operation"],
                "processor": task["processor"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"]
            })
        
        return task_list, total

    async def get_task_list(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        operation: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        ordering: str = "-created_at"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取任务列表，支持按租户ID查询和按用户ID过滤
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID（可选，如果为None则查询租户下所有任务）
            status: 任务状态（可选）
            operation: 操作类型（可选）
            page: 页码
            page_size: 每页数量
            ordering: 排序字段，'-'前缀表示降序，例如：'-created_at'表示按创建时间降序
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: (任务列表, 总数)
        """
        skip = (page - 1) * page_size
        
        if user_id:
            # 如果提供了用户ID，使用现有方法
            return await self.get_user_tasks(
                user_id=user_id,
                tenant_id=tenant_id,
                status=status,
                operation=operation,
                page=page,
                page_size=page_size,
                ordering=ordering
            )
        else:
            # 否则按租户ID查询所有任务
            logger.info(f"查询租户 {tenant_id} 下的所有任务，跳过用户ID过滤")
            tasks, total = await self.task_repo.get_tenant_tasks(
                tenant_id=tenant_id,
                status=status,
                operation=operation,
                skip=skip,
                limit=page_size,
                ordering=ordering
            )
            
            # 转换任务数据
            task_list = []
            for task in tasks:
                task_list.append({
                    "task_id": task["_id"],
                    "tenant_id": task["tenant_id"],
                    "user_id": task["user_id"],
                    "status": task["status"],
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"],
                    "operation": task["operation"],
                    "processor": task["processor"],
                    "parameters": task["parameters"],
                    "is_async": task["is_async"],
                    # "result": task["result"],
                    # "error": task["error"]
                })
            
            return task_list, total 