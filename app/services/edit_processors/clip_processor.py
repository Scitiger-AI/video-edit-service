from typing import Dict, Any, List
import os
from pathlib import Path
from . import register_processor
from .base import EditProcessor
from ...core.logging import logger
from ...core.config import settings
from ...utils.video_utils import VideoUtils


@register_processor
class ClipProcessor(EditProcessor):
    """视频剪辑处理器"""
    
    @property
    def processor_name(self) -> str:
        return "clip"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "trim",       # 裁剪视频
            "split",      # 分割视频
            "merge",      # 合并视频
            "speed",      # 调整速度
            "reverse"     # 倒放
        ]
    
    async def validate_parameters(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证操作参数
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
        """
        if operation not in self.supported_operations:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # 根据不同操作类型验证参数
        if operation == "trim":
            # 验证裁剪参数
            if "start_time" not in parameters:
                parameters["start_time"] = 0
            if "end_time" not in parameters:
                raise ValueError("Missing required parameter: end_time")
            
            # 验证时间值
            if parameters["start_time"] < 0:
                raise ValueError("start_time must be greater than or equal to 0")
            if parameters["end_time"] <= parameters["start_time"]:
                raise ValueError("end_time must be greater than start_time")
                
            # 设置默认值
            if "copy_codec" not in parameters:
                # 默认不使用copy_codec，因为它可能导致精度问题
                parameters["copy_codec"] = False
            
            # 处理视频路径
            if "video_path" not in parameters:
                raise ValueError("Missing required parameter: video_path")
            
            # 视频路径处理将在process_video中进行，保留原始路径，以避免在这里进行异步调用
                
        elif operation == "split":
            # 验证分割参数
            if "split_points" not in parameters:
                raise ValueError("Missing required parameter: split_points")
            
            # 验证分割点列表
            if not isinstance(parameters["split_points"], list) or len(parameters["split_points"]) == 0:
                raise ValueError("split_points must be a non-empty list")
            
            # 验证分割点值
            for point in parameters["split_points"]:
                if not isinstance(point, (int, float)) or point <= 0:
                    raise ValueError("All split points must be positive numbers")
            
            # 设置默认值
            if "copy_codec" not in parameters:
                parameters["copy_codec"] = False
                
            # 验证视频路径
            if "video_path" not in parameters:
                raise ValueError("Missing required parameter: video_path")
                
        elif operation == "merge":
            # 验证合并参数
            if "video_paths" not in parameters:
                raise ValueError("Missing required parameter: video_paths")
            
            # 验证视频路径列表
            if not isinstance(parameters["video_paths"], list) or len(parameters["video_paths"]) < 2:
                raise ValueError("video_paths must be a list with at least 2 items")
            
            # 视频路径验证将在process_video中进行
            
            # 设置默认值
            if "transition" not in parameters:
                parameters["transition"] = None
                
        elif operation == "speed":
            # 验证速度参数
            if "speed_factor" not in parameters:
                raise ValueError("Missing required parameter: speed_factor")
            
            # 验证速度因子
            if not isinstance(parameters["speed_factor"], (int, float)) or parameters["speed_factor"] <= 0:
                raise ValueError("speed_factor must be a positive number")
            
            # 限制速度范围
            if parameters["speed_factor"] > 10:
                raise ValueError("speed_factor cannot exceed 10")
            if parameters["speed_factor"] < 0.1:
                raise ValueError("speed_factor cannot be less than 0.1")
            
            # 验证视频路径
            if "video_path" not in parameters:
                raise ValueError("Missing required parameter: video_path")
                
        elif operation == "reverse":
            # 验证倒放参数
            if "with_audio" not in parameters:
                parameters["with_audio"] = False
            
            # 验证视频路径
            if "video_path" not in parameters:
                raise ValueError("Missing required parameter: video_path")
        
        return parameters
    
    async def process_video(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        logger.info(f"Processing video with {operation} operation")
        
        # 处理视频路径
        if operation != "merge":
            # 对于除了merge之外的操作，处理单个视频路径
            if "video_path" in parameters:
                parameters["video_path"] = await self.process_video_path(parameters["video_path"])
                logger.info(f"已处理视频路径: {parameters['video_path']}")
        else:
            # 对于merge操作，处理多个视频路径
            if "video_paths" in parameters:
                parameters["video_paths"] = await self.process_file_paths(parameters["video_paths"], "video")
                logger.info(f"已处理视频路径列表: {parameters['video_paths']}")
        
        # 实现视频剪辑逻辑
        if operation == "trim":
            # 实现视频裁剪
            return await self._trim_video(parameters)
        elif operation == "split":
            # 实现视频分割
            return await self._split_video(parameters)
        elif operation == "merge":
            # 实现视频合并
            return await self._merge_videos(parameters)
        elif operation == "speed":
            # 实现视频速度调整
            return await self._adjust_speed(parameters)
        elif operation == "reverse":
            # 实现视频倒放
            return await self._reverse_video(parameters)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    async def _trim_video(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """裁剪视频"""
        start_time = parameters.get("start_time", 0)
        end_time = parameters["end_time"]
        video_path = parameters["video_path"]
        copy_codec = parameters.get("copy_codec", False)  # 默认不使用copy_codec
        
        logger.info(f"Trimming video {video_path} from {start_time}s to {end_time}s")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "trim")
        
        # 执行视频裁剪
        success = await VideoUtils.trim_video(
            input_path=video_path,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time,
            copy_codec=copy_codec
        )
        
        if not success:
            raise RuntimeError(f"Failed to trim video: {video_path}")
        
        # 获取视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video file is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "trim",
            "output_path": output_path,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _split_video(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """分割视频"""
        split_points = parameters["split_points"]
        video_path = parameters["video_path"]
        copy_codec = parameters.get("copy_codec", False)  # 默认不使用copy_codec
        
        logger.info(f"Splitting video {video_path} at points: {split_points}")
        
        # 创建输出目录
        output_dir = os.path.join(settings.DATA_DIR, "videos", f"split_{Path(video_path).stem}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 执行视频分割
        output_paths = await VideoUtils.split_video(
            input_path=video_path,
            output_dir=output_dir,
            split_points=split_points,
            copy_codec=copy_codec
        )
        
        if not output_paths:
            raise RuntimeError(f"Failed to split video: {video_path}")
        
        # 获取分段视频信息
        parts_info = []
        for i, path in enumerate(output_paths):
            video_info = await VideoUtils.get_video_info(path)
            
            # 检查视频是否有效
            if video_info["duration"] == 0 or not video_info["streams"]:
                raise RuntimeError(f"Generated video part is invalid: {path}")
                
            parts_info.append({
                "part_index": i,
                "path": path,
                "duration": video_info["duration"],
                "size": video_info["size"]
            })
        
        return {
            "status": "success",
            "operation": "split",
            "output_paths": output_paths,
            "parts_count": len(output_paths),
            "parts_info": parts_info,
            "total_parts": len(output_paths)
        }
    
    async def _merge_videos(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """合并视频"""
        video_paths = parameters["video_paths"]
        transition = parameters.get("transition")
        
        logger.info(f"Merging {len(video_paths)} videos")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "merge")
        
        # 执行视频合并
        success = await VideoUtils.merge_videos(
            input_paths=video_paths,
            output_path=output_path,
            transition=transition
        )
        
        if not success:
            raise RuntimeError("Failed to merge videos")
        
        # 获取合并后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated merged video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "merge",
            "output_path": output_path,
            "source_count": len(video_paths),
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _adjust_speed(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调整视频速度"""
        speed_factor = parameters["speed_factor"]
        video_path = parameters["video_path"]
        
        logger.info(f"Adjusting video {video_path} speed by factor {speed_factor}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "speed")
        
        # 执行视频速度调整
        success = await VideoUtils.adjust_speed(
            input_path=video_path,
            output_path=output_path,
            speed_factor=speed_factor
        )
        
        if not success:
            raise RuntimeError(f"Failed to adjust video speed: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated speed-adjusted video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "speed",
            "output_path": output_path,
            "speed_factor": speed_factor,
            "original_duration": parameters.get("original_duration"),
            "new_duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _reverse_video(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """视频倒放"""
        video_path = parameters["video_path"]
        with_audio = parameters.get("with_audio", False)
        
        logger.info(f"Reversing video {video_path} with audio: {with_audio}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "reverse")
        
        # 执行视频倒放
        success = await VideoUtils.reverse_video(
            input_path=video_path,
            output_path=output_path,
            with_audio=with_audio
        )
        
        if not success:
            raise RuntimeError(f"Failed to reverse video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated reversed video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "reverse",
            "output_path": output_path,
            "with_audio": with_audio,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        } 