from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, model_validator
from ..core.config import settings
from ..models.task import TaskStatus


class TaskCreate(BaseModel):
    """创建任务请求模式"""
    operation: str = Field(default=settings.DEFAULT_OPERATION, description="操作类型")
    processor: str = Field(default=settings.DEFAULT_PROCESSOR, description="处理器名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")
    is_async: bool = Field(default=True, description="是否异步执行")


class TaskResponse(BaseModel):
    """任务响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="任务已创建", description="响应消息")
    task_id: str = Field(..., description="任务ID")


class TaskStatusResponse(BaseModel):
    """任务状态响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    retry_count: Optional[int] = Field(default=None, description="重试次数")
    retry_info: Optional[str] = Field(default=None, description="重试信息")


class TaskResultResponse(BaseModel):
    """任务结果响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[Any] = Field(default=None, description="任务结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    retry_count: Optional[int] = Field(default=None, description="重试次数")
    retry_info: Optional[str] = Field(default=None, description="重试信息")


class TaskListItem(BaseModel):
    """任务列表项模式"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    operation: str = Field(..., description="操作类型")
    processor: str = Field(..., description="处理器名称")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TaskListResponse(BaseModel):
    """任务列表响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="获取任务列表成功", description="响应消息")
    total: int = Field(..., description="总记录数")
    page_size: int = Field(..., description="每页记录数")
    current_page: int = Field(..., description="当前页码")
    total_pages: int = Field(..., description="总页数")
    next: Optional[str] = Field(default=None, description="下一页URL")
    previous: Optional[str] = Field(default=None, description="上一页URL")
    tasks: List[TaskListItem] = Field(..., description="任务列表")


class TaskCancelResponse(BaseModel):
    """任务取消响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="任务已取消", description="响应消息")
    task_id: str = Field(..., description="任务ID")


class TaskQuery(BaseModel):
    """任务查询参数模式"""
    status: Optional[str] = Field(default=None, description="任务状态")
    operation: Optional[str] = Field(default=None, description="操作类型")
    processor: Optional[str] = Field(default=None, description="处理器名称")
    page: int = Field(default=1, description="页码", ge=1)
    page_size: int = Field(default=10, description="每页数量", ge=1, le=100)
    ordering: str = Field(default="-created_at", description="排序字段，'-'前缀表示降序，例如：'-created_at'表示按创建时间降序")
    
    @model_validator(mode='after')
    def validate_status(self):
        """验证状态值"""
        if self.status is not None and self.status not in [s.value for s in TaskStatus]:
            valid_statuses = ", ".join([s.value for s in TaskStatus])
            raise ValueError(f"Invalid status. Valid values are: {valid_statuses}")
        return self 