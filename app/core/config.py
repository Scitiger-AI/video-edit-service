"""
配置文件
如果在 .env 文件中配置了相同的变量名, 则以 .env 文件中的配置为准
"""

import os
from typing import Annotated, Dict, List
from urllib.parse import quote_plus
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类，使用Pydantic V2语法"""
    
    # 应用信息
    APP_NAME: str = "video-edit-service"
    API_V1_STR: str = "/api"
    
    # 服务基础URL配置
    SERVICE_BASE_URL: str = "http://service.scitiger.cn/video-edit-service"
    MEDIA_BASE_PATH: str = "/media"
    
    # MongoDB配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "video_edit_service"
    MONGODB_USER: str = ""
    MONGODB_PASSWORD: str = ""
    MONGODB_AUTH_DB_NAME: str = "admin"
    
    # Redis配置（用于Celery）
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery配置
    CELERY_BROKER_URL: Annotated[str, Field(default="")] 
    CELERY_RESULT_BACKEND: Annotated[str, Field(default="")]
    
    # SciTigerCore认证服务配置
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    VERIFY_TOKEN_URL: str = "/api/platform/auth/microservice/verify-token/"
    VERIFY_API_KEY_URL: str = "/api/platform/auth/microservice/verify-api-key/"
    
    # 服务名称（用于权限检查）
    SERVICE_NAME: str = "video-edit-service"
    
    # 是否启用认证
    ENABLE_AUTH: bool = True
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    # 视频处理器配置
    DEFAULT_OPERATION: str = "trim"
    DEFAULT_PROCESSOR: str = "clip"
    
    # 数据目录
    DATA_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    
    # 任务配置
    TASK_TIME_LIMIT: int = 3600  # 任务超时时间（秒）
    
    # 处理器支持的操作列表（可在.env中配置）
    CLIP_SUPPORTED_OPERATIONS: str = "trim,split,merge,speed,reverse"
    FILTER_SUPPORTED_OPERATIONS: str = "brightness,contrast,saturation,blur,sharpen,grayscale,sepia,vignette"
    TRANSITION_SUPPORTED_OPERATIONS: str = "fade,dissolve,wipe,slide,zoom,rotate,flash,crossfade"
    AUTO_SUPPORTED_OPERATIONS: str = "music_edit,smart_edit,highlight_edit"
    
    # FFmpeg配置
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    @computed_field
    @property
    def FULL_VERIFY_TOKEN_URL(self) -> str:
        """获取完整的令牌验证URL"""
        return f"{self.AUTH_SERVICE_URL}{self.VERIFY_TOKEN_URL}"
    
    @computed_field
    @property
    def FULL_VERIFY_API_KEY_URL(self) -> str:
        """获取完整的API密钥验证URL"""
        return f"{self.AUTH_SERVICE_URL}{self.VERIFY_API_KEY_URL}"
    
    @computed_field
    @property
    def MEDIA_BASE_URL(self) -> str:
        """获取媒体文件的基础URL"""
        return f"{self.SERVICE_BASE_URL}{self.MEDIA_BASE_PATH}"
        
    @computed_field
    @property
    def MEDIA_DOWNLOAD_BASE_URL(self) -> str:
        """获取媒体文件下载的基础URL"""
        return f"{self.SERVICE_BASE_URL}{self.API_V1_STR}/download"
    
    @computed_field
    @property
    def MONGODB_CONNECTION_STRING(self) -> str:
        """获取MongoDB连接字符串"""
        if self.MONGODB_USER and self.MONGODB_PASSWORD:
            # 如果设置了用户名和密码，使用认证连接字符串
            # 对用户名和密码进行URL编码
            encoded_user = quote_plus(self.MONGODB_USER)
            encoded_password = quote_plus(self.MONGODB_PASSWORD)
            host = self.MONGODB_URL.replace('mongodb://', '')
            return f"mongodb://{encoded_user}:{encoded_password}@{host}/{self.MONGODB_AUTH_DB_NAME}"
        else:
            # 否则使用无认证连接字符串
            return self.MONGODB_URL
            
    @computed_field
    @property
    def PROCESSOR_SUPPORTED_OPERATIONS(self) -> Dict[str, List[str]]:
        """获取各处理器支持的操作列表，将逗号分隔的字符串转换为列表"""
        return {
            "clip": [operation.strip() for operation in self.CLIP_SUPPORTED_OPERATIONS.split(",")],
            "filter": [operation.strip() for operation in self.FILTER_SUPPORTED_OPERATIONS.split(",")],
            "transition": [operation.strip() for operation in self.TRANSITION_SUPPORTED_OPERATIONS.split(",")],
            "auto": [operation.strip() for operation in self.AUTO_SUPPORTED_OPERATIONS.split(",")]
        }
    
    def __init__(self, **data):
        super().__init__(**data)
        # 如果未设置Celery URL，则使用Redis URL
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            # 使用 MongoDB 作为结果后端
            # 正确的格式：mongodb://[username:password@]host:port
            self.CELERY_RESULT_BACKEND = f"mongodb://{self.MONGODB_CONNECTION_STRING.replace('mongodb://', '')}"


# 创建全局设置对象
settings = Settings() 