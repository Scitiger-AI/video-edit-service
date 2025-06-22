from typing import Dict, Type
from .base import ModelProvider
from ...core.config import settings
from ...core.logging import logger

# 模型提供商注册表
_providers: Dict[str, Type[ModelProvider]] = {}


def register_provider(provider_class: Type[ModelProvider]) -> Type[ModelProvider]:
    """
    注册模型提供商
    
    Args:
        provider_class: 提供商类
        
    Returns:
        Type[ModelProvider]: 提供商类
    """
    provider_instance = provider_class()
    _providers[provider_instance.provider_name] = provider_class
    return provider_class


def get_provider(provider_name: str = None) -> ModelProvider:
    """
    获取模型提供商实例
    
    Args:
        provider_name: 提供商名称，为None时使用默认提供商
        
    Returns:
        ModelProvider: 提供商实例
        
    Raises:
        ValueError: 提供商不存在
    """
    if provider_name is None:
        provider_name = settings.DEFAULT_PROVIDER
    
    provider_class = _providers.get(provider_name)
    
    if provider_class is None:
        available_providers = ", ".join(_providers.keys())
        logger.error(f"Provider '{provider_name}' not found. Available providers: {available_providers}")
        raise ValueError(f"Provider '{provider_name}' not found")
    
    return provider_class()


def get_all_providers() -> Dict[str, ModelProvider]:
    """
    获取所有模型提供商实例
    
    Returns:
        Dict[str, ModelProvider]: 提供商实例字典
    """
    return {name: provider_class() for name, provider_class in _providers.items()}

# 导入所有提供商模块以触发注册
# from . import aliyun  # 阿里云视频提供商