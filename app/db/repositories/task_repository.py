from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from ..mongodb import task_collection
from ...models.task import TaskModel, TaskStatus
from ...core.logging import logger


class TaskRepository:
    """任务数据访问层"""
    
    async def create(
        self,
        tenant_id: str,
        user_id: str,
        operation: str,
        processor: str,
        parameters: Dict[str, Any],
        is_async: bool = True
    ) -> str:
        """
        创建新任务
        
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
        # 创建任务数据
        task_data = TaskModel.create_task(
            tenant_id=tenant_id,
            user_id=user_id,
            operation=operation,
            processor=processor,
            parameters=parameters,
            is_async=is_async
        )
        
        # 插入数据库
        result = await task_collection.insert_one(task_data)
        
        # 返回任务ID
        return str(result.inserted_id)
    
    async def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务数据，不存在时返回None
        """
        try:
            # 查询数据库
            task = await task_collection.find_one({"_id": ObjectId(task_id)})
            
            if task:
                # 转换ObjectId为字符串
                task["_id"] = str(task["_id"])
                return task
                
            return None
        
        except Exception as e:
            logger.error(f"Error getting task by ID: {str(e)}")
            return None
    
    async def get_user_tasks(
        self,
        user_id: str,
        tenant_id: str,
        status: Optional[str] = None,
        operation: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        ordering: str = "-created_at"
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取用户的任务列表
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            status: 任务状态（可选）
            operation: 操作类型（可选）
            skip: 跳过数量
            limit: 限制数量
            ordering: 排序字段，'-'前缀表示降序，例如：'-created_at'表示按创建时间降序
            
        Returns:
            tuple: (任务列表, 总数)
        """
        try:
            # 构建查询条件
            query = {"user_id": user_id, "tenant_id": tenant_id}
            
            if status:
                query["status"] = status
                
            if operation:
                query["operation"] = operation
            
            # 查询总数
            total = await task_collection.count_documents(query)
            
            # 处理排序
            sort_field = ordering
            sort_direction = -1  # 默认降序
            
            if ordering.startswith("-"):
                sort_field = ordering[1:]
            else:
                sort_direction = 1  # 升序
            
            # 查询数据
            cursor = task_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
            
            # 转换结果
            tasks = []
            async for task in cursor:
                task["_id"] = str(task["_id"])
                tasks.append(task)
            
            return tasks, total
        
        except Exception as e:
            logger.error(f"Error getting user tasks: {str(e)}")
            return [], 0
    
    async def get_tenant_tasks(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        operation: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        ordering: str = "-created_at"
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取租户的所有任务列表（不按用户过滤）
        
        Args:
            tenant_id: 租户ID
            status: 任务状态（可选）
            operation: 操作类型（可选）
            skip: 跳过数量
            limit: 限制数量
            ordering: 排序字段，'-'前缀表示降序，例如：'-created_at'表示按创建时间降序
            
        Returns:
            tuple: (任务列表, 总数)
        """
        try:
            # 构建查询条件
            query = {"tenant_id": tenant_id}
            
            if status:
                query["status"] = status
                
            if operation:
                query["operation"] = operation
            
            # 查询总数
            total = await task_collection.count_documents(query)
            
            # 处理排序
            sort_field = ordering
            sort_direction = -1  # 默认降序
            
            if ordering.startswith("-"):
                sort_field = ordering[1:]
            else:
                sort_direction = 1  # 升序
            
            # 查询数据
            cursor = task_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
            
            # 转换结果
            tasks = []
            async for task in cursor:
                task["_id"] = str(task["_id"])
                tasks.append(task)
            
            logger.info(f"找到租户 {tenant_id} 的 {len(tasks)} 个任务，共 {total} 个")
            return tasks, total
        
        except Exception as e:
            logger.error(f"Error getting tenant tasks: {str(e)}")
            return [], 0
    
    async def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取任务
            task = await self.get_by_id(task_id)
            
            if not task:
                return False
            
            # 更新状态
            update_data = TaskModel.update_status(task, status)
            
            # 更新数据库
            result = await task_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return False
    
    async def update_result(self, task_id: str, result: Any) -> bool:
        """
        更新任务结果
        
        Args:
            task_id: 任务ID
            result: 任务结果
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取任务
            task = await self.get_by_id(task_id)
            
            if not task:
                return False
            
            # 更新结果
            update_data = TaskModel.update_result(task, result)
            
            # 更新数据库
            result = await task_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error updating task result: {str(e)}")
            return False
    
    async def update_error(self, task_id: str, error: str) -> bool:
        """
        更新任务错误
        
        Args:
            task_id: 任务ID
            error: 错误信息
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取任务
            task = await self.get_by_id(task_id)
            
            if not task:
                return False
            
            # 更新错误
            update_data = TaskModel.update_error(task, error)
            
            # 更新数据库
            result = await task_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error updating task error: {str(e)}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取任务
            task = await self.get_by_id(task_id)
            
            if not task:
                return False
            
            # 只有pending和running状态的任务可以取消
            if task["status"] not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                return False
            
            # 更新状态
            return await self.update_status(task_id, TaskStatus.CANCELLED)
        
        except Exception as e:
            logger.error(f"Error cancelling task: {str(e)}")
            return False 