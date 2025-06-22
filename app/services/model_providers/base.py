from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ModelProvider(ABC):
    """模型提供商基类"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass
    
    @abstractmethod
    async def call_model(self, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用模型
        
        Args:
            model: 模型名称
            parameters: 模型参数
            
        Returns:
            Dict[str, Any]: 模型调用结果
        """
        pass
    
    @abstractmethod
    async def validate_parameters(self, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证模型参数
        
        Args:
            model: 模型名称
            parameters: 模型参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
        """
        pass 