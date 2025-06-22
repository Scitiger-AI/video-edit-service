from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
import os

from ...utils.helpers import FileUtils


class EditProcessor(ABC):
    """视频编辑处理器基类"""
    
    # 支持的视频文件扩展名
    SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']
    
    # 支持的音频文件扩展名
    SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.aac', '.ogg', '.flac']
    
    @property
    @abstractmethod
    def processor_name(self) -> str:
        """处理器名称"""
        pass
    
    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        """支持的操作列表"""
        pass
    
    @abstractmethod
    async def process_video(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        pass
    
    @abstractmethod
    async def validate_parameters(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证操作参数
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
        """
        pass
        
    async def process_video_path(self, path: str) -> str:
        """
        处理视频文件路径，支持URL和本地路径
        
        Args:
            path: 视频文件路径或URL
            
        Returns:
            str: 处理后的本地文件路径
        """
        return await FileUtils.process_file_path(
            path=path,
            allowed_extensions=self.SUPPORTED_VIDEO_EXTENSIONS,
            file_type="video"
        )
        
    async def process_audio_path(self, path: str) -> str:
        """
        处理音频文件路径，支持URL和本地路径
        
        Args:
            path: 音频文件路径或URL
            
        Returns:
            str: 处理后的本地文件路径
        """
        return await FileUtils.process_file_path(
            path=path,
            allowed_extensions=self.SUPPORTED_AUDIO_EXTENSIONS,
            file_type="audio"
        )
        
    async def process_file_paths(self, paths: List[str], file_type: str = "video") -> List[str]:
        """
        处理多个文件路径，支持URL和本地路径
        
        Args:
            paths: 文件路径或URL列表
            file_type: 文件类型，"video"或"audio"
            
        Returns:
            List[str]: 处理后的本地文件路径列表
        """
        processed_paths = []
        for path in paths:
            if file_type == "video":
                processed_path = await self.process_video_path(path)
            else:
                processed_path = await self.process_audio_path(path)
            processed_paths.append(processed_path)
        return processed_paths 