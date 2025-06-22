from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

# 定义泛型类型变量
DataT = TypeVar('DataT')


class ResponseBase(BaseModel):
    """基础响应模式"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="操作成功", description="响应消息")


class DataResponse(ResponseBase, Generic[DataT]):
    """带数据的响应模式"""
    data: Optional[DataT] = Field(default=None, description="响应数据")


class PaginatedResponseBase(ResponseBase):
    """分页响应基础模式"""
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=10, description="每页记录数")


class PaginatedResponse(PaginatedResponseBase, Generic[DataT]):
    """分页响应模式"""
    items: list[DataT] = Field(default_factory=list, description="分页数据")


class ErrorResponse(ResponseBase):
    """错误响应模式"""
    success: bool = Field(default=False, description="操作是否成功")
    message: str = Field(default="操作失败", description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")
    details: Optional[Any] = Field(default=None, description="错误详情") 