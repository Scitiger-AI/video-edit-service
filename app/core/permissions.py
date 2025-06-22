from functools import wraps
from fastapi import Request, Depends, HTTPException, status, FastAPI
from typing import Callable, Optional, Dict, Any
from .logging import logger
from .security import verify_token, verify_api_key
from .config import settings


# 全局权限映射表，将在应用启动时填充
ROUTE_PERMISSIONS = {}


def requires_permission(resource: str, action: str):
    """
    权限检查装饰器
    
    Args:
        resource: 资源类型
        action: 操作类型
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(endpoint: Callable):
        """
        装饰器函数
        
        Args:
            endpoint: 端点函数
            
        Returns:
            Callable: 包装后的端点函数
        """
        # 保存权限信息到原始函数
        endpoint.__permission__ = {"resource": resource, "action": action}
        
        @wraps(endpoint)
        async def wrapper(*args, **kwargs):
            """
            包装函数，在调用端点前设置权限要求
            
            Returns:
                Any: 端点函数的返回值
            """
            # 从kwargs中获取request对象
            request = kwargs.get('request')
            if request is None and args:
                # 如果在kwargs中没找到，尝试从args中获取
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # 如果禁用了认证，则跳过权限检查
            if not settings.ENABLE_AUTH:
                logger.info(f"权限检查装饰器 - 认证已禁用，跳过权限检查: resource={resource}, action={action}")
                # 调用原始端点
                return await endpoint(*args, **kwargs)
            
            if request:
                # 在请求状态中设置权限要求，供其他组件使用
                request.state.required_resource = resource
                request.state.required_action = action
                logger.info(f"装饰器设置权限要求: resource={resource}, action={action}")
            
            # 调用原始端点
            return await endpoint(*args, **kwargs)
        
        # 保存权限信息到包装函数，方便收集
        wrapper.__permission__ = {"resource": resource, "action": action}
        return wrapper
    
    return decorator


def permission_required(resource: str, action: str):
    """
    创建一个权限检查依赖
    
    Args:
        resource: 资源类型
        action: 操作类型
        
    Returns:
        Callable: 依赖函数
    """
    async def permission_checker(request: Request):
        """
        检查请求是否具有所需权限
        
        Args:
            request: 请求对象
            
        Returns:
            bool: 是否具有权限
        """
        # 如果禁用了认证，则跳过权限检查
        if not settings.ENABLE_AUTH:
            logger.info(f"权限检查依赖 - 认证已禁用，跳过权限检查: resource={resource}, action={action}")
            return True
            
        # 在请求状态中存储权限要求
        request.state.required_resource = resource
        request.state.required_action = action
        
        logger.info(f"设置权限要求: resource={resource}, action={action}")
        return True
    
    # 保存权限信息到依赖函数，方便收集
    permission_checker.__permission__ = {"resource": resource, "action": action}
    return permission_checker


def check_permission(request: Request, resource: str, action: str) -> bool:
    """
    手动检查权限（用于复杂场景）
    
    Args:
        request: 请求对象
        resource: 资源类型
        action: 操作类型
        
    Returns:
        bool: 是否具有权限
    """
    # 设置权限要求
    request.state.required_resource = resource
    request.state.required_action = action
    
    # 检查是否已经通过认证
    if not getattr(request.state, "is_authenticated", False):
        return False
    
    return True


def setup_permissions(app: FastAPI):
    """
    设置权限映射表
    
    Args:
        app: FastAPI应用实例
    """
    global ROUTE_PERMISSIONS
    
    # 清空映射表
    ROUTE_PERMISSIONS.clear()
    
    # 遍历所有路由
    for route in app.routes:
        # 跳过内部路由
        if route.path.startswith("/openapi") or route.path.startswith("/docs") or route.path.startswith("/redoc"):
            continue
        
        # 检查路由处理函数是否有权限信息
        if hasattr(route, "endpoint") and hasattr(route.endpoint, "__permission__"):
            permission = route.endpoint.__permission__
            ROUTE_PERMISSIONS[route.path] = permission
            logger.info(f"注册路由权限: {route.path} -> {permission}")
    
    # 处理带参数的路由
    for path, permission in list(ROUTE_PERMISSIONS.items()):
        if "{" in path:
            # 创建路径模式
            path_pattern = path.replace("{", "").replace("}", "")
            ROUTE_PERMISSIONS[path_pattern] = permission
    
    logger.info(f"权限映射表设置完成，共 {len(ROUTE_PERMISSIONS)} 条记录")


def get_route_permission(path: str) -> Dict[str, str]:
    """
    获取路由的权限要求
    
    Args:
        path: 请求路径
        
    Returns:
        Dict[str, str]: 权限要求，包含resource和action
    """
    # 直接匹配
    if path in ROUTE_PERMISSIONS:
        return ROUTE_PERMISSIONS[path]
    
    # 尝试匹配带参数的路由
    for route_path, permission in ROUTE_PERMISSIONS.items():
        if "{" in route_path:
            # 简单的路径模式匹配
            path_parts = path.split("/")
            route_parts = route_path.split("/")
            
            if len(path_parts) == len(route_parts):
                match = True
                for i, part in enumerate(route_parts):
                    if "{" in part or path_parts[i] == part:
                        continue
                    else:
                        match = False
                        break
                
                if match:
                    return permission
    
    return {}


def example_permission_usage():
    """
    权限检查使用示例
    
    此函数展示了如何在不同场景中使用权限检查功能。
    """
    # 示例1：使用装饰器进行权限检查
    """
    @router.post("/api/resources", response_model=ResourceResponse)
    @requires_permission(resource="resource", action="create")
    async def create_resource(
        resource_data: ResourceCreate,
        request: Request,
        current_user: dict = Depends(get_current_user)
    ):
        # 函数实现...
        pass
    """
    
    # 示例2：使用依赖项进行权限检查
    """
    @router.get("/api/resources/{resource_id}", response_model=ResourceResponse)
    async def get_resource(
        resource_id: str,
        request: Request,
        current_user: dict = Depends(get_current_user),
        _: bool = Depends(permission_required("resource", "read"))
    ):
        # 函数实现...
        pass
    """
    
    # 示例3：在代码中手动检查权限
    """
    @router.put("/api/resources/{resource_id}", response_model=ResourceResponse)
    async def update_resource(
        resource_id: str,
        resource_data: ResourceUpdate,
        request: Request,
        current_user: dict = Depends(get_current_user)
    ):
        # 获取资源
        resource = await get_resource_by_id(resource_id)
        
        # 根据资源类型检查不同权限
        if resource.type == "public":
            # 公共资源只需要基本权限
            if not check_permission(request, "resource", "update"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足，无法更新公共资源"
                )
        elif resource.type == "sensitive":
            # 敏感资源需要更高级别权限
            if not check_permission(request, "sensitive_resource", "update"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足，无法更新敏感资源"
                )
        
        # 执行更新操作
        # ...
    """
    
    pass 