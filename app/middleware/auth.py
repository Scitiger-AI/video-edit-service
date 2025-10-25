from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..core.security import verify_token, verify_api_key
from ..core.logging import logger
from ..core.config import settings
from ..core.permissions import get_route_permission


async def extract_auth_info(request: Request) -> tuple[bool, dict, str]:
    """
    从请求中提取认证信息
    
    Args:
        request: 请求对象
        
    Returns:
        tuple: (is_authenticated, user_info, error_message)
    """
    # 记录请求路径
    logger.info(f"处理认证请求，路径: {request.url.path}")
    
    # 获取路由权限要求
    permission = get_route_permission(request.url.path)
    resource = permission.get("resource")
    action = permission.get("action")
    
    if resource and action:
        logger.info(f"从路由映射获取权限要求: resource={resource}, action={action}")
    
    # 从Authorization头获取
    auth_header = request.headers.get("Authorization", "")
    logger.info(f"Authorization头: {auth_header[:10] + '...' if auth_header else '无'}")
    
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2:
            scheme, token = parts
            scheme = scheme.lower()
            logger.info(f"认证方式: {scheme}")
            
            try:
                if scheme == "bearer":
                    # JWT令牌认证
                    logger.info(f"使用JWT令牌进行认证，权限检查: resource={resource}, action={action}")
                    user_info = await verify_token(token, service=settings.SERVICE_NAME, resource=resource, action=action)
                    return True, user_info, ""
                elif scheme == "apikey":
                    # API密钥认证
                    logger.info(f"使用API密钥进行认证，权限检查: resource={resource}, action={action}")
                    api_key_info = await verify_api_key(token, service=settings.SERVICE_NAME, resource=resource, action=action)
                    
                    # 根据key_type判断是系统级还是用户级API密钥
                    key_type = api_key_info.get("key_type", "")
                    tenant_id = api_key_info.get("tenant_id")
                    user_id = api_key_info.get("user_id")
                    
                    # 构建统一的用户信息结构
                    if key_type == "system":
                        user_info = {
                            "id": user_id,  # 可能为None
                            "tenant_id": tenant_id,
                            "is_system_key": True,
                            "is_user_key": False
                        }
                    else:
                        user_info = {
                            "id": user_id,
                            "tenant_id": tenant_id,  # 可能为None
                            "is_system_key": False,
                            "is_user_key": True
                        }
                    
                    logger.info(f"API密钥认证成功: key_type={key_type}, user_id={user_id}, tenant_id={tenant_id}")
                    return True, user_info, ""
            except HTTPException as e:
                logger.warning(f"认证异常: {e.detail}")
                return False, {}, e.detail
            except Exception as e:
                logger.error(f"认证过程中出现错误: {str(e)}")
                return False, {}, "Authentication failed"
        else:
            logger.warning(f"Authorization头格式不正确: {auth_header}")
    
    # 从X-Api-Key头获取
    api_key = request.headers.get("X-Api-Key")
    if api_key:
        logger.info(f"从X-Api-Key头获取认证信息，权限检查: resource={resource}, action={action}")
        try:
            api_key_info = await verify_api_key(api_key, service=settings.SERVICE_NAME, resource=resource, action=action)
            
            # 根据key_type判断是系统级还是用户级API密钥
            key_type = api_key_info.get("key_type", "")
            tenant_id = api_key_info.get("tenant_id")
            user_id = api_key_info.get("user_id")
            
            # 构建统一的用户信息结构
            if key_type == "system":
                user_info = {
                    "id": user_id,  # 可能为None
                    "tenant_id": tenant_id,
                    "is_system_key": True,
                    "is_user_key": False
                }
            else:
                user_info = {
                    "id": user_id,
                    "tenant_id": tenant_id,  # 可能为None
                    "is_system_key": False,
                    "is_user_key": True
                }
            
            logger.info(f"API密钥认证成功: key_type={key_type}, user_id={user_id}, tenant_id={tenant_id}")
            return True, user_info, ""
        except HTTPException as e:
            logger.warning(f"API密钥认证异常: {e.detail}")
            return False, {}, e.detail
        except Exception as e:
            logger.error(f"API密钥认证过程中出现错误: {str(e)}")
            return False, {}, "Authentication failed"
    
    logger.warning("请求中缺少认证信息")
    return False, {}, "Missing authentication credentials"


def should_skip_auth(request: Request) -> bool:
    """
    判断是否跳过认证和权限检查
    
    Args:
        request: 请求对象
        
    Returns:
        bool: 是否跳过认证
    """
    # 跳过OPTIONS请求和不需要认证的路径
    skip_paths = ["/docs", "/redoc", "/openapi.json",
                  f"{settings.API_V1_STR}/openapi.json",
                  f"{settings.API_V1_STR}/health",
                  f"{settings.API_V1_STR}/test",
                  f"{settings.API_V1_STR}/download", 
                #   f"{settings.API_V1_STR}/upload",
                  "/media"]  # 添加媒体文件路径
    
    # 使用前缀匹配而不是精确匹配
    if request.method == "OPTIONS":
        return True
    
    # 获取当前请求路径
    current_path = request.url.path.rstrip('/')  # 去除末尾的斜杠
    
    # 检查是否匹配任一跳过路径
    for skip_path in skip_paths:
        # 对比去除末尾斜杠后的路径或检查是否为前缀
        if current_path == skip_path.rstrip('/') or current_path.startswith(f"{skip_path}/"):
            return True
    
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件 - 负责验证用户身份和权限
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        # 记录请求路径
        logger.info(f"认证中间件处理请求，路径: {request.url.path}")
        
        # 跳过不需要认证的路径
        if should_skip_auth(request):
            logger.info(f"跳过认证，路径: {request.url.path}")
            return await call_next(request)
        
        # 如果禁用了认证，则跳过认证过程
        if not settings.ENABLE_AUTH:
            logger.info("认证已禁用，跳过认证过程")
            request.state.is_authenticated = True
            request.state.user = {"id": "system", "tenant_id": "system", "is_system_key": True}
            return await call_next(request)
        
        # 提取认证信息，传递权限参数
        is_authenticated, user_info, error = await extract_auth_info(request)
        
        # 认证失败直接返回401响应或403响应
        if not is_authenticated:
            # 判断是权限问题还是认证问题
            if "权限不足" in error or "没有所需的权限" in error:
                logger.warning(f"权限检查失败，错误: {error}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"success": False, "message": error}
                )
            else:
                logger.warning(f"认证失败，错误: {error}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"success": False, "message": error}
                )
        
        # 将认证结果附加到请求
        logger.info(f"认证成功，用户ID: {user_info.get('id')}")
        request.state.is_authenticated = is_authenticated
        request.state.user = user_info
        
        # 继续处理请求
        logger.info("继续处理请求")
        return await call_next(request)


class PermissionMiddleware(BaseHTTPMiddleware):
    """
    权限检查中间件 - 负责基础权限检查
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求的权限检查
        
        Args:
            request: 请求对象
            call_next: 下一个处理函数
            
        Returns:
            Response: 响应对象
        """
        logger.info(f"权限检查中间件处理请求，路径: {request.url.path}")
        # 跳过不需要权限检查的路径
        if should_skip_auth(request):
            return await call_next(request)
        
        # 如果禁用了认证，则跳过权限检查
        if not settings.ENABLE_AUTH:
            logger.info("认证已禁用，跳过权限检查")
            return await call_next(request)
        
        # 检查是否已经通过认证
        if not getattr(request.state, "is_authenticated", False):
            logger.warning(f"请求未通过认证，路径: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "message": "Authentication required"}
            )
        
        # 获取用户信息
        user_info = getattr(request.state, "user", {})
        
        # 获取路由级别设置的权限要求
        resource = getattr(request.state, "required_resource", None)
        action = getattr(request.state, "required_action", None)
        
        if resource and action:
            logger.info(f"PermissionMiddleware - 检测到权限要求: resource={resource}, action={action}")
            # 权限检查已经在AuthMiddleware中完成，这里只需要记录日志
            logger.info(f"PermissionMiddleware - 权限检查已通过: resource={resource}, action={action}")
        
        # 执行通用权限检查
        permission_result, error_message = self._check_common_permissions(user_info)
        if not permission_result:
            logger.error(f"权限检查失败: {error_message}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "message": error_message}
            )
        
        # 记录权限检查通过
        logger.info(f"权限检查通过，路径: {request.url.path}")
        
        # 继续处理请求
        return await call_next(request)
    
    def _check_common_permissions(self, user_info: dict) -> tuple[bool, str]:
        """
        执行通用权限检查
        
        Args:
            user_info: 用户信息
            
        Returns:
            tuple: (是否通过, 错误信息)
        """
        is_system_key = user_info.get("is_system_key", False)
        is_user_key = user_info.get("is_user_key", False)
        user_id = user_info.get("id")
        tenant_id = user_info.get("tenant_id")
        
        # 系统级API密钥权限检查
        if is_system_key:
            # 系统级API密钥必须有租户ID
            if not tenant_id:
                return False, "System API key must have tenant_id"
        
        # 用户级API密钥权限检查
        elif is_user_key:
            # 用户级API密钥必须有用户ID
            if not user_id:
                return False, "User API key must have user_id"
        
        # JWT令牌权限检查（需要同时有用户ID和租户ID）
        else:
            if not user_id or not tenant_id:
                return False, "Invalid user information"
        
        return True, "" 