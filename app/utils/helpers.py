import os
import aiohttp
import asyncio
import shutil
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
from ..core.config import settings
from ..core.logging import logger


class FileUtils:
    """文件处理工具类"""
    
    # 临时文件目录
    TEMP_DIR = Path(settings.DATA_DIR) / "temp"
    
    # 已下载文件缓存，格式为 {url: {"path": local_path, "timestamp": download_time}}
    _download_cache = {}
    
    # 缓存过期时间（小时）
    CACHE_EXPIRY_HOURS = 24
    
    @classmethod
    async def setup(cls):
        """初始化临时目录"""
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        # 清理过期的临时文件
        await cls.cleanup_expired_files()
    
    @classmethod
    async def process_file_path(
        cls, 
        path: str, 
        allowed_extensions: List[str] = None,
        file_type: str = "video",
        max_size_mb: int = 500
    ) -> str:
        """
        处理文件路径，支持URL和本地路径
        
        Args:
            path: 文件路径或URL
            allowed_extensions: 允许的文件扩展名列表
            file_type: 文件类型（用于日志和错误消息）
            max_size_mb: 最大文件大小（MB）
            
        Returns:
            str: 处理后的本地文件路径
        """
        if not path:
            raise ValueError(f"文件路径不能为空")
            
        if cls.is_url(path):
            logger.info(f"检测到{file_type}URL: {path}")
            return await cls.download_file(path, allowed_extensions, file_type, max_size_mb)
        elif os.path.isabs(path):
            logger.info(f"检测到绝对路径: {path}")
            if not os.path.exists(path):
                raise FileNotFoundError(f"文件不存在: {path}")
            if allowed_extensions and not cls.has_valid_extension(path, allowed_extensions):
                raise ValueError(f"不支持的{file_type}文件类型: {path}")
            return path
        else:
            # 处理相对路径
            abs_path = os.path.abspath(path)
            logger.info(f"将相对路径 {path} 转换为绝对路径: {abs_path}")
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"文件不存在: {abs_path}")
            if allowed_extensions and not cls.has_valid_extension(abs_path, allowed_extensions):
                raise ValueError(f"不支持的{file_type}文件类型: {abs_path}")
            return abs_path
    
    @staticmethod
    def is_url(path: str) -> bool:
        """判断是否为URL"""
        try:
            result = urlparse(path)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
            
    @staticmethod
    def has_valid_extension(path: str, allowed_extensions: List[str]) -> bool:
        """检查文件是否有有效的扩展名"""
        ext = os.path.splitext(path)[1].lower()
        return ext in allowed_extensions
    
    @classmethod
    async def download_file(
        cls, 
        url: str, 
        allowed_extensions: List[str] = None,
        file_type: str = "video",
        max_size_mb: int = 500
    ) -> str:
        """
        下载文件并返回本地路径
        
        Args:
            url: 文件URL
            allowed_extensions: 允许的文件扩展名列表
            file_type: 文件类型（用于日志）
            max_size_mb: 最大文件大小（MB）
            
        Returns:
            str: 本地文件路径
        """
        # 确保临时目录存在
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        # 检查缓存
        now = datetime.now()
        if url in cls._download_cache:
            cache_info = cls._download_cache[url]
            cache_time = cache_info["timestamp"]
            cache_path = cache_info["path"]
            
            # 检查缓存是否过期
            if (now - cache_time).total_seconds() < cls.CACHE_EXPIRY_HOURS * 3600 and os.path.exists(cache_path):
                logger.info(f"使用缓存的{file_type}文件: {url} -> {cache_path}")
                return cache_path
                
        # 生成唯一的临时文件名
        filename = f"{uuid.uuid4().hex}"
        extension = cls.get_extension_from_url(url)
        if extension:
            filename += extension
        
        temp_path = cls.TEMP_DIR / filename
        
        # 下载文件
        try:
            logger.info(f"开始下载{file_type}文件: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"下载失败，HTTP状态码: {response.status}")
                    
                    # 检查文件大小
                    content_length = response.content_length
                    if content_length and content_length > max_size_mb * 1024 * 1024:
                        raise ValueError(f"{file_type}文件过大，超过{max_size_mb}MB限制")
                    
                    # 检查文件类型
                    content_type = response.headers.get('Content-Type', '')
                    if file_type == "video" and not content_type.startswith('video/'):
                        if not cls.is_likely_video_from_url(url):
                            logger.warning(f"可能不是视频文件: {url}, Content-Type: {content_type}")
                            # 不阻塞流程，继续下载
                    
                    # 下载文件到临时路径
                    with open(temp_path, 'wb') as f:
                        total_downloaded = 0
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            if max_size_mb > 0 and total_downloaded > max_size_mb * 1024 * 1024:
                                raise ValueError(f"{file_type}文件过大，超过{max_size_mb}MB限制")
            
            logger.info(f"{file_type}文件下载完成: {url} -> {temp_path}")
            
            # 检查文件格式
            if allowed_extensions and not cls.has_valid_extension(str(temp_path), allowed_extensions):
                # 如果没有有效扩展名，尝试检测文件类型并添加扩展名
                detected_ext = await cls.detect_file_type(temp_path)
                if detected_ext and detected_ext in allowed_extensions:
                    new_path = Path(str(temp_path) + detected_ext)
                    shutil.move(temp_path, new_path)
                    temp_path = new_path
                    logger.info(f"添加检测到的扩展名: {detected_ext}")
                else:
                    os.remove(temp_path)
                    raise ValueError(f"下载的{file_type}文件格式不受支持")
            
            # 将下载的文件添加到缓存
            cls._download_cache[url] = {
                "path": str(temp_path),
                "timestamp": datetime.now()
            }
            
            return str(temp_path)
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"下载{file_type}文件失败: {url}, 错误: {str(e)}")
            raise RuntimeError(f"下载{file_type}文件失败: {str(e)}")
    
    @staticmethod
    def get_extension_from_url(url: str) -> str:
        """从URL中提取文件扩展名"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        extension = os.path.splitext(path)[1].lower()
        return extension if extension else ""
    
    @staticmethod
    def is_likely_video_from_url(url: str) -> bool:
        """根据URL判断是否可能是视频文件"""
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']
        extension = FileUtils.get_extension_from_url(url)
        return extension in video_extensions
    
    @staticmethod
    async def detect_file_type(file_path: str) -> Optional[str]:
        """检测文件类型并返回相应的扩展名"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                if mime_type.startswith('video/'):
                    ext = mimetypes.guess_extension(mime_type)
                    return ext if ext else ".mp4"  # 默认使用.mp4
                elif mime_type.startswith('audio/'):
                    ext = mimetypes.guess_extension(mime_type)
                    return ext if ext else ".mp3"  # 默认使用.mp3
            return None
        except:
            return None
    
    @classmethod
    async def cleanup_expired_files(cls):
        """清理过期的临时文件"""
        try:
            # 清理过期的缓存条目
            now = datetime.now()
            expired_urls = []
            
            for url, cache_info in cls._download_cache.items():
                cache_time = cache_info["timestamp"]
                if (now - cache_time).total_seconds() > cls.CACHE_EXPIRY_HOURS * 3600:
                    expired_urls.append(url)
                    # 尝试删除文件
                    try:
                        os.remove(cache_info["path"])
                        logger.info(f"删除过期的临时文件: {cache_info['path']}")
                    except:
                        pass
            
            # 从缓存中移除过期条目
            for url in expired_urls:
                del cls._download_cache[url]
            
            # 清理临时目录中的孤立文件（不在缓存中的文件）
            if os.path.exists(cls.TEMP_DIR):
                cached_paths = {info["path"] for info in cls._download_cache.values()}
                for file_path in os.listdir(cls.TEMP_DIR):
                    full_path = os.path.join(cls.TEMP_DIR, file_path)
                    if os.path.isfile(full_path) and full_path not in cached_paths:
                        # 检查文件是否过期
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                        if (now - file_mtime).total_seconds() > cls.CACHE_EXPIRY_HOURS * 3600:
                            try:
                                os.remove(full_path)
                                logger.info(f"删除孤立的临时文件: {full_path}")
                            except:
                                pass
        except Exception as e:
            logger.error(f"清理临时文件时出错: {str(e)}")
            
    @classmethod
    def convert_path_to_urls(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将任务结果中的文件路径转换为URL
        
        Args:
            result: 任务结果字典
            
        Returns:
            Dict[str, Any]: 转换后的任务结果字典
        """
        if not result:
            return result
            
        # 创建结果的深拷贝，避免修改原始结果
        import copy
        result_copy = copy.deepcopy(result)
        
        # 处理output_path字段
        if "output_path" in result_copy:
            file_path = result_copy.pop("output_path")  # 移除原始路径
            
            # 添加相对URL和下载URL
            relative_url, download_url, url = cls.get_urls_from_path(file_path)
            result_copy["file_url"] = relative_url
            result_copy["url"] = url
            result_copy["download_url"] = download_url
            
        # 处理output_paths字段（如果存在）
        if "output_paths" in result_copy and isinstance(result_copy["output_paths"], list):
            file_urls = []
            download_urls = []
            
            for file_path in result_copy["output_paths"]:
                relative_url, download_url, url = cls.get_urls_from_path(file_path)
                file_urls.append(relative_url)
                file_urls.append(url)
                download_urls.append(download_url)
                
            result_copy["file_urls"] = file_urls
            result_copy["download_urls"] = download_urls
            
            # 根据情况决定是否删除原始路径
            # 在本实现中，我们保留原始路径，因为它可能在内部使用
            # result_copy.pop("output_paths")
            
        # 处理嵌套的parts_info字段（如果存在）
        if "parts_info" in result_copy and isinstance(result_copy["parts_info"], list):
            for part in result_copy["parts_info"]:
                if "path" in part:
                    file_path = part["path"]
                    relative_url, download_url, url = cls.get_urls_from_path(file_path)
                    part["file_url"] = relative_url
                    part["url"] = url
                    part["download_url"] = download_url
                    # 保留原始路径
        
        return result_copy
    
    @classmethod
    def get_urls_from_path(cls, file_path: str) -> Tuple[str, str]:
        """
        从文件路径生成相对URL和下载URL
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[str, str]: (相对URL, 下载URL)
        """
        if not file_path:
            return "", ""
            
        # 如果已经是URL，直接返回
        if cls.is_url(file_path):
            return file_path, file_path
            
        try:
            # 转换为Path对象，便于路径操作
            path = Path(file_path)
            
            # 尝试获取相对于DATA_DIR的路径
            data_dir = Path(settings.DATA_DIR)
            try:
                # 计算相对路径
                relative_path = path.relative_to(data_dir)
                relative_url = str(relative_path).replace("\\", "/")
            except ValueError:
                # 如果不在DATA_DIR内，使用文件名
                relative_url = path.name
                
            # 创建下载URL
            file_name = path.name
            encoded_name = quote(file_name)
            download_url = f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{encoded_name}"
            media_base_path = f"{settings.MEDIA_BASE_PATH}/{relative_url}"
            return media_base_path, download_url, f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{media_base_path}"
            
        except Exception as e:
            logger.error(f"转换文件路径到URL时出错: {str(e)}")
            # 出错时返回文件名
            file_name = os.path.basename(file_path)
            media_base_path = f"{settings.MEDIA_BASE_PATH}/{file_name}"
            return media_base_path, f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{file_name}", f"{settings.MEDIA_DOWNLOAD_BASE_URL}/{media_base_path}"
