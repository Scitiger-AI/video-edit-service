from typing import Dict, Any, List
import os
from . import register_processor
from .base import EditProcessor
from ...core.logging import logger
from ...core.config import settings
from ...utils.video_utils import VideoUtils


@register_processor
class TransitionProcessor(EditProcessor):
    """视频转场处理器"""
    
    @property
    def processor_name(self) -> str:
        return "transition"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "fade",          # 淡入淡出
            "dissolve",      # 溶解
            "wipe",          # 擦除
            "slide",         # 滑动
            "zoom",          # 缩放
            "rotate",        # 旋转
            "flash",         # 闪烁
            "crossfade"      # 交叉淡化
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
        
        # 所有转场效果都需要两个视频
        if "video1_path" not in parameters:
            raise ValueError("Missing required parameter: video1_path")
        if "video2_path" not in parameters:
            raise ValueError("Missing required parameter: video2_path")
            
        # 视频路径验证将在process_video中进行
        
        # 根据不同转场类型验证参数
        if operation in ["fade", "dissolve", "crossfade"]:
            # 验证淡化参数
            if "duration" not in parameters:
                parameters["duration"] = 1.0  # 默认1秒
            else:
                # 确保duration是数字
                try:
                    parameters["duration"] = float(parameters["duration"])
                except (ValueError, TypeError):
                    raise ValueError("Transition duration must be a number")
                    
            if parameters["duration"] <= 0:
                raise ValueError("Transition duration must be positive")
        elif operation == "wipe":
            # 验证擦除参数
            if "direction" not in parameters:
                parameters["direction"] = "left-to-right"
            if parameters["direction"] not in ["left-to-right", "right-to-left", "top-to-bottom", "bottom-to-top"]:
                raise ValueError("Invalid wipe direction")
                
            if "duration" not in parameters:
                parameters["duration"] = 1.0  # 默认1秒
            else:
                try:
                    parameters["duration"] = float(parameters["duration"])
                except (ValueError, TypeError):
                    raise ValueError("Transition duration must be a number")
        elif operation == "slide":
            # 验证滑动参数
            if "direction" not in parameters:
                parameters["direction"] = "left"
            if parameters["direction"] not in ["left", "right", "up", "down"]:
                raise ValueError("Invalid slide direction")
                
            if "duration" not in parameters:
                parameters["duration"] = 1.0  # 默认1秒
            else:
                try:
                    parameters["duration"] = float(parameters["duration"])
                except (ValueError, TypeError):
                    raise ValueError("Transition duration must be a number")
        elif operation in ["zoom", "rotate"]:
            # 验证缩放/旋转参数
            if "direction" not in parameters:
                parameters["direction"] = "in" if operation == "zoom" else "clockwise"
            
            if operation == "zoom" and parameters["direction"] not in ["in", "out"]:
                raise ValueError("Invalid zoom direction")
            if operation == "rotate" and parameters["direction"] not in ["clockwise", "counterclockwise"]:
                raise ValueError("Invalid rotation direction")
                
            if "duration" not in parameters:
                parameters["duration"] = 1.0  # 默认1秒
            else:
                try:
                    parameters["duration"] = float(parameters["duration"])
                except (ValueError, TypeError):
                    raise ValueError("Transition duration must be a number")
        elif operation == "flash":
            # 验证闪烁参数
            if "intensity" not in parameters:
                parameters["intensity"] = 1.0
            else:
                try:
                    parameters["intensity"] = float(parameters["intensity"])
                except (ValueError, TypeError):
                    raise ValueError("Flash intensity must be a number")
                    
            if not 0 < parameters["intensity"] <= 2.0:
                raise ValueError("Flash intensity must be between 0 and 2.0")
                
            if "duration" not in parameters:
                parameters["duration"] = 0.5  # 默认0.5秒
            else:
                try:
                    parameters["duration"] = float(parameters["duration"])
                except (ValueError, TypeError):
                    raise ValueError("Transition duration must be a number")
            
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
        logger.info(f"Applying {operation} transition between videos")
        
        # 处理视频路径
        if "video1_path" in parameters:
            parameters["video1_path"] = await self.process_video_path(parameters["video1_path"])
            logger.info(f"已处理第一个视频路径: {parameters['video1_path']}")
            
        if "video2_path" in parameters:
            parameters["video2_path"] = await self.process_video_path(parameters["video2_path"])
            logger.info(f"已处理第二个视频路径: {parameters['video2_path']}")
        
        # 实现视频转场逻辑
        if operation in ["fade", "dissolve", "crossfade"]:
            # 实现淡化转场
            return await self._apply_fade_transition(operation, parameters)
        elif operation == "wipe":
            # 实现擦除转场
            return await self._apply_wipe_transition(parameters)
        elif operation == "slide":
            # 实现滑动转场
            return await self._apply_slide_transition(parameters)
        elif operation == "zoom":
            # 实现缩放转场
            return await self._apply_zoom_transition(parameters)
        elif operation == "rotate":
            # 实现旋转转场
            return await self._apply_rotate_transition(parameters)
        elif operation == "flash":
            # 实现闪烁转场
            return await self._apply_flash_transition(parameters)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    async def _apply_fade_transition(self, fade_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用淡化类转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        duration = parameters.get("duration", 1.0)
        
        logger.info(f"Applying {fade_type} transition between {video1_path} and {video2_path} with duration {duration}s")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, fade_type)
        
        # 执行转场处理
        success = await VideoUtils.apply_fade_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            fade_type=fade_type,
            duration=duration
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply {fade_type} transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": fade_type,
            "output_path": output_path,
            "duration": duration,
            "video_info": video_info
        }
    
    async def _apply_wipe_transition(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用擦除转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        direction = parameters.get("direction", "left-to-right")
        duration = parameters.get("duration", 1.0)
        
        logger.info(f"Applying wipe transition from {video1_path} to {video2_path} in {direction} direction")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "wipe")
        
        # 执行转场处理
        success = await VideoUtils.apply_wipe_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            direction=direction,
            duration=duration
        )
        
        if not success:
            raise RuntimeError("Failed to apply wipe transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "wipe",
            "output_path": output_path,
            "direction": direction,
            "duration": duration,
            "video_info": video_info
        }
    
    async def _apply_slide_transition(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用滑动转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        direction = parameters.get("direction", "left")
        duration = parameters.get("duration", 1.0)
        
        logger.info(f"Applying slide transition from {video1_path} to {video2_path} in {direction} direction")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "slide")
        
        # 执行转场处理
        success = await VideoUtils.apply_slide_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            direction=direction,
            duration=duration
        )
        
        if not success:
            raise RuntimeError("Failed to apply slide transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "slide",
            "output_path": output_path,
            "direction": direction,
            "duration": duration,
            "video_info": video_info
        }
    
    async def _apply_zoom_transition(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用缩放转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        direction = parameters.get("direction", "in")
        duration = parameters.get("duration", 1.0)
        
        logger.info(f"Applying zoom-{direction} transition from {video1_path} to {video2_path}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "zoom")
        
        # 执行转场处理
        success = await VideoUtils.apply_zoom_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            direction=direction,
            duration=duration
        )
        
        if not success:
            raise RuntimeError("Failed to apply zoom transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "zoom",
            "output_path": output_path,
            "direction": direction,
            "duration": duration,
            "video_info": video_info
        }
    
    async def _apply_rotate_transition(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用旋转转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        direction = parameters.get("direction", "clockwise")
        duration = parameters.get("duration", 1.0)
        
        logger.info(f"Applying {direction} rotation transition from {video1_path} to {video2_path}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "rotate")
        
        # 执行转场处理
        success = await VideoUtils.apply_rotate_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            direction=direction,
            duration=duration
        )
        
        if not success:
            raise RuntimeError("Failed to apply rotate transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "rotate",
            "output_path": output_path,
            "direction": direction,
            "duration": duration,
            "video_info": video_info
        }
    
    async def _apply_flash_transition(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用闪烁转场"""
        video1_path = parameters["video1_path"]
        video2_path = parameters["video2_path"]
        intensity = parameters.get("intensity", 1.0)
        duration = parameters.get("duration", 0.5)
        
        logger.info(f"Applying flash transition from {video1_path} to {video2_path} with intensity {intensity}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "flash")
        
        # 执行转场处理
        success = await VideoUtils.apply_flash_transition(
            video1_path=video1_path,
            video2_path=video2_path,
            output_path=output_path,
            intensity=intensity,
            duration=duration
        )
        
        if not success:
            raise RuntimeError("Failed to apply flash transition")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "flash",
            "output_path": output_path,
            "intensity": intensity,
            "duration": duration,
            "video_info": video_info
        } 