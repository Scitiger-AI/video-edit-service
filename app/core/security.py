import httpx
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
from .config import settings
from .logging import logger

class BearerOrApiKeyAuth(HTTPBearer):
    """自定义认证类，支持Bearer令牌和ApiKey认证"""
    
    def __init__(self, auto_error: bool = True):
        super(BearerOrApiKeyAuth, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        重写__call__方法，支持ApiKey认证方案
        
        Args:
            request: 请求对象
            
        Returns:
            HTTPAuthorizationCredentials: 认证凭据
            
        Raises:
            HTTPException: 认证失败
        """
        # 如果禁用了认证，则返回模拟的凭证
        if not settings.ENABLE_AUTH:
            logger.info("BearerOrApiKeyAuth - 认证已禁用，返回模拟凭证")
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials="disabled_auth_token")
            
        # 首先尝试使用原始HTTPBearer的方法
        try:
            credentials = await super(BearerOrApiKeyAuth, self).__call__(request)
            logger.info(f"BearerOrApiKeyAuth - 使用标准HTTPBearer认证：{credentials.scheme}")
            return credentials
        except HTTPException as e:
            # 如果标准方法失败，尝试检查是否是ApiKey认证
            auth_header = request.headers.get("Authorization")
            logger.info(f"BearerOrApiKeyAuth - 标准认证失败，检查是否是ApiKey: {auth_header}")
            
            if auth_header and auth_header.startswith("ApiKey "):
                # 是ApiKey认证
                scheme, credentials = auth_header.split()
                logger.info(f"BearerOrApiKeyAuth - 检测到ApiKey认证方案")
                return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
            
            # 尝试X-Api-Key头
            api_key = request.headers.get("X-Api-Key")
            if api_key:
                logger.info(f"BearerOrApiKeyAuth - 检测到X-Api-Key头")
                return HTTPAuthorizationCredentials(scheme="ApiKey", credentials=api_key)
            
            # 如果都失败且auto_error为True，抛出原始异常
            if self.auto_error:
                logger.warning(f"BearerOrApiKeyAuth - 认证失败: {str(e)}")
                raise e
            
            return None

# 使用自定义的认证类
security = BearerOrApiKeyAuth()

async def verify_token(token: str, service: str = None, resource: str = None, action: str = None) -> dict:
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌
        service: 服务名称（可选）
        resource: 资源类型（可选）
        action: 操作类型（可选）
        
    Returns:
        dict: 用户信息
        
    Raises:
        HTTPException: 认证失败
    """
    # 如果禁用了认证，则直接返回模拟的用户信息
    if not settings.ENABLE_AUTH:
        logger.info("认证已禁用，跳过JWT令牌验证")
        return {
            "id": "system",
            "tenant_id": "system",
            "is_system_key": True,
            "is_user_key": False
        }
    
    try:
        # 准备请求数据
        data = {
            "token": token,
            "service": service or settings.SERVICE_NAME
        }
        
        # 添加权限检查参数
        if resource:
            data["resource"] = resource
        if action:
            data["action"] = action
        
        # 记录请求信息
        logger.info(f"验证令牌 - 请求URL: {settings.FULL_VERIFY_TOKEN_URL}")
        logger.info(f"验证令牌 - 请求数据: {data}")
        
        # 发送请求到认证服务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.FULL_VERIFY_TOKEN_URL,
                json=data,
                timeout=5.0
            )
        
        # 记录响应信息
        logger.info(f"验证令牌 - 响应状态码: {response.status_code}")
        logger.info(f"验证令牌 - 响应头: {dict(response.headers)}")
        
        try:
            response_text = response.text
            logger.info(f"验证令牌 - 响应内容: {response_text[:500]}")  # 限制日志长度
            result = response.json()
        except Exception as e:
            logger.error(f"验证令牌 - 解析响应JSON失败: {str(e)}, 响应内容: {response_text[:500]}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication response",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 解析响应
        if response.status_code == 200 and result.get("success"):
            # 令牌有效
            logger.info(f"验证令牌 - 成功: {result.get('results', {})}")
            return result.get("results", {})
        else:
            # 令牌无效
            message = result.get("message", "Unknown error")
            logger.warning(f"验证令牌 - 失败: {message}")
            
            # 区分权限错误和认证错误
            if resource and action and response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足: {message}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid authentication credentials: {message}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    
    except httpx.RequestError as e:
        # 请求异常
        logger.error(f"验证令牌 - 请求错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

async def verify_api_key(key: str, service: str = None, resource: str = None, action: str = None) -> dict:
    """
    验证API密钥
    
    Args:
        key: API密钥
        service: 服务名称（可选）
        resource: 资源类型（可选）
        action: 操作类型（可选）
        
    Returns:
        dict: API密钥信息
        
    Raises:
        HTTPException: 认证失败
    """
    # 如果禁用了认证，则直接返回模拟的API密钥信息
    if not settings.ENABLE_AUTH:
        logger.info("认证已禁用，跳过API密钥验证")
        return {
            "key_type": "system",
            "tenant_id": "system",
            "user_id": "system",
            "is_system_key": True,
            "is_user_key": False
        }
    
    try:
        # 准备请求数据
        data = {
            "key": key,
            "service": service or settings.SERVICE_NAME
        }
        
        # 添加权限检查参数
        if resource:
            data["resource"] = resource
        if action:
            data["action"] = action
        
        # 记录请求信息
        logger.info(f"验证API密钥 - 请求URL: {settings.FULL_VERIFY_API_KEY_URL}")
        logger.info(f"验证API密钥 - 请求数据: {data}")
        
        # 发送请求到认证服务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.FULL_VERIFY_API_KEY_URL,
                json=data,
                timeout=5.0
            )
        
        # 记录响应信息
        logger.info(f"验证API密钥 - 响应状态码: {response.status_code}")
        logger.info(f"验证API密钥 - 响应头: {dict(response.headers)}")
        
        try:
            response_text = response.text
            logger.info(f"验证API密钥 - 响应内容: {response_text[:500]}")  # 限制日志长度
            result = response.json()
        except Exception as e:
            logger.error(f"验证API密钥 - 解析响应JSON失败: {str(e)}, 响应内容: {response_text[:500]}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication response",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # 解析响应
        if response.status_code == 200 and result.get("success"):
            # API密钥有效
            logger.info(f"验证API密钥 - 成功: {result.get('results', {})}")
            return result.get("results", {})
        else:
            # API密钥无效
            message = result.get("message", "Unknown error")
            logger.warning(f"验证API密钥 - 失败: {message}")
            
            # 区分权限错误和认证错误
            if resource and action and response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足: {message}",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid authentication credentials: {message}",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
    
    except httpx.RequestError as e:
        # 请求异常
        logger.error(f"验证API密钥 - 请求错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    获取当前用户
    
    Args:
        request: 请求对象
        credentials: 认证凭据
        
    Returns:
        dict: 用户信息
        
    Raises:
        HTTPException: 认证失败
    """
    logger.info(f"get_current_user - 开始处理认证，URL路径: {request.url.path}")
    
    # 如果禁用了认证，则返回模拟的用户信息
    if not settings.ENABLE_AUTH:
        logger.info("get_current_user - 认证已禁用，返回模拟用户信息")
        return {
            "id": "system",
            "tenant_id": "system",
            "is_system_key": True,
            "is_user_key": False
        }
    
    # 检查是否已经由中间件完成认证
    if hasattr(request.state, "user") and request.state.user:
        logger.info(f"get_current_user - 使用中间件已认证的用户信息")
        return request.state.user
    
    # 如果中间件未完成认证，则进行后备认证
    logger.warning(f"get_current_user - 中间件未完成认证，执行后备认证")
    
    if not credentials:
        logger.error("get_current_user - 缺少认证凭据")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer or ApiKey"},
        )
    
    auth_type = credentials.scheme.lower()
    token = credentials.credentials
    
    logger.info(f"get_current_user - 使用{auth_type}方式进行认证")
    
    if auth_type == "bearer":
        # JWT令牌认证
        logger.info(f"get_current_user - 开始JWT令牌验证")
        user_info = await verify_token(token, service=settings.SERVICE_NAME)
        logger.info(f"get_current_user - JWT令牌验证成功")
        return user_info
    elif auth_type == "apikey":
        # API密钥认证
        logger.info(f"get_current_user - 开始API密钥验证")
        api_key_info = await verify_api_key(token, service=settings.SERVICE_NAME)
        logger.info(f"get_current_user - API密钥验证成功")
        
        # 从API密钥响应中获取关键信息
        key_type = api_key_info.get("key_type", "")
        tenant_id = api_key_info.get("tenant_id")
        user_id = api_key_info.get("user_id")
        
        # 构建用户信息
        if key_type == "system":
            # 系统级API密钥
            user_info = {
                "id": user_id,  # 可能为None
                "tenant_id": tenant_id,
                "is_system_key": True,
                "is_user_key": False
            }
        else:
            # 用户级API密钥
            user_info = {
                "id": user_id,
                "tenant_id": tenant_id,  # 可能为None
                "is_system_key": False,
                "is_user_key": True
            }
        
        return user_info
    else:
        # 不支持的认证类型
        logger.warning(f"get_current_user - 不支持的认证类型: {auth_type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authentication scheme",
            headers={"WWW-Authenticate": "Bearer or ApiKey"},
        )

async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    获取可选的当前用户（不抛出异常）
    
    Args:
        request: 请求对象
        credentials: 认证凭据
        
    Returns:
        dict: 用户信息，认证失败时返回空字典
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return {} 