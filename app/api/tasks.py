from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import Optional
from ..schemas.task import (
    TaskCreate, TaskResponse, TaskStatusResponse, 
    TaskResultResponse, TaskListResponse, TaskCancelResponse,
    TaskQuery, TaskListItem
)
from ..services.task_service import TaskService
from ..worker.tasks import process_video_edit_task
from ..core.security import get_current_user
from ..core.permissions import requires_permission, permission_required
from ..core.logging import logger
from ..utils.response import success_response, error_response

router = APIRouter()


@router.post("/", response_model=TaskResponse)
@requires_permission(resource="tasks", action="create")
async def create_task(
    task_data: TaskCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    创建新的视频编辑任务
    
    Args:
        task_data: 任务数据
        request: 请求对象
        current_user: 当前用户
        
    Returns:
        TaskResponse: 任务创建响应
    """
    # 添加详细日志，记录current_user的完整内容
    logger.info(f"创建任务 - current_user完整内容: {current_user}")
    
    try:
        # 获取用户信息
        user_id = current_user.get("id")
        tenant_id = current_user.get("tenant_id")
        is_system_key = current_user.get("is_system_key", False)
        
        # 记录用户信息
        logger.info(f"请求用户信息: user_id={user_id}, tenant_id={tenant_id}, is_system_key={is_system_key}")
        
        # 创建任务
        task_service = TaskService()
        task_id = await task_service.create_task(
            tenant_id=tenant_id,
            user_id=user_id or "system",  # 如果没有用户ID（系统级API密钥），使用"system"
            operation=task_data.operation,
            processor=task_data.processor,
            parameters=task_data.parameters,
            is_async=task_data.is_async
        )
        
        # 如果是异步任务，发送到Celery
        if task_data.is_async:
            process_video_edit_task.delay(
                task_id=task_id,
                operation=task_data.operation,
                processor_name=task_data.processor,
                parameters=task_data.parameters
            )
        else:
            # 同步执行（不推荐）
            process_video_edit_task.apply(
                args=[task_id, task_data.operation, task_data.processor, task_data.parameters],
                throw=True
            )
        
        return success_response(data={"task_id": task_id}, message="任务已创建")
    
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return error_response(message=f"Failed to create task: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
@requires_permission(resource="tasks", action="read")
async def get_task_status(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(permission_required("tasks", "read"))
):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        request: 请求对象
        current_user: 当前用户
        
    Returns:
        TaskStatusResponse: 任务状态响应
    """
    try:
        # 获取任务状态
        task_service = TaskService()
        task_status = await task_service.get_task_status(task_id)
        
        if not task_status:
            return error_response(message=f"Task with ID {task_id} not found", status_code=status.HTTP_404_NOT_FOUND)

        
        return success_response(data=task_status, message="获取任务状态成功")
    
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return error_response(message=f"Failed to get task status: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{task_id}/result", response_model=TaskResultResponse)
@requires_permission(resource="tasks", action="read")
async def get_task_result(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(permission_required("tasks", "read"))
):
    """
    获取任务结果
    
    Args:
        task_id: 任务ID
        request: 请求对象
        current_user: 当前用户
        
    Returns:
        TaskResultResponse: 任务结果响应
    """
    try:
        # 获取任务结果
        task_service = TaskService()
        task_result = await task_service.get_task_result(task_id)
        
        if not task_result:
            return error_response(message=f"Task with ID {task_id} not found", status_code=status.HTTP_404_NOT_FOUND)
        
        return success_response(data=task_result, message="获取任务结果成功")
    
    except Exception as e:
        logger.error(f"Error getting task result: {str(e)}")
        return error_response(message=f"Failed to get task result: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
@requires_permission(resource="tasks", action="cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    取消任务
    
    Args:
        task_id: 任务ID
        request: 请求对象
        current_user: 当前用户
        
    Returns:
        TaskCancelResponse: 任务取消响应
    """
    try:
        # 取消任务
        task_service = TaskService()
        success = await task_service.cancel_task(task_id)
        
        if not success:
            return error_response(message=f"Failed to cancel task with ID {task_id}, 任务不存在或已取消/已完成", status_code=status.HTTP_400_BAD_REQUEST)
        
        return success_response(data={"task_id": task_id}, message="任务已取消")
    
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}")
        return error_response(message=f"Failed to cancel task: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
    query: TaskQuery = Depends(),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(permission_required("tasks", "list"))
):
    """
    获取任务列表
    
    Args:
        request: 请求对象
        query: 查询参数
        current_user: 当前用户
        
    Returns:
        TaskListResponse: 任务列表响应
    """
    try:
        # 获取用户信息
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        is_system_key = current_user.get("is_system_key", False)
        
        # 获取任务列表
        task_service = TaskService()
        tasks, total = await task_service.get_task_list(
            tenant_id=tenant_id,
            user_id=user_id if not is_system_key else None,  # 如果是系统密钥，不按用户ID过滤
            status=query.status,
            model=query.model,
            page=query.page,
            page_size=query.page_size,
            ordering=query.ordering
        )
        
        # 计算分页信息
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 1
        
        # 构建下一页和上一页的URL
        base_url = str(request.url).split("?")[0]
        query_params = []
        if query.status:
            query_params.append(f"status={query.status}")
        if query.model:
            query_params.append(f"model={query.model}")
        query_params.append(f"page_size={query.page_size}")
        query_params.append(f"ordering={query.ordering}")
        
        # 构建下一页URL
        next_url = None
        if query.page < total_pages:
            next_query_params = query_params.copy()
            next_query_params.append(f"page={query.page + 1}")
            next_url = f"{base_url}?{'&'.join(next_query_params)}"
            
        # 构建上一页URL
        previous_url = None
        if query.page > 1:
            prev_query_params = query_params.copy()
            prev_query_params.append(f"page={query.page - 1}")
            previous_url = f"{base_url}?{'&'.join(prev_query_params)}"
        
        return success_response(data={
            "total": total,
            "page_size": query.page_size,
            "current_page": query.page,
            "total_pages": total_pages,
            "next": next_url,
            "previous": previous_url,
            "tasks": tasks
        }, message="获取任务列表成功")
    
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        return error_response(message=f"Failed to list tasks: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) 