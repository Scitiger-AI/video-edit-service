from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List
from pydantic import BaseModel
from ..core.security import get_current_user
from ..core.permissions import requires_permission
from ..services.model_providers import get_all_providers
from ..core.logging import logger
from ..utils.response import success_response, error_response

router = APIRouter()


class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    provider: str


class ModelsResponse(BaseModel):
    """模型列表响应"""
    success: bool
    message: str
    results: Dict[str, List[str]]


@router.get("/", response_model=ModelsResponse)
async def get_supported_models():
    """
    获取系统支持的所有模型列表，按提供商分组
    
    Returns:
        ModelsResponse: 模型列表响应
    """
    try:
        # 获取所有提供商实例
        providers = get_all_providers()
        
        # 按提供商分组模型
        models_by_provider = {}
        for provider_name, provider_instance in providers.items():
            models_by_provider[provider_name] = provider_instance.supported_models
            
        logger.info(f"获取支持的模型列表成功: {models_by_provider}")
        return success_response(data=models_by_provider, message="获取支持的模型列表成功")
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return error_response(message=f"获取模型列表失败: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/all", response_model=ModelsResponse)
async def get_all_models_flat():
    """
    获取系统支持的所有模型的平铺列表
    
    Returns:
        ModelsResponse: 模型列表响应
    """
    try:
        # 获取所有提供商实例
        providers = get_all_providers()
        
        # 收集所有模型
        all_models = []
        for provider_name, provider_instance in providers.items():
            all_models.extend(provider_instance.supported_models)
            
        logger.info(f"获取所有模型成功: {all_models}")
        return success_response(data={"models": all_models}, message="获取所有模型成功")
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return error_response(message=f"获取模型列表失败: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/by-provider/{provider_name}", response_model=ModelsResponse)
async def get_provider_models(provider_name: str):
    """
    获取指定提供商支持的模型列表
    
    Args:
        provider_name: 提供商名称
    
    Returns:
        ModelsResponse: 模型列表响应
    """
    try:
        # 获取所有提供商实例
        providers = get_all_providers()
        
        if provider_name not in providers:
            logger.warning(f"提供商 {provider_name} 不存在")
            available_providers = ", ".join(providers.keys())
            return error_response(
                message=f"Provider '{provider_name}' not found. Available providers: {available_providers}",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 获取指定提供商的模型
        provider_instance = providers[provider_name]
        models = provider_instance.supported_models
        
        logger.info(f"获取提供商 {provider_name} 的模型列表成功: {models}")
        return success_response(data={provider_name: models}, message=f"获取提供商 {provider_name} 的模型列表成功")
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return error_response(message=f"获取模型列表失败: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) 