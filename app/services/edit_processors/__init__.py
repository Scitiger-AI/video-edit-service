from typing import Dict, Type
from .base import EditProcessor
from ...core.config import settings
from ...core.logging import logger

# 视频处理器注册表
_processors: Dict[str, Type[EditProcessor]] = {}


def register_processor(processor_class: Type[EditProcessor]) -> Type[EditProcessor]:
    """
    注册视频处理器
    
    Args:
        processor_class: 处理器类
        
    Returns:
        Type[EditProcessor]: 处理器类
    """
    processor_instance = processor_class()
    _processors[processor_instance.processor_name] = processor_class
    return processor_class


def get_processor(processor_name: str = None) -> EditProcessor:
    """
    获取视频处理器实例
    
    Args:
        processor_name: 处理器名称，为None时使用默认处理器
        
    Returns:
        EditProcessor: 处理器实例
        
    Raises:
        ValueError: 处理器不存在
    """
    if processor_name is None:
        processor_name = settings.DEFAULT_PROCESSOR
    
    processor_class = _processors.get(processor_name)
    
    if processor_class is None:
        available_processors = ", ".join(_processors.keys())
        logger.error(f"Processor '{processor_name}' not found. Available processors: {available_processors}")
        raise ValueError(f"Processor '{processor_name}' not found")
    
    return processor_class()


def get_all_processors() -> Dict[str, EditProcessor]:
    """
    获取所有视频处理器实例
    
    Returns:
        Dict[str, EditProcessor]: 处理器实例字典
    """
    return {name: processor_class() for name, processor_class in _processors.items()}

# 导入所有处理器模块以触发注册
from . import clip_processor  # 视频剪辑处理器
from . import filter_processor  # 视频滤镜处理器
from . import transition_processor  # 视频转场处理器
from . import auto_processor  # 自动剪辑处理器 